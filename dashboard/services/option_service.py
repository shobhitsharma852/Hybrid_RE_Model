from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from core.loader import load_model_df
from core.tod import add_tod_slot, add_tod_rate
from core.excel_option_engine import build_option_annual_table, OptionSizing, ExcelColMap

SLOT_ORDER = ["A", "C", "B", "D"]


def load_base_model(excel_path: str, colmap: ExcelColMap | None = None) -> pd.DataFrame:
    """Load the hourly base model (month x hour) dataframe from Excel."""
    colmap = colmap or ExcelColMap()
    model_df = load_model_df(excel_path)
    model_df = add_tod_slot(model_df)
    return model_df


def _normalize_rate_inputs(rates: dict | None) -> tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, float]]:
    """Return 4 slot->rate maps: solar, wind, bess, grid."""
    rates = rates or {}

    def _one(name: str, default: float) -> dict[str, float]:
        m = rates.get(name) or rates.get(f"{name}_rate_map")
        if not isinstance(m, dict):
            return {s: float(default) for s in SLOT_ORDER}
        out = {}
        for s in SLOT_ORDER:
            out[s] = float(m.get(s, default))
        return out

    solar = _one("solar_rate_map", 0.0)
    wind = _one("wind_rate_map", 0.0)
    bess = _one("bess_rate_map", 0.0)
    grid = _one("grid_rate_map", 0.0)
    return solar, wind, bess, grid


def _add_cost_columns_rs(annual_df: pd.DataFrame, solar_map: dict[str, float], wind_map: dict[str, float], bess_map: dict[str, float]) -> pd.DataFrame:
    out = annual_df.copy()
    out["tod_slot"] = out["tod_slot"].astype(str)

    slot_mask = out["tod_slot"].str.upper().isin(SLOT_ORDER)

    def _rate_for(m: dict[str, float], slot: str) -> float:
        return float(m.get(str(slot).upper(), 0.0))

    # slot-specific rates for display
    out.loc[slot_mask, "solar_rate"] = out.loc[slot_mask, "tod_slot"].map(lambda s: _rate_for(solar_map, s))
    out.loc[slot_mask, "wind_rate"] = out.loc[slot_mask, "tod_slot"].map(lambda s: _rate_for(wind_map, s))
    out.loc[slot_mask, "bess_rate"] = out.loc[slot_mask, "tod_slot"].map(lambda s: _rate_for(bess_map, s))

    # costs
    if "solar_kwh" in out.columns:
        out["solar_cost_rs"] = out.apply(
            lambda r: float(r.get("solar_kwh", 0.0)) * _rate_for(solar_map, r.get("tod_slot", "")) if str(r.get("tod_slot", "")).upper() in SLOT_ORDER else 0.0,
            axis=1,
        )
    else:
        out["solar_cost_rs"] = 0.0

    if "wind_kwh" in out.columns:
        out["wind_cost_rs"] = out.apply(
            lambda r: float(r.get("wind_kwh", 0.0)) * _rate_for(wind_map, r.get("tod_slot", "")) if str(r.get("tod_slot", "")).upper() in SLOT_ORDER else 0.0,
            axis=1,
        )
    else:
        out["wind_cost_rs"] = 0.0

    if "bess_kwh" in out.columns:
        out["bess_cost_rs"] = out.apply(
            lambda r: float(r.get("bess_kwh", 0.0)) * _rate_for(bess_map, r.get("tod_slot", "")) if str(r.get("tod_slot", "")).upper() in SLOT_ORDER else 0.0,
            axis=1,
        )
    else:
        out["bess_cost_rs"] = 0.0

    # grid_cost_rs is already in annual_df from excel_option_engine
    if "grid_cost_rs" not in out.columns and "grid_kwh" in out.columns and "grid_rate" in out.columns:
        out["grid_cost_rs"] = out["grid_kwh"] * out["grid_rate"]

    # total
    out["total_cost_rs"] = out[[c for c in ["solar_cost_rs", "wind_cost_rs", "bess_cost_rs", "grid_cost_rs"] if c in out.columns]].sum(axis=1)
    
    # ✅ format: remove decimals (keep NA-safe ints)
    for c in ["solar_cost_rs", "wind_cost_rs", "bess_cost_rs", "grid_cost_rs", "total_cost_rs"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").round(0).astype("Int64")
    
    # ---- Fix Total row (sum costs across slots) ----
    total_mask = out["tod_slot"].str.lower() == "total"
    if total_mask.any():
        slot_df = out[out["tod_slot"].str.upper().isin(SLOT_ORDER)]

        for c in ["solar_cost_rs", "wind_cost_rs", "bess_cost_rs", "grid_cost_rs", "total_cost_rs"]:
            if c in out.columns:
                out.loc[total_mask, c] = slot_df[c].sum()

        # rates should stay blank in Total row
        for c in ["solar_rate", "wind_rate", "bess_rate"]:
            if c in out.columns:
                out.loc[total_mask, c] = pd.NA

    return out


def run_option(model_df: pd.DataFrame, sizing: OptionSizing, rates: dict | None = None, colmap: ExcelColMap | None = None) -> pd.DataFrame:
    colmap = colmap or ExcelColMap()

    solar_map, wind_map, bess_map, grid_map = _normalize_rate_inputs(rates)

    # Apply grid TOD rate to hourly model (needed for grid_cost_rs in annual table)
    df = add_tod_rate(model_df.copy(), grid_map)

    annual = build_option_annual_table(df, sizing, colmap=colmap)
    annual = _add_cost_columns_rs(annual, solar_map, wind_map, bess_map)

    # UI cleanup
    
    annual = annual.drop(columns=["days"], errors="ignore")

    return annual


import pandas as pd

def summarize_totals(annual_df: pd.DataFrame) -> dict:
    # Prefer Total row if present
    if "tod_slot" in annual_df.columns and (annual_df["tod_slot"] == "Total").any():
        t = annual_df.loc[annual_df["tod_slot"] == "Total"].iloc[0]

        total_load = float(t.get("load_kwh", 0.0))
        total_re   = float(t.get("total_re_kwh", 0.0))
        re_pct     = float(t.get("re_percent", 0.0))
        grid_imp   = float(t.get("grid_kwh", 0.0))

        total_cost = (
            float(t.get("solar_cost_rs", 0.0)) +
            float(t.get("wind_cost_rs", 0.0)) +
            float(t.get("bess_cost_rs", 0.0)) +
            float(t.get("grid_cost_rs", 0.0))
        )
    else:
        # Fallback if Total row is missing
        total_load = float(annual_df.get("load_kwh", pd.Series([0.0])).sum())
        total_re   = float(annual_df.get("total_re_kwh", pd.Series([0.0])).sum())
        grid_imp   = float(annual_df.get("grid_kwh", pd.Series([0.0])).sum())
        re_pct     = (100.0 * (total_load - grid_imp) / total_load) if total_load > 0 else 0.0

        total_cost = (
            float(annual_df.get("solar_cost_rs", pd.Series([0.0])).sum()) +
            float(annual_df.get("wind_cost_rs", pd.Series([0.0])).sum()) +
            float(annual_df.get("bess_cost_rs", pd.Series([0.0])).sum()) +
            float(annual_df.get("grid_cost_rs", pd.Series([0.0])).sum())
        )

    return {
        "total_load_kwh": total_load,
        "total_re_kwh": total_re,
        "re_percent": re_pct,
        "grid_import_kwh": grid_imp,
        "total_cost_rs": total_cost,
    }
