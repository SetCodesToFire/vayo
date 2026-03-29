import streamlit as st

from driver_payout import driver_payout_page
from owner_dashboard import owner_dashboard_page
from driver_dashboard import driver_dashboard_page
from driver_leave_portal import driver_leave_portal_page
from driver_onboarding import driver_onboarding_page
from admin_leave_dashboard import admin_leave_dashboard_page
from database import init_db, authenticate_super_user, authenticate_driver, get_driver_profile

st.set_page_config(page_title="Vayo Dashboard", layout="wide")

# Initialize DB
init_db()

if "auth_logged_in" not in st.session_state:
    st.session_state.auth_logged_in = False
if "auth_role" not in st.session_state:
    st.session_state.auth_role = None
if "auth_driver_id" not in st.session_state:
    st.session_state.auth_driver_id = None
if "show_signup" not in st.session_state:
    st.session_state.show_signup = False

st.title("🚖 Vayo Cab Management System")

# -------------------------------
# SINGLE LOGIN GATE
# -------------------------------
if not st.session_state.auth_logged_in:
    if st.session_state.show_signup:
        st.subheader("🆕 Driver Signup")
        driver_onboarding_page()
        if st.button("← Back to Login", key="back_to_login_btn"):
            st.session_state.show_signup = False
            st.rerun()
    else:
        st.subheader("🔐 Login")
        with st.form("global_login_form"):
            username = st.text_input("Username / Phone Number")
            password = st.text_input("Password", type="password")
            login_submit = st.form_submit_button("Login")

        if login_submit:
            if authenticate_super_user(username.strip(), password):
                st.session_state.auth_logged_in = True
                st.session_state.auth_role = "admin"
                st.session_state.auth_driver_id = None
                st.success("Logged in as super user.")
                st.rerun()
            else:
                driver_id = authenticate_driver(username.strip(), password)
                if driver_id:
                    st.session_state.auth_logged_in = True
                    st.session_state.auth_role = "driver"
                    st.session_state.auth_driver_id = driver_id
                    st.success("Logged in as driver.")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")

        if st.button("Sign up as new driver", key="signup_btn"):
            st.session_state.show_signup = True
            st.rerun()
    st.stop()

# -------------------------------
# ROLE-BASED NAVIGATION
# -------------------------------
if st.session_state.auth_role == "admin":
    nav_options = [
        "💰 Driver Payout",
        "📊 Business Dashboard",
        "👨‍✈️ Driver Analytics",
        "📋 Driver Leave Dashboard",
        "🆕 Driver Onboarding",
    ]
    role_label = "Super User"
else:
    nav_options = ["🗓️ Driver Leave Portal"]
    role_label = "Driver"

with st.sidebar:
    st.success(f"Logged in as {role_label}")
    if st.session_state.auth_role == "driver":
        profile = get_driver_profile(st.session_state.auth_driver_id)
        if profile:
            st.caption(f"{profile['name']} ({profile['driver_id']})")
    if st.button("Logout", key="global_logout"):
        st.session_state.auth_logged_in = False
        st.session_state.auth_role = None
        st.session_state.auth_driver_id = None
        if "nav_page" in st.session_state:
            del st.session_state["nav_page"]
        st.rerun()

    if "nav_page" not in st.session_state or st.session_state.nav_page not in nav_options:
        st.session_state.nav_page = nav_options[0]

    page = st.radio("Navigation", nav_options, key="nav_page")

# -------------------------------
# ACCESS CONTROL (defense in depth)
# -------------------------------
if st.session_state.auth_role != "admin" and page != "🗓️ Driver Leave Portal":
    st.error("Access denied.")
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
elif page == "📋 Driver Leave Dashboard":
    admin_leave_dashboard_page()
elif page == "🆕 Driver Onboarding":
    driver_onboarding_page()
else:
    driver_leave_portal_page(driver_id=st.session_state.auth_driver_id)
