# scripts/test_excel_bess_streamlit_debug.py
from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np

# -----------------------------
# Import your project modules
# -----------------------------
from core.loader import load_model_df
from core.tod import add_tod_slot
from core.tod import add_tod_rate
from core.excel_option_engine import ExcelColMap, OptionSizing, build_option_annual_table

# -----------------------------
# Constants
# -----------------------------

GRID_RATES = {
    "A": 6.84,
    "C": 9.16,
    "B": 6.30,
    "D": 9.46,
}

DAYS_IN_MONTH = {
    "Jan": 31, "Feb": 28, "Mar": 31, "Apr": 30, "May": 31, "Jun": 30,
    "Jul": 31, "Aug": 31, "Sep": 30, "Oct": 31, "Nov": 30, "Dec": 31
}
SLOT_ORDER = ["A", "C", "B", "D"]


def month_slot_excel_truth_from_modeldf(model_df: pd.DataFrame, sizing: OptionSizing, colmap: ExcelColMap) -> pd.DataFrame:
    """
    Build Excel-truth annual table:
      - Build hourly typical-day load/solar/wind
      - Convert hourly -> monthly kWh via days
      - Sum into (month, slot)
      - Clip at (month, slot)
      - Annualize
    """
    df = model_df.copy()

    # make sure month/hour exist
    if colmap.month not in df.columns or colmap.hour not in df.columns:
        raise KeyError(f"model_df missing {colmap.month}/{colmap.hour}. Columns: {df.columns.tolist()}")

    # days
    if "days" not in df.columns:
        df["days"] = df[colmap.month].map(DAYS_IN_MONTH)
    if df["days"].isna().any():
        bad = sorted(df.loc[df["days"].isna(), colmap.month].unique().tolist())
        raise ValueError(f"Unknown month labels in model_df: {bad}")

    # tod_slot
    if "tod_slot" not in df.columns:
        raise KeyError("model_df has no 'tod_slot'. Add it using add_tod_slot(model_df).")

    # hourly kW (typical-day)
    # Load
    df["load_kw"] = pd.to_numeric(df[colmap.load_1mw], errors="coerce").fillna(0.0) * float(sizing.load_mw)

    # Wind
    df["wind_kw"] = (
        pd.to_numeric(df[colmap.wind_1mw], errors="coerce").fillna(0.0)
        * float(sizing.wind_mw)
        * (1.0 - float(sizing.wind_loss))
    )

    # Solar
    if sizing.solar_mode is None or float(sizing.solar_mw) <= 0:
        df["solar_kw"] = 0.0
    else:
        m = sizing.solar_mode.upper().strip()
        if m == "FT":
            sref = colmap.solar_ft_1mwp
        elif m == "SAT":
            sref = colmap.solar_sat_1mwp
        elif m == "EW":
            sref = colmap.solar_ew_1mwp
        else:
            raise ValueError(f"solar_mode must be FT/SAT/EW/None. Got: {sizing.solar_mode}")

        df["solar_kw"] = (
            pd.to_numeric(df[sref], errors="coerce").fillna(0.0)
            * float(sizing.solar_mw)             # DC MWp scaling (Excel Option A)
            * (1.0 - float(sizing.solar_loss))   # loss
        )

    # hourly -> monthly kWh
    df["load_kwh"] = df["load_kw"] * df["days"]
    df["solar_kwh"] = df["solar_kw"] * df["days"]
    df["wind_kwh"] = df["wind_kw"] * df["days"]

    # month-slot totals
    ms = (
        df.groupby([colmap.month, "tod_slot"], as_index=False)
          .agg(
              days=("days", "first"),
              load_kwh=("load_kwh", "sum"),
              solar_kwh=("solar_kwh", "sum"),
              wind_kwh=("wind_kwh", "sum"),
          )
    )
    ms["total_re_kwh"] = ms["solar_kwh"] + ms["wind_kwh"]

    # ✅ Excel truth: clip at (month, slot)
    ms["excess_kwh"] = (ms["total_re_kwh"] - ms["load_kwh"]).clip(lower=0.0)
    ms["grid_kwh"]   = (ms["load_kwh"] - ms["total_re_kwh"]).clip(lower=0.0)

    # annualize
    annual = (
        ms.groupby("tod_slot", as_index=False)
          .agg(
              load_kwh=("load_kwh", "sum"),
              solar_kwh=("solar_kwh", "sum"),
              wind_kwh=("wind_kwh", "sum"),
              total_re_kwh=("total_re_kwh", "sum"),
              excess_kwh=("excess_kwh", "sum"),
              grid_kwh=("grid_kwh", "sum"),
          )
    )

    annual["re_percent"] = np.where(
        annual["load_kwh"] > 0,
        100.0 * (annual["load_kwh"] - annual["grid_kwh"]) / annual["load_kwh"],
        0.0
    )

    # order A,C,B,D
    annual["tod_slot"] = pd.Categorical(annual["tod_slot"], categories=SLOT_ORDER, ordered=True)
    annual = annual.sort_values("tod_slot").reset_index(drop=True)

    # total row
    total = {
        "tod_slot": "Total",
        "load_kwh": annual["load_kwh"].sum(),
        "solar_kwh": annual["solar_kwh"].sum(),
        "wind_kwh": annual["wind_kwh"].sum(),
        "total_re_kwh": annual["total_re_kwh"].sum(),
        "excess_kwh": annual["excess_kwh"].sum(),
        "grid_kwh": annual["grid_kwh"].sum(),
    }
    total["re_percent"] = 100.0 * (total["load_kwh"] - total["grid_kwh"]) / total["load_kwh"] if total["load_kwh"] else 0.0

    annual = pd.concat([annual, pd.DataFrame([total])], ignore_index=True)

    return annual, ms


