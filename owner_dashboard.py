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
    driver_gross_col = _col("driver_gross")
    cng_col = _col("cng")
    subscription_col = _col("subscription")
    if not driver_gross_col or not cng_col:
        st.error("Payout data is missing `driver gross` or `cng`.")
        return
    driver_payout = day_df[driver_gross_col].sum()
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
    if driver_gross_col:
        agg[driver_gross_col] = "sum"
    if cng_col:
        agg[cng_col] = "sum"
    summary = df.groupby(df["date"].dt.date).agg(agg).reset_index()
    rename_map = {fare_col: "gross_fare"}
    if driver_gross_col:
        rename_map[driver_gross_col] = "driver_gross"
    if cng_col:
        rename_map[cng_col] = "cng"
    summary = summary.rename(columns=rename_map)

    # Profit = gross fare - driver payout - subscription - cng
    if all(col in summary.columns for col in ["gross_fare", "driver_payout", "subscription", "cng"]):
        summary["profit"] = (
            summary["gross_fare"] - summary["driver_payout"] - summary["subscription"] - summary["cng"]
        )

    st.dataframe(summary)

    st.subheader("📈 Monthly Profit (From Saved Data)")
    colm1, colm2 = st.columns(2)
    with colm1:
        selected_year = st.number_input(
            "Year",
            min_value=2026,
            max_value=2100,
            value=int(pd.Timestamp.today().year),
        )
    with colm2:
        selected_month = st.number_input("Month", min_value=1, max_value=12, value=int(pd.Timestamp.today().month))

    # Use actual saved payout data for the month
    if selected_month:
        month_start = pd.Timestamp(int(selected_year), int(selected_month), 1).date()
        month_end = (pd.Timestamp(int(selected_year), int(selected_month), 1) + pd.offsets.MonthEnd(0)).date()
        month_df = df[(df["date"].dt.date >= month_start) & (df["date"].dt.date <= month_end)]

        if month_df.empty:
            st.info("No data for selected month.")
        else:
            gross_m = month_df[fare_col].sum()
            driver_payout_m = month_df[driver_gross_col].sum()
            subscription_m = month_df[subscription_col].sum()
            cng_m = month_df[cng_col].sum()
            profit_m = gross_m - driver_payout_m - subscription_m - cng_m
            owner_percent_m = (profit_m / gross_m * 100) if gross_m else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("Gross Uber", f"₹{gross_m:,.0f}")
            c2.metric("Profit", f"₹{profit_m:,.0f}")
            c3.metric("Owner %", f"{owner_percent_m:.2f}%")
