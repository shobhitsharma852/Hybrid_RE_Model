# scripts/verify_excess_excel_style.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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
# TOD slots (matches your project)
# -----------------------------
def assign_tod_slot(hour: int) -> str:
    if 0 <= hour < 6:
        return "A"  # 12am–6am
    elif 6 <= hour < 9:
        return "C"  # 6am–9am
    elif 9 <= hour < 17:
        return "B"  # 9am–5pm
    else:
        return "D"  # 5pm–12am

# -----------------------------
# Excel column map (edit names to match your Data sheet)
# -----------------------------
@dataclass(frozen=True)
class ExcelColMap:
    sheet_name: str = "Data"  # change if your sheet is named differently

    month: str = "month"      # e.g., "Jan", "Feb", ...
    hour: str = "hour"        # 0..23

    # hourly references from Excel Data sheet:
    load_1mw: str = "load_1mw"  # hourly kWh (or kW) for 1 MW load reference (typical day)
    wind_1mw: str = "wind_generation_reference_for_1_mw"  # hourly gen for 1 MW wind (typical day)

    # solar reference is per 1 MWp (DC) for each technology
    solar_ft_1mwp: str = "160_ft_solar_generation_reference_for_1_mwp"
    solar_sat_1mwp: str = "sat_solar_generation_reference_for_1_mwp"
    solar_ew_1mwp: str = "ew_solar_generation_reference_for_1_mwp"

# -----------------------------
# Option sizing
# IMPORTANT: Option A = solar_mwp is DC MWp directly (NO dc/ac conversion)
# -----------------------------
@dataclass(frozen=True)
class OptionSizing:
    load_mw: float = 1.0

    solar_mode: str | None = None  # "FT"/"SAT"/"EW"/None
    solar_mwp: float = 0.0         # DC MWp (Option A)
    solar_loss: float = 0.0        # e.g. 0.10

    wind_mw: float = 0.0           # MW
    wind_loss: float = 0.0         # e.g. 0.10

# -----------------------------
# IO: load model_df from Excel
# -----------------------------
def load_model_df(xlsx: Path, colmap: ExcelColMap) -> pd.DataFrame:
    df = pd.read_excel(xlsx, sheet_name=colmap.sheet_name)

    needed = [colmap.month, colmap.hour, colmap.load_1mw, colmap.wind_1mw,
              colmap.solar_ft_1mwp, colmap.solar_sat_1mwp, colmap.solar_ew_1mwp]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise KeyError(f"Missing columns in Excel sheet '{colmap.sheet_name}': {missing}")

    # basic cleanup
    df = df.copy()
    df[colmap.hour] = pd.to_numeric(df[colmap.hour], errors="coerce").astype(int)
    df[colmap.month] = df[colmap.month].astype(str)

    # days + slot
    df["days"] = df[colmap.month].map(DAYS_IN_MONTH)
    if df["days"].isna().any():
        bad = sorted(df.loc[df["days"].isna(), colmap.month].unique().tolist())
        raise ValueError(f"Unknown month labels found: {bad}. Expected {list(DAYS_IN_MONTH.keys())}")

    df["tod_slot"] = df[colmap.hour].apply(assign_tod_slot)

    # make all refs numeric
    for c in [colmap.load_1mw, colmap.wind_1mw,
              colmap.solar_ft_1mwp, colmap.solar_sat_1mwp, colmap.solar_ew_1mwp]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    return df

# -----------------------------
# Solar reference selector
# -----------------------------
def solar_ref_col(colmap: ExcelColMap, solar_mode: str) -> str:
    m = solar_mode.upper().strip()
    if m == "FT":
        return colmap.solar_ft_1mwp
    if m == "SAT":
        return colmap.solar_sat_1mwp
    if m == "EW":
        return colmap.solar_ew_1mwp
    raise ValueError(f"solar_mode must be FT/SAT/EW/None. Got: {solar_mode}")

