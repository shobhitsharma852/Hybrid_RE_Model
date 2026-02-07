from pathlib import Path
import pandas as pd

MONTHS = {"jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"}

def detect_time_month_headers(xlsx_path: Path, sheet: str, scan_rows=300):      #Reads only the first 300 rows (default)
    """
    Finds rows that look like:
    ['Time', 'Jan', 'Feb', ..., 'Dec']
    """
    preview = pd.read_excel(
        xlsx_path,
        sheet_name=sheet,
        header=None,                                #No headers assumed (header=None)
        nrows=scan_rows
    )

    header_rows = []

    for i in range(len(preview)):
        row = preview.iloc[i].dropna().astype(str).str.strip().str.lower()         #Cleans up the row values 
        if "time" in row.values and MONTHS.issubset(set(row.values)):          #Checks if 'time' and all months are present in the row
            header_rows.append(i)

    return sorted(header_rows)                                                  #Return sorted list of detected header rows


def compute_block_ranges(header_rows, total_rows):
    """
    “If a table starts at row X, where does it end?”
    """
    ranges = []
    for i, start in enumerate(header_rows):
        stop = header_rows[i + 1] if i + 1 < len(header_rows) else total_rows
        '''If there is another table after this one, stop at the next table’s start.
          If there is no next table, stop at the end of the sheet.'''
        ranges.append((start, stop))
    return ranges
