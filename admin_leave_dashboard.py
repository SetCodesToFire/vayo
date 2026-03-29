import streamlit as st
import pandas as pd
from datetime import date

from database import get_connection


def _fallback_admin_leave_dashboard_data(year, month=None):
    conn = get_connection()
    driver_df = pd.read_sql(
        """
        SELECT driver_id, first_name, last_name, phone_number, date_of_joining
        FROM drivers
        ORDER BY driver_id
        """,
        conn,
    )

    query = """
        SELECT driver_id, date, reason, month, year, leave_taken
        FROM driver_leaves
        WHERE year = %s
    """
    params = [year]
    if month:
        query += " AND month = %s"
        params.append(month)
    query += " ORDER BY date DESC"
    leave_df = pd.read_sql(query, conn, params=tuple(params))
    conn.close()

    if driver_df.empty:
        return {
            "driver_count": 0,
            "leave_count": 0,
            "avg_leaves_per_driver": 0.0,
            "driver_summary": pd.DataFrame(),
            "leave_history": pd.DataFrame(),
        }

    if leave_df.empty:
        driver_summary = driver_df.copy()
        driver_summary["driver_name"] = (
            driver_summary["first_name"].fillna("") + " " + driver_summary["last_name"].fillna("")
        ).str.strip()
        driver_summary["leaves_taken"] = 0
        driver_summary["last_leave_date"] = pd.NaT
        driver_summary = driver_summary[
            ["driver_id", "driver_name", "phone_number", "date_of_joining", "leaves_taken", "last_leave_date"]
        ]
        return {
            "driver_count": int(len(driver_summary)),
            "leave_count": 0,
            "avg_leaves_per_driver": 0.0,
            "driver_summary": driver_summary,
            "leave_history": pd.DataFrame(),
        }

    leave_df["date"] = pd.to_datetime(leave_df["date"], errors="coerce")
    leave_counts = (
        leave_df.groupby("driver_id")
        .agg(leaves_taken=("leave_taken", "sum"), last_leave_date=("date", "max"))
        .reset_index()
    )
    driver_summary = driver_df.merge(leave_counts, on="driver_id", how="left")
    driver_summary["driver_name"] = (
        driver_summary["first_name"].fillna("") + " " + driver_summary["last_name"].fillna("")
    ).str.strip()
    driver_summary["leaves_taken"] = driver_summary["leaves_taken"].fillna(0).astype(int)
    driver_summary = driver_summary[
        ["driver_id", "driver_name", "phone_number", "date_of_joining", "leaves_taken", "last_leave_date"]
    ].sort_values(["leaves_taken", "driver_name"], ascending=[False, True])

    leave_history = leave_df.merge(
        driver_df[["driver_id", "first_name", "last_name"]],
        on="driver_id",
        how="left",
    )
    leave_history["driver_name"] = (
        leave_history["first_name"].fillna("") + " " + leave_history["last_name"].fillna("")
    ).str.strip()
    leave_history = leave_history[["driver_id", "driver_name", "date", "reason", "month", "year"]]

    total_drivers = int(len(driver_summary))
    total_leaves = int(driver_summary["leaves_taken"].sum())
    avg_leaves = round(total_leaves / total_drivers, 2) if total_drivers else 0.0
    return {
        "driver_count": total_drivers,
        "leave_count": total_leaves,
        "avg_leaves_per_driver": avg_leaves,
        "driver_summary": driver_summary,
        "leave_history": leave_history,
    }


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
    try:
        from database import get_admin_leave_dashboard_data

        data = get_admin_leave_dashboard_data(int(selected_year), selected_month)
    except ImportError:
        data = _fallback_admin_leave_dashboard_data(int(selected_year), selected_month)

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
