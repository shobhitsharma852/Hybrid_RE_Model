from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

# Make project root importable when running: streamlit run dashboard/app.py
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from core.excel_option_engine import ExcelColMap
from dashboard.components.sidebar_inputs import render_sidebar
from dashboard.components.kpis import render_kpis
from dashboard.components.charts import render_charts_energy, render_charts_costs
from dashboard.services.option_service import load_base_model, run_option, summarize_totals


st.set_page_config(page_title="Hybrid RE Options Dashboard", layout="wide")

st.markdown(
    """
    <style>
    /* Remove ellipsis from metric values */
    div[data-testid="stMetricValue"] {
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: unset !important;
    }

    /* Allow labels to wrap nicely */
    div[data-testid="stMetricLabel"] {
        white-space: normal !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("Hybrid RE Options Dashboard ⚡")

st.divider()

# Demo file for public deployments
default_demo = str((ROOT / "data" / "demo" / "MH_BESS_Solar_Wind_DEMO.xlsx").resolve())


@st.cache_data(show_spinner=False)
def _cached_load_base(excel_path: str) -> pd.DataFrame:
    return load_base_model(excel_path, colmap=ExcelColMap())


# Sidebar inputs
ui = render_sidebar(default_excel_path=default_demo)
excel_input = ui.excel_input

try:
    if isinstance(excel_input, str):
        # Demo mode: use file path
        model_df = _cached_load_base(excel_input)
    else:
        # Upload mode: UploadedFile -> temp file path
        suffix = Path(excel_input.name).suffix.lower()
        if suffix not in [".xlsx", ".xls"]:
            st.error("Unsupported file type. Please upload .xlsx or .xls")
            st.stop()

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(excel_input.getbuffer())
            tmp_path = tmp.name

        model_df = _cached_load_base(tmp_path)
except Exception as e:
    st.error(f"Failed to load Excel/model_df.\n\n{e}")
    st.stop()

try:
    annual_df = run_option(model_df, ui.sizing, rates=ui.rates, colmap=ExcelColMap())
except Exception as e:
    st.error(f"Failed to compute option table.\n\n{e}")
    st.stop()

# KPIs (top row)
totals = summarize_totals(annual_df)
render_kpis(totals)

st.divider()

# Tabs

tab_overview, tab_energy, tab_costs = st.tabs(["Overview", "Energy", "Costs"])

with tab_overview:
    st.subheader("Annual TOD table")
    st.dataframe(annual_df, use_container_width=True)

with tab_energy:
    st.subheader("Energy charts")
    render_charts_energy(annual_df)

with tab_costs:
    st.subheader("Cost charts")
    render_charts_costs(annual_df)
