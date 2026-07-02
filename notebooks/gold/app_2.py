"""
Course Completion Dashboard
============================
Streamlit app that reads two gold-layer parquet files and
renders interactive charts + KPI cards.

Run:  streamlit run app_2.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Course Completion Dashboard",
    page_icon="🎓",
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
def load_daily_completions():
    df = pd.read_parquet("daily_completions_by_category.parquet")
    df["event_date"] = pd.to_datetime(df["event_date"])
    return df

@st.cache_data
def load_dropout_rate():
    df = pd.read_parquet("dropout_rate.parquet")
    df["event_date"] = pd.to_datetime(df["event_date"])
    return df

daily_df   = load_daily_completions()
dropout_df = load_dropout_rate()

# ============================================================
# SIDEBAR — DATE RANGE FILTER
# ============================================================
st.sidebar.title("Filters")

# Global date boundaries across both tables
global_min = min(daily_df["event_date"].min(), dropout_df["event_date"].min()).date()
global_max = max(daily_df["event_date"].max(), dropout_df["event_date"].max()).date()

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
mask_daily   = (daily_df["event_date"].dt.date >= start_date) & \
               (daily_df["event_date"].dt.date <= end_date)
mask_dropout = (dropout_df["event_date"].dt.date >= start_date) & \
               (dropout_df["event_date"].dt.date <= end_date)

filtered_daily   = daily_df[mask_daily].copy()
filtered_dropout = dropout_df[mask_dropout].copy()

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.metric("Completion rows in range", len(filtered_daily))
st.sidebar.metric("Dropout rows in range",    len(filtered_dropout))

# ============================================================
# TITLE
# ============================================================
st.title("Course Completion Dashboard")
st.caption(f"Showing data from **{start_date}** to **{end_date}**")

# ============================================================
# METRIC CARDS — Total Completions & Average Dropout Rate
# ============================================================
col1, col2 = st.columns(2)

total_completions = filtered_daily["completion_count"].sum()
avg_dropout_rate = filtered_dropout["dropout_rate_pct"].mean() if len(filtered_dropout) > 0 else 0.0

col1.metric(
    label="Total Completions",
    value=f"{total_completions:,.0f}",
)
col2.metric(
    label="Average Dropout Rate",
    value=f"{avg_dropout_rate:.2f}%",
)

# ============================================================
# CHART 1 — Grouped Bar: Completion Count by Course Category
# ============================================================
st.markdown("### Completions by Category")

if len(filtered_daily) > 0:
    # Aggregate to category for the bar chart
    bar_data = (
        filtered_daily
        .groupby("course_category", as_index=False)
        .agg(completion_count=("completion_count", "sum"),
             avg_completion_pct=("avg_completion_pct", "mean"))
        .sort_values("completion_count", ascending=False)
    )

    fig_bar = px.bar(
        bar_data,
        x="course_category",
        y="completion_count",
        color="course_category",
        labels={
            "course_category": "Course Category",
            "completion_count": "Completion Count",
        },
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_bar.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(categoryorder="total descending"),
        showlegend=False,
        margin=dict(l=40, r=20, t=40, b=40),
        height=420,
    )
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("No completion data in the selected date range.")

# ============================================================
# CHART 2 — Line: Dropout Rate % Over Time
# ============================================================
st.markdown("### Dropout Rate Over Time")

if len(filtered_dropout) > 0:
    line_data = filtered_dropout.sort_values("event_date")

    fig_line = px.line(
        line_data,
        x="event_date",
        y="dropout_rate_pct",
        labels={
            "event_date": "Date",
            "dropout_rate_pct": "Dropout Rate (%)",
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
        yaxis=dict(range=[0, max(line_data["dropout_rate_pct"].max() * 1.15, 10)]),
        margin=dict(l=40, r=20, t=20, b=40),
        height=380,
    )
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("No dropout data in the selected date range.")

# ============================================================
# FOOTER — Data last updated
# ============================================================
last_updated = global_max.strftime("%B %d, %Y")
st.markdown(
    f'<div class="footer-text">Data last updated: {last_updated}</div>',
    unsafe_allow_html=True,
)
