


import csv
import json
import os
from collections import defaultdict
from typing import Dict, List, Set
try:
    from tqdm import tqdm
except ImportError:
    
    def tqdm(iterable, desc=None, total=None):
        if desc:
            print(desc)
        return iterable
from violation_detection import compare_network_with_sources


current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FLOWS_CSV = os.path.join(current_dir, "data_flows_with_appid.csv")
LABEL_CSV = os.path.join(current_dir, "label.csv")
MANIFEST_CSV = os.path.join(current_dir, "manifest.csv")
OUTPUT_JSON = os.path.join(current_dir, "violations_all_apps.json")
OUTPUT_CSV = os.path.join(current_dir, "violations_all_apps.csv")


def load_network_data() -> Dict[str, List[str]]:
    
    network_data = defaultdict(set)
    
    
    with open(DATA_FLOWS_CSV, 'r') as f:
        total_lines = sum(1 for _ in f) - 1  
    
    with open(DATA_FLOWS_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in tqdm(reader, desc="Loading network data", total=total_lines):
            app_id = row.get('app_id', '')
            data_type = row.get('data_type', '').strip()
            if app_id and data_type:
                network_data[app_id].add(data_type)
    
    
    return {app_id: list(types) for app_id, types in network_data.items()}


def load_label_data() -> Dict[str, Dict]:
    
    label_data = defaultdict(lambda: {
        'declared_types': set(),
        'data_not_collected': False
    })
    
    
    with open(LABEL_CSV, 'r') as f:
        total_lines = sum(1 for _ in f) - 1  
    
    with open(LABEL_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in tqdm(reader, desc="Loading label data", total=total_lines):
            app_id = row.get('app_id', '')
            data_type = row.get('data_type', '').strip()
            privacy_type = row.get('privacy_type', '').strip()
            
            if app_id:
                
                if privacy_type and 'not collected' in privacy_type.lower():
                    label_data[app_id]['data_not_collected'] = True
                elif data_type:  
                    label_data[app_id]['declared_types'].add(data_type)
    
    
    return {
        app_id: {
            'declared_types': list(data['declared_types']),
            'data_not_collected': data['data_not_collected']
        }
        for app_id, data in label_data.items()
    }


def load_manifest_data() -> Dict[str, Dict]:
    
    manifest_data = defaultdict(lambda: {
        'declared_types': set(),
        'data_not_collected': False
    })
    
    if not os.path.exists(MANIFEST_CSV):
        return {}
    
    
    with open(MANIFEST_CSV, 'r') as f:
        total_lines = sum(1 for _ in f) - 1  
    
    with open(MANIFEST_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in tqdm(reader, desc="Loading manifest data", total=total_lines):
            app_id = row.get('app_id', '')
            data_type = row.get('data_type', '').strip()
            
            if app_id and data_type:
                manifest_data[app_id]['declared_types'].add(data_type)
    
    
    return {
        app_id: {
            'declared_types': list(data['declared_types']),
            'data_not_collected': data['data_not_collected']
        }
        for app_id, data in manifest_data.items()
    }


def process_all_apps():
    
    print("Loading data...")
    network_data = load_network_data()
    label_data = load_label_data()
    manifest_data = load_manifest_data()
    
    print(f"Loaded {len(network_data)} apps with network data")
    print(f"Loaded {len(label_data)} apps with label data")
    print(f"Loaded {len(manifest_data)} apps with manifest data")
    
    
    all_app_ids = set(label_data.keys())
    print(f"\nTotal apps to process: {len(all_app_ids)} (should be 306)")
    
    all_results = []
    all_violations = []
    
    print("\nProcessing apps...")
    
    for app_id in tqdm(sorted(all_app_ids), desc="Processing apps", total=len(all_app_ids)):
        
        network_types = network_data.get(app_id, [])
        
        label_info = label_data.get(app_id, {
            'declared_types': [],
            'data_not_collected': False
        })
        label_declared = set(label_info['declared_types'])
        label_data_not_collected = label_info['data_not_collected']
        
        
        manifest_info = manifest_data.get(app_id, {
            'declared_types': [],
            'data_not_collected': False
        })
        manifest_declared = set(manifest_info['declared_types'])
        manifest_data_not_collected = manifest_info['data_not_collected']
        
        
        try:
            results = compare_network_with_sources(
                network_types,
                label_declared,
                manifest_declared,
                app_id,
                label_data_not_collected,
                manifest_data_not_collected
            )
            
            
            app_result = {
                'app_id': app_id,
                'network_types_count': len(network_types),
                'label_declared_count': len(label_declared),
                'manifest_declared_count': len(manifest_declared),
                'violations': results,
                'total_violations': results['summary']['total_violations']
            }
            all_results.append(app_result)
            
            
            
            for violation in results['network_vs_label']:
                all_violations.append({
                    'app_id': app_id,
                    'source': 'label',
                    'violation_type': violation['violation_type'],
                    'collected_type': violation['collected_type'],
                    'expected_apple_types': ', '.join(violation.get('expected_apple_types', [])),
                    'declared_types': ', '.join(violation.get('declared_types', [])),
                    'data_not_collected': violation.get('data_not_collected', False)
                })
            
            
            if 'cannot_compare' not in results['network_vs_manifest']:
                for violation in results['network_vs_manifest']:
                    all_violations.append({
                        'app_id': app_id,
                        'source': 'manifest',
                        'violation_type': violation['violation_type'],
                        'collected_type': violation['collected_type'],
                        'expected_apple_types': ', '.join(violation.get('expected_apple_types', [])),
                        'declared_types': ', '.join(violation.get('declared_types', [])),
                        'data_not_collected': violation.get('data_not_collected', False)
                    })
            
            
            if 'cannot_compare' not in results['network_vs_policy']:
                for violation in results['network_vs_policy']:
                    all_violations.append({
                        'app_id': app_id,
                        'source': 'policy',
                        'violation_type': violation['violation_type'],
                        'collected_type': violation['collected_type'],
                        'expected_apple_types': ', '.join(violation.get('expected_apple_types', [])),
                        'declared_types': '',
                        'policy_action': violation.get('policy_action', '')
                    })
        
        except Exception as e:
            print(f"  Error processing app {app_id}: {e}")
            continue
    
    
    print(f"\nSaving results to {OUTPUT_JSON}...")
    with open(OUTPUT_JSON, 'w') as f:
        json.dump({
            'total_apps': len(all_results),
            'total_violations': len(all_violations),
            'apps': all_results
        }, f, indent=2)
    
    
    print(f"Saving violations to {OUTPUT_CSV}...")
    if all_violations:
        fieldnames = ['app_id', 'source', 'violation_type', 'collected_type', 
                     'expected_apple_types', 'declared_types', 'data_not_collected', 'policy_action']
        with open(OUTPUT_CSV, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_violations)
    
    
    print("\n" + "=" * 70)
    print("Summary Statistics:")
    print("=" * 70)
    print(f"Total apps processed: {len(all_results)}")
    print(f"Total violations: {len(all_violations)}")
    
    
    by_source = defaultdict(int)
    by_type = defaultdict(int)
    for v in all_violations:
        by_source[v['source']] += 1
        by_type[v['violation_type']] += 1
    
    print(f"\nTotal violations by source:")
    for source, count in sorted(by_source.items()):
        print(f"  {source}: {count} violations")
    
    print(f"\nViolations by type:")
    for vtype, count in sorted(by_type.items()):
        print(f"  {vtype}: {count}")
    
    
    apps_with_label_violations = 0
    apps_with_manifest_violations = 0
    apps_with_policy_violations = 0
    
    apps_cannot_compare_manifest = 0
    apps_cannot_compare_policy = 0
    
    for r in all_results:
        summary = r['violations']['summary']
        
        
        if summary.get('label_violations', 0) > 0:
            apps_with_label_violations += 1
        
        
        manifest_violations = summary.get('manifest_violations')
        if manifest_violations == 'cannot_compare':
            apps_cannot_compare_manifest += 1
        elif manifest_violations and manifest_violations > 0:
            apps_with_manifest_violations += 1
        
        
        policy_violations = summary.get('policy_violations')
        if policy_violations == 'cannot_compare':
            apps_cannot_compare_policy += 1
        elif policy_violations and policy_violations > 0:
            apps_with_policy_violations += 1
    
    print(f"\n" + "=" * 70)
    print("Apps with violations (separated by source):")
    print("=" * 70)
    print(f"Label violations: {apps_with_label_violations}/{len(all_results)} apps have violations")
    print(f"Manifest violations: {apps_with_manifest_violations}/{len(all_results)} apps have violations")
    print(f"Policy violations: {apps_with_policy_violations}/{len(all_results)} apps have violations")
    
    print(f"\nCannot compare:")
    print(f"  Manifest: {apps_cannot_compare_manifest}/{len(all_results)} apps")
    print(f"  Policy: {apps_cannot_compare_policy}/{len(all_results)} apps")
    
    print("=" * 70)


if __name__ == "__main__":
    process_all_apps()
