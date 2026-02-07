# core/excel_bess.py
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BessPolicy:
    bess_eff: float = 0.80          # usable fraction of excess
    discharge_to_slot: str = "D"    # Excel pushes BESS discharge to D


def apply_excel_bess(annual_slot: pd.DataFrame, policy: BessPolicy) -> pd.DataFrame:
    """
    Input must have: excess_kwh, grid_kwh_pre_bess, load_kwh
    Output adds: bess_kwh, grid_kwh, re_used_kwh, re_percent
    """
    required = {"tod_slot", "excess_kwh", "grid_kwh_pre_bess", "load_kwh"}
    missing = required - set(annual_slot.columns)
    if missing:
        raise KeyError(f"annual_slot missing: {sorted(missing)}")

    out = annual_slot.copy()

    bess_total_usable = float(out["excess_kwh"].sum()) * float(policy.bess_eff)

    out["bess_kwh"] = 0.0
    out.loc[out["tod_slot"].astype(str) == str(policy.discharge_to_slot), "bess_kwh"] = bess_total_usable

    out["grid_kwh"] = (out["grid_kwh_pre_bess"] - out["bess_kwh"]).clip(lower=0.0)

    out["re_used_kwh"] = out["load_kwh"] - out["grid_kwh"]
    out["re_percent"] = np.where(
        out["load_kwh"] > 0,
        100.0 * out["re_used_kwh"] / out["load_kwh"],
        0.0
    )

    return out
