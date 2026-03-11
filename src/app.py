import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv
from google import genai

# --- PATHS & CONFIG ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "olist.db")

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# --- AUTO BUILD DATABASE IF IT DOESN'T EXIST ---
# this runs automatically on Streamlit Cloud on first launch
# so the database is built from the CSV files without needing to upload olist.db
if not os.path.exists(DB_PATH):
    import subprocess
    setup_path = os.path.join(BASE_DIR, "src", "database_setup.py")
    st.info("Building database for the first time. This takes about 60 seconds...")
    subprocess.run(["python", setup_path], check=True)
    st.rerun()

SCHEMA = """
You are an expert Data Analyst working with the Olist E-commerce SQLite database.
Your only job is to convert natural language questions into valid SQLite queries.
Return ONLY the raw SQL query. No markdown, no backticks, no explanation.

Tables available:
1. customers (customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state)
2. orders (order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at, order_delivered_customer_date, order_estimated_delivery_date)
3. order_items (order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value)
4. order_payments (order_id, payment_sequential, payment_type, payment_installments, payment_value)
5. order_reviews (review_id, order_id, review_score, review_creation_date, review_answer_timestamp)
6. products (product_id, product_category_name, product_name_lenght, product_description_lenght, product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm)
7. sellers (seller_id, seller_zip_code_prefix, seller_city, seller_state)
8. geolocation (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state)
9. category_translation (product_category_name, product_category_name_english)

RULES:
- Always JOIN category_translation to show English category names
- For revenue always use SUM(order_items.price)
- Always add LIMIT 10 unless user asks for more
- Only write SELECT queries, never DELETE UPDATE or INSERT
- Always give columns descriptive aliases e.g. 'Total Revenue' instead of 'SUM(price)'
"""


