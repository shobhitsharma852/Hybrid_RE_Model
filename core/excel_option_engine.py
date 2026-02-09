from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

# -----------------------------
# Constants
# -----------------------------
DAYS_IN_MONTH = {
    "Jan": 31, "Feb": 28, "Mar": 31, "Apr": 30, "May": 31, "Jun": 30,
    "Jul": 31, "Aug": 31, "Sep": 30, "Oct": 31, "Nov": 30, "Dec": 31
}
SLOT_ORDER = ["A", "C", "B", "D"]

# -----------------------------
# Column mapping
# -----------------------------
@dataclass(frozen=True)
class ExcelColMap:
    month: str = "month"
    hour: str = "hour"

    load_1mw: str = "load_1mw"
    wind_1mw: str = "wind_generation_reference_for_1_mw"

    solar_ft_1mwp: str = "160_ft_solar_generation_reference_for_1_mwp"
    solar_sat_1mwp: str = "sat_solar_generation_reference_for_1_mwp"
    solar_ew_1mwp: str = "ew_solar_generation_reference_for_1_mwp"

    tod_slot: str = "tod_slot"
    tod_rate: str = "tod_rate_rs_per_kwh"


@dataclass(frozen=True)
class OptionSizing:
    load_mw: float = 1.0

    # Solar
    solar_mode: str | None = None
    solar_mw: float = 0.0          # MWp (DC)
    solar_loss: float = 0.0

    # Solar modelling mode:
    # - "dc_only": Excel parity (no inverter cap)
    # - "ac_limited": inverter constrained using DC/AC ratio
    solar_model_mode: str = "dc_only"
    solar_dcac: float | None = None   # DC/AC ratio (e.g., 1.45, 1.60)

    # Wind
    wind_mw: float = 0.0
    wind_loss: float = 0.0



# -----------------------------
# Helpers
# -----------------------------
def _require(df: pd.DataFrame, cols: list[str], where: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"[{where}] Missing columns: {missing}. Available: {list(df.columns)}")


def _solar_ref_col(colmap: ExcelColMap, mode: str) -> str:
    m = mode.upper().strip()
    if m == "FT":
        return colmap.solar_ft_1mwp
    if m == "SAT":
        return colmap.solar_sat_1mwp
    if m == "EW":
        return colmap.solar_ew_1mwp
    raise ValueError(f"Unknown solar_mode='{mode}' (use FT/SAT/EW/None)")


