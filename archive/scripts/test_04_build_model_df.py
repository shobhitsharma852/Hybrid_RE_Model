from pathlib import Path
import pandas as pd

from core.excel_blocks import detect_time_month_headers, compute_block_ranges
from core.excel_timeseries import extract_block_timeseries
from core.model_builder import build_model_df

XLSX_PATH = Path("data") / "MH_BESS_Solar_Wind.xlsx"
SHEET = "Data"

# 1) detect blocks
header_rows = detect_time_month_headers(XLSX_PATH, sheet=SHEET, scan_rows=300)
full = pd.read_excel(XLSX_PATH, sheet_name=SHEET, header=None)
ranges = compute_block_ranges(header_rows, total_rows=full.shape[0])

# 2) extract blocks
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

print("Detected blocks:", len(blocks))

# 3) ✅ NOW: name them (temporary names first; we'll refine next)
block_names = [f"block_{i}" for i in range(len(blocks))]

model_df = build_model_df(blocks, block_names)

print("model_df shape:", model_df.shape)
print(model_df.head(10).to_string(index=False))
print("\nColumns:", model_df.columns.tolist())
