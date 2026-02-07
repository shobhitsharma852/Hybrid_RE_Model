from __future__ import annotations
import pandas as pd

def scale_series(ts: pd.DataFrame, value_col: str, factor: float, out_col: str | None = None) -> pd.DataFrame:
    """
    Multiply a long timeseries (hour, month, value_col) by a factor.
    """
    out_col = out_col or value_col
    out = ts.copy()
    out[out_col] = out[value_col].astype(float) * float(factor)
    return out

def add_total_re(df: pd.DataFrame, solar_col: str, wind_col: str | None, out_col: str = "total_re") -> pd.DataFrame:
    out = df.copy()
    if wind_col and wind_col in out.columns:
        out[out_col] = out[solar_col].astype(float) + out[wind_col].astype(float)
    else:
        out[out_col] = out[solar_col].astype(float)
    return out

def add_excess(df: pd.DataFrame, total_re_col: str, load_col: str, out_col: str = "excess") -> pd.DataFrame:
    out = df.copy()
    out[out_col] = (out[total_re_col].astype(float) - out[load_col].astype(float)).clip(lower=0.0)
    return out
