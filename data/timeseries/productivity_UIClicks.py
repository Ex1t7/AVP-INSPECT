import pandas as pd
import matplotlib.pyplot as plt

# ================== ONE GLOBAL FONT SIZE ==================
FONT_FS   = 24  # <- change once, everything follows
LINEWIDTH = 3.5

# Crisp/selectable PDF text
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"]  = 42

# ================== Load data ==================
path = "timeseries_click_xy_data.csv"
df = pd.read_csv(path)

# Apps to include
targets = ["1Blocker", "Airmail", "OmniFocus", "Quick Notes", "Numerics"]

# Fixed color set (keep consistent across panels)
colors = ["red", "blue", "green", "orange", "purple"]

# Canonical key → legend name
legend_map = {
    "1blocker": "1Blocker",
    "airmail": "Airmail",
    "omnifocus": "OmniFocus 4",
    "quick notes": "Quick Notes",
    "numerics": "Numerics",
}

def canonical_key(app_name: str):
    n = str(app_name).lower()
    for key in legend_map:
        if key in n:
            return key
    return None

# ================== Filter rows ==================
mask = False
for t in targets:
    mask = mask | df["app_name"].str.contains(t, case=False, na=False)

df_sel = df[mask].copy()
df_sel["canon"] = df_sel["app_name"].apply(canonical_key)
df_sel = df_sel[df_sel["canon"].notna()]

# ================== Convert seconds → minutes ==================
df_sel["time_min"] = df_sel["x_time_seconds"] / 60.0
df_sel = df_sel[df_sel["time_min"] <= 20]

# ================== Plot ==================
fig, ax = plt.subplots(figsize=(12.0, 9.0))  # exact 4:3

plot_order = ["1blocker", "airmail", "omnifocus", "quick notes", "numerics"]

for canon_key, color in zip(plot_order, colors):
    sub = df_sel[df_sel["canon"] == canon_key].copy()
    if sub.empty:
        continue

    sub = sub.sort_values("time_min")[["time_min", "y_cumulative_clicks"]].copy()

    # Force origin (0,0)
    first_t = float(sub["time_min"].iloc[0])
    first_y = float(sub["y_cumulative_clicks"].iloc[0])
    if first_t != 0.0 or first_y != 0.0:
        sub = pd.concat(
            [pd.DataFrame({"time_min": [0.0], "y_cumulative_clicks": [0]}), sub],
            ignore_index=True,
        )

    # Extend line horizontally to 20 minutes
    last_time = float(sub["time_min"].iloc[-1])
    last_val  = float(sub["y_cumulative_clicks"].iloc[-1])
    if last_time < 20.0:
        sub = pd.concat(
            [sub, pd.DataFrame({"time_min": [20.0], "y_cumulative_clicks": [last_val]})],
            ignore_index=True,
        )

    ax.plot(
        sub["time_min"],
        sub["y_cumulative_clicks"],
        label=legend_map[canon_key],
        color=color,
        linewidth=LINEWIDTH,
    )

# ================== Axes (SAME FONT SIZE) ==================
ax.set_xlabel("Exploration Time (minutes)", fontsize=FONT_FS, labelpad=10)
ax.set_ylabel("Cumulative UI Clicks", fontsize=FONT_FS, labelpad=10)

ax.tick_params(axis="both", labelsize=FONT_FS, width=1.5)
ax.set_xlim(0, 20)
ax.set_ylim(0, 60)

# ================== Legend (SAME FONT SIZE) ==================
ax.legend(
    fontsize=FONT_FS,
    loc="upper left",
    frameon=True,
    handlelength=3,
)

# ================== Tight layout (leave space for caption) ==================
fig.tight_layout(rect=[0.03, 0.15, 0.98, 0.98])

# ================== Panel caption (SAME FONT SIZE) ==================
fig.text(
    0.5, 0.06,
    "(a) Productivity",
    ha="center",
    va="center",
    fontsize=FONT_FS,
)

# ================== Export ==================
output_pdf = "productivity_ui_clicks.pdf"
fig.savefig(output_pdf, format="pdf")
plt.show()

print(f"Saved plot to {output_pdf}")

