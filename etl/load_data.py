from pathlib import Path
import pandas as pd
from db_connection import get_engine

# --- Chemins (robustes, indépendants du dossier d'exécution) ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "processed" / "superstore_clean.csv"

# --- Connexion ---
engine = get_engine()

# --- Extraction (dtype forcé pour Postal Code : évite la perte du zéro initial) ---
df = pd.read_csv(DATA_PATH, dtype={"Postal Code": str})

# --- Transformation : dim_date ---
dates = pd.to_datetime(df["Order Date"]).drop_duplicates().reset_index(drop=True)
dim_date = pd.DataFrame({
    "full_date": dates,
    "year": dates.dt.year,
    "quarter": dates.dt.quarter,
    "month": dates.dt.month,
    "month_name": dates.dt.month_name(),
    "day": dates.dt.day,
    "day_of_week": dates.dt.day_name(),
    "is_weekend": dates.dt.dayofweek >= 5
})
dim_date.to_sql("dim_date", engine, if_exists="append", index=False)

# --- Transformation : dim_customer ---
dim_customer = (
    df[["Customer ID", "Customer Name", "Segment"]]
    .drop_duplicates()
    .rename(columns={
        "Customer ID": "customer_id",
        "Customer Name": "customer_name",
        "Segment": "segment"
    })
)
dim_customer.to_sql("dim_customer", engine, if_exists="append", index=False)

# --- Transformation : dim_product ---
dim_product = (
    df[["Product ID", "Product Name", "Category", "Sub-Category"]]
    .drop_duplicates(subset="Product ID", keep="first")
    .rename(columns={
        "Product ID": "product_id",
        "Product Name": "product_name",
        "Category": "category",
        "Sub-Category": "sub_category"
    })
)
dim_product.to_sql("dim_product", engine, if_exists="append", index=False)

# --- Transformation : dim_region ---
dim_region = (
    df[["Region", "State", "City", "Postal Code", "Country"]]
    .drop_duplicates()
    .reset_index(drop=True)
    .rename(columns={
        "Region": "region", "State": "state", "City": "city",
        "Postal Code": "postal_code", "Country": "country"
    })
)
dim_region.to_sql("dim_region", engine, if_exists="append", index=False)

# --- Rechargement des dimensions pour récupérer les clés générées ---
dim_date_db = pd.read_sql("SELECT date_id, full_date FROM dim_date", engine)
dim_region_db = pd.read_sql(
    "SELECT region_id, region, state, city, postal_code FROM dim_region", engine
)

# --- Transformation : fact_sales (jointures pour récupérer les FK) ---
df["Order Date"] = pd.to_datetime(df["Order Date"]).dt.normalize()
dim_date_db["full_date"] = pd.to_datetime(dim_date_db["full_date"]).dt.normalize()

fact = df.merge(dim_date_db, left_on="Order Date", right_on="full_date")
fact = fact.merge(
    dim_region_db,
    left_on=["Region", "State", "City", "Postal Code"],
    right_on=["region", "state", "city", "postal_code"]
)

fact_sales = fact[[
    "Order ID", "date_id", "Customer ID", "Product ID", "region_id",
    "Ship Mode", "Sales", "Quantity", "Discount", "Profit"
]].rename(columns={
    "Order ID": "order_id", "Customer ID": "customer_id",
    "Product ID": "product_id", "Ship Mode": "ship_mode",
    "Sales": "sales_amount", "Quantity": "quantity",
    "Discount": "discount", "Profit": "profit"
})

fact_sales.to_sql("fact_sales", engine, if_exists="append", index=False)

# --- Contrôle qualité ---
assert len(fact_sales) == len(df), "Perte ou duplication de lignes lors du chargement !"
print(f"Chargement terminé : {len(fact_sales)} lignes dans fact_sales")