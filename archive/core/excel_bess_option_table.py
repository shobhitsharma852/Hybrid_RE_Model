# core/excel_bess_option_table.py
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

from core.excel_option_engine import ExcelColMap, OptionSizing  # reuse your existing dataclasses
from core.excel_netting import month_slot_netting_excel, annualize_slot_table, SLOT_ORDER
from core.excel_bess import BessPolicy, apply_excel_bess
from core.tariff_costing import TariffRates, add_costs


def make_option_hourly_kw(model_df: pd.DataFrame, sizing: OptionSizing, colmap: ExcelColMap) -> pd.DataFrame:
    """
    Build the hourly (typical-day) table with load_kw, solar_kw, wind_kw.
    No hourly clipping happens here.
    """
    df = model_df.copy()

    df["load_kw"] = pd.to_numeric(df[colmap.load_1mw], errors="coerce").fillna(0.0) * float(sizing.load_mw)
    df["wind_kw"] = (
        pd.to_numeric(df[colmap.wind_1mw], errors="coerce").fillna(0.0)
        * float(sizing.wind_mw)
        * (1.0 - float(sizing.wind_loss))
    )

    # solar ref selection
    if sizing.solar_mode is None or float(sizing.solar_mw) <= 0:
        df["solar_kw"] = 0.0
    else:
        mode = sizing.solar_mode.upper().strip()
        if mode == "FT":
            sref = colmap.solar_ft_1mwp
        elif mode == "SAT":
            sref = colmap.solar_sat_1mwp
        elif mode == "EW":
            sref = colmap.solar_ew_1mwp
        else:
            raise ValueError(f"solar_mode must be FT/SAT/EW/None. Got: {sizing.solar_mode}")

        df["solar_kw"] = (
            pd.to_numeric(df[sref], errors="coerce").fillna(0.0)
            * float(sizing.solar_mw)          # DC MWp scaling (Excel Option A)
            * (1.0 - float(sizing.solar_loss))
        )

    # Keep these columns for netting module
    keep = [colmap.month, colmap.hour, "days", "tod_slot", "load_kw", "solar_kw", "wind_kw"]
    # days/tod_slot may already exist from tod.py; if not, netting will create them
    return df[ [c for c in keep if c in df.columns] + [c for c in [colmap.month, colmap.hour] if c not in keep] ].copy()


def build_excel_bess_annual_table(
    model_df: pd.DataFrame,
    sizing: OptionSizing,
    colmap: ExcelColMap = ExcelColMap(),
    bess_policy: BessPolicy = BessPolicy(),
    tariffs: TariffRates = TariffRates(),
) -> pd.DataFrame:
    """
    Output columns match your notebook-style final table:
    Slot, Load, Solar, Wind, Total RE, Excess, BESS, Grid, RE %, rates + costs, Total row.
    """
    opt_hourly = make_option_hourly_kw(model_df, sizing, colmap)

    # 1) Excel-style month-slot netting (clip at month-slot)
    ms = month_slot_netting_excel(
        opt_hourly,
        month_col=colmap.month,
        hour_col=colmap.hour,
        load_kw_col="load_kw",
        solar_kw_col="solar_kw",
        wind_kw_col="wind_kw",
    )

    # 2) Annualize per slot
    annual = annualize_slot_table(ms)

    # 3) Apply Excel-style BESS
    annual = apply_excel_bess(annual, bess_policy)

    # 4) Add costs
    annual = add_costs(annual, tariffs)

    # Add Total row
    total_load = float(annual["load_kwh"].sum())
    total = {
        "tod_slot": "Total",
        "load_kwh": annual["load_kwh"].sum(),
        "solar_kwh": annual["solar_kwh"].sum(),
        "wind_kwh": annual["wind_kwh"].sum(),
        "total_re_kwh": annual["total_re_kwh"].sum(),
        "excess_kwh": annual["excess_kwh"].sum(),
        "grid_kwh_pre_bess": annual["grid_kwh_pre_bess"].sum(),
        "bess_kwh": annual["bess_kwh"].sum(),
        "grid_kwh": annual["grid_kwh"].sum(),
        "re_used_kwh": annual["re_used_kwh"].sum(),
        "re_percent": 100.0 * (annual["re_used_kwh"].sum() / total_load) if total_load else 0.0,
        "solar_rate": tariffs.solar_rate,
        "wind_rate": tariffs.wind_rate,
        "bess_rate": tariffs.bess_rate,
        "grid_rate": np.nan,
        "solar_cost": annual["solar_cost"].sum(),
        "wind_cost": annual["wind_cost"].sum(),
        "bess_cost": annual["bess_cost"].sum(),
        "grid_cost": annual["grid_cost"].sum(),
        "total_cost": annual["total_cost"].sum(),
    }

    out = pd.concat([annual, pd.DataFrame([total])], ignore_index=True)

    # Rename to your “sheet-like” labels
    out = out.rename(columns={
        "tod_slot": "Slot",
        "load_kwh": "Load",
        "solar_kwh": "Solar",
        "wind_kwh": "Wind",
        "total_re_kwh": "Total RE",
        "excess_kwh": "Excess",
        "bess_kwh": "BESS",
        "grid_kwh": "Grid",
        "re_percent": "RE %",
        "solar_rate": "Solar Rate",
        "wind_rate": "Wind Rate",
        "bess_rate": "BESS Rate",
        "grid_rate": "Grid Rate",
        "solar_cost": "Solar Cost",
        "wind_cost": "Wind Cost",
        "bess_cost": "BESS Cost",
        "grid_cost": "Grid Cost",
        "total_cost": "Total Cost",
    })

    # Ordering A,C,B,D then Total
    slots = out[out["Slot"] != "Total"].copy()
    total_row = out[out["Slot"] == "Total"].copy()
    slots["Slot"] = pd.Categorical(slots["Slot"], categories=SLOT_ORDER, ordered=True)
    slots = slots.sort_values("Slot")
    out = pd.concat([slots, total_row], ignore_index=True)

    # Display rounding (Excel-like)
    for c in ["Load", "Solar", "Wind", "Total RE", "Excess", "BESS", "Grid"]:
        out[c] = out[c].round(0)
    out["RE %"] = out["RE %"].round(0)

    return out
