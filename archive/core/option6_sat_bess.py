# from dataclasses import dataclass
# from typing import Optional, Dict
# import pandas as pd


# # ----------------------------
# # Config
# # ----------------------------
# MONTH_ORDER = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

# DAYS_IN_MONTH: Dict[str, int] = {
#     "Jan": 31, "Feb": 28, "Mar": 31, "Apr": 30,
#     "May": 31, "Jun": 30, "Jul": 31, "Aug": 31,
#     "Sep": 30, "Oct": 31, "Nov": 30, "Dec": 31,
# }

# SLAB_ORDER = [
#     "A (12am to 6am)",
#     "C (6am to 9am)",
#     "B (9am to 5pm)",
#     "D (5pm to 12am)",
#     "Total",
# ]


# @dataclass
# class OptionSizing:
#     # MW sizing
#     load_mw: float
#     solar_mw: float
#     wind_mw: float = 0.0

#     # Column names in model_df (1MW reference columns)
#     load_col_1mw: str = "load_1mw"
#     solar_col_1mw: str = ""  # REQUIRED: pass FT/SAT/EW col name here
#     wind_col_1mw: str = "wind_generation_reference_for_1_mw"  # change if needed


# def _assign_slab(hour: int) -> str:
#     """
#     Excel-compatible slab mapping:
#     A: 0-5
#     C: 6-8
#     B: 9-16
#     D: 17-23
#     """
#     if 0 <= hour <= 5:
#         return "A (12am to 6am)"
#     if 6 <= hour <= 8:
#         return "C (6am to 9am)"
#     if 9 <= hour <= 16:
#         return "B (9am to 5pm)"
#     if 17 <= hour <= 23:
#         return "D (5pm to 12am)"
#     return "Unknown"


# def build_option_slab_table(model_df: pd.DataFrame, sizing: OptionSizing) -> pd.DataFrame:
#     """
#     Builds slab-wise annual energy table.

#     Assumption (matches your verification):
#     - model_df values are "typical-day hourly energy" for 1MW reference (kWh per hour)
#       OR "hourly kW" for 1MW reference (numerically same for 1-hour bins).
#     - Annual energy is computed by: sum_over_hours_in_month(...) * days_in_month
#     """

#     if not sizing.solar_col_1mw:
#         raise ValueError("OptionSizing.solar_col_1mw is required (pass FT/SAT/EW solar column name).")

#     df = model_df.copy()

#     # ---- Validate required columns
#     required = ["month", "hour", sizing.load_col_1mw, sizing.solar_col_1mw]
#     missing = [c for c in required if c not in df.columns]
#     if missing:
#         raise KeyError(f"Missing columns: {missing}. Available columns: {df.columns.tolist()}")

#     # ---- Clean month order + hour type
#     df["month"] = df["month"].astype(str).str.strip()
#     df["month"] = pd.Categorical(df["month"], categories=MONTH_ORDER, ordered=True)
#     df = df.dropna(subset=["month"])

#     df["hour"] = pd.to_numeric(df["hour"], errors="coerce")
#     df = df.dropna(subset=["hour"])
#     df["hour"] = df["hour"].astype(int)

#     # ---- Scale 1MW reference -> sized MW
#     # These are still "per-day hourly bins" at this point.
#     df["load"] = pd.to_numeric(df[sizing.load_col_1mw], errors="coerce").fillna(0.0) * sizing.load_mw
#     df["solar"] = pd.to_numeric(df[sizing.solar_col_1mw], errors="coerce").fillna(0.0) * sizing.solar_mw

#     if sizing.wind_mw > 0.0 and sizing.wind_col_1mw in df.columns:
#         df["wind"] = pd.to_numeric(df[sizing.wind_col_1mw], errors="coerce").fillna(0.0) * sizing.wind_mw
#     else:
#         df["wind"] = 0.0

#     # ---- Convert typical-day -> monthly energy BEFORE slabs
#     # This is the key fix: month-wise *days must happen while month is still present.
#     df["days"] = df["month"].astype(str).map(DAYS_IN_MONTH).astype(int)

