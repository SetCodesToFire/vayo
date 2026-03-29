import streamlit as st
from datetime import date

from database import (
    authenticate_driver,
    get_driver_leave_summary,
    get_driver_leave_history,
    apply_driver_leave,
)


def driver_leave_portal_page():
    st.header("🗓️ Driver Leave Portal")

    if "leave_logged_in" not in st.session_state:
        st.session_state.leave_logged_in = False
    if "leave_driver_id" not in st.session_state:
        st.session_state.leave_driver_id = None
    if "leave_username" not in st.session_state:
        st.session_state.leave_username = None

    if not st.session_state.leave_logged_in:
        _render_login()
        return

    _render_driver_dashboard()


def _render_login():
    st.subheader("🔐 Driver Login")
    with st.form("driver_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_submit = st.form_submit_button("Login")

    if login_submit:
        driver_id = authenticate_driver(username.strip(), password)
        if driver_id:
            st.session_state.leave_logged_in = True
            st.session_state.leave_driver_id = driver_id
            st.session_state.leave_username = username.strip()
            st.success("Login successful.")
            st.rerun()
        else:
            st.error("Invalid username or password.")


def _render_driver_dashboard():
    today = date.today()
    driver_id = st.session_state.leave_driver_id
    username = st.session_state.leave_username

    top_col1, top_col2 = st.columns([4, 1])
    with top_col1:
        st.caption(f"Logged in as `{username}` ({driver_id})")
    with top_col2:
        if st.button("Logout"):
            st.session_state.leave_logged_in = False
            st.session_state.leave_driver_id = None
            st.session_state.leave_username = None
            st.rerun()

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
        if leave_date.year != today.year or leave_date.month != today.month:
            st.error("You can apply leave only for the current month.")
        else:
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
