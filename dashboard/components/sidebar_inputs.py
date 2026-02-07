from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union

import streamlit as st

from core.excel_option_engine import OptionSizing

# Slot display order used across tables/charts
SLOT_ORDER = ["A", "C", "B", "D"]

# Only 2 options: Typical, Custom
SOLAR_RATE_PLANS = {
    "Typical": {"A": 5.05, "C": 5.05, "B": 5.05, "D": 5.05},
    "Custom": None,
}
WIND_RATE_PLANS = {
    "Typical": {"A": 5.65, "C": 5.65, "B": 5.65, "D": 5.65},
    "Custom": None,
}
BESS_RATE_PLANS = {
    "Typical": {"A": 6.00, "C": 6.00, "B": 6.00, "D": 6.00},
    "Custom": None,
}
GRID_TOD_PLANS = {
    "Typical": {"A": 6.84, "C": 9.16, "B": 6.30, "D": 9.46},
    "Custom": None,
}


@dataclass
class SidebarResult:
    sizing: OptionSizing
    rates: dict
    excel_input: Any  # str (demo path) OR UploadedFile
    

def _slot_rate_selector(title: str, plans: dict[str, dict[str, float] | None]) -> dict[str, float]:
    st.sidebar.markdown(f"### {title} rates (₹/kWh)")

    plan = st.sidebar.selectbox(
        f"{title} plan",
        options=list(plans.keys()),
        index=0,
        key=f"{title}_plan",
    )

    defaults = plans["Typical"]

    if plan == "Typical":
        preset = defaults
        st.sidebar.caption(
            f"Slots: A {preset['A']:.2f} | C {preset['C']:.2f} | B {preset['B']:.2f} | D {preset['D']:.2f}"
        )
        return dict(preset)

    # Custom mode: inputs inside expander
    with st.sidebar.expander(f"Edit {title} slot rates", expanded=False):
        out = {}
        for s in ["A", "C", "B", "D"]:
            out[s] = float(
                st.number_input(
                    f"Slot {s}",
                    min_value=0.0,
                    value=float(defaults[s]),
                    step=0.01,
                    key=f"{title}_{s}",
                )
            )

    st.sidebar.caption(
        f"Custom: A {out['A']:.2f} | C {out['C']:.2f} | B {out['B']:.2f} | D {out['D']:.2f}"
    )
    return out


def render_sidebar(default_excel_path: str) -> SidebarResult:
    """Render sidebar controls and return a single structured object."""

    # --- Logo at top (PNG) ---
    ROOT = Path(__file__).resolve().parents[2]
    logo_path = ROOT / "assets" / "insolare_logo.png"
    if logo_path.exists():
        st.sidebar.image(str(logo_path), use_container_width=True)

    # Slightly tighter spacing under logo
    st.sidebar.markdown("<hr style='margin:6px 0 12px 0;'>", unsafe_allow_html=True)

    st.sidebar.header("Inputs")

    # --- Dual mode: demo vs upload ---
    mode = st.sidebar.radio(
        "Data source",
        ["Use demo file", "Upload my Excel"],
        index=0,
    )

    if mode == "Use demo file":
        excel_input = default_excel_path
    else:
        uploaded_file = st.sidebar.file_uploader(
            "Upload Excel",
            type=["xlsx", "xls"],
            help="Upload your Hybrid RE Excel input file",
        )
        if uploaded_file is None:
            st.sidebar.info("Upload an Excel file to continue.")
            st.stop()
        excel_input = uploaded_file

    # --- Sizing ---
    st.sidebar.subheader("Plant sizing")
    load_mw = st.sidebar.number_input("Load (MW)", min_value=0.0, value=1.0, step=0.1)

    solar_mode = st.sidebar.selectbox("Solar mode", options=["None", "FT", "SAT", "EW"], index=2)
    solar_dc_mwp = st.sidebar.number_input("Solar DC size (MWp)", min_value=0.0, value=1.74, step=0.01)
    solar_loss_pct = st.sidebar.number_input("Solar loss (%)", min_value=0.0, max_value=99.0, value=10.0, step=0.5)

    wind_mw = st.sidebar.number_input("Wind (MW)", min_value=0.0, value=0.0, step=0.1)
    wind_loss_pct = st.sidebar.number_input("Wind loss (%)", min_value=0.0, max_value=99.0, value=0.0, step=0.5)

    # --- Rates ---
    solar_rate_map = _slot_rate_selector("Solar", SOLAR_RATE_PLANS)
    wind_rate_map = _slot_rate_selector("Wind", WIND_RATE_PLANS)
    bess_rate_map = _slot_rate_selector("BESS", BESS_RATE_PLANS)
    grid_rate_map = _slot_rate_selector("Grid TOD", GRID_TOD_PLANS)



    sizing = OptionSizing(
        load_mw=float(load_mw),
        solar_mode=None if solar_mode == "None" else solar_mode,
        solar_mw=float(solar_dc_mwp),
        solar_loss=float(solar_loss_pct) / 100.0,
        wind_mw=float(wind_mw),
        wind_loss=float(wind_loss_pct) / 100.0,
        
    )

    rates = {
        "solar_rate_map": solar_rate_map,
        "wind_rate_map": wind_rate_map,
        "bess_rate_map": bess_rate_map,
        "grid_rate_map": grid_rate_map,
    }

    return SidebarResult(
        sizing=sizing,
        rates=rates,
        excel_input=excel_input,
        
    )
