import os
import pandas as pd
import sqlite3
from dotenv import load_dotenv
from google import genai

# load api key from .env file
load_dotenv()

# set up paths properly using absolute references
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "olist.db")

# connect to gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# the schema is the "cheat sheet" we give gemini so it understands
# our exact database structure before writing any sql
SCHEMA = """
You are an expert SQL analyst working with the Olist Brazilian E-commerce SQLite database.
Your only job is to convert natural language questions into valid SQLite queries.
Return ONLY the raw SQL query. No markdown, no backticks, no explanation whatsoever.

Tables available:

1. customers
   - customer_id (text, primary key)
   - customer_unique_id (text)
   - customer_zip_code_prefix (text)
   - customer_city (text)
   - customer_state (text)

2. orders
   - order_id (text, primary key)
   - customer_id (text, foreign key -> customers)
   - order_status (text: delivered, shipped, canceled, invoiced, etc)
   - order_purchase_timestamp (text)
   - order_approved_at (text)
   - order_delivered_carrier_date (text)
   - order_delivered_customer_date (text)
   - order_estimated_delivery_date (text)

3. order_items
   - order_id (text, foreign key -> orders)
   - order_item_id (integer)
   - product_id (text, foreign key -> products)
   - seller_id (text, foreign key -> sellers)
   - shipping_limit_date (text)
   - price (real)
   - freight_value (real)

4. order_payments
   - order_id (text, foreign key -> orders)
   - payment_sequential (integer)
   - payment_type (text: credit_card, boleto, voucher, debit_card)
   - payment_installments (integer)
   - payment_value (real)

5. order_reviews
   - review_id (text)
   - order_id (text, foreign key -> orders)
   - review_score (integer, scale of 1 to 5)
   - review_comment_title (text)
   - review_comment_message (text)
   - review_creation_date (text)
   - review_answer_timestamp (text)

6. products
   - product_id (text, primary key)
   - product_category_name (text)
   - product_name_lenght (integer)
   - product_description_lenght (integer)
   - product_photos_qty (integer)
   - product_weight_g (real)
   - product_length_cm (real)
   - product_height_cm (real)
   - product_width_cm (real)

7. sellers
   - seller_id (text, primary key)
   - seller_zip_code_prefix (text)
   - seller_city (text)
   - seller_state (text)

8. category_translation
   - product_category_name (text)
   - product_category_name_english (text)

9. geolocation
   - geolocation_zip_code_prefix (text)
   - geolocation_lat (real)
   - geolocation_lng (real)
   - geolocation_city (text)
   - geolocation_state (text)

IMPORTANT RULES:
- Always JOIN category_translation to show English category names
- For revenue always use SUM(order_items.price)
- Always add LIMIT 10 unless the user asks for more
- Only write SELECT queries, never DELETE, UPDATE or INSERT
"""


def convert_to_sql(user_question):
    # send the schema plus the user question to gemini
    # gemini reads the schema and generates the correct sql
    prompt = f"{SCHEMA}\n\nUser Question: {user_question}\nSQL Query:"

    response = client.models.generate_content(
        model="gemini-2.5-flash",  
        contents=prompt
    )

    # clean up response in case gemini adds any formatting we dont want
    sql = response.text.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql


def run_query(sql):
    try:
        # read only connection for security
        # this means gemini can never accidentally modify or delete our data
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

        # pandas read_sql gives us a clean dataframe directly
        # this is perfect because streamlit works natively with dataframes
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df, None

    except Exception as e:
        return None, str(e)


def ask(user_question):
    print(f"\nquestion: {user_question}")

    # step 1: convert english question to sql using gemini
    print("converting to sql...")
    sql = convert_to_sql(user_question)
    print(f"generated sql:\n{sql}")

    # step 2: run the sql safely against our database
    print("\nrunning query...")
    df, error = run_query(sql)

    if error:
        print(f"query failed: {error}")
        return None, sql

    # step 3: display results cleanly using pandas
    print(f"\nresults: {len(df)} rows returned")
    print(df.to_string(index=False))
    return df, sql


# test with real questions when we run this file directly
if __name__ == "__main__":
    ask("How many total records are in the customers table?")
    ask("What are the top 5 product categories by total revenue?")
    ask("Which city has the most customers?")