# sync_heatmap_csvs.py
# Makes two CSVs have identical:
#   (1) data_type rows (keeps only intersection)
#   (2) entity-label columns (keeps only intersection)
# Drops everything else, aligns row/col order, and writes outputs.

import pandas as pd
from pathlib import Path

# ================== INPUTS ==================
IN_CONTRARY = Path("heatmap_entity_label_contrary_disclosure_data.csv")
IN_NEGLECT  = Path("heatmap_entity_label_neglect_disclosure_data.csv")

# ================== OUTPUTS ==================
OUT_CONTRARY = Path("heatmap_entity_label_contrary_common.csv")
OUT_NEGLECT  = Path("heatmap_entity_label_neglect_common.csv")

# ================== LOAD ==================
df_c = pd.read_csv(IN_CONTRARY)
df_n = pd.read_csv(IN_NEGLECT)

if "data_type" not in df_c.columns or "data_type" not in df_n.columns:
    raise ValueError("Both CSVs must contain a 'data_type' column as the first column (or at least present).")

# Optional: normalize whitespace/casing if your data_type strings are messy
df_c["data_type"] = df_c["data_type"].astype(str).str.strip()
df_n["data_type"] = df_n["data_type"].astype(str).str.strip()

# ================== KEEP ONLY COMMON data_type ROWS ==================
common_data_types = sorted(set(df_c["data_type"]).intersection(set(df_n["data_type"])))

df_c = df_c[df_c["data_type"].isin(common_data_types)].copy()
df_n = df_n[df_n["data_type"].isin(common_data_types)].copy()

# Force identical row order
df_c = df_c.set_index("data_type").loc[common_data_types].reset_index()
df_n = df_n.set_index("data_type").loc[common_data_types].reset_index()

# ================== KEEP ONLY COMMON ENTITY COLUMNS ==================
common_entities = sorted((set(df_c.columns) & set(df_n.columns)) - {"data_type"})
common_cols = ["data_type"] + common_entities

df_c = df_c[common_cols].copy()
df_n = df_n[common_cols].copy()

# ================== FINAL CONSISTENCY CHECK ==================
if list(df_c.columns) != list(df_n.columns):
    raise RuntimeError("Column mismatch after syncing (this should not happen).")

if list(df_c["data_type"]) != list(df_n["data_type"]):
    raise RuntimeError("Row mismatch after syncing (this should not happen).")

# ================== SAVE ==================
df_c.to_csv(OUT_CONTRARY, index=False)
df_n.to_csv(OUT_NEGLECT, index=False)

print("Synced successfully.")
print(f"Common data_types    : {len(common_data_types)}")
print(f"Common entity columns: {len(common_entities)}")
print("Wrote:")
print(f" - {OUT_CONTRARY}")
print(f" - {OUT_NEGLECT}")

