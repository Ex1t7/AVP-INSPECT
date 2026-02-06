import matplotlib
matplotlib.use("Agg")  # headless-safe PDF export

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# =========================
# Inputs
# =========================
CSV_A = "heatmap_entity_label_contrary_common.csv"   # reference
CSV_B = "heatmap_entity_label_neglect_common.csv"    # attached
OUT_PDF = "entity_violation.pdf"

TOP_K_ENTITIES = 15
TOP_K_TYPES    = 30
DROP_UNKNOWN   = True

# =========================
# Style (match default pair styling)
# =========================
FIG_W, FIG_H = 16, 9   # 4:3

XTICK_FS = 18
YTICK_FS = 18
CELL_FS  = 12
CBAR_FS  = 14
TITLE_FS = 14

# Fixed color scale (0–450)
VMIN = 0
VMAX = 450

plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"]  = 42

# =========================
# Helpers
# =========================
def load_matrix(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = df.set_index(df.columns[0])

    if DROP_UNKNOWN:
        col_map = {c.lower(): c for c in df.columns}
        if "unknown" in col_map:
            df = df.drop(columns=[col_map["unknown"]])

    return df.apply(pd.to_numeric, errors="coerce").fillna(0)


def select_axes(df: pd.DataFrame):
    cols = df.sum(axis=0).sort_values(ascending=False).head(TOP_K_ENTITIES).index
    rows = df[cols].sum(axis=1).sort_values(ascending=False).head(TOP_K_TYPES).index
    return list(rows), list(cols)


def draw_heatmap(ax, df_xy, title, show_yaxis):
    data = df_xy.values.astype(float)
    masked = np.where(data == 0, np.nan, data)

    cmap = plt.cm.YlOrRd.copy()
    cmap.set_bad(color="white")

    ax.set_facecolor("white")
    im = ax.imshow(
        masked,
        aspect="auto",
        cmap=cmap,
        vmin=VMIN,
        vmax=VMAX
    )

    ax.set_title(title, fontsize=TITLE_FS)

    ax.set_xticks(range(len(df_xy.columns)))
    ax.set_xticklabels(
        df_xy.columns,
        rotation=35,
        ha="right",
        fontsize=XTICK_FS
    )

    ax.set_yticks(range(len(df_xy.index)))
    if show_yaxis:
        ax.set_yticklabels(df_xy.index, fontsize=YTICK_FS)
    else:
        ax.set_yticklabels([])
        ax.tick_params(axis="y", length=0)

    # annotate non-zero cells
    for i in range(df_xy.shape[0]):
        for j in range(df_xy.shape[1]):
            v = data[i, j]
            if v > 0:
                ax.text(
                    j, i, f"{int(v)}",
                    ha="center",
                    va="center",
                    fontsize=CELL_FS
                )

    return im


# =========================
# Load data + align axes
# =========================
dfA = load_matrix(CSV_A)
dfB = load_matrix(CSV_B)

rows, cols = select_axes(dfA)

dfA_xy = dfA.reindex(index=rows, columns=cols, fill_value=0).clip(upper=VMAX)
dfB_xy = dfB.reindex(index=rows, columns=cols, fill_value=0).clip(upper=VMAX)

# =========================
# Figure layout (2 heatmaps + dedicated colorbar)
# =========================
fig, axes = plt.subplots(
    1, 2,
    figsize=(FIG_W, FIG_H),
    gridspec_kw={"width_ratios": [1.0, 1.0]}
)

# Match your default geometry
fig.subplots_adjust(
    left=0.20,   # auto-fixed later
    right=0.90,  # leaves space for colorbar at 0.92+
    top=0.92,
    bottom=0.22,
    wspace=0.10
)

im1 = draw_heatmap(axes[0], dfA_xy, "Contrary", show_yaxis=True)
im2 = draw_heatmap(axes[1], dfB_xy, "Neglect", show_yaxis=False)

# Dedicated colorbar axis (outside subplots; no overlap)
cax = fig.add_axes([0.92, 0.25, 0.015, 0.60])  # [left, bottom, width, height]
cbar = fig.colorbar(im2, cax=cax)
cbar.set_label("Disclosure Count", fontsize=CBAR_FS)
cbar.ax.tick_params(labelsize=CBAR_FS)

# =========================
# Auto-fix left margin so y-labels never get cut
# =========================
fig.canvas.draw()
renderer = fig.canvas.get_renderer()
yticklabels = [t for t in axes[0].get_yticklabels() if t.get_text()]
if yticklabels:
    max_w_px = max(t.get_window_extent(renderer=renderer).width for t in yticklabels)
    fig_w_px = fig.bbox.width
    left_needed = (max_w_px / fig_w_px) + 0.06
    left_needed = min(max(left_needed, 0.14), 0.45)
    fig.subplots_adjust(left=left_needed)
    fig.canvas.draw()

# =========================
# Export
# =========================
fig.savefig(OUT_PDF, format="pdf")
plt.close(fig)

print(f"[+] Saved -> {OUT_PDF}")

