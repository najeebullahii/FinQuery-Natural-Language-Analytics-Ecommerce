import pandas as pd
from sqlalchemy import create_engine
import os

# finds the root project folder automatically regardless of where you run the script from
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(BASE_DIR, "olist.db")


def build_ultimate_db():

    # connect to sqlite - creates the olist.db file if it doesnt exist yet
    engine = create_engine(f"sqlite:///{DB_PATH}")

    # mapping each csv file to a clean simple table name
    # this makes it much easier for gemini to write accurate sql later
    tables_to_process = {
        "customers": "olist_customers_dataset.csv",
        "orders": "olist_orders_dataset.csv",
        "order_items": "olist_order_items_dataset.csv",
        "order_payments": "olist_order_payments_dataset.csv",
        "order_reviews": "olist_order_reviews_dataset.csv",
        "products": "olist_products_dataset.csv",
        "sellers": "olist_sellers_dataset.csv",
        "geolocation": "olist_geolocation_dataset.csv",
        "category_translation": "product_category_name_translation.csv"
    }

    print("starting the olist database build...\n")

    for table_name, filename in tables_to_process.items():
        filepath = os.path.join(DATA_DIR, filename)

        # safety check - skip the file if it doesnt exist instead of crashing
        if not os.path.exists(filepath):
            print(f"warning: {filename} not found - skipping")
            continue

        print(f"processing {filename} into table '{table_name}'...")

        # load csv into a dataframe
        df = pd.read_csv(filepath)

        # --- CLEANING PHASE ---

        # standardize all column names to lowercase with underscores
        # gemini generates much more accurate sql when column names are clean
        df.columns = [c.lower().replace(" ", "_").strip() for c in df.columns]

        for col in df.columns:
            if "date" in col or "timestamp" in col:
                # convert to datetime first so we can standardize the format
                # then convert back to string because sqlite doesn't handle
                # pandas timestamp objects directly
                df[col] = pd.to_datetime(df[col], errors="coerce")
                df[col] = df[col].astype(str).replace("NaT", "Unknown")

        # fill missing values so queries dont return errors or None values
        # missing text becomes 'Unknown', missing numbers become 0
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].fillna("Unknown")
            else:
                df[col] = df[col].fillna(0)

        # --- SAVE TO DATABASE ---

        # replace means running this script again just refreshes the data cleanly
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        print(f"done - {len(df):,} rows loaded into '{table_name}'")

    print(f"\nall done! your database is ready at: {DB_PATH}")


if __name__ == "__main__":
    build_ultimate_db()