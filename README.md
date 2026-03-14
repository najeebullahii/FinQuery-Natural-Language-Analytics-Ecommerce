# FinQuery — Natural Language Analytics for E-Commerce

**Live Demo:** [View the app here](https://finquery-natural-language-analytics-ecommerce-bzogrhfvcqxkedqz.streamlit.app)

---

## Overview

FinQuery is a business intelligence application that lets anyone ask plain English questions about a real e-commerce database and receive instant, visualized answers. No SQL knowledge required.

The problem it solves is simple but common. In most companies, getting answers from a database requires either knowing SQL yourself or waiting for a data analyst to write a query for you. FinQuery removes that barrier entirely. A business user, a product manager, or an executive can type a question like "Which product categories generate the most revenue?" or "Which states have the most customers?" and get a chart and a data table back within seconds.

The system sends the question to Google's Gemini 2.5 Flash AI model along with a detailed description of the database structure. Gemini interprets the intent of the question and writes a precise SQL query. That query runs against a local SQLite database containing the full Olist Brazilian E-Commerce dataset, and the results are returned as both an interactive chart and an explorable data table.

---

## What Makes This Project Different

Most natural language to SQL demos use toy datasets with three or four tables. This project uses a real-world commercial dataset with nine interconnected relational tables and over 1.6 million rows. The queries Gemini generates often involve multiple JOIN operations across customers, orders, products, reviews, and category translations simultaneously.

The application also includes a read-only database connection as a security layer. This means that even if the AI model were to generate a destructive query, the database driver itself would reject it at the connection level. The prompt reinforces this by instructing the model to write only SELECT statements, but the technical constraint exists independently of that instruction.

---

## Dashboard Preview

The main interface uses a chat layout. You type a question, the system processes it, and the response appears as a chart followed by the data table. A collapsible panel beneath each response shows the exact SQL query that Gemini generated, which is useful for learning, auditing, or adapting the query manually.

![Top 10 product categories by total revenue](https://raw.githubusercontent.com/najeebullahii/FinQuery-Natural-Language-Analytics-Ecommerce/main/screenshots/revenue_by_category.png)

*The chart above was produced by asking "What are the top 10 product categories by total revenue?" — the system joined four tables and aggregated pricing data across 112,650 order line items.*

![SQL generation panel](https://raw.githubusercontent.com/najeebullahii/FinQuery-Natural-Language-Analytics-Ecommerce/main/screenshots/sql_generation.png)

*Every response includes the SQL query Gemini wrote to answer the question. The queries are production-quality, using table aliases, proper JOIN conditions, GROUP BY, and ORDER BY clauses.*

---

## Example Results

**Revenue trend by year**

Asking "What is the total revenue per year?" extracts the year from order purchase timestamps and aggregates product prices across all matching order items, revealing year-over-year business growth from 2016 through 2018.

![Total revenue broken down by year](https://raw.githubusercontent.com/najeebullahii/FinQuery-Natural-Language-Analytics-Ecommerce/main/screenshots/revenue_per_year.png)

**Customer satisfaction analysis**

Asking "Which 10 product categories have the lowest average review score?" produces a query that joins order items, products, reviews, and category translations in a single statement the kind of query that takes a junior analyst several minutes to write correctly.

![Bottom 10 categories by average review score](https://raw.githubusercontent.com/najeebullahii/FinQuery-Natural-Language-Analytics-Ecommerce/main/screenshots/lowest_rated_categories.png)

*Security and services, diapers and hygiene, and office furniture rank as the three lowest rated categories, the kind of insight that directly informs product strategy decisions.*

---

## The Dataset

This project uses the Olist Brazilian E-Commerce Public Dataset, published on Kaggle. It contains real transactional data from a Brazilian online marketplace between 2016 and 2018, anonymized for public use.

The database contains nine tables:

| Table | Records | Description |
|---|---|---|
| customers | 99,441 | Customer locations and identifiers |
| orders | 99,441 | Order status and timestamps |
| order_items | 112,650 | Line items with product and pricing |
| order_payments | 103,886 | Payment type and installment data |
| order_reviews | 99,224 | Customer review scores and comments |
| products | 32,951 | Product dimensions and category |
| sellers | 3,095 | Seller location information |
| geolocation | 1,000,163 | ZIP code coordinate mapping |
| category_translation | 71 | Portuguese to English category names |

Total: 1,612,141 rows across nine relational tables.

---

## Technical Architecture

The application is structured across four Python files.

**database_setup.py**
Handles the one-time ingestion of nine CSV files into a local SQLite database. It cleans column names to lowercase, fills null values with appropriate defaults, converts datetime columns to strings for SQLite compatibility, and loads each table using SQLAlchemy. Running this file once builds the entire database from scratch.

**nl_to_sql.py**
Contains the core AI conversion logic. It constructs a prompt that includes the full database schema table names, column names, data types, foreign key relationships, and explicit rules and sends it to the Gemini API along with the user's question. The rules embedded in the schema instruct the model to always join the category translation table, always use SUM of price for revenue calculations, always limit results to 10 rows by default, and never write anything other than SELECT statements. The function strips any markdown formatting from the model's response before returning clean SQL.

**app.py**
The Streamlit front end. It manages conversation history using session state so previous questions and answers remain visible as the user continues asking questions. Chart generation is automatic if the query result contains one text column and one numeric column, it renders a bar chart; if it contains two numeric columns, it renders a scatter plot. The Plotly charts use a consistent colour palette matching the application's design theme. A processing lock prevents the user from submitting multiple requests simultaneously, which would exhaust API quota unnecessarily.

**test_gemini.py**
A standalone script for verifying the Gemini API connection and model availability independently of the full application.

---

## Security Design

Two independent layers protect the database from modification:

**Layer 1 — Prompt instruction.** The schema prompt explicitly instructs Gemini to write only SELECT statements and never write DELETE, UPDATE, or INSERT. This handles the vast majority of cases.

**Layer 2 — Read-only connection.** The SQLite connection is opened with `mode=ro` in the URI, which means the database driver will reject any write operation at the file system level regardless of what SQL is submitted. This layer operates independently of the AI model's behaviour.

---

## Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python 3.14 |
| AI model | Google Gemini 2.5 Flash |
| AI SDK | google-genai |
| Database | SQLite |
| ORM | SQLAlchemy |
| Web framework | Streamlit |
| Charting | Plotly Express |
| Data processing | Pandas |
| Environment management | python-dotenv |

---

## Running This Project Locally

**1. Clone or download the repository**

Download the ZIP from GitHub and extract it, or clone it using Git.

**2. Create a virtual environment**

Open a terminal in the project folder and run:
```bash
python -m venv venv
venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set up your API key**

Create a file named `.env` in the root of the project folder and add:
```
GEMINI_API_KEY=your_key_here
```

You can get a free API key at [aistudio.google.com](https://aistudio.google.com).

**5. Build the database**
```bash
python src/database_setup.py
```

This loads all nine CSV files and builds the SQLite database. It takes approximately 30 to 60 seconds depending on your machine.

**6. Launch the application**
```bash
streamlit run src/app.py
```

Open your browser at `http://localhost:8501`.

---

## Project Structure
```
FinQuery-Olist-Ecommerce-Intelligence/
├── data/
│   ├── olist_customers_dataset.csv
│   ├── olist_orders_dataset.csv
│   ├── olist_order_items_dataset.csv
│   ├── olist_order_payments_dataset.csv
│   ├── olist_order_reviews_dataset.csv
│   ├── olist_products_dataset.csv
│   ├── olist_sellers_dataset.csv
│   ├── olist_geolocation_dataset.csv
│   └── product_category_name_translation.csv
├── src/
│   ├── database_setup.py
│   ├── nl_to_sql.py
│   ├── app.py
│   └── test_gemini.py
├── screenshots/
│   ├── revenue_by_category.png
│   ├── revenue_per_year.png
│   ├── lowest_rated_categories.png
│   └── sql_generation.png
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Dataset Source

Olist Brazilian E-Commerce Public Dataset
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

---

## Live Demo

A deployed version of this application is available on Streamlit Community Cloud:

[Launch FinQuery](https://finquery-natural-language-analytics-ecommerce-bzogrhfvcqxkedqz.streamlit.app)
```