# -----------------------------
# MAIN ENGINE
# -----------------------------
def build_option_annual_table(
    model_df: pd.DataFrame,
    sizing: OptionSizing,
    rates: dict | None = None,
    colmap: ExcelColMap = ExcelColMap(),
) -> pd.DataFrame:
    """
    Returns Annual TOD table with:
      Energy (kWh): load, solar, wind, total_re, excess, bess, grid
      Share (%): re_percent
      Rates (₹/kWh): solar_rate, wind_rate, bess_rate, grid_rate
      Costs (₹): solar_cost_rs, wind_cost_rs, bess_cost_rs, grid_cost_rs

    Notes:
    - No rounding at hourly. Rounding only at annual output.
    - Total row is computed correctly (percentages not summed).
    - Slot order enforced as A, C, B, D, Total.
    """

    rates = rates or {}

    df = model_df.copy()

    _require(df, [colmap.month, colmap.hour, colmap.tod_slot, colmap.tod_rate], "keys/tod")
    _require(df, [colmap.load_1mw, colmap.wind_1mw], "base refs")

    # attach days per month
    df["days"] = df[colmap.month].map(DAYS_IN_MONTH)
    if df["days"].isna().any():
        bad = sorted(df.loc[df["days"].isna(), colmap.month].unique().tolist())
        raise ValueError(f"Unknown month labels: {bad}. Expected {list(DAYS_IN_MONTH.keys())}")

    # -----------------------------
    # Hourly kW (NO rounding here)
    # -----------------------------
    load_ref = pd.to_numeric(df[colmap.load_1mw], errors="coerce").fillna(0.0)
    wind_ref = pd.to_numeric(df[colmap.wind_1mw], errors="coerce").fillna(0.0)

    df["load_kw"] = load_ref * float(sizing.load_mw)

    if sizing.solar_mode and float(sizing.solar_mw) > 0:
        sref_col = _solar_ref_col(colmap, sizing.solar_mode)
        _require(df, [sref_col], f"solar ref ({sizing.solar_mode})")
        solar_ref = pd.to_numeric(df[sref_col], errors="coerce").fillna(0.0)
        df["solar_kw"] = solar_ref * float(sizing.solar_mw) * (1.0 - float(sizing.solar_loss))
    else:
        df["solar_kw"] = 0.0

    df["wind_kw"] = wind_ref * float(sizing.wind_mw) * (1.0 - float(sizing.wind_loss))
    df["total_re_kw"] = df["solar_kw"] + df["wind_kw"]

    # -----------------------------
    # Daily (typical day) -> Monthly (multiply by days)
    # at (month, tod_slot) level (Excel-truth clipping)
    # -----------------------------
    slot_daily = df.groupby([colmap.month, colmap.tod_slot], as_index=False).agg(
        load_kwh=("load_kw", "sum"),
        solar_kwh=("solar_kw", "sum"),
        wind_kwh=("wind_kw", "sum"),
        total_re_kwh=("total_re_kw", "sum"),
        grid_rate_excel=(colmap.tod_rate, "first"),
        days=("days", "first"),
    )

    for c in ["load_kwh", "solar_kwh", "wind_kwh", "total_re_kwh"]:
        slot_daily[c] = slot_daily[c] * slot_daily["days"]

    slot_daily["excess_kwh"] = (slot_daily["total_re_kwh"] - slot_daily["load_kwh"]).clip(lower=0.0)
    slot_daily["grid_kwh"] = (slot_daily["load_kwh"] - slot_daily["total_re_kwh"]).clip(lower=0.0)

    # -----------------------------
    # Annual by TOD slot
    # -----------------------------
    annual = slot_daily.groupby(colmap.tod_slot, as_index=False).agg(
        load_kwh=("load_kwh", "sum"),
        solar_kwh=("solar_kwh", "sum"),
        wind_kwh=("wind_kwh", "sum"),
        total_re_kwh=("total_re_kwh", "sum"),
        excess_kwh=("excess_kwh", "sum"),
        grid_kwh=("grid_kwh", "sum"),
        grid_rate_excel=("grid_rate_excel", "first"),
    )

    # -----------------------------
    # Enforce Excel slot order (A, C, B, D)
    # -----------------------------
    annual[colmap.tod_slot] = pd.Categorical(
        annual[colmap.tod_slot],
        categories=SLOT_ORDER,
        ordered=True
    )
    annual = annual.sort_values(colmap.tod_slot).reset_index(drop=True)

    # -----------------------------
    # BESS logic (Excel truth)
    # -----------------------------
    bess_eff = 0.80
    discharge_slot = "D"

    bess_total_usable = float(annual["excess_kwh"].sum()) * bess_eff

    annual["bess_kwh"] = 0.0
    annual.loc[annual[colmap.tod_slot] == discharge_slot, "bess_kwh"] = bess_total_usable

    # Grid AFTER BESS
    annual["grid_kwh"] = (annual["grid_kwh"] - annual["bess_kwh"]).clip(lower=0.0)

    # -----------------------------
    # Rates (slot-based)
    # -----------------------------
    slot_series = annual[colmap.tod_slot].astype(str)

    # Solar/Wind/BESS rates from sidebar maps
    annual["solar_rate"] = slot_series.map(rates.get("solar_rate_map", {}))
    annual["wind_rate"] = slot_series.map(rates.get("wind_rate_map", {}))
    annual["bess_rate"] = slot_series.map(rates.get("bess_rate_map", {}))

    # Grid rate: allow sidebar override, else use Excel's TOD rate
    grid_map = rates.get("grid_rate_map")
    if isinstance(grid_map, dict) and grid_map:
        annual["grid_rate"] = slot_series.map(grid_map)
    else:
        annual["grid_rate"] = annual["grid_rate_excel"]

    # -----------------------------
    # Costs (₹)
    # -----------------------------
    annual["solar_cost_rs"] = annual["solar_kwh"] * annual["solar_rate"]
    annual["wind_cost_rs"] = annual["wind_kwh"] * annual["wind_rate"]
    annual["bess_cost_rs"] = annual["bess_kwh"] * annual["bess_rate"]
    annual["grid_cost_rs"] = annual["grid_kwh"] * annual["grid_rate"]

    # -----------------------------
    # RE % (per slot)
    # -----------------------------
    annual["re_percent"] = np.where(
        annual["load_kwh"] > 0,
        100.0 * (annual["load_kwh"] - annual["grid_kwh"]) / annual["load_kwh"],
        0.0
    )

    # -----------------------------
    # Total row (clean & correct)
    # -----------------------------
    sum_cols = [
        "load_kwh", "solar_kwh", "wind_kwh", "total_re_kwh",
        "excess_kwh", "bess_kwh", "grid_kwh",
        "solar_cost_rs", "wind_cost_rs", "bess_cost_rs", "grid_cost_rs",
    ]

    total = {colmap.tod_slot: "Total"}
    for c in sum_cols:
        total[c] = float(annual[c].sum()) if c in annual.columns else 0.0

    # Rates not meaningful on total row
    for c in ["solar_rate", "wind_rate", "bess_rate", "grid_rate"]:
        total[c] = np.nan

    total_load = float(total.get("load_kwh", 0.0))
    total_grid = float(total.get("grid_kwh", 0.0))
    total["re_percent"] = (100.0 * (total_load - total_grid) / total_load) if total_load > 0 else 0.0

    out = pd.concat([annual, pd.DataFrame([total])], ignore_index=True)

    # -----------------------------
    # ROUND ONLY AT ANNUAL OUTPUT
    # -----------------------------
    kwh_cols = ["load_kwh", "solar_kwh", "wind_kwh", "total_re_kwh", "excess_kwh", "bess_kwh", "grid_kwh"]
    cost_cols = ["solar_cost_rs", "wind_cost_rs", "bess_cost_rs", "grid_cost_rs"]
    rate_cols = ["solar_rate", "wind_rate", "bess_rate", "grid_rate"]

    for c in kwh_cols:
        if c in out.columns:
            out[c] = out[c].round(0)

    for c in cost_cols:
        if c in out.columns:
            out[c] = out[c].round(0)

    for c in rate_cols:
        if c in out.columns:
            out[c] = out[c].round(2)

    if "re_percent" in out.columns:
        out["re_percent"] = out["re_percent"].round(1)

    # -----------------------------
    # FINAL COLUMN ORDER (ONE PLACE)
    # -----------------------------
    cols = [
        # Energy (kWh)
        "tod_slot",
        "load_kwh", "solar_kwh", "wind_kwh", "total_re_kwh",
        "excess_kwh", "bess_kwh", "grid_kwh",

        # Share
        "re_percent",

        # Rates
        "solar_rate", "wind_rate", "bess_rate", "grid_rate",

        # Costs
        "solar_cost_rs", "wind_cost_rs", "bess_cost_rs", "grid_cost_rs",
    ]

    # return only requested columns (if present)
    return out[[c for c in cols if c in out.columns]]
