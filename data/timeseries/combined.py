#!/usr/bin/env python3
"""
Make TWO 5x1 (one-row) combined PDFs from your files:

Order (left→right):
  productivity, creative, entertainment, social_health, lifestyle
"""

from pathlib import Path
from pypdf import PdfReader, PdfWriter
from pypdf._page import PageObject

# ---------------------------
# Config
# ---------------------------
IN_DIR = Path(".")
OUT_UI = Path("timeseries_ui_clicks.pdf")
OUT_NET = Path("timeseries_network_traffic.pdf")

ORDER = ["productivity", "creative", "entertainment", "social_health", "lifestyle"]

UI_FILES = [f"{c}_ui_clicks.pdf" for c in ORDER]
NET_FILES = [f"{c}_network_traffic.pdf" for c in ORDER]

# ---- Tighter layout ----
GAP_PTS = 2          # space between figures (smaller = tighter). Try 0–4.
MARGIN_PTS = 12      # outer margins
SCALE = 1.0
UNIFORM_CELL = True
V_ALIGN = "center"   # "top" | "center" | "bottom"


def first_page(pdf_path: Path) -> PageObject:
    r = PdfReader(str(pdf_path))
    if not r.pages:
        raise ValueError(f"No pages in {pdf_path}")
    return r.pages[0]


def place_page(dst: PageObject, src: PageObject, tx: float, ty: float, scale: float) -> None:
    dst.merge_transformed_page(src, (scale, 0, 0, scale, tx, ty))


def combine_5x1(files: list[str], out_pdf: Path) -> None:
    paths = [IN_DIR / f for f in files]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing files:\n  " + "\n  ".join(missing))

    pages = [first_page(p) for p in paths]

    sizes = []
    for pg in pages:
        w = float(pg.mediabox.width) * SCALE
        h = float(pg.mediabox.height) * SCALE
        sizes.append((w, h))

    if UNIFORM_CELL:
        cell_w = max(w for w, _ in sizes)
        cell_h = max(h for _, h in sizes)
        total_w = MARGIN_PTS * 2 + 5 * cell_w + 4 * GAP_PTS
        total_h = MARGIN_PTS * 2 + cell_h
    else:
        cell_h = max(h for _, h in sizes)
        total_w = MARGIN_PTS * 2 + sum(w for w, _ in sizes) + 4 * GAP_PTS
        total_h = MARGIN_PTS * 2 + cell_h

    out_page = PageObject.create_blank_page(width=total_w, height=total_h)

    x = MARGIN_PTS
    for i, pg in enumerate(pages):
        w_i, h_i = sizes[i]

        if V_ALIGN == "top":
            y = MARGIN_PTS + (cell_h - h_i)
        elif V_ALIGN == "bottom":
            y = MARGIN_PTS
        else:
            y = MARGIN_PTS + (cell_h - h_i) / 2.0

        if UNIFORM_CELL:
            x_i = x + (cell_w - w_i) / 2.0
            place_page(out_page, pg, x_i, y, SCALE)
            x += cell_w + GAP_PTS
        else:
            place_page(out_page, pg, x, y, SCALE)
            x += w_i + GAP_PTS

    writer = PdfWriter()
    writer.add_page(out_page)
    with open(out_pdf, "wb") as f:
        writer.write(f)

    print(f"[OK] {out_pdf}  ({total_w:.1f} x {total_h:.1f} pts)")
    print("     Order:", ", ".join(files))


if __name__ == "__main__":
    combine_5x1(UI_FILES, OUT_UI)
    combine_5x1(NET_FILES, OUT_NET)

