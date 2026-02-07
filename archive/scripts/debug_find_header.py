from pathlib import Path
import pandas as pd

XLSX_PATH = Path("data") / "MH_BESS_Solar_Wind.xlsx"
sheet = "Data"

preview = pd.read_excel(XLSX_PATH, sheet_name=sheet, header=None, nrows=250)

for r in range(250):
    row = preview.iloc[r].tolist()
    row_str = [str(x).strip() for x in row if pd.notna(x)]
    if any(v.lower() == "time" for v in row_str) and any(v == "Jan" for v in row_str):
        print("Found candidate row:", r, row_str[:20])
