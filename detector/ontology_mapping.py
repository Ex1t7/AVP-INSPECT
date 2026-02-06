


import json
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path




INTEGRATION_MAP_PATH = "/mnt/ssd2/VR_monkey/ppaudit_analysis/apple_layer2_integration_final.json"

def load_integration_map() -> Dict:
    
    with open(INTEGRATION_MAP_PATH, 'r') as f:
        return json.load(f)


def build_traffic_to_apple_mapping() -> Dict[str, List[str]]:
    
    integration_data = load_integration_map()
    integration_map = integration_data.get('integration_map', {})
    
    traffic_to_apple = {}
    
    for apple_type, info in integration_map.items():
        children = info.get('children', [])
        for child in children:
            child_lower = child.lower()
            if child_lower not in traffic_to_apple:
                traffic_to_apple[child_lower] = []
            traffic_to_apple[child_lower].append(apple_type)
    
    return traffic_to_apple


def build_parent_mapping() -> Dict[str, str]:
    
    integration_data = load_integration_map()
    integration_map = integration_data.get('integration_map', {})
    
    apple_to_parent = {}
    for apple_type, info in integration_map.items():
        parent = info.get('parent', '')
        if parent:
            apple_to_parent[apple_type] = parent
    
    return apple_to_parent



_TRAFFIC_TO_APPLE = None
_APPLE_TO_PARENT = None


def get_traffic_to_apple_mapping() -> Dict[str, List[str]]:
    global _TRAFFIC_TO_APPLE
    if _TRAFFIC_TO_APPLE is None:
        _TRAFFIC_TO_APPLE = build_traffic_to_apple_mapping()
    return _TRAFFIC_TO_APPLE


def get_apple_to_parent_mapping() -> Dict[str, str]:
    global _APPLE_TO_PARENT
    if _APPLE_TO_PARENT is None:
        _APPLE_TO_PARENT = build_parent_mapping()
    return _APPLE_TO_PARENT




def get_apple_types_for_traffic(traffic_type: str) -> List[str]:
    
    mapping = get_traffic_to_apple_mapping()
    traffic_type_lower = traffic_type.lower().strip()
    return mapping.get(traffic_type_lower, [])


def is_covered_by_apple_types(traffic_type: str, declared_types: Set[str]) -> bool:
    
    apple_types = get_apple_types_for_traffic(traffic_type)
    
    
    if not apple_types:
        return True  
    
    declared_lower = {d.lower() for d in declared_types}
    
    
    for apple_type in apple_types:
        if apple_type.lower() in declared_lower:
            return True
    
    
    apple_to_parent = get_apple_to_parent_mapping()
    for apple_type in apple_types:
        current = apple_type
        while current in apple_to_parent:
            parent = apple_to_parent[current]
            if parent.lower() in declared_lower:
                return True
            current = parent
    
    return False


def get_violation_details(traffic_type: str, declared_types: Set[str]) -> dict:
    
    apple_types = get_apple_types_for_traffic(traffic_type)
    declared_lower = {d.lower() for d in declared_types}
    
    has_ontology_mapping = len(apple_types) > 0
    
    if not has_ontology_mapping:
        return {
            'is_violation': False,  
            'traffic_type': traffic_type,
            'expected_apple_types': [],
            'declared_types': list(declared_types),
            'missing_types': [],
            'has_ontology_mapping': False
        }
    
    is_covered = is_covered_by_apple_types(traffic_type, declared_types)
    
    return {
        'is_violation': not is_covered,
        'traffic_type': traffic_type,
        'expected_apple_types': apple_types,
        'declared_types': list(declared_types),
        'missing_types': [t for t in apple_types if t.lower() not in declared_lower],
        'has_ontology_mapping': True
    }




def get_all_apple_types() -> List[str]:
    
    integration_data = load_integration_map()
    return list(integration_data.get('integration_map', {}).keys())


def get_mapped_traffic_types() -> List[str]:
    
    mapping = get_traffic_to_apple_mapping()
    return list(mapping.keys())


def get_unmapped_traffic_types(all_traffic_types: List[str]) -> List[str]:
    
    mapping = get_traffic_to_apple_mapping()
    return [t for t in all_traffic_types if t.lower() not in mapping]




def print_mapping_stats():
    
    mapping = get_traffic_to_apple_mapping()
    apple_types = get_all_apple_types()
    
    print("=" * 60)
    print("Ontology Mapping Statistics")
    print("=" * 60)
    print(f"Apple Privacy Label types: {len(apple_types)}")
    print(f"Traffic types with ontology mapping: {len(mapping)}")
    print()
    
    print("Traffic Type -> Apple Type Mappings:")
    print("-" * 60)
    for traffic_type, apple_types_list in sorted(mapping.items()):
        print(f"  {traffic_type:<30} -> {apple_types_list}")


if __name__ == "__main__":
    print_mapping_stats()
    
    print("\n" + "=" * 60)
    print("Violation Check Examples:")
    print("-" * 60)
    
    
    test_types = ["email addr", "phone num", "device id", "geo location", 
                  "browsing", "hand tracking data", "gameplay", "error report"]
    
    declared = {"Email Address", "User ID", "Product Interaction"}
    
    for tt in test_types:
        details = get_violation_details(tt, declared)
        if details['has_ontology_mapping']:
            status = "❌ VIOLATION" if details['is_violation'] else "✓ COVERED"
            print(f"{tt:<25} {status:<15} expected: {details['expected_apple_types']}")
        else:
            print(f"{tt:<25} ⚠ NO MAPPING   (not in ontology)")
