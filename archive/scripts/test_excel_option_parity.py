from pathlib import Path
from core.loader import load_model_df
from core.tod import add_tod_slot, add_tod_rate
from core.excel_option_engine import build_option_annual_table, OptionSizing, ExcelColMap

colmap = ExcelColMap(
    load_1mw="load_1mw",
    wind_1mw="wind_generation_reference_for_1_mw",
    solar_ft_1mwp="160_ft_solar_generation_reference_for_1_mwp",
    solar_sat_1mwp="sat_solar_generation_reference_for_1_mwp",
    solar_ew_1mwp="ew_solar_generation_reference_for_1_mwp",
    tod_slot="tod_slot",
    tod_rate="tod_rate_rs_per_kwh",
    month="month",
    hour="hour",
)

XLSX = Path("data") / "MH_BESS_Solar_Wind.xlsx"
RATES = {"A": 6.84, "C": 9.16, "B": 6.30, "D": 9.46}

model_df = load_model_df(XLSX)
model_df = add_tod_slot(model_df)
model_df = add_tod_rate(model_df, RATES)

opt6_sat = OptionSizing(
    load_mw=1.0,
    solar_mode="EW",
    solar_mw=2.08,
    solar_loss=0.10,
    wind_mw=0.0,
    wind_loss=0.0,
)

df = build_option_annual_table(model_df, opt6_sat, colmap=colmap)
print(df)