# -----------------------------
# Build hourly option power (typical-day)
# -----------------------------
def make_option_hourly_kw(model_df: pd.DataFrame, sizing: OptionSizing, colmap: ExcelColMap) -> pd.DataFrame:
    df = model_df.copy()

    # Load (1 MW reference scaled by load_mw)
    df["load_kw"] = df[colmap.load_1mw] * float(sizing.load_mw)

    # Wind (1 MW reference scaled by wind_mw and loss)
    df["wind_kw"] = df[colmap.wind_1mw] * float(sizing.wind_mw) * (1.0 - float(sizing.wind_loss))

    # Solar (per 1 MWp DC reference scaled by solar_mwp and loss)  ✅ Option A
    if sizing.solar_mode is None or float(sizing.solar_mwp) <= 0:
        df["solar_kw"] = 0.0
    else:
        sref = solar_ref_col(colmap, sizing.solar_mode)
        df["solar_kw"] = df[sref] * float(sizing.solar_mwp) * (1.0 - float(sizing.solar_loss))

    df["re_kw"] = df["solar_kw"] + df["wind_kw"]
    return df

# -----------------------------
# Excel-style month-slot aggregation + excess
# (THIS is the core you wanted)
# -----------------------------
def month_slot_table_excel_excess(df_hourly: pd.DataFrame) -> pd.DataFrame:
    """
    Input: typical-day hourly rows with columns:
      month, tod_slot, days, load_kw, solar_kw, wind_kw
    Output: month-slot table with monthly kWh + excess/grid computed at (month, slot).
    """
    required = {"month", "tod_slot", "days", "load_kw", "solar_kw", "wind_kw"}
    missing = required - set(df_hourly.columns)
    if missing:
        raise KeyError(f"df_hourly missing required columns: {sorted(missing)}")

    df = df_hourly.copy()

    # Convert hourly -> monthly kWh (typical-day × days) BEFORE netting
    df["load_kwh"] = df["load_kw"] * df["days"]
    df["solar_kwh"] = df["solar_kw"] * df["days"]
    df["wind_kwh"] = df["wind_kw"] * df["days"]

    # Sum hours into (month, slot)
    ms = (df.groupby(["month", "tod_slot"], as_index=False)
            .agg(days=("days", "first"),
                 load_kwh=("load_kwh", "sum"),
                 solar_kwh=("solar_kwh", "sum"),
                 wind_kwh=("wind_kwh", "sum")))

    ms["total_re_kwh"] = ms["solar_kwh"] + ms["wind_kwh"]

    # ✅ Excel excess logic: clip after reaching month-slot totals
    ms["excess_kwh"] = (ms["total_re_kwh"] - ms["load_kwh"]).clip(lower=0.0)
    ms["grid_kwh"]   = (ms["load_kwh"] - ms["total_re_kwh"]).clip(lower=0.0)

    # ordering
    ms["tod_slot"] = pd.Categorical(ms["tod_slot"], categories=SLOT_ORDER, ordered=True)
    ms["month"] = pd.Categorical(ms["month"], categories=list(DAYS_IN_MONTH.keys()), ordered=True)
    ms = ms.sort_values(["month", "tod_slot"]).reset_index(drop=True)

    return ms

