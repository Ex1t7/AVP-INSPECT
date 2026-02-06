#!/usr/bin/env python3
"""
make_common_heatmap_inputs.py

Reads two heatmap CSVs (matrix-style), and trims BOTH to the common:
- data_type labels (row index)
- entity labels (column headers)

Assumes:
- First column = data_type (row labels)
- Remaining columns = entities
- Cell values = numeric (or convertible)

Outputs:
- <A_stem>__COMMON.csv
- <B_stem>__COMMON.csv
"""

from pathlib import Path
import pandas as pd
import numpy as np


# =========================
# Config (edit if needed)
# =========================
CSV_A = "heatmap_entity_manifest_contrary_disclosure_data.csv"
CSV_B = "heatmap_entity_manifest_neglect_disclosure_data.csv"

DROP_UNKNOWN_COL = True   # drop columns named "Unknown" (case-insensitive)
DROP_UNKNOWN_ROW = True   # drop rows named "Unknown" (case-insensitive)

# If you want case-insensitive matching / whitespace cleanup:
NORMALIZE_LABELS = True


# =========================
# Helpers
# =========================
def norm_label(x: str) -> str:
    x = "" if x is None else str(x)
    x = x.strip()
    x = " ".join(x.split())  # collapse internal whitespace
    return x.lower() if NORMALIZE_LABELS else x


def load_matrix(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if df.shape[1] < 2:
        raise ValueError(f"{csv_path} does not look like a matrix CSV (needs >= 2 columns).")

    # First column is row label
    first_col = df.columns[0]
    df = df.set_index(first_col)

    # Normalize row/col labels (optionally)
    if NORMALIZE_LABELS:
        df.index = [norm_label(i) for i in df.index]
        df.columns = [norm_label(c) for c in df.columns]

    # Drop duplicate labels cleanly (keep first)
    if df.index.duplicated().any():
        dup = df.index[df.index.duplicated()].unique().tolist()
        print(f"[warn] Duplicate row labels found (keeping first): {dup[:10]}{'...' if len(dup) > 10 else ''}")
        df = df[~df.index.duplicated(keep="first")]

    if pd.Index(df.columns).duplicated().any():
        dup = pd.Index(df.columns)[pd.Index(df.columns).duplicated()].unique().tolist()
        print(f"[warn] Duplicate column labels found (keeping first): {dup[:10]}{'...' if len(dup) > 10 else ''}")
        df = df.loc[:, ~pd.Index(df.columns).duplicated(keep="first")]

    # Optional unknown drops
    if DROP_UNKNOWN_ROW:
        df = df.loc[[i for i in df.index if i.lower() != "unknown"]]

    if DROP_UNKNOWN_COL:
        df = df.loc[:, [c for c in df.columns if c.lower() != "unknown"]]

    # Convert values to numeric where possible (keeps NaN if not)
    df = df.apply(pd.to_numeric, errors="coerce")

    return df


def save_common(df: pd.DataFrame, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Put row index back as first column (same format as input)
    out = df.copy()
    out.insert(0, "data_type", out.index)
    out.to_csv(out_path, index=False)


# =========================
# Main
# =========================
def main():
    a_path = Path(CSV_A)
    b_path = Path(CSV_B)

    A = load_matrix(str(a_path))
    B = load_matrix(str(b_path))

    common_rows = sorted(set(A.index).intersection(B.index))
    common_cols = sorted(set(A.columns).intersection(B.columns))

    if len(common_rows) == 0:
        raise ValueError("No common data_type row labels found between the two CSVs.")
    if len(common_cols) == 0:
        raise ValueError("No common entity column labels found between the two CSVs.")

    A_common = A.loc[common_rows, common_cols]
    B_common = B.loc[common_rows, common_cols]

    out_a = a_path.with_suffix("").name + "__COMMON.csv"
    out_b = b_path.with_suffix("").name + "__COMMON.csv"

    save_common(A_common, Path(out_a))
    save_common(B_common, Path(out_b))

    # Quick report
    print("==== Common trim report ====")
    print(f"A original: rows={A.shape[0]}, cols={A.shape[1]}")
    print(f"B original: rows={B.shape[0]}, cols={B.shape[1]}")
    print(f"COMMON    : rows={len(common_rows)}, cols={len(common_cols)}")
    print(f"Wrote: {out_a}")
    print(f"Wrote: {out_b}")

    # Optional: list what got dropped (small-ish)
    dropped_rows_a = sorted(set(A.index) - set(common_rows))
    dropped_rows_b = sorted(set(B.index) - set(common_rows))
    dropped_cols_a = sorted(set(A.columns) - set(common_cols))
    dropped_cols_b = sorted(set(B.columns) - set(common_cols))

    print("\nDropped from A (rows):", len(dropped_rows_a))
    print("Dropped from B (rows):", len(dropped_rows_b))
    print("Dropped from A (cols):", len(dropped_cols_a))
    print("Dropped from B (cols):", len(dropped_cols_b))


if __name__ == "__main__":
    main()

