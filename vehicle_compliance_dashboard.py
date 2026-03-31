import streamlit as st
from datetime import date

import pandas as pd

import branding
from database import get_vehicles_df


def vehicle_compliance_dashboard_page():
    branding.render_page_header("🚚 Vehicle Compliance Dashboard")

    vehicles = get_vehicles_df()
    if vehicles.empty:
        st.info("No vehicles found.")
        return

    today = date.today()
    for col in ["permit_expiry", "insurance_expiry", "service_due_date"]:
        if col in vehicles.columns:
            vehicles[col] = pd.to_datetime(vehicles[col], errors="coerce").dt.date
            vehicles[f"{col}_days_left"] = vehicles[col].apply(
                lambda d: (d - today).days if pd.notna(d) else None
            )

    # Simple severity coloring in UI would require AgGrid; keep it as numbers + hints.
    st.subheader("Expiry Overview (Days Left)")
    st.dataframe(
        vehicles[
            [
                "vehicle_id",
                "vehicle_number",
                "permit_expiry",
                "permit_expiry_days_left",
                "insurance_expiry",
                "insurance_expiry_days_left",
                "service_due_date",
                "service_due_date_days_left",
            ]
        ],
        use_container_width=True,
    )

    st.caption("Rule of thumb: lower days-left means higher urgency.")

