import streamlit as st

import branding
from database import onboard_vehicle, get_vehicles_df


def vehicle_onboarding_page():
    branding.render_page_header("🚚 Vehicle Onboarding")

    st.write("Add a new vehicle and its compliance/maintenance dates.")

    with st.form("vehicle_onboarding_form"):
        c1, c2 = st.columns(2)

        with c1:
            vehicle_number = st.text_input("Vehicle Number", key="vehicle_number")
            date_of_purchase = st.date_input("Vehicle Purchase Date", key="date_of_purchase")
            permit_expiry = st.date_input("Permit Expiry Date", key="permit_expiry")

        with c2:
            insurance_expiry = st.date_input("Insurance Expiry Date", key="insurance_expiry")
            service_due_date = st.date_input("Service Due Date", key="service_due_date")

        submit = st.form_submit_button("Onboard Vehicle")

    if submit:
        success, payload = onboard_vehicle(
            vehicle_number=vehicle_number,
            date_of_purchase=date_of_purchase,
            permit_expiry=permit_expiry,
            insurance_expiry=insurance_expiry,
            service_due_date=service_due_date,
        )
        if not success:
            st.error(payload)
        else:
            st.success("Vehicle onboarded successfully.")
            st.rerun()

    st.subheader("Existing Vehicles")
    vehicles = get_vehicles_df()
    if vehicles.empty:
        st.info("No vehicles found.")
    else:
        st.dataframe(vehicles, use_container_width=True)

