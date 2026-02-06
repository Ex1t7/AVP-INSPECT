#!/usr/bin/env python3
# barchart.py
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # headless-safe PDF export
import matplotlib.pyplot as plt

# ---------- VERY LARGE fonts for single-column paper ----------
plt.rcParams.update({
    "font.size": 26,
    "axes.labelsize": 28,
    "axes.titlesize": 30,
    "xtick.labelsize": 26,
    "ytick.labelsize": 26,
    "legend.fontsize": 26,
    "legend.title_fontsize": 27,
    # Crisp/selectable PDF text
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

# ---------- Load data (FIX: time_breakdown.csv is gzip-compressed) ----------
# If your file is plain CSV, you can remove compression="gzip".
df = pd.read_csv("time_breakdown.csv")  # :contentReference[oaicite:0]{index=0}

# ---------- Columns used in plot ----------
components = ["UI State Recognition", "Virtual Cursor Movement", "State Comparison"]

colors = {
    "UI State Recognition": "red",
    "Virtual Cursor Movement": "blue",
    "State Comparison": "green",
}

# ---------- Canonical name mapping ----------
CANONICAL_MAP = {
    "bento": "Bento",
    "shotbot": "Shotbot",
    "magnet crop": "Magnet Crop",
    "spatial video": "Spatial Video Studio",
    "heypster": "Heypster-gif",

    "cronica": "Cronica",
    "gametrack": "GameTrack",
    "kitsune": "Kitsune",
    "pga": "PGA TOUR",
    "study snacks": "Study Snacks",

    "floor plan": "Floor Plan",
    "box": "Box",
    "alo": "Alo",
    "turn off the lights": "Turn Off the Lights",

    "1blocker": "1Blocker",
    "airmail": "Airmail",
    "omnifocus": "OmniFocus",
    "quick notes": "Quick Notes",
    "numerics": "Numerics",

    "ai girlfriend": "AI Girlfriend",
    "persona": "Persona Chat",
    "emdr": "EMDR",
    "hi sticky": "Hi Sticky",
    "cardpointers": "Card Pointers",
}

def canonical_name(raw):
    s = str(raw).lower()
    for k, v in CANONICAL_MAP.items():
        if k in s:
            return v
    return None

# ---------- Basic validation ----------
required_cols = {"app_name", *components}
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise ValueError(
        "Missing required columns in time_breakdown.csv: "
        f"{missing}\nFound columns: {list(df.columns)}"
    )

# ---------- Canonicalize + filter to the apps we care about ----------
df["canon"] = df["app_name"].apply(canonical_name)
df = df[df["canon"].notna()].copy()

order = [
    "Bento", "Shotbot", "Magnet Crop", "Spatial Video Studio", "Heypster-gif",
    "Cronica", "GameTrack", "Kitsune", "PGA TOUR", "Study Snacks",
    "Floor Plan", "Box", "Alo", "Turn Off the Lights",
    "1Blocker", "Airmail", "OmniFocus", "Quick Notes", "Numerics",
    "AI Girlfriend", "Persona Chat", "EMDR", "Hi Sticky", "Card Pointers",
]

# Keep only those in order (and in that order)
df = df.set_index("canon").reindex(order).dropna(subset=components, how="all").reset_index()

# ---------- Plot (stacked horizontal bars) ----------
fig, ax = plt.subplots(figsize=(18, 18))  # tall for single column

left = [0.0] * len(df)
legend_used = set()

for i, row in df.iterrows():
    for c in components:
        label = c if c not in legend_used else None
        ax.barh(
            i,
            float(row[c]),
            left=left[i],
            color=colors[c],
            label=label,
            alpha=0.5,
        )
        if label:
            legend_used.add(c)
        left[i] += float(row[c])

# ---------- Axes ----------
ax.set_yticks(range(len(df)))
ax.set_yticklabels(df["canon"])
ax.set_xlabel("Time")
ax.set_ylabel("Apps")

# If you want a fixed x-limit, keepzip this. Otherwise comment it out.
ax.set_xlim(0, 20)

# ---------- Legend (push right, avoid overlapping) ----------
box = ax.get_position()
ax.set_position([box.x0, box.y0, box.width * 0.78, box.height])

# ---------- Legend (bottom-right, inside figure) ----------
ax.legend(
    loc="lower right",
    frameon=True,
)

# ---------- Layout + Export ----------
fig.tight_layout()
fig.savefig(
    "time_breakdown_per_iteration_singlecol.pdf",
    format="pdf",
    bbox_inches="tight",
)
print("[OK] Wrote: time_breakdown_per_iteration_singlecol.pdf")

