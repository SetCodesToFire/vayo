import streamlit as st
import pandas as pd

import branding
from datetime import date

from database import get_pending_leaves_df, set_leave_status


def leave_approvals_page():
    branding.render_page_header("📩 Leave Approvals")

    today = date.today()
    st.caption("Approve or reject pending driver leaves.")

    c1, c2 = st.columns(2)
    with c1:
        selected_year = st.number_input(
            "Year",
            min_value=2020,
            max_value=2100,
            value=int(today.year),
            step=1,
        )
    with c2:
        month_map = {"All Months": None}
        month_map.update(
            {
                "January": 1,
                "February": 2,
                "March": 3,
                "April": 4,
                "May": 5,
                "June": 6,
                "July": 7,
                "August": 8,
                "September": 9,
                "October": 10,
                "November": 11,
                "December": 12,
            }
        )
        selected_month_label = st.selectbox("Month", list(month_map.keys()), index=0)
        selected_month = month_map[selected_month_label]

    pending_df = get_pending_leaves_df(int(selected_year), selected_month)

    pending_count = 0 if pending_df is None else len(pending_df)
    st.subheader(f"⏳ Pending Leaves ({pending_count})")

    if pending_df.empty:
        st.info("No pending leaves found for the selected filter.")
        return

    display_cols = [
        "id",
        "driver_id",
        "driver_name",
        "date",
        "month",
        "year",
        "reason",
        "leave_status",
    ]
    display_df = pending_df[display_cols].copy()
    if "date" in display_df.columns:
        display_df["date"] = pd.to_datetime(display_df["date"]).dt.date

    st.dataframe(display_df, use_container_width=True)

    # Simple approval controls
    pending_ids = pending_df["id"].tolist()
    selected_leave_id = st.selectbox("Select Leave ID to approve/reject", pending_ids)

    colm1, colm2 = st.columns(2)
    with colm1:
        if st.button("✅ Approve selected", key="approve_selected"):
            ok, msg = set_leave_status(selected_leave_id, "Approved")
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    with colm2:
        if st.button("❌ Reject selected", key="reject_selected"):
            ok, msg = set_leave_status(selected_leave_id, "Rejected")
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

