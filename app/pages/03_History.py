"""
History & Value Page

Shows past value captured, YTD totals, and reporting from ValueLogs.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

from app.utils.sheets_client import get_perks, get_value_logs, get_trips

st.title("📈 History & Value")
st.caption("See what you've captured and where your biggest wins came from")

# Load data
perks = get_perks()
value_logs = get_value_logs()
trips = get_trips()

if not value_logs:
    st.warning("No value logs found yet. Start logging usage from the Dashboard to see history here.")
    st.stop()

# Create lookup for nice display
perk_lookup = {p["perk_id"]: p for p in perks}
trip_lookup = {t["trip_id"]: t for t in trips}

# Enrich logs
enriched_logs = []
for log in value_logs:
    perk = perk_lookup.get(log.get("perk_id"), {})
    trip = trip_lookup.get(log.get("trip_id"), {}) if log.get("trip_id") else {}

    enriched_logs.append({
        "used_date": log.get("used_date"),
        "card": perk.get("card", "Unknown"),
        "perk_name": perk.get("name", log.get("perk_id")),
        "period": log.get("period_key"),
        "value_captured": log.get("value_captured", 0),
        "notes": log.get("notes", ""),
        "trip": trip.get("name", ""),
        "source": log.get("source", ""),
        "perk_id": log.get("perk_id"),
        "log_id": log.get("log_id"),
    })

df = pd.DataFrame(enriched_logs)

# Convert date column
df["used_date"] = pd.to_datetime(df["used_date"], errors="coerce")

# =====================
# Filters
# =====================
col1, col2, col3 = st.columns([1.5, 2, 2])

with col1:
    years = sorted(df["used_date"].dt.year.dropna().unique().astype(int), reverse=True)
    selected_year = st.selectbox("Year", options=["All"] + years, index=0)

with col2:
    cards = sorted(df["card"].dropna().unique())
    selected_cards = st.multiselect("Cards", options=cards, default=cards)

with col3:
    search_term = st.text_input("Search notes or perk", placeholder="Search...")

# Apply filters
filtered_df = df.copy()

if selected_year != "All":
    filtered_df = filtered_df[filtered_df["used_date"].dt.year == selected_year]

if selected_cards:
    filtered_df = filtered_df[filtered_df["card"].isin(selected_cards)]

if search_term:
    mask = (
        filtered_df["notes"].str.contains(search_term, case=False, na=False) |
        filtered_df["perk_name"].str.contains(search_term, case=False, na=False)
    )
    filtered_df = filtered_df[mask]

# =====================
# Summary
# =====================
st.divider()

total_value = filtered_df["value_captured"].sum()
total_logs = len(filtered_df)

col1, col2 = st.columns(2)
col1.metric("Total Value Captured (filtered)", f"${total_value:,.0f}")
col2.metric("Number of Logs", total_logs)

# =====================
# Main Table
# =====================
st.subheader("Usage History")

display_df = filtered_df[[
    "used_date", "card", "perk_name", "period", "value_captured", "notes", "trip"
]].copy()

display_df = display_df.sort_values("used_date", ascending=False)
display_df["used_date"] = display_df["used_date"].dt.strftime("%Y-%m-%d")

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "used_date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
        "value_captured": st.column_config.NumberColumn("Value ($)", format="$%.0f"),
    }
)

# =====================
# Charts
# =====================
if not filtered_df.empty:
    st.divider()
    st.subheader("Charts")

    col1, col2 = st.columns(2)

    with col1:
        # Value by Month
        monthly = (
            filtered_df.groupby(filtered_df["used_date"].dt.to_period("M"))["value_captured"]
            .sum()
            .reset_index()
        )
        monthly["used_date"] = monthly["used_date"].astype(str)
        fig_month = px.bar(
            monthly,
            x="used_date",
            y="value_captured",
            title="Value Captured by Month",
            labels={"used_date": "Month", "value_captured": "Value ($)"},
            color_discrete_sequence=["#3b82f6"],
        )
        fig_month.update_layout(showlegend=False)
        st.plotly_chart(fig_month, use_container_width=True)

    with col2:
        # Value by Card (Pie)
        by_card = filtered_df.groupby("card")["value_captured"].sum().reset_index()
        fig_card = px.pie(
            by_card,
            values="value_captured",
            names="card",
            title="Value by Card",
            hole=0.4,
        )
        st.plotly_chart(fig_card, use_container_width=True)

    # Top Perks by Value (Horizontal Bar)
    top_perks = (
        filtered_df.groupby("perk_name")["value_captured"]
        .sum()
        .sort_values(ascending=True)
        .tail(10)
        .reset_index()
    )
    fig_top = px.bar(
        top_perks,
        x="value_captured",
        y="perk_name",
        orientation="h",
        title="Top Perks by Value Captured",
        labels={"value_captured": "Total Value ($)", "perk_name": "Perk"},
        color_discrete_sequence=["#10b981"],
    )
    fig_top.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_top, use_container_width=True)

    # Cumulative Value Over Time (Line)
    if not filtered_df.empty:
        monthly = (
            filtered_df.groupby(filtered_df["used_date"].dt.to_period("M"))["value_captured"]
            .sum()
            .reset_index()
        )
        monthly["used_date"] = monthly["used_date"].astype(str)
        monthly = monthly.sort_values("used_date")
        monthly["cumulative"] = monthly["value_captured"].cumsum()

        fig_cum = px.line(
            monthly,
            x="used_date",
            y="cumulative",
            title="Cumulative Value Over Time",
            markers=True,
            labels={"used_date": "Month", "cumulative": "Cumulative Value ($)"},
            color_discrete_sequence=["#8b5cf6"],
        )
        fig_cum.update_layout(hovermode="x unified")
        st.plotly_chart(fig_cum, use_container_width=True)
