


import json
import os
import csv
import re
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any, Optional
import sys

sys.path.insert(0, '/mnt/ssd2/VR_monkey/ppaudit_analysis')
from ontology_mapping import (
    get_apple_types_for_traffic,
    is_covered_by_apple_types,
    get_violation_details,
    get_mapped_traffic_types,
)



DATA_FLOWS_PATH = "/mnt/ssd2/VR_monkey/ppaudit_analysis/data_flows_output_v2/data_flows.csv"
PRIVACY_LABELS_DIR = "/mnt/ssd2/VR_monkey/privacy_details"
APP_STORE_DATA_DIR = "/mnt/ssd2/VR_monkey/app_store_data"
OUTPUT_DIR = "/mnt/ssd2/VR_monkey/ppaudit_analysis/violations_output"


def load_app_id_mapping() -> Dict[str, str]:
    
    mapping = {}
    
    for fname in os.listdir(APP_STORE_DATA_DIR):
        if not fname.startswith("app_") or not fname.endswith(".json"):
            continue
        
        
        
        parts = fname[4:-5].split("_", 1)  
        if len(parts) >= 2:
            app_id = parts[0]
            app_name_from_file = parts[1].replace("_", " ")
            
            
            try:
                with open(os.path.join(APP_STORE_DATA_DIR, fname), 'r') as f:
                    data = json.load(f)
                    app_name = data.get('trackName', app_name_from_file)
                    mapping[app_name] = app_id
                    
                    mapping[app_name_from_file] = app_id
            except:
                mapping[app_name_from_file] = app_id
    
    return mapping


def load_privacy_label(app_id: str) -> Optional[dict]:
    
    label_path = os.path.join(PRIVACY_LABELS_DIR, f"privacy_label_id{app_id}.json")
    
    if not os.path.exists(label_path):
        return None
    
    try:
        with open(label_path, 'r') as f:
            data = json.load(f)
            return data
    except:
        return None


def extract_declared_types(privacy_label: dict) -> Tuple[Set[str], bool]:
    
    declared_types = set()
    data_not_collected = False
    
    try:
        privacy_details = privacy_label['data'][0]['attributes']['privacyDetails']
        privacy_types = privacy_details.get('privacyTypes', [])
        
        for pt in privacy_types:
            identifier = pt.get('identifier', '')
            
            
            if identifier == 'DATA_NOT_COLLECTED':
                data_not_collected = True
                continue
            
            
            for dc in pt.get('dataCategories', []):
                for dt in dc.get('dataTypes', []):
                    if isinstance(dt, str):
                        declared_types.add(dt)
                    elif isinstance(dt, dict):
                        declared_types.add(dt.get('dataType', ''))
            
            
            for purpose in pt.get('purposes', []):
                for dc in purpose.get('dataCategories', []):
                    for dt in dc.get('dataTypes', []):
                        if isinstance(dt, str):
                            declared_types.add(dt)
                        elif isinstance(dt, dict):
                            declared_types.add(dt.get('dataType', ''))
    except Exception as e:
        pass
    
    return declared_types, data_not_collected


