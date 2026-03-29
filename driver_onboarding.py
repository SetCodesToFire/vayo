import re
import streamlit as st

from database import onboard_driver


def driver_onboarding_page():
    st.header("🆕 Driver Onboarding")

    with st.form("driver_onboarding_form"):
        c1, c2 = st.columns(2)
        with c1:
            first_name = st.text_input("First Name")
            dl_number = st.text_input("DL Number")
            current_address = st.text_area("Current Address")
            phone_number = st.text_input("Personal Contact Number (Username)")
            password = st.text_input("Password", type="password")
        with c2:
            last_name = st.text_input("Last Name")
            aadhar_number = st.text_input("Aadhar Number")
            permanent_address = st.text_area("Permanent Address")
            emergency_contact = st.text_input("Emergency Contact Number")

        submit = st.form_submit_button("Onboard Driver")

    if not submit:
        return

    fields = {
        "First Name": first_name,
        "Last Name": last_name,
        "DL Number": dl_number,
        "Aadhar Number": aadhar_number,
        "Current Address": current_address,
        "Permanent Address": permanent_address,
        "Personal Contact Number": phone_number,
        "Emergency Contact Number": emergency_contact,
        "Password": password,
    }

    missing = [label for label, value in fields.items() if not str(value).strip()]
    if missing:
        st.error("All fields are mandatory.")
        return

    normalized_phone = re.sub(r"\D", "", phone_number)
    normalized_emergency = re.sub(r"\D", "", emergency_contact)
    if not normalized_phone or not normalized_emergency:
        st.error("Please enter valid contact numbers.")
        return

    if len(password) < 6:
        st.error("Password must be at least 6 characters.")
        return

    success, payload = onboard_driver(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        dl_number=dl_number.strip(),
        aadhar_number=aadhar_number.strip(),
        current_address=current_address.strip(),
        permanent_address=permanent_address.strip(),
        phone_number=normalized_phone,
        emergency_contact=normalized_emergency,
        password=password,
    )

    if not success:
        st.error(payload)
        return

    driver_id = payload["driver_id"]
    joining_date = payload["date_of_joining"]
    first_month_leaves = payload["first_month_leaves"]
    masked_aadhar = payload["masked_aadhar"]

    st.success("Driver onboarded successfully")
    c1, c2, c3 = st.columns(3)
    c1.metric("Driver ID", driver_id)
    c2.metric("Date of Joining", str(joining_date))
    c3.metric("Initial Month Leaves", first_month_leaves)
    st.caption(f"Aadhar: {masked_aadhar}")
