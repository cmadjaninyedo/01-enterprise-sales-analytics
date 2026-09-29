"""
ETL de chargement du Superstore Dataset vers le schéma en étoile PostgreSQL.

Caractéristiques :
- Idempotent : TRUNCATE des tables (ordre FK-safe) avant chargement, donc
  relancer le script plusieurs fois ne duplique jamais les données.
- Transactionnel : tout le chargement (truncate + inserts) est fait dans une
  seule transaction SQLAlchemy ; en cas d'erreur, rien n'est appliqué
  (rollback automatique).
- Contrôles qualité post-chargement : volumétrie, clés primaires dupliquées,
  clés étrangères orphelines, valeurs métier incohérentes (quantity <= 0,
  sales_amount < 0).

Usage :
    python etl/load_data.py
"""
import logging
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from db_connection import get_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("load_data")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "processed" / "superstore_clean.csv"

# Ordre de troncature : la table de faits d'abord (FK vers les dimensions),
# puis les dimensions. RESTART IDENTITY remet les SERIAL à 1, CASCADE
# nettoie toute dépendance éventuelle.
TABLES_TRUNCATE_ORDER = [
    "fact_sales",
    "dim_date",
    "dim_customer",
    "dim_product",
    "dim_region",
]


def extract() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Fichier source introuvable : {DATA_PATH}\n"
            "Vérifiez que data/processed/superstore_clean.csv est bien présent."
        )
    df = pd.read_csv(DATA_PATH, dtype={"Postal Code": str})
    log.info("Extraction : %d lignes lues depuis %s", len(df), DATA_PATH.name)

    # Contrôle qualité pré-chargement : colonnes clés jamais nulles
    required_cols = ["Order ID", "Order Date", "Customer ID", "Product ID", "Region", "Sales", "Quantity"]
    nulls = df[required_cols].isna().sum()
    nulls = nulls[nulls > 0]
    if not nulls.empty:
        raise ValueError(
            f"Valeurs manquantes détectées dans des colonnes clés avant chargement :\n{nulls}"
        )
    return df


