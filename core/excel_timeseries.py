import pandas as pd

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def extract_block_timeseries(
    xlsx_path,
    sheet,
    header_row,
    stop_row,
    value_name,
):
    # Read full sheet once (ok for now; later we can optimize with skiprows/nrows)
    full = pd.read_excel(xlsx_path, sheet_name=sheet, header=None)

    raw = full.iloc[header_row:stop_row].copy()

    # First row is header
    header = raw.iloc[0].tolist()
    raw = raw.iloc[1:].copy()
    raw.columns = header

    # Remove duplicate column names (important when "Time" appears twice)
    raw = raw.loc[:, ~pd.Index(raw.columns).duplicated()]

    # Find "Time" column
    time_cols = [
        c for c in raw.columns
        if isinstance(c, str) and c.strip().lower() == "time"
    ]
    if not time_cols:
        raise ValueError(f"No 'Time' column found in block starting at row {header_row}. Header was: {header}")

    time_col = time_cols[0]

    # Month columns present in this block
    month_cols = [m for m in MONTHS if m in raw.columns]
    if not month_cols:
        raise ValueError(f"No month columns found in block starting at row {header_row}. Header was: {header}")

    # Keep only needed columns
    raw = raw[[time_col] + month_cols].copy()

    # Rename Time -> hour and clean hour
    raw = raw.rename(columns={time_col: "hour"})
    raw["hour"] = pd.to_numeric(raw["hour"], errors="coerce")
    raw = raw.dropna(subset=["hour"])
    raw["hour"] = raw["hour"].astype(int)

    # Long format
    ts = raw.melt(
        id_vars="hour",
        value_vars=month_cols,
        var_name="month",
        value_name=value_name
    )

    # Force Jan->Dec order (fixes your alphabetic issue)
    ts["month"] = pd.Categorical(ts["month"], categories=MONTHS, ordered=True)

    # Values numeric
    ts[value_name] = pd.to_numeric(ts[value_name], errors="coerce").fillna(0.0)

    return ts.sort_values(["month", "hour"]).reset_index(drop=True)