def load_data_flows() -> Dict[str, Set[Tuple[str, str]]]:
    
    app_flows = defaultdict(set)
    
    with open(DATA_FLOWS_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            app = row['app']
            data_type = row['data_type']
            destination = row['destination']
            app_flows[app].add((data_type, destination))
    
    return app_flows


def detect_violations():
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    
    print("Loading app ID mapping...")
    app_id_mapping = load_app_id_mapping()
    print(f"Loaded {len(app_id_mapping)} app mappings")
    
    print("Loading data flows...")
    app_flows = load_data_flows()
    print(f"Loaded flows for {len(app_flows)} apps")
    
    
    print("\nDetecting violations...")
    
    all_violations = []  
    app_summaries = {}
    
    apps_with_label = 0
    apps_without_label = 0
    apps_data_not_collected = 0
    
    for app_name, flows in app_flows.items():
        
        app_id = app_id_mapping.get(app_name)
        
        if not app_id:
            
            for stored_name, stored_id in app_id_mapping.items():
                if app_name.lower() in stored_name.lower() or stored_name.lower() in app_name.lower():
                    app_id = stored_id
                    break
        
        if not app_id:
            apps_without_label += 1
            app_summaries[app_name] = {
                'app_id': None,
                'has_label': False,
                'data_not_collected': False,
                'declared_types': [],
                'collected_types': list(set(f[0] for f in flows)),
                'violations': [],
                'neglect_count': 0,
                'contrary_count': 0,
            }
            continue
        
        
        privacy_label = load_privacy_label(app_id)
        
        if not privacy_label:
            apps_without_label += 1
            app_summaries[app_name] = {
                'app_id': app_id,
                'has_label': False,
                'data_not_collected': False,
                'declared_types': [],
                'collected_types': list(set(f[0] for f in flows)),
                'violations': [],
                'neglect_count': 0,
                'contrary_count': 0,
            }
            continue
        
        apps_with_label += 1
        
        
        declared_types, data_not_collected = extract_declared_types(privacy_label)
        
        if data_not_collected:
            apps_data_not_collected += 1
        
        
        collected_types = set(f[0] for f in flows)
        
        
        app_violations = []
        neglect_count = 0
        contrary_count = 0
        
        for data_type, destination in flows:
            
            details = get_violation_details(data_type, declared_types)
            
            
            if not details['has_ontology_mapping']:
                continue
            
            
            if details['is_violation']:
                apple_types = details['expected_apple_types']
                if data_not_collected:
                    
                    violation_type = "Contrary Disclosure"
                    contrary_count += 1
                else:
                    
                    violation_type = "Neglect Disclosure"
                    neglect_count += 1
                
                violation = {
                    'app': app_name,
                    'app_id': app_id,
                    'data_type': data_type,
                    'destination': destination,
                    'violation_type': violation_type,
                    'expected_apple_types': apple_types,
                    'declared_types': list(declared_types),
                }
                app_violations.append(violation)
                all_violations.append(violation)
        
        app_summaries[app_name] = {
            'app_id': app_id,
            'has_label': True,
            'data_not_collected': data_not_collected,
            'declared_types': list(declared_types),
            'collected_types': list(collected_types),
            'violations': app_violations,
            'neglect_count': neglect_count,
            'contrary_count': contrary_count,
        }
    
    
    print("\n" + "=" * 70)
    print("Violation Detection Results")
    print("=" * 70)
    
    total_neglect = sum(s['neglect_count'] for s in app_summaries.values())
    total_contrary = sum(s['contrary_count'] for s in app_summaries.values())
    apps_with_violations = sum(1 for s in app_summaries.values() if s['neglect_count'] + s['contrary_count'] > 0)
    
    
    unique_violations = set()
    for v in all_violations:
        unique_violations.add((v['app'], v['data_type']))
    
    print(f"Apps with privacy labels: {apps_with_label}")
    print(f"Apps without privacy labels: {apps_without_label}")
    print(f"Apps declared 'Data Not Collected': {apps_data_not_collected}")
    print(f"\nApps with violations: {apps_with_violations}")
    print(f"Total violation flows: {len(all_violations)}")
    print(f"Unique violations (app + data_type): {len(unique_violations)}")
    print(f"  - Neglect Disclosure: {total_neglect}")
    print(f"  - Contrary Disclosure: {total_contrary}")
    
    
    violations_csv = os.path.join(OUTPUT_DIR, 'violations.csv')
    with open(violations_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['app', 'app_id', 'data_type', 'destination', 
                                                'violation_type', 'expected_apple_types', 'declared_types'])
        writer.writeheader()
        for v in all_violations:
            row = v.copy()
            row['expected_apple_types'] = '|'.join(row['expected_apple_types'])
            row['declared_types'] = '|'.join(row['declared_types'])
            writer.writerow(row)
    print(f"\nSaved violations to: {violations_csv}")
    
    
    unique_violations_csv = os.path.join(OUTPUT_DIR, 'violations_unique.csv')
    unique_violation_list = []
    for app, data_type in unique_violations:
        
        for v in all_violations:
            if v['app'] == app and v['data_type'] == data_type:
                unique_violation_list.append({
                    'app': app,
                    'data_type': data_type,
                    'violation_type': v['violation_type'],
                    'expected_apple_types': v['expected_apple_types'],
                })
                break
    
    with open(unique_violations_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['app', 'data_type', 'violation_type', 'expected_apple_types'])
        writer.writeheader()
        for v in unique_violation_list:
            row = v.copy()
            row['expected_apple_types'] = '|'.join(row['expected_apple_types'])
            writer.writerow(row)
    print(f"Saved unique violations to: {unique_violations_csv}")
    
    
    summary = {
        'total_apps': len(app_flows),
        'apps_with_labels': apps_with_label,
        'apps_without_labels': apps_without_label,
        'apps_data_not_collected': apps_data_not_collected,
        'apps_with_violations': apps_with_violations,
        'total_violation_flows': len(all_violations),
        'unique_violations': len(unique_violations),
        'neglect_disclosure_count': total_neglect,
        'contrary_disclosure_count': total_contrary,
        'app_summaries': app_summaries,
    }
    
    
    apps_by_violations = sorted(
        [(app, s['neglect_count'] + s['contrary_count']) for app, s in app_summaries.items()],
        key=lambda x: -x[1]
    )
    summary['top_violating_apps'] = apps_by_violations[:20]
    
    
    violation_by_type = defaultdict(int)
    for v in all_violations:
        violation_by_type[v['data_type']] += 1
    summary['violations_by_data_type'] = dict(sorted(violation_by_type.items(), key=lambda x: -x[1]))
    
    summary_path = os.path.join(OUTPUT_DIR, 'violations_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"Saved summary to: {summary_path}")
    
    
    print("\nTop 10 Apps by Violations:")
    for app, count in apps_by_violations[:10]:
        s = app_summaries[app]
        print(f"  {app:<40} {count:>4} violations (N:{s['neglect_count']}, C:{s['contrary_count']})")
    
    
    print("\nTop 10 Violated Data Types:")
    for dt, count in list(summary['violations_by_data_type'].items())[:10]:
        print(f"  {dt:<25} {count:>5} violations")


if __name__ == "__main__":
    detect_violations()
