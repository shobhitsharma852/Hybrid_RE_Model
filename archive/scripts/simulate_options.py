from pathlib import Path
import pandas as pd

from core.loader import load_model_df
from core.option6_sat_bess import OptionSizing, build_option_slab_table

# ---- settings ----
XLSX_PATH = Path("data") / "MH_BESS_Solar_Wind.xlsx"
SHEET = "Data"

COL_LOAD = "load_1mw"
COL_WIND = "wind_generation_reference_for_1_mw"
SOLAR_COLS = {
    "FT": "160_ft_solar_generation_reference_for_1_mwp",
    "SAT": "sat_solar_generation_reference_for_1_mwp",
    "EW": "ew_solar_generation_reference_for_1_mwp",
}

DAYS = {"Jan":31,"Feb":28,"Mar":31,"Apr":30,"May":31,"Jun":30,"Jul":31,"Aug":31,"Sep":30,"Oct":31,"Nov":30,"Dec":31}

def annual_kwh_from_typical_day(df: pd.DataFrame, col: str, mw: float) -> float:
    # typical-day hourly (kWh per hour for 1 MW) -> multiply by days in month -> annual kWh
    return float((df[col] * df["month"].map(DAYS) * mw).sum())

def run_case(load_mw: float, solar_mw: float, wind_mw: float = 0.0):
    model_df = load_model_df(XLSX_PATH, sheet=SHEET)

    print("\n" + "=" * 90)
    print(f"CASE: load_mw={load_mw}, solar_mw={solar_mw}, wind_mw={wind_mw}")
    print("=" * 90)

    for name, solar_col in SOLAR_COLS.items():
        print("\n" + "-" * 90)
        print(f"OPTION = {name}  | solar_col = {solar_col}")
        print("-" * 90)

        sizing = OptionSizing(
            load_mw=load_mw,
            solar_mw=solar_mw,
            wind_mw=wind_mw,
            load_col_1mw=COL_LOAD,
            solar_col_1mw=solar_col,
            wind_col_1mw=COL_WIND,
        )

        slab = build_option_slab_table(model_df, sizing)

        # Pretty print
        pd.options.display.float_format = "{:,.2f}".format
        print(slab)

        # Quick annual check (from hourly table)
        annual_load = annual_kwh_from_typical_day(model_df, COL_LOAD, load_mw)
        annual_solar = annual_kwh_from_typical_day(model_df, solar_col, solar_mw)
        annual_wind = annual_kwh_from_typical_day(model_df, COL_WIND, wind_mw) if wind_mw else 0.0

        print("\nANNUAL (computed from hourly+days):")
        print(f"  load : {annual_load:,.2f} kWh")
        print(f"  solar: {annual_solar:,.2f} kWh")
        print(f"  wind : {annual_wind:,.2f} kWh")

if __name__ == "__main__":
    # Try multiple solar sizes quickly:
    run_case(load_mw=1.00, solar_mw=1.88, wind_mw=0.0)
    run_case(load_mw=1.00, solar_mw=2.08, wind_mw=0.0)
    run_case(load_mw=1.00, solar_mw=1.74, wind_mw=0.0)
