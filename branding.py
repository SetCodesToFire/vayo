"""Shared Vayo Cab Service branding (logo + titles)."""
from pathlib import Path
from typing import Optional

import streamlit as st

_ROOT = Path(__file__).resolve().parent
LOGO_PATH = _ROOT / "logo.png"


def logo_path() -> Optional[str]:
    p = LOGO_PATH
    return str(p) if p.is_file() else None


def render_sidebar_logo() -> None:
    path = logo_path()
    if path:
        st.image(path, width=120)
        st.caption("Vayo Cab Service")
    st.markdown("---")


def render_app_header(subtitle: str = "Management System") -> None:
    path = logo_path()
    c1, c2 = st.columns([1, 6])
    with c1:
        if path:
            st.image(path, width=80)
    with c2:
        st.markdown("### Vayo Cab Service")
        st.caption(subtitle)


def render_page_header(title: str) -> None:
    path = logo_path()
    c1, c2 = st.columns([1, 8])
    with c1:
        if path:
            st.image(path, width=56)
    with c2:
        st.markdown(f"## {title}")
