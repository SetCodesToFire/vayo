import streamlit as st
from datetime import date

import branding
from database import (
    get_driver_leave_summary,
    get_driver_leave_history,
    apply_driver_leave,
    get_driver_profile,
)


def driver_leave_portal_page(driver_id=None):
    branding.render_page_header("🗓️ Driver Leave Portal")
    if not driver_id:
        st.error("Driver session not found. Please log in again.")
        return
    _render_driver_dashboard(driver_id)


def _render_driver_dashboard(driver_id):
    today = date.today()
    profile = get_driver_profile(driver_id)

    top_col1, top_col2 = st.columns([4, 1])
    with top_col1:
        if profile:
            st.caption(
                f"Logged in as `{profile['name']}` ({driver_id}) • Phone: `{profile['phone_number']}` • Joined: `{profile['date_of_joining']}`"
            )
        else:
            st.caption(f"Logged in as `{driver_id}`")
    with top_col2:
        st.caption("Use sidebar logout")

    summary = get_driver_leave_summary(driver_id, today.year, today.month)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Month Leaves Left", summary["current_month_remaining"])
    c2.metric("Carry Forward Leaves", summary["carry_forward"])
    c3.metric("Total Available Leaves", summary["total_available"])
    c4.metric("Projected Year-End Bonus", f"₹{summary['projected_bonus']:,}")

    if summary["current_month_remaining"] <= 0:
        st.error("Monthly leave limit exceeded for current month.")
    if summary["total_available"] <= 0:
        st.error("No leaves available to apply.")

    st.subheader("📝 Apply Leave")
    with st.form("apply_leave_form"):
        leave_date = st.date_input("Select date", value=today)
        reason = st.text_area("Reason (optional)")
        apply_submit = st.form_submit_button("Apply Leave")

    if apply_submit:
        success, message = apply_driver_leave(driver_id, leave_date, reason)
        if success:
            st.success(message)
            st.rerun()
        else:
            st.error(message)

    st.subheader("📜 Leave History")
    history_df = get_driver_leave_history(driver_id)
    if history_df.empty:
        st.info("No leave records found.")
    else:
        st.dataframe(history_df, use_container_width=True)
