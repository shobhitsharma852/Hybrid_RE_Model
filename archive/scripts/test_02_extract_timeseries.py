from pathlib import Path
from core.excel_read import extract_timeseries_from_time_month_table

XLSX_PATH = Path("data") / "MH_BESS_Solar_Wind.xlsx"
SHEET_NAME = "Data"

for header_row in [1, 38, 75, 112, 149]:
    print("\n" + "="*80)
    print("TRY header_row =", header_row)

    try:
        ts = extract_timeseries_from_time_month_table(
            XLSX_PATH,
            sheet=SHEET_NAME,
            value_name="value_1mw",
            header_row=header_row,   # ✅ force specific block
        )

        print("Extracted shape:", ts.shape)
        print(ts.head(5))
        print("Hours:", sorted(ts["hour"].unique())[:5], "...", sorted(ts["hour"].unique())[-5:])
        print("Month sums (first 3):")
        print(ts.groupby("month")["value_1mw"].sum().head(3))

    except Exception as e:
        print("FAILED:", repr(e))
