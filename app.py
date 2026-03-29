import streamlit as st

from driver_payout import driver_payout_page
from owner_dashboard import owner_dashboard_page
from driver_dashboard import driver_dashboard_page
from driver_leave_portal import driver_leave_portal_page
from driver_onboarding import driver_onboarding_page
from database import init_db, authenticate_super_user

st.set_page_config(page_title="Vayo Dashboard", layout="wide")

# Initialize DB
init_db()

if "super_user_logged_in" not in st.session_state:
    st.session_state.super_user_logged_in = False

ADMIN_PAGES = {
    "💰 Driver Payout",
    "📊 Business Dashboard",
    "👨‍✈️ Driver Analytics",
}
DRIVER_PAGES = ["🆕 Driver Onboarding", "🗓️ Driver Leave Portal"]
ADMIN_PAGES_ORDER = ["💰 Driver Payout", "📊 Business Dashboard", "👨‍✈️ Driver Analytics"]

st.title("🚖 Vayo Cab Management System")

# -------------------------------
# SIDEBAR: super user login + navigation
# -------------------------------
with st.sidebar:
    st.subheader("Navigation")

    if st.session_state.super_user_logged_in:
        st.success("Signed in as super user")
        if st.button("Admin logout", key="super_logout"):
            st.session_state.super_user_logged_in = False
            if st.session_state.get("nav_page") in ADMIN_PAGES:
                st.session_state.nav_page = DRIVER_PAGES[0]
            st.rerun()
    else:
        with st.expander("🔐 Super user (admin) login", expanded=False):
            st.caption("Required for Driver Payout, Business Dashboard, and Driver Analytics.")
            su_user = st.text_input("Username", key="super_username")
            su_pass = st.text_input("Password", type="password", key="super_password")
            if st.button("Log in as super user", key="super_login_btn"):
                if authenticate_super_user(su_user, su_pass):
                    st.session_state.super_user_logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid super user credentials.")

    if st.session_state.super_user_logged_in:
        nav_options = ADMIN_PAGES_ORDER + DRIVER_PAGES
    else:
        nav_options = DRIVER_PAGES

    if "nav_page" not in st.session_state or st.session_state.nav_page not in nav_options:
        st.session_state.nav_page = nav_options[0]

    page = st.radio(
        "Go to",
        nav_options,
        key="nav_page",
        label_visibility="collapsed",
    )

# -------------------------------
# ACCESS CONTROL (defense in depth)
# -------------------------------
if page in ADMIN_PAGES and not st.session_state.super_user_logged_in:
    st.error("Access denied. These pages are only available to super users. Use **Super user login** in the sidebar.")
    st.stop()

# -------------------------------
# PAGES
# -------------------------------
if page == "💰 Driver Payout":
    driver_payout_page()
elif page == "📊 Business Dashboard":
    owner_dashboard_page()
elif page == "👨‍✈️ Driver Analytics":
    driver_dashboard_page()
elif page == "🆕 Driver Onboarding":
    driver_onboarding_page()
else:
    driver_leave_portal_page()
