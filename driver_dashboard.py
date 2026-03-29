import streamlit as st
import pandas as pd
from database import get_dataframe

def driver_dashboard_page():

    st.header("👨‍✈️ Driver Analytics")

    df = get_dataframe()

    if df.empty:
        st.warning("No data available")
        return

    df['date'] = pd.to_datetime(df['date'])
    min_date = df['date'].min().date()
    max_date = df['date'].max().date()

    selected_dates = st.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # Streamlit date_input can return different shapes based on interaction state.
    # Normalize robustly to (start_date, end_date) as plain date objects.
    if isinstance(selected_dates, (tuple, list)):
        if len(selected_dates) == 2:
            start_date, end_date = selected_dates[0], selected_dates[1]
        elif len(selected_dates) == 1:
            start_date = end_date = selected_dates[0]
        else:
            start_date, end_date = min_date, max_date
    else:
        start_date = end_date = selected_dates

    # Defensive fallback for rare malformed values (e.g. nested tuple)
    if isinstance(start_date, (tuple, list)):
        start_date = start_date[0] if len(start_date) else min_date
    if isinstance(end_date, (tuple, list)):
        end_date = end_date[0] if len(end_date) else max_date

    filtered_df = df[
        (df['date'].dt.date >= start_date) &
        (df['date'].dt.date <= end_date)
    ]

    if filtered_df.empty:
        st.info("No trips found for the selected date range.")
        return

    # -------------------------------
    # SUMMARY
    # -------------------------------
    total_earning = filtered_df['net_payout'].sum()
    total_trips = len(filtered_df)
    total_drivers = filtered_df['driver'].nunique()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Earnings", f"₹{total_earning:,.0f}")
    col2.metric("Total Trips", total_trips)
    col3.metric("Active Drivers", total_drivers)

    # -------------------------------
    # DRIVER-WISE TABLE
    # -------------------------------
    st.subheader("👥 Driver Summary")

    driver_summary = filtered_df.groupby('driver').agg({
        'driver_gross': 'sum',
        'net_payout': 'sum'
    }).reset_index().sort_values('net_payout', ascending=False)

    st.dataframe(driver_summary)

    # -------------------------------
    # DAILY TABLE
    # -------------------------------
    st.subheader("📅 Daily Breakdown")

    daily = filtered_df.groupby(filtered_df['date'].dt.date).agg({
        'driver_gross': 'sum',
        'net_payout': 'sum'
    }).reset_index()

    st.dataframe(daily)

    st.bar_chart(daily.set_index('date')['net_payout'])