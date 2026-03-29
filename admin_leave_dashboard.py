import streamlit as st
from datetime import date

from database import get_admin_leave_dashboard_data


def admin_leave_dashboard_page():
    st.header("📋 Central Driver Leave Dashboard")

    today = date.today()
    col1, col2 = st.columns(2)
    with col1:
        selected_year = st.number_input(
            "Year",
            min_value=2020,
            max_value=2100,
            value=today.year,
            step=1,
        )
    with col2:
        month_options = {
            "All Months": None,
            "January": 1,
            "February": 2,
            "March": 3,
            "April": 4,
            "May": 5,
            "June": 6,
            "July": 7,
            "August": 8,
            "September": 9,
            "October": 10,
            "November": 11,
            "December": 12,
        }
        selected_month_label = st.selectbox("Month", list(month_options.keys()), index=0)

    selected_month = month_options[selected_month_label]
    data = get_admin_leave_dashboard_data(int(selected_year), selected_month)

    k1, k2, k3 = st.columns(3)
    k1.metric("Total Drivers", data["driver_count"])
    k2.metric("Total Leaves Taken", data["leave_count"])
    k3.metric("Avg Leaves / Driver", data["avg_leaves_per_driver"])

    st.subheader("👥 Driver-wise Leave Summary")
    if data["driver_summary"].empty:
        st.info("No drivers found.")
    else:
        st.dataframe(data["driver_summary"], use_container_width=True)

    st.subheader("📅 Leave History")
    if data["leave_history"].empty:
        st.info("No leave records found for selected period.")
    else:
        st.dataframe(data["leave_history"], use_container_width=True)
