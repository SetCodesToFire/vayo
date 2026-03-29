import streamlit as st

from driver_payout import driver_payout_page
from owner_dashboard import owner_dashboard_page
from driver_dashboard import driver_dashboard_page
from driver_leave_portal import driver_leave_portal_page
from database import init_db

st.set_page_config(page_title="Vayo Dashboard", layout="wide")

# Initialize DB
init_db()

st.title("🚖 Vayo Cab Management System")

# -------------------------------
# TOP NAVIGATION
# -------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "💰 Driver Payout",
    "📊 Business Dashboard",
    "👨‍✈️ Driver Analytics",
    "🗓️ Driver Leave Portal",

])

with tab1:
    driver_payout_page()

with tab2:
    owner_dashboard_page()

with tab3:
    driver_dashboard_page()

with tab4:
    driver_leave_portal_page()
