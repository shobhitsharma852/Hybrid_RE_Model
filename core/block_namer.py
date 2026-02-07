from __future__ import annotations
from pathlib import Path
import re
import pandas as pd

def _clean_title(s: str) -> str:       #Excel titles often have inconsistent spacing
    s = str(s).strip()
    s = re.sub(r"\s+", " ", s)         # " Load Reference 1 MW "           "Load Reference 1 MW"
    return s  

def _slug(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")    #"file@name#1"  → "file_name_1"
    return s

def detect_block_titles(
    xlsx_path: Path,
    sheet: str,
    header_rows: list[int],
    lookback_rows: int = 3,
) -> list[str]:
    """
    For each header_row (where Time/Jan/... appears),
    look ABOVE it to find the nearest non-empty text cell
    that acts like the block title.
    """
    full = pd.read_excel(xlsx_path, sheet_name=sheet, header=None)

    titles = []
    for hr in header_rows:
        title = None

        # search rows above the header row
        for r in range(max(0, hr - lookback_rows), hr)[::-1]:
            row = full.iloc[r].tolist()

            # pick the first meaningful text cell in that row
            for cell in row:
                if pd.isna(cell):
                    continue
                txt = _clean_title(cell)
                if txt and txt.lower() not in ("time", "jan", "feb", "mar"):
                    title = txt
                    break
            if title:
                break

        if not title:
            title = f"block_{hr}"

        titles.append(title)

    return titles

def map_titles_to_names(titles: list[str]) -> list[str]:
    """
    Convert Excel titles into stable python column names.
    You can improve these rules anytime without touching extraction code.
    """
    names = []
    for t in titles:
        tl = t.lower()

        # Load blocks
        if "load" in tl and "reference" in tl and "1mw" in tl:
            names.append("load_1mw")
            continue
        if "load requirement" in tl:
            names.append("load_requirement_1mw")
            continue

        # Solar blocks
        if "ft solar" in tl and "1mw" in tl:
            names.append("solar_ft_1mw")
            continue
        if "sat solar" in tl and "1mw" in tl:
            names.append("solar_sat_1mw")
            continue

        # Wind blocks
        if "wind" in tl and "1mw" in tl:
            names.append("wind_1mw")
            continue

        # BESS related
        if "difference" in tl and "discharging limits" in tl:
            names.append("bess_discharge_limit_kw")
            continue
        if "difference" in tl and "charging limits" in tl:
            names.append("bess_charge_limit_kw")
            continue

        # fallback
        names.append(_slug(t))

    # If duplicates happen, make them unique
    seen = {}
    out = []
    for n in names:
        if n not in seen:
            seen[n] = 1
            out.append(n)
        else:
            seen[n] += 1
            out.append(f"{n}_{seen[n]}")
    return out
