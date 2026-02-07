from pathlib import Path
import pandas as pd

from core.model_builder import build_model_df
from core.excel_blocks import detect_time_month_headers, compute_block_ranges
from core.excel_timeseries import extract_block_timeseries
from core.block_namer import detect_block_titles, map_titles_to_names
from core.option6_sat_bess import OptionSizing, build_option_slab_table
XLSX_PATH = Path("data") / "MH_BESS_Solar_Wind.xlsx"
SHEET = "Data"

# --- Build model_df (same as Step 5) ---
header_rows = detect_time_month_headers(XLSX_PATH, sheet=SHEET, scan_rows=300)
titles = detect_block_titles(XLSX_PATH, sheet=SHEET, header_rows=header_rows, lookback_rows=4)
names  = map_titles_to_names(titles)

full = pd.read_excel(XLSX_PATH, sheet_name=SHEET, header=None)
ranges = compute_block_ranges(header_rows, total_rows=full.shape[0])

blocks = []
for i, (start, stop) in enumerate(ranges):
    ts = extract_block_timeseries(
        xlsx_path=XLSX_PATH,
        sheet=SHEET,
        header_row=start,
        stop_row=stop,
        value_name=f"block_{i}",
    )
    blocks.append(ts)

model_df = build_model_df(blocks, names)
print("\nmodel_df columns:")
print(model_df.columns.tolist())

print("\nPossible solar columns:")
print([c for c in model_df.columns if "solar" in c.lower()])

print("\nPossible sat columns:")
print([c for c in model_df.columns if "sat" in c.lower()])


# --- Step 6 sizing ---
sizing = OptionSizing(
    load_mw=1.0,
    solar_col_1mw="160_ft_solar_generation_reference_for_1_mwp",
    solar_mw=1.88,
    wind_col_1mw=None,
    wind_mw=0.0
)


slab = build_option_slab_table(model_df, sizing)

print("\n=== OPTION 6 (SAT) slab-wise (NO BESS yet) ===")
print(slab.to_string(index=False))
