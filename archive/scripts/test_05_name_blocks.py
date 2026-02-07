from pathlib import Path
import pandas as pd

from core.excel_blocks import detect_time_month_headers, compute_block_ranges
from core.excel_timeseries import extract_block_timeseries
from core.block_namer import detect_block_titles, map_titles_to_names
from core.model_builder import build_model_df

XLSX_PATH = Path("data") / "MH_BESS_Solar_Wind.xlsx"
SHEET = "Data"

# 1) detect block headers
header_rows = detect_time_month_headers(XLSX_PATH, sheet=SHEET, scan_rows=300)

# 2) get titles + final names
titles = detect_block_titles(XLSX_PATH, sheet=SHEET, header_rows=header_rows, lookback_rows=4)
names  = map_titles_to_names(titles)

print("\n=== Block naming ===")
for i, (hr, t, n) in enumerate(zip(header_rows, titles, names)):
    print(f"{i:02d} | header_row={hr:3d} | title='{t}' -> name='{n}'")

# 3) compute ranges
full = pd.read_excel(XLSX_PATH, sheet_name=SHEET, header=None)
ranges = compute_block_ranges(header_rows, total_rows=full.shape[0])

# 4) extract blocks
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

# 5) build model_df with REAL names
model_df = build_model_df(blocks, names)

print("\nmodel_df columns:", model_df.columns.tolist())
print(model_df.head(8).to_string(index=False))

