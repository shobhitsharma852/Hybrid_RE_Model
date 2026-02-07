# from pathlib import Path
# from core.loader import load_model_df

# # change import to your actual file name where build_option_slab_table lives
# from core.option6_sat_bess import OptionSizing, build_option_slab_table


# XLSX_PATH = Path("data") / "MH_BESS_Solar_Wind.xlsx"
# model_df = load_model_df(XLSX_PATH, sheet="Data")


# print("\nmodel_df columns:\n", model_df.columns.tolist())

# # ✅ exact columns from your screenshot
# COL_LOAD = "load_1mw"
# COL_WIND = "wind_generation_reference_for_1_mw"

# SOLAR_COLS = {
#     "FT":  "160_ft_solar_generation_reference_for_1_mwp",
#     "SAT": "sat_solar_generation_reference_for_1_mwp",
#     "EW":  "ew_solar_generation_reference_for_1_mwp",
# }

# # sizing (use your current values)
# LOAD_MW  = 1.00
# SOLAR_MW = 1.74

# # first test without wind; later you can enable wind_mw too
# WIND_MW = 0.0


# for name, solar_col in SOLAR_COLS.items():
#     print("\n" + "=" * 80)
#     print(f"OPTION = {name}")

#     sizing = OptionSizing(
#         load_mw=LOAD_MW,
#         solar_mw=SOLAR_MW,
#         wind_mw=WIND_MW,
#         solar_col_1mw=solar_col,
#         wind_col_1mw=COL_WIND,
#         load_col_1mw=COL_LOAD,
#     )

#     slab = build_option_slab_table(model_df, sizing)
#     print(slab)
# tmp = model_df[model_df["month"]=="Feb"]
# print("Feb solar hourly sum:", tmp["sat_solar_generation_reference_for_1_mwp"].sum())

# sat = model_df.groupby("month")["sat_solar_generation_reference_for_1_mwp"].sum()
# print("Daily sums:\n", sat)

# DAYS = {"Jan":31,"Feb":28,"Mar":31,"Apr":30,"May":31,"Jun":30,"Jul":31,"Aug":31,"Sep":30,"Oct":31,"Nov":30,"Dec":31}
# annual = sum(sat[m]*DAYS[m] for m in DAYS if m in sat.index)
# print("Annual SAT (computed):", annual)

# from pathlib import Path

# from core.loader import load_model_df
# from core.option6_sat_bess import OptionSizing, build_option_slab_table

# # --------------------------------------------------
# # Paths
# # --------------------------------------------------
# XLSX_PATH = Path("data") / "MH_BESS_Solar_Wind.xlsx"
# SHEET = "Data"

# # --------------------------------------------------
# # Build model_df ONCE
# # --------------------------------------------------
# model_df = load_model_df(XLSX_PATH, sheet=SHEET)

# print("\nmodel_df columns:")
# print(model_df.columns.tolist())
# SOLAR_COLS = {
#     "FT":  "160_ft_solar_generation_reference_for_1_mwp",
#     "SAT": "sat_solar_generation_reference_for_1_mwp",
#     "EW":  "ew_solar_generation_reference_for_1_mwp",
# }

# for name, solar_col in SOLAR_COLS.items():
#     print("\n" + "=" * 80)
#     print(f"OPTION = {name}")

#     sizing = OptionSizing(
#         load_mw=1.0,
#         solar_mw=1.74,
#         wind_mw=0.0,
#         load_col_1mw="load_1mw",
#         solar_col_1mw=solar_col,
#         wind_col_1mw="wind_generation_reference_for_1_mw",
#     )

#     slab = build_option_slab_table(model_df, sizing)
#     print(slab)

from pathlib import Path
from pathlib import Path

Path("outputs").mkdir(parents=True, exist_ok=True)
out.to_csv("outputs/all_options_excel_mode_slab.csv", index=False)

import pandas as pd

from core.loader import load_model_df
from core.option6_sat_bess import OptionSizing, build_option_slab_table

# -----------------------
# CONFIG
# -----------------------
XLSX = Path("data") / "MH_BESS_Solar_Wind.xlsx"
SHEET = "Data"

# Set your sizing values (Excel mode)
LOAD_MW = 1.0
SOLAR_MW = 1.74
WIND_MW  = 0.0   # set >0 when you want wind included

# Exact columns you already saw in model_df (from your screenshot)
COL_LOAD = "load_1mw"
COL_WIND = "wind_generation_reference_for_1_mw"

SOLAR_COLS = {
    "FT": "160_ft_solar_generation_reference_for_1_mwp",
    "SAT": "sat_solar_generation_reference_for_1_mwp",
    "EW": "ew_solar_generation_reference_for_1_mwp",
}

# -----------------------
# RUN
# -----------------------
model_df = load_model_df(XLSX, sheet=SHEET)
print("\nmodel_df columns:\n", model_df.columns.tolist())

all_results = []

for opt_name, solar_col in SOLAR_COLS.items():
    print("\n" + "=" * 90)
    print(f"OPTION = {opt_name}")

    sizing = OptionSizing(
        load_mw=LOAD_MW,
        solar_mw=SOLAR_MW,
        wind_mw=WIND_MW,
        load_col_1mw=COL_LOAD,
        solar_col_1mw=solar_col,
        wind_col_1mw=COL_WIND,
    )

    slab = build_option_slab_table(model_df, sizing)

    # Add grid import/export (energy units)
    slab["grid_import_kwh"] = (slab["load"] - slab["total_re"]).clip(lower=0.0)
    slab["grid_export_kwh"] = (slab["total_re"] - slab["load"]).clip(lower=0.0)

    # Pretty print (rounded)
    show = slab[[
        "slab", "load", "solar", "wind", "total_re", "excess",
        "grid_import_kwh", "grid_export_kwh"
    ]].copy()

    print(show.round(3).to_string(index=False))

    # store for optional export
    tmp = slab.copy()
    tmp["option"] = opt_name
    all_results.append(tmp)

# Optional: save one combined CSV
out = pd.concat(all_results, ignore_index=True)
out.to_csv("outputs/all_options_excel_mode_slab.csv", index=False)
print("\nSaved: outputs/all_options_excel_mode_slab.csv")
