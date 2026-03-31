import streamlit as st
from datetime import date

import branding
from database import get_drivers_df, get_vehicles_df, assign_driver_to_vehicle, get_active_assignments_df


def driver_vehicle_assignment_page():
    branding.render_page_header("🧑‍🤝‍🧑 Attach Drivers to Vehicle")

    drivers = get_drivers_df()
    vehicles = get_vehicles_df()

    if drivers.empty:
        st.warning("No drivers found. Please onboard a driver first.")
        return
    if vehicles.empty:
        st.warning("No vehicles found. Please onboard a vehicle first.")
        return

    st.subheader("Assign an active vehicle to a driver")

    selected_date = st.date_input("Assignment Start Date", value=date.today(), key="assign_start_date")

    driver_options = {row.driver_id: f"{row.driver_name} ({row.driver_id})" for row in drivers.itertuples(index=False)}
    vehicle_options = {row.vehicle_id: f"{row.vehicle_number} ({row.vehicle_id})" for row in vehicles.itertuples(index=False)}

    c1, c2, c3 = st.columns([3, 3, 2])
    with c1:
        driver_id = st.selectbox("Driver", list(driver_options.keys()), format_func=lambda x: driver_options[x])
    with c2:
        vehicle_id = st.selectbox("Vehicle", list(vehicle_options.keys()), format_func=lambda x: vehicle_options[x])

    with c3:
        if st.button("Attach", key="attach_driver_vehicle"):
            success, message = assign_driver_to_vehicle(driver_id, vehicle_id, selected_date)
            if not success:
                st.error(message)
            else:
                st.success(message)
                st.rerun()

    st.subheader("Active Assignments")
    active_df = get_active_assignments_df(selected_date)
    if active_df.empty:
        st.info("No active assignments found for selected date.")
    else:
        st.dataframe(active_df, use_container_width=True)

