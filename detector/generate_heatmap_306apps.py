


import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
import os


plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans']
plt.rcParams['axes.unicode_minus'] = False


current_dir = os.path.dirname(os.path.abspath(__file__))
VIOLATIONS_JSON = os.path.join(current_dir, "violations_all_apps.json")
OUTPUT_PREFIX = "heatmap_306apps"

def load_violations():
    
    print(f"Loading violations from {VIOLATIONS_JSON}...")
    with open(VIOLATIONS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Total apps: {data['total_apps']}")
    print(f"Total violations: {data['total_violations']}")
    
    
    all_violations = []
    
    for app in data['apps']:
        app_id = app['app_id']
        violations = app.get('violations', {})
        
        
        if 'network_vs_label' in violations:
            for v in violations['network_vs_label']:
                if v.get('is_violation', False):
                    all_violations.append({
                        'app_id': app_id,
                        'source': 'label',
                        'violation_type': v['violation_type'],
                        'collected_type': v['collected_type']
                    })
        
        
        if 'network_vs_manifest' in violations and 'cannot_compare' not in violations['network_vs_manifest']:
            for v in violations['network_vs_manifest']:
                if v.get('is_violation', False):
                    all_violations.append({
                        'app_id': app_id,
                        'source': 'manifest',
                        'violation_type': v['violation_type'],
                        'collected_type': v['collected_type']
                    })
        
        
        if 'network_vs_policy' in violations and 'cannot_compare' not in violations['network_vs_policy']:
            for v in violations['network_vs_policy']:
                if v.get('is_violation', False):
                    all_violations.append({
                        'app_id': app_id,
                        'source': 'policy',
                        'violation_type': v['violation_type'],
                        'collected_type': v['collected_type']
                    })
    
    print(f"Extracted {len(all_violations)} violation records")
    return all_violations

def generate_heatmap_by_source_and_type(violations):
    
    print("\n" + "="*70)
    print("Generating Heatmap: Data Type vs Violation Type by Source")
    print("="*70)
    
    
    df = pd.DataFrame(violations)
    
    
    
    deduped = df.drop_duplicates(subset=['app_id', 'collected_type', 'source', 'violation_type'])
    
    
    heatmap_data = defaultdict(lambda: defaultdict(int))
    
    for _, row in deduped.iterrows():
        data_type = row['collected_type']
        source = row['source']
        vtype = row['violation_type']
        
        key = f"{source}_{vtype}"
        heatmap_data[data_type][key] += 1
    
    
    heatmap_df = pd.DataFrame(heatmap_data).T.fillna(0)
    
    
    desired_columns = [
        'label_incorrect_disclosure', 'label_neglect_disclosure',
        'manifest_incorrect_disclosure', 'manifest_neglect_disclosure',
        'policy_incorrect_disclosure', 'policy_neglect_disclosure'
    ]
    
    for col in desired_columns:
        if col not in heatmap_df.columns:
            heatmap_df[col] = 0
    
    
    existing_cols = [col for col in desired_columns if col in heatmap_df.columns]
    heatmap_df = heatmap_df[existing_cols]
    
    
    heatmap_df = heatmap_df[(heatmap_df.T != 0).any()]
    
    
    heatmap_df['Total'] = heatmap_df.sum(axis=1)
    heatmap_df = heatmap_df.sort_values('Total', ascending=False)
    heatmap_df = heatmap_df.drop('Total', axis=1)
    
    
    csv_file = f'{OUTPUT_PREFIX}_by_source_type.csv'
    heatmap_df.to_csv(csv_file)
    print(f"✓ Saved: {csv_file}")
    
    
    fig, ax = plt.subplots(figsize=(16, max(10, len(heatmap_df) * 0.3)))
    
    
    annot_array = heatmap_df.values.astype(int).astype(str)
    annot_array[heatmap_df.values == 0] = ''
    
    sns.heatmap(heatmap_df, annot=annot_array, fmt='', cmap='YlOrRd',
                linewidths=0.5, cbar_kws={'label': 'Number of Apps'},
                ax=ax, annot_kws={'fontsize': 9})
    
    ax.set_title('Privacy Violations by Data Type, Source, and Violation Type\n(Each App Counted Once Per Data Type)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Source + Violation Type', fontsize=12)
    ax.set_ylabel('Data Type (Collected Type)', fontsize=12)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.yticks(fontsize=9)
    
    plt.tight_layout()
    img_file = f'{OUTPUT_PREFIX}_by_source_type.png'
    plt.savefig(img_file, dpi=300, bbox_inches='tight')
    print(f"✓ Generated: {img_file}")
    plt.close()
    
    return heatmap_df

def generate_heatmap_for_source(violations, source_name):
    
    print(f"\n{'='*70}")
    print(f"Generating Heatmap for {source_name.upper()}: Data Type vs Violation Type")
    print(f"{'='*70}")
    
    df = pd.DataFrame(violations)
    
    
    source_df = df[df['source'] == source_name].copy()
    
    if len(source_df) == 0:
        print(f"⚠️  No violations found for {source_name}")
        return None
    
    
    deduped = source_df.drop_duplicates(subset=['app_id', 'collected_type', 'violation_type'])
    
    
    stats = deduped.groupby(['collected_type', 'violation_type']).size().reset_index(name='app_count')
    
    
    pivot = stats.pivot_table(
        index='collected_type',
        columns='violation_type',
        values='app_count',
        fill_value=0
    )
    
    
    if 'incorrect_disclosure' not in pivot.columns:
        pivot['incorrect_disclosure'] = 0
    if 'neglect_disclosure' not in pivot.columns:
        pivot['neglect_disclosure'] = 0
    
    pivot = pivot[['incorrect_disclosure', 'neglect_disclosure']]
    
    
    pivot['Total'] = pivot['incorrect_disclosure'] + pivot['neglect_disclosure']
    
    
    pivot = pivot.sort_values('Total', ascending=False)
    
    
    csv_file = f'{OUTPUT_PREFIX}_{source_name}.csv'
    pivot.to_csv(csv_file)
    print(f"✓ Saved: {csv_file}")
    
    
    fig, ax = plt.subplots(figsize=(10, max(8, len(pivot) * 0.3)))
    
    plot_data = pivot[['incorrect_disclosure', 'neglect_disclosure']]
    
    
    annot_array = plot_data.values.astype(int).astype(str)
    annot_array[plot_data.values == 0] = ''
    
    sns.heatmap(plot_data, annot=annot_array, fmt='', cmap='YlOrRd',
                linewidths=0.5, cbar_kws={'label': 'Number of Apps'},
                ax=ax, annot_kws={'fontsize': 11, 'fontweight': 'bold'})
    
    source_title = source_name.capitalize()
    if source_name == 'label':
        source_title = 'Privacy Label'
    elif source_name == 'manifest':
        source_title = 'Privacy Manifest'
    elif source_name == 'policy':
        source_title = 'Privacy Policy'
    
    ax.set_title(f'Privacy Violations by Data Type and Violation Type\n({source_title} - Each App Counted Once Per Data Type)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Violation Type', fontsize=12)
    ax.set_ylabel('Data Type (Collected Type)', fontsize=12)
    plt.xticks(fontsize=11)
    plt.yticks(fontsize=9)
    
    
    ax.text(0.5, -0.12, 'incorrect_disclosure: Claims "No Collection" but actually collects',
            transform=ax.transAxes, ha='center', fontsize=9, color='darkred')
    ax.text(0.5, -0.16, 'neglect_disclosure: Collects but doesn\'t declare',
            transform=ax.transAxes, ha='center', fontsize=9, color='darkblue')
    
    plt.tight_layout()
    img_file = f'{OUTPUT_PREFIX}_{source_name}.png'
    plt.savefig(img_file, dpi=300, bbox_inches='tight')
    print(f"✓ Generated: {img_file}")
    plt.close()
    
    
    fig, ax = plt.subplots(figsize=(12, max(8, len(pivot) * 0.3)))
    
    annot_full = pivot.values.astype(int).astype(str)
    annot_full[pivot.values == 0] = ''
    
    sns.heatmap(pivot, annot=annot_full, fmt='', cmap='Blues',
                linewidths=0.5, cbar_kws={'label': 'Number of Apps'},
                ax=ax, annot_kws={'fontsize': 10, 'fontweight': 'bold'})
    
    ax.set_title(f'Privacy Violations by Data Type (with Total)\n({source_title} - Each App Counted Once Per Data Type)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Violation Type', fontsize=12)
    ax.set_ylabel('Data Type (Collected Type)', fontsize=12)
    plt.xticks(fontsize=11)
    plt.yticks(fontsize=9)
    
    plt.tight_layout()
    img_file2 = f'{OUTPUT_PREFIX}_{source_name}_with_total.png'
    plt.savefig(img_file2, dpi=300, bbox_inches='tight')
    print(f"✓ Generated: {img_file2}")
    plt.close()
    
    return pivot


def print_summary_statistics(violations):
    
    print("\n" + "="*70)
    print("Summary Statistics")
    print("="*70)
    
    df = pd.DataFrame(violations)
    
    print(f"\nTotal violation records: {len(df)}")
    print(f"Unique apps with violations: {df['app_id'].nunique()}")
    print(f"Unique data types: {df['collected_type'].nunique()}")
    
    print(f"\nViolations by source:")
    source_counts = df['source'].value_counts()
    for source, count in source_counts.items():
        print(f"  {source}: {count}")
    
    print(f"\nViolations by type:")
    type_counts = df['violation_type'].value_counts()
    for vtype, count in type_counts.items():
        print(f"  {vtype}: {count}")
    
    print(f"\nApps with violations by source:")
    for source in ['label', 'manifest', 'policy']:
        apps_with_violations = df[df['source'] == source]['app_id'].nunique()
        print(f"  {source}: {apps_with_violations} apps")
    
    print(f"\nTop 10 data types by violation count:")
    top_types = df['collected_type'].value_counts().head(10)
    for dtype, count in top_types.items():
        print(f"  {dtype}: {count}")

def main():
    
    print("="*70)
    print("Heatmap Generation for 306 Apps Violation Results")
    print("="*70)
    
    
    violations = load_violations()
    
    if not violations:
        print("⚠️  No violations found!")
        return
    
    
    print_summary_statistics(violations)
    
    
    generate_heatmap_for_source(violations, 'label')
    generate_heatmap_for_source(violations, 'manifest')
    generate_heatmap_for_source(violations, 'policy')
    
    print("\n" + "="*70)
    print("✨ Heatmap Generation Complete!")
    print("="*70)
    print(f"\nGenerated files for each source:")
    for source in ['label', 'manifest', 'policy']:
        print(f"  - {OUTPUT_PREFIX}_{source}.csv")
        print(f"  - {OUTPUT_PREFIX}_{source}.png")
        print(f"  - {OUTPUT_PREFIX}_{source}_with_total.png")

if __name__ == '__main__':
    main()
