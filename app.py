import streamlit as st

from driver_payout import driver_payout_page
from owner_dashboard import owner_dashboard_page
from driver_dashboard import driver_dashboard_page
from driver_leave_portal import driver_leave_portal_page
from driver_onboarding import driver_onboarding_page
from database import init_db

st.set_page_config(page_title="Vayo Dashboard", layout="wide")

# Initialize DB
init_db()

st.title("🚖 Vayo Cab Management System")

# -------------------------------
# SIDEBAR NAVIGATION
# -------------------------------
page = st.sidebar.radio(
    "Navigation",
    [
        "💰 Driver Payout",
        "📊 Business Dashboard",
        "👨‍✈️ Driver Analytics",
        "🆕 Driver Onboarding",
        "🗓️ Driver Leave Portal",
    ],
)

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
