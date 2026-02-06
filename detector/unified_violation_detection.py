


import sys
from typing import Set, Dict, List, Optional, Tuple
from collections import defaultdict

sys.path.insert(0, '/mnt/ssd2/VR_monkey/ppaudit_analysis')
from ontology_mapping import (
    get_violation_details,
    is_covered_by_apple_types,
    get_apple_types_for_traffic
)


def detect_violation_network_vs_label_manifest(
    network_data_type: str,
    declared_types: Set[str],
    data_not_collected: bool = False
) -> Optional[Dict]:
    
    
    if data_not_collected:
        return {
            'is_violation': True,
            'violation_type': 'incorrect_disclosure',  
            'collected_type': network_data_type,
            'expected_apple_types': get_apple_types_for_traffic(network_data_type),
            'declared_types': [],
            'data_not_collected': True,
            'has_ontology_mapping': True
        }
    
    
    details = get_violation_details(network_data_type, declared_types)
    
    if details['is_violation']:
        return {
            'is_violation': True,
            'violation_type': 'neglect_disclosure',
            'collected_type': network_data_type,
            'expected_apple_types': details['expected_apple_types'],
            'declared_types': list(declared_types),
            'missing_types': details['missing_types'],
            'has_ontology_mapping': details['has_ontology_mapping']
        }
    
    return None


def load_policy_triplets_for_app(app_id: str) -> List[Dict]:
    
    import csv
    import os
    
    csv_path = "/mnt/ssd2/VR_monkey/ppaudit_analysis/ppaudit_cus_triplets_stripped.csv"
    if not os.path.exists(csv_path):
        return []
    
    triplets = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('app_id') == app_id:
                triplets.append({
                    'entity': row.get('entity', ''),
                    'action': row.get('action', ''),  
                    'data_type': row.get('data_type', ''),
                    'sentence_preview': row.get('sentence_preview', '')
                })
    
    return triplets


def detect_violation_network_vs_policy(
    network_data_type: str,  
    policy_triplets: List[Dict]  
) -> Optional[Dict]:
    
    
    
    matching_triplets = []
    
    for triplet in policy_triplets:
        policy_data_type = triplet.get('data_type', '')
        
        
        if policy_data_type.lower() == network_data_type.lower():
            matching_triplets.append(triplet)
    
    
    not_collect_triplets = [
        t for t in matching_triplets 
        if t.get('action', '').lower() == 'not_collect'
    ]
    
    if not_collect_triplets:
        
        return {
            'is_violation': True,
            'violation_type': 'incorrect_disclosure',
            'collected_type': network_data_type,
            'expected_apple_types': get_apple_types_for_traffic(network_data_type),
            'declared_types': [],
            'policy_action': 'not_collect',
            'has_ontology_mapping': True
        }
    
    
    if not matching_triplets:
        
        return {
            'is_violation': True,
            'violation_type': 'neglect_disclosure',
            'collected_type': network_data_type,
            'expected_apple_types': get_apple_types_for_traffic(network_data_type),
            'declared_types': [],
            'policy_action': None,  
            'has_ontology_mapping': True
        }
    
    
    return None


def detect_violation_unified(
    collected_data_type: str,
    declared_types: Set[str],
    data_not_collected: bool = False
) -> Dict:
    
    
    
    details = get_violation_details(collected_data_type, declared_types)
    
    violation_type = None
    if details['is_violation']:
        if data_not_collected:
            violation_type = 'contrary_disclosure'  
        else:
            violation_type = 'neglect_disclosure'   
    
    return {
        'is_violation': details['is_violation'],
        'violation_type': violation_type,
        'collected_type': collected_data_type,
        'expected_apple_types': details['expected_apple_types'],
        'declared_types': list(declared_types),
        'missing_types': details['missing_types'],
        'has_ontology_mapping': details['has_ontology_mapping']
    }


def compare_network_with_sources(
    network_types: List[str],
    label_declared: Set[str],
    manifest_declared: Set[str],
    app_id: str,  
    label_data_not_collected: bool = False,
    manifest_data_not_collected: bool = False
) -> Dict:
    
    
    policy_triplets = load_policy_triplets_for_app(app_id)
    
    network_vs_label = []
    network_vs_manifest = []
    network_vs_policy = []
    
    for network_type in network_types:
        
        result = detect_violation_network_vs_label_manifest(
            network_type,
            label_declared,
            label_data_not_collected
        )
        if result:
            network_vs_label.append(result)
        
        
        result = detect_violation_network_vs_label_manifest(
            network_type,
            manifest_declared,
            manifest_data_not_collected
        )
        if result:
            network_vs_manifest.append(result)
        
        
        result = detect_violation_network_vs_policy(
            network_type,
            policy_triplets
        )
        if result:
            network_vs_policy.append(result)
    
    
    by_type = defaultdict(int)
    for v in network_vs_label + network_vs_manifest + network_vs_policy:
        by_type[v['violation_type']] += 1
    
    return {
        'network_vs_label': network_vs_label,
        'network_vs_manifest': network_vs_manifest,
        'network_vs_policy': network_vs_policy,
        'summary': {
            'total_violations': len(network_vs_label) + len(network_vs_manifest) + len(network_vs_policy),
            'by_source': {
                'network_vs_label': len(network_vs_label),
                'network_vs_manifest': len(network_vs_manifest),
                'network_vs_policy': len(network_vs_policy)
            },
            'by_type': dict(by_type)
        }
    }


if __name__ == "__main__":
    
    print("=" * 70)
    print("Unified Violation Detection - Network vs Other Sources")
    print("=" * 70)
    
    
    app_id = "1365531024"  
    network_types = ['device id', 'geo location', 'browsing']
    label_declared = {'User ID', 'Purchase History'}
    manifest_declared = {'User ID'}
    label_data_not_collected = True  
    manifest_data_not_collected = False
    
    print("\nApp ID:", app_id)
    print("Network types:", network_types)
    print("Label declared:", label_declared)
    print("Label data_not_collected:", label_data_not_collected)
    print("Manifest declared:", manifest_declared)
    
    
    policy_triplets = load_policy_triplets_for_app(app_id)
    print(f"Policy triplets loaded: {len(policy_triplets)}")
    if policy_triplets:
        print("Sample policy triplets:")
        for t in policy_triplets[:3]:
            print(f"  - {t['data_type']:20s} | {t['action']:12s} | {t['entity']}")
    
    print("\n" + "-" * 70)
    print("Violation Detection Results:")
    print("-" * 70)
    
    results = compare_network_with_sources(
        network_types,
        label_declared,
        manifest_declared,
        app_id,
        label_data_not_collected,
        manifest_data_not_collected
    )
    
    print(f"\nNetwork vs Label: {len(results['network_vs_label'])} violations")
    for v in results['network_vs_label']:
        print(f"  - {v['collected_type']:20s} -> {v['violation_type']}")
    
    print(f"\nNetwork vs Manifest: {len(results['network_vs_manifest'])} violations")
    for v in results['network_vs_manifest']:
        print(f"  - {v['collected_type']:20s} -> {v['violation_type']}")
    
    print(f"\nNetwork vs Policy: {len(results['network_vs_policy'])} violations")
    for v in results['network_vs_policy']:
        print(f"  - {v['collected_type']:20s} -> {v['violation_type']}")
        if 'policy_action' in v:
            print(f"    Policy action: {v['policy_action']}")
    
    print("\n" + "=" * 70)
    print("Summary:")
    print(f"  Total violations: {results['summary']['total_violations']}")
    print(f"  By source: {results['summary']['by_source']}")
    print(f"  By type: {results['summary']['by_type']}")
    print("=" * 70)
