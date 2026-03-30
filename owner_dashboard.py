import streamlit as st
import pandas as pd
from database import get_dataframe
import branding

def owner_dashboard_page():

    branding.render_page_header("📊 Business Dashboard")

    df = get_dataframe()

    if df.empty:
        st.warning("No data available")
        return

    df['date'] = pd.to_datetime(df['date'])

    def _col(name: str):
        for c in df.columns:
            if c.lower() == name.lower():
                return c
        return None

    fare_col = _col("fare")
    if not fare_col:
        st.error("Payout data is missing `fare` (gross fare). Re-save payouts from Driver Payout.")
        return

    # -------------------------------
    # DATE FILTER
    # -------------------------------
    selected_date = st.date_input("Select Date", key="owner_date")

    day_df = df[df['date'].dt.date == selected_date]

    if day_df.empty:
        st.warning("No data for selected date")
        return

    # -------------------------------
    # CALCULATIONS
    # -------------------------------
    # Gross Uber = sum of gross trip fare (not driver 30% share stored in driver_gross)
    gross_uber = day_df[fare_col].sum()
    net_col = _col("net_payout")
    cng_col = _col("cng")
    subscription_col = _col("subscription")
    if not net_col or not cng_col:
        st.error("Payout data is missing `net_payout` or `cng`.")
        return
    driver_payout = day_df[net_col].sum()
    cng = day_df[cng_col].sum()
    subscription = day_df[subscription_col].sum()

    owner_earning = gross_uber - driver_payout - subscription - cng
    owner_percent = (owner_earning / gross_uber * 100) if gross_uber else 0

    # -------------------------------
    # DISPLAY
    # -------------------------------
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Gross Uber Earnings", f"₹{gross_uber:,.0f}")
    col2.metric("Driver Payout", f"₹{driver_payout:,.0f}")
    col3.metric("Subscription Cost", f"₹{subscription:,.0f}")
    col4.metric("CNG Cost", f"₹{cng:,.0f}")
    col5.metric("Owner Earnings", f"₹{owner_earning:,.0f}")

    st.metric("Owner %", f"{owner_percent:.2f}%")

    # -------------------------------
    # DATE-WISE SUMMARY
    # -------------------------------
    st.subheader("📅 Date-wise Summary")

    agg = {fare_col: "sum"}
    if net_col:
        agg[net_col] = "sum"
    if cng_col:
        agg[cng_col] = "sum"
    summary = df.groupby(df["date"].dt.date).agg(agg).reset_index()
    rename_map = {fare_col: "gross_fare"}
    if net_col:
        rename_map[net_col] = "net_payout"
    if cng_col:
        rename_map[cng_col] = "cng"
    summary = summary.rename(columns=rename_map)

    st.dataframe(summary)