def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Fraunces:ital,wght@0,400;0,700;1,400&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        background-color: #F5F4F0;
        color: #1A1A2E;
    }

    .stApp {
        background-color: #F5F4F0;
    }

    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }

    /* ── SIDEBAR ── */
    [data-testid="stSidebar"] {
        background: #FFFFFF;
        border-right: 1px solid #E8E4DC;
    }

    [data-testid="stSidebar"] .stMarkdown h3 {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #9B8EA0;
        margin-bottom: 0.8rem;
    }

    [data-testid="stSidebar"] .stButton button {
        background: #F9F8F6;
        border: 1px solid #E8E4DC;
        border-radius: 10px;
        color: #4A4560;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.78rem;
        font-weight: 400;
        padding: 0.65rem 0.9rem;
        text-align: left;
        transition: all 0.18s ease;
        margin-bottom: 5px;
        line-height: 1.4;
    }

    [data-testid="stSidebar"] .stButton button:hover {
        background: #FFF8EE;
        border-color: #D4A843;
        color: #1A1A2E;
        transform: translateX(3px);
    }

    /* ── MAIN HEADER ── */
    .header-wrap {
        background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
        border-radius: 20px;
        padding: 2.5rem 3rem;
        margin-bottom: 1.8rem;
        position: relative;
        overflow: hidden;
    }

    .header-wrap::before {
        content: '';
        position: absolute;
        top: -40px;
        right: -40px;
        width: 200px;
        height: 200px;
        background: radial-gradient(circle, rgba(212, 168, 67, 0.15) 0%, transparent 70%);
        border-radius: 50%;
    }

    .header-wrap::after {
        content: '';
        position: absolute;
        bottom: -30px;
        left: 30%;
        width: 150px;
        height: 150px;
        background: radial-gradient(circle, rgba(212, 168, 67, 0.08) 0%, transparent 70%);
        border-radius: 50%;
    }

    .header-badge {
        display: inline-block;
        background: rgba(212, 168, 67, 0.15);
        border: 1px solid rgba(212, 168, 67, 0.3);
        border-radius: 20px;
        padding: 0.25rem 0.9rem;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: #D4A843;
        margin-bottom: 1rem;
    }

    .header-title {
        font-family: 'Fraunces', serif;
        font-size: 3rem;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1.1;
        margin: 0 0 0.8rem 0;
        letter-spacing: -0.02em;
    }

    .header-title span {
        color: #D4A843;
    }

    .header-subtitle {
        font-size: 0.9rem;
        color: rgba(255,255,255,0.55);
        font-weight: 300;
        max-width: 520px;
        line-height: 1.6;
        margin: 0;
    }

    /* ── STATS ROW ── */
    .stats-row {
        display: flex;
        gap: 12px;
        margin-bottom: 1.8rem;
    }

    .stat-pill {
        flex: 1;
        background: #FFFFFF;
        border: 1px solid #E8E4DC;
        border-radius: 14px;
        padding: 1.2rem;
        text-align: center;
        transition: box-shadow 0.2s;
    }

    .stat-pill:hover {
        box-shadow: 0 4px 20px rgba(26,26,46,0.08);
    }

    .stat-num {
        font-family: 'Fraunces', serif;
        font-size: 1.7rem;
        font-weight: 700;
        color: #1A1A2E;
        display: block;
        line-height: 1;
    }

    .stat-lbl {
        font-size: 0.65rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #9B8EA0;
        display: block;
        margin-top: 0.4rem;
    }

    /* ── SECTION LABEL ── */
    .section-label {
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #9B8EA0;
        margin-bottom: 0.8rem;
        display: block;
    }

    /* ── CHAT MESSAGES ── */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: #FFFFFF !important;
        border: 1px solid #E8E4DC !important;
        border-radius: 14px !important;
        padding: 1rem 1.4rem !important;
        margin-bottom: 8px;
    }

    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        background: #FFF8EE !important;
        border: 1px solid #F0E6CC !important;
        border-radius: 14px !important;
        padding: 1rem 1.4rem !important;
        margin-bottom: 16px;
    }

    /* ── CHAT INPUT ── */
    [data-testid="stChatInput"] {
        background: #FFFFFF !important;
        border: 2px solid #E8E4DC !important;
        border-radius: 16px !important;
    }

    [data-testid="stChatInput"]:focus-within {
        border-color: #D4A843 !important;
        box-shadow: 0 0 0 4px rgba(212, 168, 67, 0.1) !important;
    }

    [data-testid="stChatInput"] textarea {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: #1A1A2E !important;
        font-size: 0.9rem !important;
    }

    /* ── EXPANDER ── */
    [data-testid="stExpander"] {
        background: #FFFFFF !important;
        border: 1px solid #E8E4DC !important;
        border-radius: 12px !important;
    }

    [data-testid="stExpander"] summary {
        color: #9B8EA0 !important;
        font-size: 0.8rem !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* ── DATAFRAME ── */
    [data-testid="stDataFrame"] {
        border: 1px solid #E8E4DC !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        background: #FFFFFF !important;
    }

    /* ── ALERTS ── */
    [data-testid="stAlert"] {
        border-radius: 12px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.85rem !important;
    }

    /* ── DIVIDER ── */
    hr { border-color: #E8E4DC !important; }

    /* ── FOOTER ── */
    .footer-txt {
        font-size: 0.7rem;
        color: #C4BCCA;
        text-align: center;
        letter-spacing: 0.06em;
        padding: 0.5rem 0 1rem;
    }

    /* scrollbar */
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: #F5F4F0; }
    ::-webkit-scrollbar-thumb { background: #D4C4A8; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)


def generate_chart(df):
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = df.select_dtypes(include="object").columns.tolist()

    clean_theme = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(249,248,246,0.6)",
        font=dict(family="Plus Jakarta Sans", color="#4A4560", size=12),
        xaxis=dict(
            gridcolor="#F0ECE4",
            linecolor="#E8E4DC",
            tickfont=dict(color="#9B8EA0", size=11)
        ),
        yaxis=dict(
            gridcolor="#F0ECE4",
            linecolor="#E8E4DC",
            tickfont=dict(color="#9B8EA0", size=11)
        ),
        margin=dict(l=20, r=20, t=30, b=60),
        hoverlabel=dict(
            bgcolor="#1A1A2E",
            bordercolor="#D4A843",
            font=dict(family="Plus Jakarta Sans", color="#FFFFFF")
        )
    )

    if len(numeric_cols) >= 1 and len(text_cols) >= 1:
        fig = px.bar(
            df,
            x=text_cols[0],
            y=numeric_cols[0],
            color=numeric_cols[0],
            color_continuous_scale=[[0, "#F0E6CC"], [0.5, "#D4A843"], [1, "#1A1A2E"]]
        )
        fig.update_traces(
            marker_line_width=0,
            hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra></extra>"
        )
        fig.update_layout(**clean_theme)
        fig.update_layout(coloraxis_showscale=False, xaxis_tickangle=-35)
        return fig

    elif len(numeric_cols) >= 2:
        fig = px.scatter(
            df,
            x=numeric_cols[0],
            y=numeric_cols[1],
            color_discrete_sequence=["#D4A843"]
        )
        fig.update_traces(marker=dict(size=8, opacity=0.7))
        fig.update_layout(**clean_theme)
        return fig

    return None


# ══════════════════════════════
#  APP
# ══════════════════════════════
st.set_page_config(
    page_title="FinQuery — Olist Intelligence",
    page_icon="🛒",
    layout="wide"
)

inject_css()

# ── SIDEBAR ──
with st.sidebar:
    st.markdown("""
    <div style='padding: 1.2rem 0 1rem 0;'>
        <div style='font-family: Fraunces, serif; font-size: 1.3rem; font-weight: 700; color: #1A1A2E;'>FinQuery</div>
        <div style='font-size: 0.65rem; color: #9B8EA0; letter-spacing: 0.15em; text-transform: uppercase; margin-top: 2px;'>Olist Intelligence</div>
    </div>
    <hr style='border-color: #E8E4DC; margin-bottom: 1.2rem;'>
    """, unsafe_allow_html=True)

    st.markdown("### 💡 Try these questions")

    suggestions = [
    "What are the top 5 product categories by total revenue?",
    "Which state has the most customers?",
    "What are the top 10 categories by average review score?",       
    "Which 10 categories have the lowest average review score?", 
    "How many orders were delivered successfully?",
    "Which payment type is most popular?",
    "What are the top 5 sellers by total sales?",
    "What is the total revenue per year?"
]

    for s in suggestions:
        if st.button(s, use_container_width=True):
            st.session_state.suggestion = s

    st.markdown("""
    <hr style='border-color: #E8E4DC; margin-top: 1.5rem;'>
    <div style='font-size: 0.7rem; color: #C4BCCA; line-height: 1.8; padding-top: 0.4rem;'>
        🔒 Read-only secure connection<br>
        ⚡ Powered by Gemini 2.5 Flash<br>
        🗄️ 1.6M rows · 9 tables
    </div>
    """, unsafe_allow_html=True)

# ── HEADER ──
st.markdown("""
<div class="header-wrap">
    <div class="header-badge">AI-Powered · Natural Language · SQL</div>
    <h1 class="header-title">Fin<span>Query</span></h1>
    <p class="header-subtitle">Ask any business question in plain English and get instant answers from 1.6 million rows of real Brazilian e-commerce data.</p>
</div>
""", unsafe_allow_html=True)

# ── STATS ──
st.markdown("""
<div class="stats-row">
    <div class="stat-pill"><span class="stat-num">1.6M</span><span class="stat-lbl">Total Rows</span></div>
    <div class="stat-pill"><span class="stat-num">9</span><span class="stat-lbl">Linked Tables</span></div>
    <div class="stat-pill"><span class="stat-num">99K+</span><span class="stat-lbl">Orders</span></div>
    <div class="stat-pill"><span class="stat-num">32K+</span><span class="stat-lbl">Products</span></div>
    <div class="stat-pill"><span class="stat-num">3K+</span><span class="stat-lbl">Sellers</span></div>
</div>
""", unsafe_allow_html=True)

# ── SESSION STATE ──
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

# ── CHAT HISTORY ──
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sql" in message:
            with st.expander("🔍 View generated SQL"):
                st.code(message["sql"], language="sql")
        if "data" in message:
            fig = generate_chart(message["data"])
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            st.dataframe(message["data"], use_container_width=True)

# ── CHAT INPUT ──
default = st.session_state.pop("suggestion", "")

if st.session_state.is_processing:
    st.chat_input("Please wait — query is running...", disabled=True)
    prompt = None
else:
    prompt = st.chat_input("Ask a business question e.g. What are the top 10 cities by number of orders?")

question = default or prompt

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    st.session_state.is_processing = True

    with st.chat_message("assistant"):
        with st.spinner("Analysing your question..."):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",  # updated to gemini-2.5-flash
                    contents=SCHEMA + f"\n\nUser Question: {question}\nSQL Query:"
                )

                sql = response.text.strip()
                sql = sql.replace("```sql", "").replace("```", "").strip()

                with st.expander("🔍 View generated SQL"):
                    st.code(sql, language="sql")

                conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
                df = pd.read_sql_query(sql, conn)
                conn.close()

                if df.empty:
                    st.warning("No results found. Try rephrasing your question.")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "No results found for that question.",
                        "sql": sql
                    })
                else:
                    st.success(f"✓ {len(df)} rows returned")

                    fig = generate_chart(df)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)

                    st.dataframe(df, use_container_width=True)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Here are the results for: *{question}*",
                        "sql": sql,
                        "data": df
                    })

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    st.warning("⏳ Rate limit reached. Please wait 1-2 minutes before asking another question.")
                else:
                    st.error(f"Something went wrong: {e}")

            finally:
                st.session_state.is_processing = False

# ── FOOTER ──
st.divider()
st.markdown("""
<p class="footer-txt">FINQUERY &nbsp;·&nbsp; Gemini 2.5 Flash &nbsp;·&nbsp; SQLite &nbsp;·&nbsp; Streamlit &nbsp;·&nbsp; Olist Brazilian E-Commerce Dataset &nbsp;·&nbsp; Read-only secure connection</p>
""", unsafe_allow_html=True)