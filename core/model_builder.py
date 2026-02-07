from __future__ import annotations
from pathlib import Path
import pandas as pd

# This is your month order (fixes alphabetical sorting forever)
MONTH_ORDER = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def _ensure_month_order(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["month"] = pd.Categorical(df["month"], categories=MONTH_ORDER, ordered=True)
    return df.sort_values(["month", "hour"]).reset_index(drop=True)

def build_model_df(blocks: list[pd.DataFrame], block_names: list[str]) -> pd.DataFrame:
    """
    blocks: list of long tables: [hour, month, block_i]
    block_names: same length; final column names to use
    Returns: one merged long table: [month, hour, <named columns...>]
    """
    assert len(blocks) == len(block_names), "blocks and block_names length mismatch"

    base = blocks[0][["month","hour"]].copy()
    base = _ensure_month_order(base)

    for df, name in zip(blocks, block_names):
        value_col = [c for c in df.columns if c not in ("month","hour")]
        if len(value_col) != 1:
            raise ValueError(f"Expected exactly 1 value column in block, got {value_col}")
        v = value_col[0]

        tmp = df[["month","hour",v]].copy()
        tmp = tmp.rename(columns={v: name})
        base = base.merge(tmp, on=["month","hour"], how="left")

    # numeric + fill
    for c in base.columns:
        if c not in ("month","hour"):
            base[c] = pd.to_numeric(base[c], errors="coerce").fillna(0.0)

    return _ensure_month_order(base)
