import pandas as pd
import matplotlib.pyplot as plt

# ================== ONE GLOBAL FONT SIZE ==================
FONT_FS   = 24  # <- change once, everything follows
LINEWIDTH = 3.5

# Make PDF text selectable + crisp
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"]  = 42

# ================== Inputs ==================
CSV_PATH = "timeseries_traffic_xy_data.csv"
CAPTION  = "(b) Creative"
OUT_PDF  = "creative_network_traffic.pdf"

# Apps to include
targets = [
    "Bento",
    "Shotbot",
    "Magnet",
    "Spatial Video",
    "Heypster",
]

# Fixed 5 colors
colors = ["red", "blue", "green", "orange", "purple"]

# Canonical substring keys
canonical_keys = {
    "bento": "bento",
    "shotbot": "shotbot",
    "magnet": "magnet",
    "spatial video": "spatial video",
    "heypster": "heypster",
}

def canonical_key(app_name: str):
    n = str(app_name).lower()
    for key in canonical_keys:
        if key in n:
            return key
    return None

# Paper-ready legend names
legend_map = {
    "bento": "Bento",
    "shotbot": "Shotbot",
    "magnet": "Magnet Crop",
    "spatial video": "Spatial Video Studio",
    "heypster": "Heypster",
}

# Plot order controls legend order too
plot_order = ["bento", "shotbot", "magnet", "spatial video", "heypster"]

# Legend placement (match base; change if needed)
LEGEND_LOC = "upper left"

# ================== Load data ==================
df = pd.read_csv(CSV_PATH)

# ================== Filter rows ==================
mask = False
for t in targets:
    mask = mask | df["app_name"].str.contains(t, case=False, na=False)

df_sel = df[mask].copy()
df_sel["canon"] = df_sel["app_name"].apply(canonical_key)
df_sel = df_sel[df_sel["canon"].notna()].copy()

# ================== Convert seconds → minutes ==================
df_sel["time_min"] = df_sel["x_time_seconds"] / 60.0
df_sel = df_sel[df_sel["time_min"] <= 20].copy()

# ================== Plot (exact 4:3) ==================
fig, ax = plt.subplots(figsize=(12.0, 9.0))  # exact 4:3 (same as base)

for canon_key, color in zip(plot_order, colors):
    sub = df_sel[df_sel["canon"] == canon_key].copy()
    if sub.empty:
        continue

    sub = sub.sort_values("time_min")[["time_min", "y_cumulative_requests"]].copy()

    # Force origin (0,0)
    first_t = float(sub["time_min"].iloc[0])
    first_y = float(sub["y_cumulative_requests"].iloc[0])
    if first_t != 0.0 or first_y != 0.0:
        sub = pd.concat(
            [pd.DataFrame({"time_min": [0.0], "y_cumulative_requests": [0]}), sub],
            ignore_index=True,
        )

    # Extend horizontally to 20 minutes
    last_time = float(sub["time_min"].iloc[-1])
    last_val  = float(sub["y_cumulative_requests"].iloc[-1])
    if last_time < 20.0:
        sub = pd.concat(
            [sub, pd.DataFrame({"time_min": [20.0], "y_cumulative_requests": [last_val]})],
            ignore_index=True,
        )

    ax.plot(
        sub["time_min"],
        sub["y_cumulative_requests"],
        label=legend_map.get(canon_key, canon_key),
        color=color,
        linewidth=LINEWIDTH,
    )

# ================== Axes (SAME FONT SIZE) ==================
ax.set_xlabel("Exploration Time (minutes)", fontsize=FONT_FS, labelpad=10)
ax.set_ylabel("Cumulative Network Requests", fontsize=FONT_FS, labelpad=10)

ax.tick_params(axis="both", labelsize=FONT_FS, width=1.5)
ax.set_xlim(0, 20)
ax.set_ylim(bottom=0)

# ================== Legend (SAME FONT SIZE) ==================
ax.legend(
    fontsize=FONT_FS,
    loc=LEGEND_LOC,
    frameon=True,
    handlelength=3,
)

# ================== Layout (leave space for caption) ==================
fig.tight_layout(rect=[0.03, 0.15, 0.98, 0.98])

# ================== Panel caption (SAME FONT SIZE) ==================
fig.text(
    0.5, 0.06,
    CAPTION,
    ha="center",
    va="center",
    fontsize=FONT_FS,
)

# ================== Export ==================
fig.savefig(OUT_PDF, format="pdf")
plt.show()

print(f"Saved plot to {OUT_PDF}")

