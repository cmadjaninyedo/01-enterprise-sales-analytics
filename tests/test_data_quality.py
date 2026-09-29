"""
Suite de tests de qualité de données pour le schéma en étoile
Enterprise Sales Analytics.

Ces tests s'exécutent contre une base PostgreSQL déjà chargée
(après `python etl/load_data.py`). Ce ne sont pas des tests unitaires
sur du code isolé, mais des tests d'intégrité de données, dans l'esprit
de ce qu'on attend d'un projet Analytics Engineering (proches de
`dbt test` : unique, not_null, relationships, accepted_range).

Prérequis :
    - Un fichier .env valide à la racine du projet (voir .env.example)
    - La base doit avoir été chargée au préalable : python etl/load_data.py

Lancer :
    pytest tests/test_data_quality.py -v

Si la base est inaccessible, les tests sont automatiquement "skipped"
(plutôt que de faire échouer toute la suite pour une raison d'environnement).
"""
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "etl"))
from db_connection import get_engine  # noqa: E402


@pytest.fixture(scope="session")
def conn():
    try:
        engine = get_engine()
        connection = engine.connect()
    except (SQLAlchemyError, ValueError) as e:
        pytest.skip(f"Base de données inaccessible ({e}) — vérifiez .env et que le chargement a été fait.")
    yield connection
    connection.close()


def _scalar(conn, query: str):
    return conn.execute(text(query)).scalar()


# --- Clés primaires : unicité ---------------------------------------------

@pytest.mark.parametrize("table,pk", [
    ("dim_date", "date_id"),
    ("dim_customer", "customer_id"),
    ("dim_product", "product_id"),
    ("dim_region", "region_id"),
    ("fact_sales", "sales_id"),
])
def test_primary_key_unique(conn, table, pk):
    n_dup = _scalar(conn, f"""
        SELECT COUNT(*) FROM (
            SELECT {pk} FROM {table} GROUP BY {pk} HAVING COUNT(*) > 1
        ) t
    """)
    assert n_dup == 0, f"{table}.{pk} : {n_dup} clé(s) primaire(s) dupliquée(s)"


def test_dim_customer_pk_unique(conn):
    """Alias explicite demandé dans l'audit portfolio."""
    assert _scalar(conn, """
        SELECT COUNT(*) FROM (
            SELECT customer_id FROM dim_customer GROUP BY customer_id HAVING COUNT(*) > 1
        ) t
    """) == 0


def test_dim_product_pk_unique(conn):
    """Alias explicite demandé dans l'audit portfolio."""
    assert _scalar(conn, """
        SELECT COUNT(*) FROM (
            SELECT product_id FROM dim_product GROUP BY product_id HAVING COUNT(*) > 1
        ) t
    """) == 0


# --- Clés étrangères : absence de lignes orphelines ------------------------

@pytest.mark.parametrize("fk_col,dim_table,dim_pk", [
    ("date_id", "dim_date", "date_id"),
    ("customer_id", "dim_customer", "customer_id"),
    ("product_id", "dim_product", "product_id"),
    ("region_id", "dim_region", "region_id"),
])
def test_fact_sales_fk_no_orphans(conn, fk_col, dim_table, dim_pk):
    n_orphans = _scalar(conn, f"""
        SELECT COUNT(*) FROM fact_sales f
        LEFT JOIN {dim_table} d ON f.{fk_col} = d.{dim_pk}
        WHERE d.{dim_pk} IS NULL
    """)
    assert n_orphans == 0, f"fact_sales.{fk_col} : {n_orphans} ligne(s) orpheline(s) vers {dim_table}"


def test_fact_sales_fk_customer(conn):
    """Alias explicite demandé dans l'audit portfolio."""
    assert _scalar(conn, """
        SELECT COUNT(*) FROM fact_sales f
        LEFT JOIN dim_customer d ON f.customer_id = d.customer_id
        WHERE d.customer_id IS NULL
    """) == 0


def test_fact_sales_fk_product(conn):
    """Alias explicite demandé dans l'audit portfolio."""
    assert _scalar(conn, """
        SELECT COUNT(*) FROM fact_sales f
        LEFT JOIN dim_product d ON f.product_id = d.product_id
        WHERE d.product_id IS NULL
    """) == 0


# --- Règles métier -----------------------------------------------------

def test_fact_sales_no_negative_quantity(conn):
    n_bad = _scalar(conn, "SELECT COUNT(*) FROM fact_sales WHERE quantity <= 0")
    assert n_bad == 0, f"{n_bad} ligne(s) avec quantity <= 0"


def test_fact_sales_no_negative_sales_amount(conn):
    n_bad = _scalar(conn, "SELECT COUNT(*) FROM fact_sales WHERE sales_amount < 0")
    assert n_bad == 0, f"{n_bad} ligne(s) avec sales_amount < 0"


def test_fact_sales_not_null_columns(conn):
    n_bad = _scalar(conn, """
        SELECT COUNT(*) FROM fact_sales
        WHERE order_id IS NULL OR date_id IS NULL OR customer_id IS NULL
           OR product_id IS NULL OR region_id IS NULL OR sales_amount IS NULL
           OR quantity IS NULL
    """)
    assert n_bad == 0, f"{n_bad} ligne(s) avec une colonne obligatoire NULL"


# --- Volumétrie ----------------------------------------------------------

def test_row_count_matches_source_csv(conn):
    import pandas as pd
    csv_path = Path(__file__).resolve().parent.parent / "data" / "processed" / "superstore_clean.csv"
    expected = len(pd.read_csv(csv_path))
    actual = _scalar(conn, "SELECT COUNT(*) FROM fact_sales")
    assert actual == expected, f"fact_sales contient {actual} lignes, {expected} attendues (source CSV)"


def test_order_to_line_ratio_plausible(conn):
    """Contrôle de cohérence métier : ~2 lignes par commande en moyenne (valeur
    empirique documentée dans docs/dictionnaire_donnees.md pour ce dataset)."""
    n_lines = _scalar(conn, "SELECT COUNT(*) FROM fact_sales")
    n_orders = _scalar(conn, "SELECT COUNT(DISTINCT order_id) FROM fact_sales")
    ratio = n_lines / n_orders
    assert 1.5 <= ratio <= 2.5, f"Ratio lignes/commande inhabituel : {ratio:.2f}"