#     for col in ["load", "solar", "wind"]:
#         df[col] = df[col] * df["days"]

#     # ---- Total RE + Excess (monthly energy)
#     df["total_re"] = df["solar"] + df["wind"]
#     df["excess"] = (df["total_re"] - df["load"]).clip(lower=0.0)

#     # ---- Slab mapping
#     df["slab"] = df["hour"].apply(_assign_slab)
#     df = df[df["slab"] != "Unknown"].copy()

#     # ---- Slab totals (annual)
#     slab = (
#         df.groupby("slab", as_index=False)[["load","solar","wind","total_re","excess"]]
#         .sum()
#     )

#     # ---- Add Total row
#     total_row = pd.DataFrame([{
#         "slab": "Total",
#         "load": slab["load"].sum(),
#         "solar": slab["solar"].sum(),
#         "wind": slab["wind"].sum(),
#         "total_re": slab["total_re"].sum(),
#         "excess": slab["excess"].sum(),
#     }])
#     slab = pd.concat([slab, total_row], ignore_index=True)

#     # ---- Order slabs like Excel
#     slab["slab"] = pd.Categorical(slab["slab"], categories=SLAB_ORDER, ordered=True)
#     slab = slab.sort_values("slab").reset_index(drop=True)

#     return slab

from dataclasses import dataclass
import pandas as pd

from core.scaling import add_total_re, add_excess
from core.slabs import add_slab

@dataclass
class OptionSizing:
    load_mw: float
    solar_mw: float
    wind_mw: float = 0.0
    solar_col_1mw: str = "sat_solar_generation_reference_for_1_mwp"
    wind_col_1mw: str = "wind_generation_reference_for_1_mw"
    load_col_1mw: str = "load_1mw"

SLAB_ORDER = ["A (12am to 6am)", "C (6am to 9am)", "B (9am to 5pm)", "D (5pm to 12am)"]

DAYS_IN_MONTH = {
    "Jan": 31, "Feb": 28, "Mar": 31, "Apr": 30,
    "May": 31, "Jun": 30, "Jul": 31, "Aug": 31,
    "Sep": 30, "Oct": 31, "Nov": 30, "Dec": 31,
}

def build_option_slab_table(model_df: pd.DataFrame, sizing: OptionSizing) -> pd.DataFrame:
    df = model_df.copy()

    # Validate required columns early
    for col in [sizing.load_col_1mw, sizing.solar_col_1mw]:
        if col not in df.columns:
            raise KeyError(f"Missing required column: {col}. Available: {df.columns.tolist()}")

    # Scale 1MW reference to chosen MW
    df["load"]  = df[sizing.load_col_1mw]  * sizing.load_mw
    df["solar"] = df[sizing.solar_col_1mw] * sizing.solar_mw

    if sizing.wind_mw > 0 and sizing.wind_col_1mw in df.columns:
        df["wind"] = df[sizing.wind_col_1mw] * sizing.wind_mw
    else:
        df["wind"] = 0.0

    # Convert "typical day hourly profile" -> monthly energy (matches Excel style)
    df["days"] = df["month"].map(DAYS_IN_MONTH).astype(int)
    for c in ["load", "solar", "wind"]:
        df[c] = df[c] * df["days"]

    df = add_total_re(df, solar_col="solar", wind_col="wind", out_col="total_re")
    df = add_excess(df, total_re_col="total_re", load_col="load", out_col="excess")

    df = add_slab(df, hour_col="hour")

    cols = ["load", "solar", "wind", "total_re", "excess"]

    # ✅ HARD GUARANTEE: exactly one row per slab
    slab = (
        df.groupby("slab", as_index=False)[cols]
          .sum()
    )

    # Add Total row
    total_row = {"slab": "Total"}
    for c in cols:
        total_row[c] = slab[c].sum()
    slab = pd.concat([slab, pd.DataFrame([total_row])], ignore_index=True)

    # Order slabs
    slab["slab"] = pd.Categorical(slab["slab"], categories=SLAB_ORDER + ["Total"], ordered=True)
    slab = slab.sort_values("slab").reset_index(drop=True)

    return slab
