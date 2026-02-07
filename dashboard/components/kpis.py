# dashboard/components/kpis.py
from __future__ import annotations

import streamlit as st


def _fmt_kwh(v: float) -> str:
    if v is None:
        return "-"
    try:
        v = float(v)
    except Exception:
        return "-"
    return f"{v:,.0f} kWh"


def _fmt_rs(v: float) -> str:
    if v is None:
        return "-"
    try:
        v = float(v)
    except Exception:
        return "-"
    return f"₹ {v:,.0f}"


def render_kpis(totals: dict):
    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Total Load", _fmt_kwh(totals.get("load_kwh", 0.0)))
    c2.metric("Total RE", _fmt_kwh(totals.get("total_re_kwh", 0.0)))
    c3.metric("RE %", f"{totals.get('re_percent', 0.0):.1f}%")
    c4.metric("Grid Import", _fmt_kwh(totals.get("grid_kwh", 0.0)))
    c5.metric("Total Cost", _fmt_rs(totals.get("total_cost_rs", totals.get("grid_cost_rs", 0.0))))
