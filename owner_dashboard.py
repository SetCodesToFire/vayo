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

    # -------------------------------
    # DATE FILTER
    # -------------------------------
    selected_date = st.date_input("Select Date", key="owner_date")

    day_df = df[df['date'].dt.date == selected_date]

    if day_df.empty:
        st.warning("No data for selected date")
        return

    # -------------------------------
    # INPUTS
    # -------------------------------
    col1, col2 = st.columns(2)

    with col1:
        subscription = st.number_input("Subscription Cost", value=0)

    with col2:
        cng_extra = st.number_input("Extra CNG Adjustment", value=0)

    # -------------------------------
    # CALCULATIONS
    # -------------------------------
    gross_uber = day_df['driver_gross'].sum()
    driver_payout = day_df['net_payout'].sum()
    cng = day_df['cng'].sum() + cng_extra

    owner_earning = gross_uber - driver_payout - subscription - cng
    owner_percent = (owner_earning / gross_uber * 100) if gross_uber else 0

    # -------------------------------
    # DISPLAY
    # -------------------------------
    col1, col2, col3 = st.columns(3)

    col1.metric("Gross Uber Earnings", f"₹{gross_uber:,.0f}")
    col2.metric("Driver Payout", f"₹{driver_payout:,.0f}")
    col3.metric("Owner Earnings", f"₹{owner_earning:,.0f}")

    st.metric("Owner %", f"{owner_percent:.2f}%")

    # -------------------------------
    # DATE-WISE SUMMARY
    # -------------------------------
    st.subheader("📅 Date-wise Summary")

    summary = df.groupby(df['date'].dt.date).agg({
        'driver_gross': 'sum',
        'net_payout': 'sum',
        'cng': 'sum'
    }).reset_index()

    st.dataframe(summary)