def main():
    XLSX = Path("data") / "MH_BESS_Solar_Wind.xlsx"

    # 1) Load model_df (your block-extraction pipeline)
    model_df = load_model_df(XLSX, sheet="Data")

    # 2) Add TOD slot (Streamlit uses this)
    model_df = add_tod_slot(model_df)

    model_df = add_tod_rate(model_df, GRID_RATES)

    # 3) Build sizing (same as your screenshot)
    sizing = OptionSizing(
        load_mw=1.0,
        solar_mode="EW",
        solar_mw=2.08,
        solar_loss=0.10,
        wind_mw=0.0,
        wind_loss=0.0,
    )

    colmap = ExcelColMap()

    # 4) Streamlit/current engine output
    streamlit_annual = build_option_annual_table(model_df, sizing, colmap)

    # 5) Excel-truth output (month+slot clipping)
    truth_annual, truth_ms = month_slot_excel_truth_from_modeldf(model_df, sizing, colmap)

    # Normalize to same column set if needed
    # (your build_option_annual_table may have extra columns like grid_rate/cost)
    keep = ["tod_slot", "load_kwh", "solar_kwh", "wind_kwh", "total_re_kwh", "excess_kwh", "grid_kwh"]
    s = streamlit_annual.copy()
    for c in keep:
        if c not in s.columns:
            s[c] = np.nan
    s = s[keep]

    t = truth_annual.copy()
    t = t[keep]

    # 6) Print both + diff
    print("\n==============================")
    print("STREAMLIT / CURRENT ENGINE")
    print("==============================")
    print(s.to_string(index=False))

    print("\n==============================")
    print("EXCEL-TRUTH (MONTH+SLOT CLIP)")
    print("==============================")
    print(t.to_string(index=False))

    # diff
    diff = s.copy()
    for c in keep[1:]:
        diff[c] = (s[c].fillna(0.0) - t[c].fillna(0.0))
    print("\n==============================")
    print("DIFF  (streamlit - truth)")
    print("==============================")
    print(diff.to_string(index=False))

    # 7) Debug the known pain area: May/Jun/Jul slot B in truth month-slot table
    subset = truth_ms[(truth_ms["tod_slot"] == "B") & (truth_ms["month"].isin(["May", "Jun", "Jul"]))].copy()
    cols = ["month", "tod_slot", "days", "solar_kwh", "load_kwh", "total_re_kwh", "excess_kwh", "grid_kwh"]
    print("\n==============================")
    print("TRUTH month-slot rows: May/Jun/Jul Slot B")
    print("==============================")
    print(subset[cols].to_string(index=False))

    # 8) Hard asserts (optional): you can enable these once parity is stable
    # Example from your screenshot (rounded):
    # expected_total_load = 8760000
    # assert int(round(t.loc[t["tod_slot"]=="Total","load_kwh"].values[0])) == expected_total_load

    print("\n[OK] Debug run finished.")


if __name__ == "__main__":
    main()