# -----------------------------
# Annual slot table (Option-table view)
# -----------------------------
def annual_slot_table_from_month_slot(ms: pd.DataFrame) -> pd.DataFrame:
    """
    Sums month-slot rows to annual per slot, plus a Total row.
    """
    g = (ms.groupby("tod_slot", as_index=False)
           .agg(load_kwh=("load_kwh", "sum"),
                solar_kwh=("solar_kwh", "sum"),
                wind_kwh=("wind_kwh", "sum"),
                total_re_kwh=("total_re_kwh", "sum"),
                excess_kwh=("excess_kwh", "sum"),
                grid_kwh=("grid_kwh", "sum")))

    g["re_percent"] = np.where(g["load_kwh"] > 0, 100.0 * (g["load_kwh"] - g["grid_kwh"]) / g["load_kwh"], 0.0)

    # total row
    total = {
        "tod_slot": "Total",
        "load_kwh": g["load_kwh"].sum(),
        "solar_kwh": g["solar_kwh"].sum(),
        "wind_kwh": g["wind_kwh"].sum(),
        "total_re_kwh": g["total_re_kwh"].sum(),
        "excess_kwh": g["excess_kwh"].sum(),
        "grid_kwh": g["grid_kwh"].sum(),
    }
    total["re_percent"] = 100.0 * (total["load_kwh"] - total["grid_kwh"]) / total["load_kwh"] if total["load_kwh"] else 0.0

    out = pd.concat([g, pd.DataFrame([total])], ignore_index=True)

    # Excel-like display rounding (keep raw floats if you want)
    for c in ["load_kwh", "solar_kwh", "wind_kwh", "total_re_kwh", "excess_kwh", "grid_kwh"]:
        out[c] = out[c].round(0)
    out["re_percent"] = out["re_percent"].round(0)

    # order
    if "tod_slot" in out.columns:
        # keep Total last
        out_slots = out[out["tod_slot"] != "Total"].copy()
        out_total = out[out["tod_slot"] == "Total"].copy()
        out_slots["tod_slot"] = pd.Categorical(out_slots["tod_slot"], categories=SLOT_ORDER, ordered=True)
        out_slots = out_slots.sort_values("tod_slot")
        out = pd.concat([out_slots, out_total], ignore_index=True)

    return out

# -----------------------------
# Utility: annual solar only (slot-wise + total)
# -----------------------------
def annual_solar_generation(ms: pd.DataFrame) -> pd.DataFrame:
    """
    Returns annual solar kWh per slot + total, from month-slot table.
    """
    g = (ms.groupby("tod_slot", as_index=False)
           .agg(solar_kwh=("solar_kwh", "sum")))
    total = {"tod_slot": "Total", "solar_kwh": g["solar_kwh"].sum()}
    out = pd.concat([g, pd.DataFrame([total])], ignore_index=True)
    out["solar_kwh"] = out["solar_kwh"].round(0)
    return out

# -----------------------------
# Main run (edit option here)
# -----------------------------
if __name__ == "__main__":
    XLSX = Path("data") / "MH_BESS_Solar_Wind.xlsx"  # change path if needed
    colmap = ExcelColMap(sheet_name="Data")

    model_df = load_model_df(XLSX, colmap)

    # Example: EW, DC=2.08 MWp, loss=10%, no wind
    opt = OptionSizing(
        load_mw=1.0,
        solar_mode="EW",
        solar_mwp=2.08,      # ✅ DC MWp (Option A)
        solar_loss=0.10,
        wind_mw=0.0,
        wind_loss=0.0,
    )

    hourly = make_option_hourly_kw(model_df, opt, colmap)

    # ✅ Excel-style month-slot netting table (source of truth)
    ms = month_slot_table_excel_excess(hourly)

    # Annual option table (slot-wise)
    annual = annual_slot_table_from_month_slot(ms)

    # Solar annual generation table
    solar_annual = annual_solar_generation(ms)

    print("\n=== Solar annual generation (kWh) ===")
    print(solar_annual.to_string(index=False))

    print("\n=== Annual slot table (Excel-style excess) ===")
    print(annual.to_string(index=False))

    # If you want to inspect May/Jun/Jul Slot B rows:
    subset = ms[(ms["month"].isin(["May", "Jun", "Jul"])) & (ms["tod_slot"] == "B")].copy()
    print("\n=== May/Jun/Jul Slot B (month-slot truth table) ===")
    cols = ["month","tod_slot","days","solar_kwh","load_kwh","total_re_kwh","excess_kwh","grid_kwh"]
    print(subset[cols].to_string(index=False))