def build_dimensions(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    dates = pd.to_datetime(df["Order Date"]).drop_duplicates().reset_index(drop=True)
    dim_date = pd.DataFrame({
        "full_date": dates,
        "year": dates.dt.year,
        "quarter": dates.dt.quarter,
        "month": dates.dt.month,
        "month_name": dates.dt.month_name(),
        "day": dates.dt.day,
        "day_of_week": dates.dt.day_name(),
        "is_weekend": dates.dt.dayofweek >= 5,
    })

    dim_customer = (
        df[["Customer ID", "Customer Name", "Segment"]]
        .drop_duplicates()
        .rename(columns={
            "Customer ID": "customer_id",
            "Customer Name": "customer_name",
            "Segment": "segment",
        })
    )

    # Anomalie connue du Superstore Dataset : 32 Product ID associés à
    # plusieurs Product Name distincts. Décision assumée : conserver la
    # première occurrence rencontrée (voir docs/dictionnaire_donnees.md).
    dim_product = (
        df[["Product ID", "Product Name", "Category", "Sub-Category"]]
        .drop_duplicates(subset="Product ID", keep="first")
        .rename(columns={
            "Product ID": "product_id",
            "Product Name": "product_name",
            "Category": "category",
            "Sub-Category": "sub_category",
        })
    )

    dim_region = (
        df[["Region", "State", "City", "Postal Code", "Country"]]
        .drop_duplicates()
        .reset_index(drop=True)
        .rename(columns={
            "Region": "region", "State": "state", "City": "city",
            "Postal Code": "postal_code", "Country": "country",
        })
    )

    # Contrôle qualité : pas de doublon sur la clé métier de chaque dimension
    for name, frame, key in [
        ("dim_customer", dim_customer, "customer_id"),
        ("dim_product", dim_product, "product_id"),
    ]:
        dup = frame[frame.duplicated(subset=key, keep=False)]
        if not dup.empty:
            raise ValueError(f"{name} : {len(dup)} lignes en doublon sur la clé {key}")

    return {
        "dim_date": dim_date,
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_region": dim_region,
    }


def build_fact(df: pd.DataFrame, conn) -> pd.DataFrame:
    dim_date_db = pd.read_sql("SELECT date_id, full_date FROM dim_date", conn)
    dim_region_db = pd.read_sql(
        "SELECT region_id, region, state, city, postal_code FROM dim_region", conn
    )

    df = df.copy()
    df["Order Date"] = pd.to_datetime(df["Order Date"]).dt.normalize()
    dim_date_db["full_date"] = pd.to_datetime(dim_date_db["full_date"]).dt.normalize()

    fact = df.merge(dim_date_db, left_on="Order Date", right_on="full_date", how="left")
    fact = fact.merge(
        dim_region_db,
        left_on=["Region", "State", "City", "Postal Code"],
        right_on=["region", "state", "city", "postal_code"],
        how="left",
    )

    # Contrôle qualité : toute ligne source doit trouver sa date_id et sa
    # region_id (jointure "left" volontaire, pour détecter et signaler les
    # orphelins plutôt que les faire disparaître silencieusement comme le
    # ferait une jointure "inner").
    orphans = fact[fact["date_id"].isna() | fact["region_id"].isna()]
    if not orphans.empty:
        raise ValueError(
            f"{len(orphans)} ligne(s) source sans correspondance dans dim_date/dim_region — "
            "chargement interrompu, aucune ligne insérée."
        )

    fact_sales = fact[[
        "Order ID", "date_id", "Customer ID", "Product ID", "region_id",
        "Ship Mode", "Sales", "Quantity", "Discount", "Profit"
    ]].rename(columns={
        "Order ID": "order_id", "Customer ID": "customer_id",
        "Product ID": "product_id", "Ship Mode": "ship_mode",
        "Sales": "sales_amount", "Quantity": "quantity",
        "Discount": "discount", "Profit": "profit",
    })
    fact_sales["date_id"] = fact_sales["date_id"].astype(int)
    fact_sales["region_id"] = fact_sales["region_id"].astype(int)

    # Contrôle qualité métier : pas de quantité négative ou nulle, pas de CA négatif
    bad_qty = fact_sales[fact_sales["quantity"] <= 0]
    bad_sales = fact_sales[fact_sales["sales_amount"] < 0]
    if not bad_qty.empty or not bad_sales.empty:
        raise ValueError(
            f"Valeurs métier incohérentes : {len(bad_qty)} ligne(s) quantity <= 0, "
            f"{len(bad_sales)} ligne(s) sales_amount < 0."
        )

    return fact_sales


def run_post_load_quality_checks(conn, source_row_count: int) -> None:
    """Contrôles qualité exécutés une fois toutes les tables chargées."""
    checks_passed = []

    # 1. Volumétrie : fact_sales doit correspondre exactement au fichier source
    n_fact = conn.execute(text("SELECT COUNT(*) FROM fact_sales")).scalar()
    if n_fact != source_row_count:
        raise ValueError(
            f"Volumétrie incohérente : {n_fact} lignes dans fact_sales, "
            f"{source_row_count} attendues (source)."
        )
    checks_passed.append(f"Volumétrie fact_sales : {n_fact} lignes (= source)")

    # 2. Clés primaires uniques sur les dimensions (garanti par la contrainte
    #    PK PostgreSQL, mais on le revérifie explicitement pour la traçabilité)
    for table, key in [("dim_customer", "customer_id"), ("dim_product", "product_id"),
                        ("dim_region", "region_id"), ("dim_date", "date_id")]:
        dup = conn.execute(text(
            f"SELECT COUNT(*) FROM (SELECT {key} FROM {table} GROUP BY {key} HAVING COUNT(*) > 1) t"
        )).scalar()
        if dup > 0:
            raise ValueError(f"{table} : {dup} clé(s) primaire(s) {key} dupliquée(s)")
    checks_passed.append("Clés primaires : aucune duplication sur les 4 dimensions")

    # 3. Clés étrangères orphelines dans fact_sales
    orphan_checks = {
        "date_id": "dim_date",
        "customer_id": "dim_customer",
        "product_id": "dim_product",
        "region_id": "dim_region",
    }
    for fk, dim_table in orphan_checks.items():
        pk = "date_id" if dim_table == "dim_date" else fk
        n_orphans = conn.execute(text(
            f"SELECT COUNT(*) FROM fact_sales f "
            f"LEFT JOIN {dim_table} d ON f.{fk} = d.{pk} WHERE d.{pk} IS NULL"
        )).scalar()
        if n_orphans > 0:
            raise ValueError(f"fact_sales : {n_orphans} ligne(s) orpheline(s) sur {fk} -> {dim_table}")
    checks_passed.append("Clés étrangères : aucune ligne orpheline dans fact_sales")

    # 4. Cohérence CA Python vs SQL (arrondi float64 vs NUMERIC attendu, écart marginal)
    ca_sql = conn.execute(text("SELECT ROUND(SUM(sales_amount), 2) FROM fact_sales")).scalar()
    checks_passed.append(f"CA total (SQL, NUMERIC) : {ca_sql}")

    for line in checks_passed:
        log.info("✓ %s", line)


def main() -> int:
    try:
        df = extract()
        engine = get_engine()

        with engine.begin() as conn:
            log.info("Purge des tables existantes (idempotence)...")
            for table in TABLES_TRUNCATE_ORDER:
                conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))

            dims = build_dimensions(df)
            for name, frame in dims.items():
                frame.to_sql(name, conn, if_exists="append", index=False)
                log.info("Chargé %s : %d lignes", name, len(frame))

            fact_sales = build_fact(df, conn)
            fact_sales.to_sql("fact_sales", conn, if_exists="append", index=False)
            log.info("Chargé fact_sales : %d lignes", len(fact_sales))

            run_post_load_quality_checks(conn, source_row_count=len(df))

        log.info("Chargement terminé avec succès : %d lignes dans fact_sales", len(fact_sales))
        return 0

    except FileNotFoundError as e:
        log.error("Fichier source manquant : %s", e)
        return 1
    except ValueError as e:
        log.error("Contrôle qualité échoué, transaction annulée (rollback) : %s", e)
        return 1
    except SQLAlchemyError as e:
        log.error("Erreur base de données, transaction annulée (rollback) : %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
