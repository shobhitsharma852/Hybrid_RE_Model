from __future__ import annotations
from pathlib import Path
import pandas as pd

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def find_header_row_with_time_and_months(xlsx_path: Path, sheet: str, scan_rows: int = 80) -> int:
    """
    Scans the top scan_rows rows and returns the row index that contains:
      - a 'Time' cell (or 'Hour')
      - and at least 6 month names (Jan..Dec)
    """
    preview = pd.read_excel(xlsx_path, sheet_name=sheet, header=None, nrows=scan_rows)

    for r in range(len(preview)):
        row_vals = [str(x).strip() for x in preview.iloc[r].tolist() if pd.notna(x)]
        if not row_vals:
            continue

        has_time = any(v.lower() in ("time", "hour") for v in row_vals)
        month_hits = sum(v in MONTHS for v in row_vals)

        if has_time and month_hits >= 6:   # >=6 months is strong enough
            return r

    raise ValueError(
        f"Could not find a header row with Time+months in sheet={sheet}. "
        f"Scanned first {scan_rows} rows."
    )


def extract_timeseries_from_time_month_table(
    xlsx_path,
    sheet: str,
    value_name: str,
    header_row: int,
    stop_row: int | None = None,   # ✅ new
)-> pd.DataFrame:
    """
    Reads a sheet that contains somewhere a block like:
      Time | Jan | Feb | ... | Dec
    and returns:
      month | hour | <value_name>
    """
    if header_row is None:
        header_row = find_header_row_with_time_and_months(xlsx_path, sheet, scan_rows=scan_rows)

    df = pd.read_excel(xlsx_path, sheet_name=sheet, header=header_row)

    # detect time column
    time_col = None
    for c in df.columns:
        if str(c).strip().lower() in ("time", "hour"):
            time_col = c
            break
    if time_col is None:
        # sometimes time column name becomes 'Time ' etc
        for c in df.columns:
            if "time" in str(c).strip().lower() or "hour" in str(c).strip().lower():
                time_col = c
                break
    if time_col is None:
        raise ValueError(f"Could not detect time column after using header_row={header_row}. Columns={list(df.columns)}")

    # detect month columns
    cols = [str(c).strip() for c in df.columns]
    month_cols = [c for c in cols if c in MONTHS]
    if not month_cols:
        raise ValueError(f"Could not detect month columns after using header_row={header_row}. Columns={list(df.columns)}")

    out = df[[time_col] + month_cols].copy()

    out[time_col] = pd.to_numeric(out[time_col], errors="coerce")
    out = out.dropna(subset=[time_col])

    out["hour"] = out[time_col].round(0).astype(int)
    out = out.drop(columns=[time_col])

    long_df = out.melt(id_vars=["hour"], var_name="month", value_name=value_name)
    long_df[value_name] = pd.to_numeric(long_df[value_name], errors="coerce").fillna(0.0)

    long_df = long_df[(long_df["hour"] >= 0) & (long_df["hour"] <= 23)].copy()
    long_df["month"] = pd.Categorical(long_df["month"], categories=MONTHS, ordered=True)
    long_df = long_df.sort_values(["month", "hour"]).reset_index(drop=True)

    return long_df
