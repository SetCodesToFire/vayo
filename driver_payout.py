import streamlit as st
import pandas as pd
import os
from processor import calculate_driver_payouts, generate_driver_pdfs
from database import (
    save_to_db,
    resolve_driver_id_by_full_name,
    get_active_vehicle_for_driver,
    upsert_vehicle_cng,
    get_pending_payouts_for_date_df,
    mark_payouts_paid_for_date,
)
import branding

def driver_payout_page():

    branding.render_page_header("💰 Driver Payout System")

    # -------------------------------
    # SESSION STATE
    # -------------------------------
    if "results" not in st.session_state:
        st.session_state.results = None

    if "df" not in st.session_state:
        st.session_state.df = None

    if "processed_df" not in st.session_state:
        st.session_state.processed_df = None
    if "adjusted_df" not in st.session_state:
        st.session_state.adjusted_df = None

    if "vehicle_cng_inputs" not in st.session_state:
        st.session_state.vehicle_cng_inputs = {}

    if "cash_delta_inputs" not in st.session_state:
        st.session_state.cash_delta_inputs = {}

    if "selected_payout_date" not in st.session_state:
        st.session_state.selected_payout_date = None

    if "is_committed" not in st.session_state:
        st.session_state.is_committed = False

    if "uploaded_file_signature" not in st.session_state:
        st.session_state.uploaded_file_signature = None

    # -------------------------------
    # FILE UPLOAD
    # -------------------------------
    uploaded_file = st.file_uploader("Upload Uber CSV", type=["csv"], key="driver_upload")

    if uploaded_file:
        current_signature = (uploaded_file.name, uploaded_file.size)

        # Only reset state when user uploads a new/different file.
        if st.session_state.uploaded_file_signature != current_signature:
            df = pd.read_csv(uploaded_file)
            df.columns = df.columns.str.strip()

            st.session_state.df = df
            st.session_state.results = None
            st.session_state.processed_df = None
            st.session_state.adjusted_df = None
            st.session_state.vehicle_cng_inputs = {}
            st.session_state.cash_delta_inputs = {}
            st.session_state.is_committed = False
            st.session_state.uploaded_file_signature = current_signature

            st.success("File uploaded successfully ✅")
        else:
            df = st.session_state.df

        with st.expander("Preview uploaded data", expanded=False):
            st.dataframe(df.head())
    else:
        st.info("Step 1: Upload Uber CSV to continue.")
        return

    # -------------------------------
    # INPUTS + GENERATE (submit-based)
    # -------------------------------
    st.subheader("🧾 Payout Inputs")
    st.caption("Flow: Upload CSV -> Generate Sheet -> (optional) cash/CNG adjustments -> Generate PDFs -> Save & Commit")
    with st.form("payout_generate_form", clear_on_submit=False):
        payout_date_input = st.date_input(
            "Payout Date",
            value=st.session_state.selected_payout_date or pd.Timestamp.today().date(),
            key="driver_payout_date",
        )
        generate_sheet_submit = st.form_submit_button("🚀 Generate / Refresh Payout Sheet")

    if generate_sheet_submit:
        st.session_state.selected_payout_date = payout_date_input
        base_df = calculate_driver_payouts(st.session_state.df)

        # Resolve driver_id + active vehicle per payout date
        base_df["driver_id"] = base_df["Driver"].apply(resolve_driver_id_by_full_name)
        base_df["vehicle_id"] = base_df["driver_id"].apply(
            lambda did: get_active_vehicle_for_driver(did, st.session_state.selected_payout_date) if did else None
        )

        missing_driver = base_df[base_df["driver_id"].isna()]
        if not missing_driver.empty:
            examples_list = missing_driver["Driver"].astype(str).head(10).tolist()
            examples = ", ".join(examples_list)
            st.warning(
                "Some Uber drivers are not onboarded yet (driver name mismatch). "
                f"Examples: {examples}"
            )

            if st.button("➕ Create missing driver(s) (open onboarding)", key="missing_drivers_onboard_btn"):
                # Prefill onboarding for the first missing driver (others will need manual follow-up)
                first_missing = examples_list[0] if examples_list else ""
                parts = str(first_missing).strip().split()
                pre_last = parts[-1].upper() if parts else ""
                pre_first = " ".join(parts[:-1]).upper() if len(parts) > 1 else ""

                st.session_state["driver_onboarding_prefill_first_name"] = pre_first.title() if pre_first else ""
                st.session_state["driver_onboarding_prefill_last_name"] = pre_last.title() if pre_last else ""

                # Redirect to onboarding
                st.session_state["nav_page"] = "🆕 Driver Onboarding"
                st.rerun()

            st.stop()
        else:
            # Note: if vehicle_id is missing for some drivers, we still allow generation.
            # Those drivers will get CNG = 0 because vehicle CNG allocation only applies to drivers with a vehicle.
            st.session_state.processed_df = base_df
            st.session_state.adjusted_df = None
            st.session_state.results = None
            st.session_state.is_committed = False

            # Initialize editable inputs
            st.session_state.cash_delta_inputs = {d: 0.0 for d in base_df["Driver"].tolist()}
            st.session_state.vehicle_cng_inputs = {v: 0.0 for v in sorted([vid for vid in base_df["vehicle_id"].unique().tolist() if vid])}

            st.success("✅ Payout sheet ready. Add adjustments if needed, then generate PDFs.")

    # -------------------------------
    # EDIT CASH DELTAS + VEHICLE CNG
    # -------------------------------
    if st.session_state.processed_df is not None and not st.session_state.processed_df.empty:
        # Wrap adjustment inputs in a form so Streamlit doesn't rerun on every keystroke.
        with st.form("payout_adjustments_form", clear_on_submit=False):
            st.subheader("✏️ Adjust Cash Collected (delta add/subtract)")

            adjusted_df = st.session_state.processed_df.copy()
            cash_delta_inputs_local = {}

            for i, row in adjusted_df.iterrows():
                driver_name = row["Driver"]
                key = f"cash_delta_{i}"
                default_val = float(st.session_state.cash_delta_inputs.get(driver_name, 0.0))
                delta = st.number_input(
                    f"Cash delta for {driver_name} (₹)",
                    value=default_val,
                    step=1.0,
                    key=key,
                )
                cash_delta_inputs_local[driver_name] = float(delta)
                adjusted_df.at[i, "cash_adjustment"] = float(delta)
                adjusted_df.at[i, "Cash_Collected"] = float(row["Cash_Collected"]) + float(delta)
                adjusted_df.at[i, "Net_Payout"] = float(row["Driver_Gross"]) + float(row["Cash_Collected"] + delta) + float(
                    row["Tip"]
                )

            st.subheader("⛽ Daily CNG Input")
            vehicle_ids = sorted([vid for vid in adjusted_df["vehicle_id"].dropna().unique().tolist() if vid])
            vehicle_cng_inputs_local = {}
            c1, c2 = st.columns(2)
            with c1:
                # Fallback when no vehicle assignments exist for selected date.
                vehicle_cng_inputs_local["__TOTAL__"] = st.number_input(
                    f"Total CNG for {st.session_state.selected_payout_date} (₹)",
                    value=float(st.session_state.vehicle_cng_inputs.get("__TOTAL__", 0.0)),
                    min_value=0.0,
                    step=100.0,
                    key="cng_total_fallback",
                )
                st.info(
                    "Total CNG will be split equally across generated drivers."
                )
            with c2:
                st.caption("CNG affects owner profit calculations.")

            submit_generate_pdfs = st.form_submit_button("📄 Generate Payout PDFs")

        if submit_generate_pdfs:
            # Persist values for next rerun
            st.session_state.cash_delta_inputs = cash_delta_inputs_local
            st.session_state.vehicle_cng_inputs = vehicle_cng_inputs_local

            adjusted_df_final = adjusted_df.copy()
            adjusted_df_final["cng"] = 0.0

            if vehicle_ids:
                for vid in vehicle_ids:
                    drivers_for_vehicle = adjusted_df_final[adjusted_df_final["vehicle_id"] == vid]
                    count = len(drivers_for_vehicle)
                    cng_per_driver = (float(vehicle_cng_inputs_local.get(vid, 0.0)) / count) if count else 0.0
                    adjusted_df_final.loc[drivers_for_vehicle.index, "cng"] = cng_per_driver
            else:
                total_cng = float(vehicle_cng_inputs_local.get("__TOTAL__", 0.0))
                count = len(adjusted_df_final)
                cng_per_driver = (total_cng / count) if count else 0.0
                adjusted_df_final["cng"] = cng_per_driver

            adjusted_df_final["payment_status"] = "Pending"

            today_folder = st.session_state.selected_payout_date.strftime("%Y-%m-%d")
            output_folder = os.path.join("outputs", today_folder)
            os.makedirs(output_folder, exist_ok=True)

            results = generate_driver_pdfs(adjusted_df_final, output_folder)
            st.session_state.results = results
            st.session_state.adjusted_df = adjusted_df_final
            st.session_state.is_committed = False
            st.success("✅ PDFs generated. Download them now, then click Save and Commit.")

    # -------------------------------
    # DOWNLOAD PDFs + COMMIT
    # -------------------------------
    if st.session_state.results:
        st.subheader("📥 Download Driver PDFs")
        for driver, file_path in st.session_state.results.items():
            with open(file_path, "rb") as f:
                st.download_button(
                    label=f"Download {driver}",
                    data=f,
                    file_name=file_path.split("/")[-1],
                    key=f"download_{driver}",
                )

        if st.button("💾 Save and Commit", key="save_commit_btn", disabled=st.session_state.is_committed):
            if st.session_state.adjusted_df is None:
                st.error("No payout data found. Generate PDFs first.")
            else:
                # Save vehicle CNG once per vehicle for this date
                for vid, cng_amt in st.session_state.vehicle_cng_inputs.items():
                    upsert_vehicle_cng(vid, st.session_state.selected_payout_date, cng_amt)

                save_to_db(st.session_state.adjusted_df, st.session_state.selected_payout_date)
                st.session_state.is_committed = True
                st.success("✅ Payout data committed to database.")

    # Payment status management (admin)
    if st.session_state.selected_payout_date:
        show_payment_status = st.toggle("Show payout payment status section", value=False, key="show_payout_status_toggle")
        if show_payment_status:
            st.subheader("💳 Payout Payment Status")
            pending_df = get_pending_payouts_for_date_df(st.session_state.selected_payout_date)
            if pending_df.empty:
                st.info("No pending payouts for the selected date.")
            else:
                st.dataframe(pending_df, use_container_width=True)
                if st.button("✅ Mark All Pending as Paid", key="mark_all_paid"):
                    mark_payouts_paid_for_date(st.session_state.selected_payout_date)
                    st.success("✅ Updated payout status to Paid.")
                    st.rerun()
