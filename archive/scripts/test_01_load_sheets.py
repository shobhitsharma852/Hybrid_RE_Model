from pathlib import Path
from core.loader import list_sheets

XLSX = Path("data") / "MH_BESS_Solar_Wind.xlsx"

print("Excel exists:", XLSX.exists())
print("Sheets:", list_sheets(XLSX))
