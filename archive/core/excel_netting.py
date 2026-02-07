# core/excel_netting.py
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

DAYS_IN_MONTH = {
    "Jan": 31, "Feb": 28, "Mar": 31, "Apr": 30, "May": 31, "Jun": 30,
    "Jul": 31, "Aug": 31, "Sep": 30, "Oct": 31, "Nov": 30, "Dec": 31
}
SLOT_ORDER = ["A", "C", "B", "D"]


def assign_tod_slot(hour: int) -> str:
    if 0 <= hour < 6:
        return "A"
    if 6 <= hour < 9:
        return "C"
    if 9 <= hour < 17:
        return "B"
    return "D"


def ensure_days_and_slot(df: pd.DataFrame, month_col: str, hour_col: str) -> pd.DataFrame:
    out = df.copy()

    if "days" not in out.columns:
        out["days"] = out[month_col].map(DAYS_IN_MONTH)
        if out["days"].isna().any():
            bad = sorted(out.loc[out["days"].isna(), month_col].unique().tolist())
            raise ValueError(f"Unknown month labels: {bad}. Expected {list(DAYS_IN_MONTH.keys())}")

    if "tod_slot" not in out.columns:
        out["tod_slot"] = out[hour_col].astype(int).apply(assign_tod_slot)

    return out


def month_slot_netting_excel(
    opt_hourly: pd.DataFrame,
    month_col: str = "month",
    hour_col: str = "hour",
    load_kw_col: str = "load_kw",
    solar_kw_col: str = "solar_kw",
    wind_kw_col: str = "wind_kw",
) -> pd.DataFrame:
    """
    Excel-style month-slot netting:
      1) hourly kW * days -> monthly kWh (per hour row)
      2) sum within (month, slot)
      3) clip excess/grid at (month, slot) level
    """
    required = {month_col, hour_col, load_kw_col, solar_kw_col, wind_kw_col}
    missing = required - set(opt_hourly.columns)
    if missing:
        raise KeyError(f"opt_hourly missing: {sorted(missing)}")

    df = ensure_days_and_slot(opt_hourly, month_col=month_col, hour_col=hour_col)

    # hourly -> monthly kWh (typical day × days)
    df["load_kwh"] = df[load_kw_col] * df["days"]
    df["solar_kwh"] = df[solar_kw_col] * df["days"]
    df["wind_kwh"] = df[wind_kw_col] * df["days"]

    # month-slot totals
    ms = (
        df.groupby([month_col, "tod_slot"], as_index=False)
          .agg(
              days=("days", "first"),
              load_kwh=("load_kwh", "sum"),
              solar_kwh=("solar_kwh", "sum"),
              wind_kwh=("wind_kwh", "sum"),
          )
    )
    ms["total_re_kwh"] = ms["solar_kwh"] + ms["wind_kwh"]

    # Excel clipping AFTER month-slot aggregation
    ms["excess_kwh"] = (ms["total_re_kwh"] - ms["load_kwh"]).clip(lower=0.0)
    ms["grid_kwh_pre_bess"] = (ms["load_kwh"] - ms["total_re_kwh"]).clip(lower=0.0)

    # ordering
    ms["tod_slot"] = pd.Categorical(ms["tod_slot"], categories=SLOT_ORDER, ordered=True)
    ms[month_col] = pd.Categorical(ms[month_col], categories=list(DAYS_IN_MONTH.keys()), ordered=True)
    ms = ms.sort_values([month_col, "tod_slot"]).reset_index(drop=True)

    return ms


def annualize_slot_table(ms: pd.DataFrame) -> pd.DataFrame:
    """
    Sum month-slot rows to annual per slot.
    """
    required = {"tod_slot", "load_kwh", "solar_kwh", "wind_kwh", "total_re_kwh", "excess_kwh", "grid_kwh_pre_bess"}
    missing = required - set(ms.columns)
    if missing:
        raise KeyError(f"month-slot df missing: {sorted(missing)}")

    annual = (
        ms.groupby("tod_slot", as_index=False)
          .agg(
              load_kwh=("load_kwh", "sum"),
              solar_kwh=("solar_kwh", "sum"),
              wind_kwh=("wind_kwh", "sum"),
              total_re_kwh=("total_re_kwh", "sum"),
              excess_kwh=("excess_kwh", "sum"),
              grid_kwh_pre_bess=("grid_kwh_pre_bess", "sum"),
          )
    )
    annual["tod_slot"] = pd.Categorical(annual["tod_slot"], categories=SLOT_ORDER, ordered=True)
    annual = annual.sort_values("tod_slot").reset_index(drop=True)
    return annual
