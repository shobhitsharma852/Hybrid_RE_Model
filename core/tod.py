import pandas as pd

# Your banking slabs:
# A: 12am–6am  -> hours 0..5
# C: 6am–9am   -> hours 6..8
# B: 9am–5pm   -> hours 9..16
# D: 5pm–12am  -> hours 17..23

def add_tod_slot(df: pd.DataFrame, hour_col: str = "hour", out_col: str = "tod_slot") -> pd.DataFrame:
    h = df[hour_col].astype(int)

    def _slot(x: int) -> str:
        if 0 <= x <= 5:
            return "A"
        if 6 <= x <= 8:
            return "C"
        if 9 <= x <= 16:
            return "B"
        return "D"

    df[out_col] = h.map(_slot)
    return df


def add_tod_rate(
    df: pd.DataFrame,
    rates: dict[str, float],
    slot_col: str = "tod_slot",
    out_col: str = "tod_rate_rs_per_kwh",
) -> pd.DataFrame:
    df[out_col] = df[slot_col].map(rates).astype(float)
    return df
