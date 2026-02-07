from pathlib import Path
import pandas as pd

from core.excel_blocks import detect_time_month_headers, compute_block_ranges
from core.excel_timeseries import extract_block_timeseries
from core.block_namer import detect_block_titles, map_titles_to_names
from core.model_builder import build_model_df


def list_sheets(xlsx_path: Path) -> list[str]:
    xlsx_path = Path(xlsx_path)
    return pd.ExcelFile(xlsx_path).sheet_names


def load_model_df(xlsx_path: Path, sheet: str = "Data") -> pd.DataFrame:
    """
    Builds unified model_df:
    columns like:
    month, hour, load_1mw, <solar columns>, wind_1mw
    """

    xlsx_path = Path(xlsx_path)

    header_rows = detect_time_month_headers(xlsx_path, sheet=sheet, scan_rows=300)

    titles = detect_block_titles(
        xlsx_path, sheet=sheet, header_rows=header_rows, lookback_rows=4
    )
    names = map_titles_to_names(titles)

    full = pd.read_excel(xlsx_path, sheet_name=sheet, header=None)
    ranges = compute_block_ranges(header_rows, total_rows=full.shape[0])

    blocks = []
    for i, (start, stop) in enumerate(ranges):
        ts = extract_block_timeseries(
            xlsx_path=xlsx_path,
            sheet=sheet,
            header_row=start,
            stop_row=stop,
            value_name=f"block_{i}",
        )
        blocks.append(ts)

    model_df = build_model_df(blocks, names)
    return model_df
