#!/usr/bin/env python3
"""
Ontology-based Mapping: Traffic Data Types <-> Apple Privacy Label Data Types
-----------------------------------------------------------------------------
使用已定义的 ontology 层级关系 (apple_layer2_integration_final.json) 
来确定 traffic data types 与 Apple Privacy Label data types 之间的映射。

映射原则（基于 ontology 关系）：
1. 子节点关系 (is-a): 如果 traffic_type 是 Apple_type 的 child，则 traffic_type 被 Apple_type 覆盖
2. 祖先关系: 如果 traffic_type 的祖先是某个 Apple_type，则 traffic_type 被 Apple_type 覆盖
3. 无关系: 如果 traffic_type 与任何 Apple_type 都没有 ontology 关系，则无法映射
"""

import json
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path


# ==================== 加载 Ontology 关系 ====================

INTEGRATION_MAP_PATH = "/mnt/ssd2/VR_monkey/ppaudit_analysis/apple_layer2_integration_final.json"

def load_integration_map() -> Dict:
    """加载 Apple -> Traffic 的集成映射"""
    with open(INTEGRATION_MAP_PATH, 'r') as f:
        return json.load(f)


def build_traffic_to_apple_mapping() -> Dict[str, List[str]]:
    """
    从 integration_map 构建 traffic_type -> [apple_types] 的反向映射
    
    逻辑：如果 traffic_type 是 Apple_type 的 child，则该 traffic_type 映射到该 Apple_type
    """
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
    """
    构建 Apple_type -> parent 的映射（用于层级向上查找）
    """
    integration_data = load_integration_map()
    integration_map = integration_data.get('integration_map', {})
    
    apple_to_parent = {}
    for apple_type, info in integration_map.items():
        parent = info.get('parent', '')
        if parent:
            apple_to_parent[apple_type] = parent
    
    return apple_to_parent


# 全局缓存
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


# ==================== 映射函数 ====================

def get_apple_types_for_traffic(traffic_type: str) -> List[str]:
    """
    获取 traffic type 对应的 Apple privacy label data types
    
    基于 ontology 中的 child 关系：
    - 如果 traffic_type 是某个 Apple_type 的 child，返回该 Apple_type
    
    Args:
        traffic_type: 从 traffic 检测到的 data type
    
    Returns:
        对应的 Apple data types 列表（空列表表示 ontology 中无映射）
    """
    mapping = get_traffic_to_apple_mapping()
    traffic_type_lower = traffic_type.lower().strip()
    return mapping.get(traffic_type_lower, [])


def is_covered_by_apple_types(traffic_type: str, declared_types: Set[str]) -> bool:
    """
    检查 traffic type 是否被 declared Apple types 覆盖
    
    基于 ontology 关系判断覆盖：
    1. 直接覆盖：traffic_type 是某个 declared Apple_type 的 child
    2. 祖先覆盖：declared Apple_type 是 traffic_type 对应的 Apple_type 的祖先
    
    Args:
        traffic_type: 从 traffic 检测到的 data type
        declared_types: App 声明的 Apple data types (set of strings)
    
    Returns:
        True 如果被覆盖（无 violation），False 如果未覆盖（有 violation）
    """
    apple_types = get_apple_types_for_traffic(traffic_type)
    
    # 如果 ontology 中没有映射关系，无法判断 violation
    if not apple_types:
        return True  # 保守策略：无映射则不报 violation
    
    declared_lower = {d.lower() for d in declared_types}
    
    # 检查直接覆盖
    for apple_type in apple_types:
        if apple_type.lower() in declared_lower:
            return True
    
    # 检查祖先覆盖（向上遍历 ontology）
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
    """
    获取 violation 的详细信息
    
    Returns:
        {
            'is_violation': bool,
            'traffic_type': str,
            'expected_apple_types': list,  # 基于 ontology 的期望 types
            'declared_types': list,
            'missing_types': list,
            'has_ontology_mapping': bool
        }
    """
    apple_types = get_apple_types_for_traffic(traffic_type)
    declared_lower = {d.lower() for d in declared_types}
    
    has_ontology_mapping = len(apple_types) > 0
    
    if not has_ontology_mapping:
        return {
            'is_violation': False,  # 无 ontology 映射，不报 violation
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


# ==================== 辅助函数 ====================

def get_all_apple_types() -> List[str]:
    """获取所有 Apple data types"""
    integration_data = load_integration_map()
    return list(integration_data.get('integration_map', {}).keys())


def get_mapped_traffic_types() -> List[str]:
    """获取所有有 ontology 映射的 traffic types"""
    mapping = get_traffic_to_apple_mapping()
    return list(mapping.keys())


def get_unmapped_traffic_types(all_traffic_types: List[str]) -> List[str]:
    """获取所有无 ontology 映射的 traffic types"""
    mapping = get_traffic_to_apple_mapping()
    return [t for t in all_traffic_types if t.lower() not in mapping]


# ==================== 统计信息 ====================

def print_mapping_stats():
    """打印映射统计"""
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
    
    # 模拟测试
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
