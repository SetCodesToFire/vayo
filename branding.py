"""Shared Vayo Cab Service branding (logo + titles)."""
import os
from pathlib import Path
from typing import Optional

import streamlit as st

_ROOT = Path(__file__).resolve().parent


def _logo_candidates():
    cwd = Path(os.getcwd()).resolve()
    env_pwd = Path(os.environ.get("PWD", "")).resolve() if os.environ.get("PWD") else None
    candidates = [
        _ROOT / "logo.png",
        cwd / "logo.png",
        cwd / "assets" / "logo.png",
        _ROOT.parent / "logo.png",
    ]
    if env_pwd:
        candidates.extend([
            env_pwd / "logo.png",
            env_pwd / "assets" / "logo.png",
        ])
    # Keep order, remove duplicates
    seen = set()
    unique = []
    for c in candidates:
        key = str(c)
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def logo_path() -> Optional[str]:
    for p in _logo_candidates():
        if p.is_file():
            return str(p)
    return None


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
    c1, c2 = st.columns([8])
    with c1:
        if path:
            st.image(path, width=56)
    with c2:
        st.markdown(f"## {title}")
