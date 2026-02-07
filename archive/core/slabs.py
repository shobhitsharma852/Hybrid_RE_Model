from __future__ import annotations
import pandas as pd

# Define slabs (you can edit once to match Excel exactly)
# A: 00-06, C: 06-09, B: 09-17, D: 17-24
SLABS = {
    "A (12am to 6am)": list(range(0, 6)),
    "C (6am to 9am)": list(range(6, 9)),
    "B (9am to 5pm)": list(range(9, 17)),
    "D (5pm to 12am)": list(range(17, 24)),
}

def add_slab(df: pd.DataFrame, hour_col: str = "hour") -> pd.DataFrame:
    out = df.copy()

    def hour_to_slab(h: int) -> str:
        for slab, hours in SLABS.items():
            if int(h) in hours:
                return slab
        return "UNKNOWN"

    out["slab"] = out[hour_col].astype(int).map(hour_to_slab)
    return out

def slab_month_sum(df: pd.DataFrame, value_cols: list[str]) -> pd.DataFrame:
    """
    Returns sums by (month, slab) for each value column.
    """
    g = df.groupby(["month", "slab"], observed=True)[value_cols].sum().reset_index()
    return g

def slab_total_sum(df: pd.DataFrame, value_cols: list[str]) -> pd.DataFrame:
    """
    Returns sums by slab across all months.
    """
    g = df.groupby(["slab"], observed=True)[value_cols].sum().reset_index()
    return g

def add_total_row(slab_df: pd.DataFrame, value_cols: list[str]) -> pd.DataFrame:
    """
    Adds Total row (sum of all slabs).
    """
    total = {c: slab_df[c].sum() for c in value_cols}
    total["slab"] = "Total"
    return pd.concat([slab_df, pd.DataFrame([total])], ignore_index=True)
