from pathlib import Path
from core.excel_blocks import detect_time_month_headers, compute_block_ranges
from core.excel_timeseries import extract_block_timeseries
import pandas as pd

XLSX = Path("data") / "MH_BESS_Solar_Wind.xlsx"
SHEET = "Data"

headers = detect_time_month_headers(XLSX, SHEET)
print("Detected header rows:", headers)

total_rows = pd.read_excel(XLSX, sheet_name=SHEET, header=None).shape[0]
ranges = compute_block_ranges(headers, total_rows)

for i, (start, stop) in enumerate(ranges):
    ts = extract_block_timeseries(
        XLSX,
        sheet=SHEET,
        header_row=start,
        stop_row=stop,
        value_name=f"block_{i}"
    )

    print(f"\nBlock {i}")
    print("Shape:", ts.shape)
    print(ts.head())
    print("Monthly sum (first 3):")
    print(ts.groupby("month")[f"block_{i}"].sum().head(3))
