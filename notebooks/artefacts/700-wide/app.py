"""
Sales Performance Dashboard
============================
Streamlit app that reads two gold-layer parquet files and
renders interactive charts + KPI cards.

Run:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Sales Performance Dashboard",
    page_icon="📊",
    layout="wide",
)

# ============================================================
# CUSTOM STYLING
# ============================================================
st.markdown("""
<style>
    /* ── Metric cards ── */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e3a5f 0%, #264a6e 100%);
        padding: 1.2rem 1.5rem;
        border-radius: 0.75rem;
        color: #ffffff;
    }
    div[data-testid="stMetric"] label {
        color: #a8c7e2 !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
    }

    /* ── Footer ── */
    .footer-text {
        text-align: center;
        color: #888;
        font-size: 0.85rem;
        padding: 2rem 0 1rem 0;
        border-top: 1px solid #e0e0e0;
        margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# LOAD DATA (cached so re-runs don't re-read from disk)
# ============================================================
@st.cache_data
def load_sales():
    df = pd.read_parquet("gold/daily_sales_by_category.parquet")
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df

@st.cache_data
def load_returns():
    df = pd.read_parquet("gold/returns_rate.parquet")
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df

sales_df   = load_sales()
returns_df = load_returns()

# ============================================================
# SIDEBAR — DATE RANGE FILTER
# ============================================================
st.sidebar.title("Filters")

# Global date boundaries across both tables
global_min = min(sales_df["order_date"].min(), returns_df["order_date"].min()).date()
global_max = max(sales_df["order_date"].max(), returns_df["order_date"].max()).date()

# Default: last 30 days of available data
default_start = max(global_min, global_max - timedelta(days=30))
default_end   = global_max

date_range = st.sidebar.date_input(
    "Date range",
    value=(default_start, default_end),
    min_value=global_min,
    max_value=global_max,
)

# Handle single-date selection (user clicked but hasn't picked end yet)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = default_start, default_end

# Apply filter
mask_sales   = (sales_df["order_date"].dt.date >= start_date) & \
               (sales_df["order_date"].dt.date <= end_date)
mask_returns = (returns_df["order_date"].dt.date >= start_date) & \
               (returns_df["order_date"].dt.date <= end_date)

filtered_sales   = sales_df[mask_sales].copy()
filtered_returns = returns_df[mask_returns].copy()

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.metric("Sales rows in range",  len(filtered_sales))
st.sidebar.metric("Returns rows in range", len(filtered_returns))

# ============================================================
# TITLE
# ============================================================
st.title("Sales Performance Dashboard")
st.caption(f"Showing data from **{start_date}** to **{end_date}**")

# ============================================================
# METRIC CARDS — Total Revenue & Average Returns Rate
# ============================================================
col1, col2 = st.columns(2)

total_revenue = filtered_sales["total_revenue"].sum()
avg_return_rate = filtered_returns["returns_rate_pct"].mean() if len(filtered_returns) > 0 else 0.0

col1.metric(
    label="Total Revenue",
    value=f"${total_revenue:,.2f}",
)
col2.metric(
    label="Average Returns Rate",
    value=f"{avg_return_rate:.2f}%",
)

# ============================================================
# CHART 1 — Grouped Bar: Total Revenue by Region
#           Color split by product_category
# ============================================================
st.markdown("### Revenue by Region")

if len(filtered_sales) > 0:
    # Aggregate to region x category for the bar chart
    bar_data = (
        filtered_sales
        .groupby(["region", "product_category"], as_index=False)["total_revenue"]
        .sum()
        .sort_values("total_revenue", ascending=False)
    )

    fig_bar = px.bar(
        bar_data,
        x="region",
        y="total_revenue",
        color="product_category",
        barmode="group",
        labels={
            "region": "Region",
            "total_revenue": "Total Revenue ($)",
            "product_category": "Category",
        },
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_bar.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(categoryorder="total descending"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=40, b=40),
        height=420,
    )
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("No sales data in the selected date range.")

# ============================================================
# CHART 2 — Line: Returns Rate % Over Time
# ============================================================
st.markdown("### Returns Rate Over Time")

if len(filtered_returns) > 0:
    line_data = filtered_returns.sort_values("order_date")

    fig_line = px.line(
        line_data,
        x="order_date",
        y="returns_rate_pct",
        labels={
            "order_date": "Date",
            "returns_rate_pct": "Returns Rate (%)",
        },
        markers=True,
    )
    fig_line.update_traces(
        line=dict(color="#e05252", width=2.5),
        marker=dict(size=5, color="#e05252"),
    )
    fig_line.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(range=[0, max(line_data["returns_rate_pct"].max() * 1.15, 10)]),
        margin=dict(l=40, r=20, t=20, b=40),
        height=380,
    )
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("No returns data in the selected date range.")

# ============================================================
# FOOTER — Data last updated
# ============================================================
last_updated = global_max.strftime("%B %d, %Y")
st.markdown(
    f'<div class="footer-text">Data last updated: {last_updated}</div>',
    unsafe_allow_html=True,
)
