# core/tariff_costing.py
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TariffRates:
    solar_rate: float = 5.05
    wind_rate: float = 5.65
    bess_rate: float = 6.00
    grid_rate_map: dict[str, float] = None  # set in __post_init__
    cost_in_rupees: bool = False            # False => divide by 1000

    def __post_init__(self):
        if self.grid_rate_map is None:
            object.__setattr__(self, "grid_rate_map", {"A": 6.84, "C": 9.16, "B": 6.30, "D": 9.46})


def add_costs(df: pd.DataFrame, rates: TariffRates) -> pd.DataFrame:
    """
    Requires: tod_slot, solar_kwh, wind_kwh, bess_kwh, grid_kwh
    Adds: solar_cost, wind_cost, bess_cost, grid_cost, total_cost + rate columns
    """
    required = {"tod_slot", "solar_kwh", "wind_kwh", "bess_kwh", "grid_kwh"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"df missing: {sorted(missing)}")

    out = df.copy()
    div = 1.0 if rates.cost_in_rupees else 1000.0

    out["solar_rate"] = float(rates.solar_rate)
    out["wind_rate"] = float(rates.wind_rate)
    out["bess_rate"] = float(rates.bess_rate)
    out["grid_rate"] = out["tod_slot"].astype(str).map(rates.grid_rate_map)

    out["solar_cost"] = out["solar_kwh"] * out["solar_rate"] / div
    out["wind_cost"] = out["wind_kwh"] * out["wind_rate"] / div
    out["bess_cost"] = out["bess_kwh"] * out["bess_rate"] / div
    out["grid_cost"] = out["grid_kwh"] * out["grid_rate"] / div

    out["total_cost"] = out["solar_cost"] + out["wind_cost"] + out["bess_cost"] + out["grid_cost"]

    return out
