import re
import streamlit as st

from database import onboard_driver
import branding


def driver_onboarding_page():
    branding.render_page_header("🆕 Driver Onboarding")

    prefill_first = st.session_state.get("driver_onboarding_prefill_first_name", "")
    prefill_last = st.session_state.get("driver_onboarding_prefill_last_name", "")

    with st.form("driver_onboarding_form"):
        c1, c2 = st.columns(2)
        with c1:
            first_name = st.text_input("First Name", value=prefill_first, key="onb_first_name")
            dl_number = st.text_input("DL Number")
            current_address = st.text_area("Current Address")
            phone_number = st.text_input("Personal Contact Number (Username)")
            monthly_income_target = st.number_input(
                "Monthly Income Target (₹/month)",
                min_value=30000.0,
                value=30000.0,
                step=1000.0,
            )
            password = st.text_input("Password", type="password")
        with c2:
            last_name = st.text_input("Last Name", value=prefill_last, key="onb_last_name")
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
        "Monthly Income Target (₹/month)": monthly_income_target,
        "Password": password,
    }

    missing = [label for label, value in fields.items() if not str(value).strip()]
    if missing:
        st.error("All fields are mandatory.")
        return

    normalized_phone = re.sub(r"\D", "", phone_number)
    normalized_emergency = re.sub(r"\D", "", emergency_contact)
    normalized_aadhar = re.sub(r"\D", "", aadhar_number)
    normalized_dl = dl_number.strip().upper().replace(" ", "")

    # Simple format validation for common Indian identifiers
    phone_re = r"^\d{10,15}$"
    aadhar_re = r"^\d{12}$"
    dl_re = r"^[A-Z0-9]{8,20}$"

    if not re.match(phone_re, normalized_phone):
        st.error("Please enter a valid phone number (10-15 digits).")
        return
    if not re.match(phone_re, normalized_emergency):
        st.error("Please enter a valid emergency contact number (10-15 digits).")
        return
    if not re.match(aadhar_re, normalized_aadhar):
        st.error("Please enter a valid Aadhar number (12 digits).")
        return
    if not re.match(dl_re, normalized_dl):
        st.error("Please enter a valid DL number (8-20 alphanumeric characters).")
        return

    if len(password) < 6:
        st.error("Password must be at least 6 characters.")
        return

    success, payload = onboard_driver(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        dl_number=normalized_dl,
        aadhar_number=normalized_aadhar,
        current_address=current_address.strip(),
        permanent_address=permanent_address.strip(),
        phone_number=normalized_phone,
        emergency_contact=normalized_emergency,
        monthly_income_target=monthly_income_target,
        password=password,
    )

    if not success:
        st.error(payload)
        return

    # Clear any onboarding prefill once successfully created
    st.session_state.pop("driver_onboarding_prefill_first_name", None)
    st.session_state.pop("driver_onboarding_prefill_last_name", None)

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
