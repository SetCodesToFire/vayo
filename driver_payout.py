import streamlit as st
import pandas as pd
from processor import process_file
from database import save_to_db

def driver_payout_page():

    st.header("💰 Driver Payout System")

    # -------------------------------
    # SESSION STATE
    # -------------------------------
    if "results" not in st.session_state:
        st.session_state.results = None

    if "df" not in st.session_state:
        st.session_state.df = None

    if "processed_df" not in st.session_state:
        st.session_state.processed_df = None

    if "cng_per_driver" not in st.session_state:
        st.session_state.cng_per_driver = 0.0

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
            st.session_state.cng_per_driver = 0.0
            st.session_state.is_committed = False
            st.session_state.uploaded_file_signature = current_signature

            st.success("File uploaded successfully ✅")
        else:
            df = st.session_state.df

        st.dataframe(df.head())
    else:
        st.info("Step 1: Upload Uber CSV to continue.")
        return

    # -------------------------------
    # INPUTS
    # -------------------------------
    st.subheader("🧾 Payout Inputs")
    payout_date = st.date_input("Payout Date", key="driver_payout_date")
    st.session_state.selected_payout_date = payout_date

    st.subheader("⛽ Enter CNG Cost")

    cng_input = st.number_input("CNG Cost ₹", min_value=0.0, value=0.0, key="driver_cng")

    # -------------------------------
    # GENERATE
    # -------------------------------
    if st.session_state.df is not None:

        if st.button("🚀 Generate Payouts", key="generate_btn"):

            results, processed_df, cng_per_driver = process_file(st.session_state.df, cng_input)

            st.session_state.results = results
            st.session_state.processed_df = processed_df
            st.session_state.cng_per_driver = cng_per_driver
            st.session_state.is_committed = False

            st.success("✅ Payout PDFs generated successfully! Review and download, then click Save and Commit.")

    # -------------------------------
    # DOWNLOAD PDFs
    # -------------------------------
    if st.session_state.results:

        st.subheader("📥 Download Driver PDFs")

        for driver, file_path in st.session_state.results.items():

            with open(file_path, "rb") as f:

                st.download_button(
                    label=f"Download {driver}",
                    data=f,
                    file_name=file_path.split("/")[-1],
                    key=f"download_{driver}"
                )

        if st.button("💾 Save and Commit", key="save_commit_btn", disabled=st.session_state.is_committed):
            if st.session_state.processed_df is None:
                st.error("No generated payout data found. Please generate payouts first.")
            else:
                save_to_db(
                    st.session_state.processed_df,
                    st.session_state.selected_payout_date,
                    st.session_state.cng_per_driver
                )
                st.session_state.is_committed = True
                st.success("✅ Payout data committed to database.")