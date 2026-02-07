from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

SLOT_ORDER = ["A", "C", "B", "D"]


def _slot_df(df: pd.DataFrame) -> pd.DataFrame:
    """Remove Total row and enforce A,C,B,D ordering."""
    out = df.copy()
    if "tod_slot" not in out.columns:
        return out

    out["tod_slot"] = out["tod_slot"].astype(str)
    out = out[out["tod_slot"].str.lower() != "total"].copy()
    out["tod_slot"] = pd.Categorical(out["tod_slot"], categories=SLOT_ORDER, ordered=True)
    out = out.sort_values("tod_slot")
    return out


def _has_cols(df: pd.DataFrame, cols: list[str]) -> bool:
    return all(c in df.columns for c in cols)


def render_charts_energy(annual_df: pd.DataFrame) -> None:
    """Energy tab: clean layout."""
    df = _slot_df(annual_df)

    energy_cols = [c for c in ["load_kwh", "solar_kwh", "wind_kwh", "total_re_kwh", "grid_kwh"] if c in df.columns]
    if not energy_cols:
        st.info("No energy columns found to plot.")
        return

    melt = df.melt(id_vars=["tod_slot"], value_vars=energy_cols, var_name="metric", value_name="kwh")
    fig1 = px.bar(melt, x="tod_slot", y="kwh", color="metric", barmode="group", title="Energy by TOD slot")
    st.plotly_chart(fig1, use_container_width=True, key="energy_by_slot")

    c1, c2 = st.columns(2, gap="large")

    with c1:
        if "re_percent" in df.columns:
            fig2 = px.bar(df, x="tod_slot", y="re_percent", title="RE % by TOD slot")
            st.plotly_chart(fig2, use_container_width=True, key="re_percent_by_slot")
        else:
            st.info("re_percent not available.")

    with c2:
        if _has_cols(df, ["solar_kwh", "grid_kwh"]):
            fig3 = px.bar(df, x="tod_slot", y=["solar_kwh", "grid_kwh"], barmode="group", title="Solar vs Grid (kWh)")
            st.plotly_chart(fig3, use_container_width=True, key="solar_vs_grid")
        else:
            st.info("solar_kwh/grid_kwh not available.")


def render_charts_costs(annual_df: pd.DataFrame) -> None:
    """Costs tab: clean layout."""
    df = _slot_df(annual_df)

    solar_c = "solar_cost_rs" if "solar_cost_rs" in df.columns else "solar_cost"
    wind_c = "wind_cost_rs" if "wind_cost_rs" in df.columns else "wind_cost"
    bess_c = "bess_cost_rs" if "bess_cost_rs" in df.columns else "bess_cost"
    grid_c = "grid_cost_rs" if "grid_cost_rs" in df.columns else "grid_cost"
    total_c = "total_cost_rs" if "total_cost_rs" in df.columns else "total_cost"

    c1, c2 = st.columns(2, gap="large")

    with c1:
        if grid_c in df.columns:
            fig1 = px.bar(df, x="tod_slot", y=grid_c, title="Grid cost by TOD slot")
            st.plotly_chart(fig1, use_container_width=True, key="grid_cost_by_slot")
        else:
            st.info("Grid cost column not found.")

    with c2:
        if total_c in df.columns:
            fig2 = px.bar(df, x="tod_slot", y=total_c, title="Total cost by TOD slot")
            st.plotly_chart(fig2, use_container_width=True, key="total_cost_by_slot")
        else:
            st.info("Total cost column not found.")

    breakdown_cols = [c for c in [solar_c, wind_c, bess_c, grid_c] if c in df.columns]
    if breakdown_cols:
        melt = df.melt(id_vars=["tod_slot"], value_vars=breakdown_cols, var_name="source", value_name="cost")
        fig3 = px.bar(melt, x="tod_slot", y="cost", color="source", barmode="stack", title="Cost breakdown by TOD slot")
        st.plotly_chart(fig3, use_container_width=True, key="cost_breakdown")
    else:
        st.info("No cost breakdown columns found.")
