print("✅ test_loader.py started")


from pathlib import Path
from core.loader import load_model_df

XLSX_PATH = Path("data") / "MH_BESS_Solar_Wind.xlsx"
df = load_model_df(XLSX_PATH)

print("Loaded shape:", df.shape)
print("Columns:", df.columns.tolist())
print("Months:", sorted(df["month"].unique()))
print("Hours:", sorted(df["hour"].unique())[:5], "...", sorted(df["hour"].unique())[-5:])
print(df.head(5))
