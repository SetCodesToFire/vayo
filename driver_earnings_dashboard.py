import calendar
from datetime import date, timedelta

import pandas as pd
import streamlit as st

import branding
from database import (
    get_driver_payouts_df,
    get_driver_pending_payouts_df,
    get_driver_monthly_leave_count,
    get_monthly_target,
    set_monthly_target,
    get_driver_profile,
)


def driver_earnings_dashboard_page(driver_id):
    branding.render_page_header("📈 Driver Earnings & Scores")

    profile = get_driver_profile(driver_id)
    if profile:
        st.caption(f"Driver: {profile['name']} ({driver_id})")

    today = date.today()
    year = today.year
    month = today.month

    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    payouts_month_df = get_driver_payouts_df(driver_id, month_start, today)
    total_earning = float(payouts_month_df["driver_gross"].sum()) if not payouts_month_df.empty else 0.0
    total_trips = float(payouts_month_df["trips_count"].sum()) if not payouts_month_df.empty else 0.0

    target = float(get_monthly_target(driver_id, year, month))
    if target <= 0:
        target = 0.0

    earnings_score = 0.0
    if target > 0:
        earnings_score = min(5.0, (total_earning / target) * 5.0)

    per_trip = (total_earning / total_trips) if total_trips > 0 else 0.0
    if per_trip > 350:
        efficiency_score = 5
    elif 300 <= per_trip <= 350:
        efficiency_score = 4
    elif 250 <= per_trip <= 300:
        efficiency_score = 3
    elif 200 <= per_trip <= 250:
        efficiency_score = 2
    else:
        efficiency_score = 1

    leaves_count = get_driver_monthly_leave_count(driver_id, year, month)
    if leaves_count <= 2:
        attendance_score = 5
    elif leaves_count == 3:
        attendance_score = 4
    elif leaves_count == 4:
        attendance_score = 3
    elif leaves_count == 5:
        attendance_score = 2
    else:
        attendance_score = 1

    rating_score = (earnings_score * 0.5) + (efficiency_score * 0.3) + (attendance_score * 0.2)

    # Incentive eligibility rules
    incentive = 0
    if rating_score > 4:
        incentive = 1500
    elif round(rating_score) == 3:
        incentive = 1000

    st.subheader("📊 Monthly Progress")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Monthly Earnings", f"₹{total_earning:,.0f}")
    col2.metric("Trips", f"{int(total_trips)}")
    col3.metric("Monthly Target", f"₹{target:,.0f}")
    col4.metric("Projected Incentive", f"₹{incentive:,.0f}")

    # Target progress + daily required
    amount_left = max(0.0, target - total_earning)
    days_left_including_today = max(1, (month_end - today).days + 1)
    daily_left = (amount_left / days_left_including_today) if amount_left > 0 else 0.0

    c5, c6 = st.columns(2)
    c5.metric("Amount Left to Target", f"₹{amount_left:,.0f}")
    c6.metric("Daily Left (to reach by month end)", f"₹{daily_left:,.0f}")
    st.caption(f"Calculated across {days_left_including_today} day(s) remaining in this month (including today).")

    st.subheader("🎯 Set Monthly Income Target")
    with st.form("monthly_target_form"):
        target_input = st.number_input("Target (₹/month)", min_value=0.0, value=target, step=100.0)
        submitted = st.form_submit_button("Save Target")
        if submitted:
            set_monthly_target(driver_id, year, month, target_input)
            st.success("Target updated.")
            st.rerun()

    st.subheader("⭐ Rating Breakdown (Current Month)")
    r1, r2, r3, r4, r5 = st.columns(5)
    r4.metric("Rating Score", f"{rating_score:.2f}/5")

    st.subheader("📈 Earnings Trend")
    # 1 week trend
    week_start = today - timedelta(days=6)
    week_df = get_driver_payouts_df(driver_id, week_start, today)
    if not week_df.empty:
        week_df["date"] = pd.to_datetime(week_df["date"])
        week_daily = week_df.groupby(week_df["date"].dt.date)["driver_gross"].sum().reset_index()
        week_daily = week_daily.rename(columns={"driver_gross": "daily_earning"})
        st.caption("Last 7 days")
        st.line_chart(week_daily.set_index(week_daily.columns[0])["daily_earning"])
    else:
        st.info("No earnings data for last 7 days.")

    # 30 days trend
    month_start_30 = today - timedelta(days=29)
    df30 = get_driver_payouts_df(driver_id, month_start_30, today)
    if not df30.empty:
        df30["date"] = pd.to_datetime(df30["date"])
        monthly_daily = df30.groupby(df30["date"].dt.date)["driver_gross"].sum().reset_index()
        monthly_daily = monthly_daily.rename(columns={"driver_gross": "daily_earning"})
        st.caption("Last 30 days")
        st.line_chart(monthly_daily.set_index(monthly_daily.columns[0])["daily_earning"])
    else:
        st.info("No earnings data for last 30 days.")

    st.subheader("⏳ Pending Payouts")
    pending_df = get_driver_pending_payouts_df(driver_id)
    if pending_df.empty:
        st.info("No pending payouts.")
    else:
        st.dataframe(pending_df[["date", "driver_gross", "payment_status", "trips_count"]], use_container_width=True)

