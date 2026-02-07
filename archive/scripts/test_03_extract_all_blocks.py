from pathlib import Path
import pandas as pd

from core.excel_blocks import detect_time_month_headers, compute_block_ranges
from core.excel_timeseries import extract_block_timeseries

XLSX_PATH = Path("data") / "MH_BESS_Solar_Wind.xlsx"
SHEET = "Data"

print("Excel exists:", XLSX_PATH.exists())

# 1) detect header rows
header_rows = detect_time_month_headers(XLSX_PATH, sheet=SHEET, scan_rows=300)
print("Detected header rows:", header_rows)

# 2) load sheet once to get total rows (needed for last block stop)
full = pd.read_excel(XLSX_PATH, sheet_name=SHEET, header=None)
total_rows = len(full)

# 3) compute (start, stop) for each block
ranges = compute_block_ranges(header_rows, total_rows)
print("Block ranges:", ranges)

# 4) extract each block
blocks = []
for i, (start, stop) in enumerate(ranges):
    ts = extract_block_timeseries(
        xlsx_path=XLSX_PATH,
        sheet=SHEET,
        header_row=start,
        stop_row=stop,
        value_name=f"block_{i}",
    )
    print(f"Block {i} shape:", ts.shape)
    blocks.append(ts)

print("Done. Blocks extracted:", len(blocks))
