#!/usr/bin/env python3
"""
Unified Violation Detection for Multiple Data Sources
-----------------------------------------------------
支持 4 个数据来源的统一 violation 检测：
1. label: Privacy Labels (Apple App Store)
2. manifest: Privacy Manifests (NSPrivacyAccessedAPITypes)
3. policy: Privacy Policies (文本分析，有 collect/not collect)
4. network: Network Traffic (实际收集的数据)

检测逻辑：
- 所有来源的 data types 都先映射到 ontology 节点
- 使用相同的 ontology 关系检查函数
- 但不同来源有不同的 violation 类型判断规则
"""

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
    """
    Network vs Label/Manifest 的检测
    
    逻辑：
    - 如果声明 "Data Not Collected" 但 network 有 → Incorrect Disclosure (Contrary Disclosure)
    - 如果 network 有，但 label/manifest 没有声明 → Neglect Disclosure
    - 如果 network 有，且 label/manifest 有声明 → 无 violation
    
    Args:
        network_data_type: 从 network 收集到的 data type (已映射到 ontology)
        declared_types: Label/Manifest 声明的 data types (已映射到 ontology)
        data_not_collected: 是否声明 "Data Not Collected"
    
    Returns:
        None 如果无 violation，否则返回 violation dict
    """
    # 如果声明 "Data Not Collected"，但 network 有 → Incorrect Disclosure
    if data_not_collected:
        return {
            'is_violation': True,
            'violation_type': 'incorrect_disclosure',  # 对应 Contrary Disclosure
            'collected_type': network_data_type,
            'expected_apple_types': get_apple_types_for_traffic(network_data_type),
            'declared_types': [],
            'data_not_collected': True,
            'has_ontology_mapping': True
        }
    
    # 检查是否有声明
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
    """
    从 CSV 加载指定 app 的 policy triplets
    
    Args:
        app_id: App ID
    
    Returns:
        List of triplets: [{'entity': str, 'action': 'collect'|'not_collect', 'data_type': str}, ...]
    """
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
                    'action': row.get('action', ''),  # 'collect' or 'not_collect'
                    'data_type': row.get('data_type', ''),
                    'sentence_preview': row.get('sentence_preview', '')
                })
    
    return triplets


def detect_violation_network_vs_policy(
    network_data_type: str,  # 已映射到 ontology
    policy_triplets: List[Dict]  # [{'entity': str, 'action': 'collect'|'not_collect', 'data_type': str}, ...]
) -> Optional[Dict]:
    """
    Network vs Policy 的检测
    
    逻辑：
    1. 如果 policy triplet 的 action 是 "not_collect" 但 network 有 → Incorrect Disclosure
    2. 如果 policy 没有该 data type 的 triplet，但 network 有 → Omit (Neglect Disclosure)
    3. 如果 policy 有 "collect" 且 network 有 → 无 violation
    
    注意：policy 的 data_type 已经是 ontology 节点，需要基于 ontology 关系匹配
    - 直接匹配：policy_data_type == network_data_type
    - 关系匹配：基于 ontology 父子关系（如果 network_data_type 是 policy_data_type 的子节点，也算匹配）
    
    Args:
        network_data_type: 从 network 收集到的 data type (已映射到 ontology)
        policy_triplets: Policy triplets，格式：{'entity': str, 'action': 'collect'|'not_collect', 'data_type': str}
    
    Returns:
        None 如果无 violation，否则返回 violation dict
    """
    # 查找 policy 中是否有该 data type 的 triplet
    # policy 的 data_type 已经是 ontology 节点，直接字符串匹配
    matching_triplets = []
    
    for triplet in policy_triplets:
        policy_data_type = triplet.get('data_type', '')
        
        # 直接字符串匹配（都是 ontology 节点）
        if policy_data_type.lower() == network_data_type.lower():
            matching_triplets.append(triplet)
    
    # 如果 policy 中有 "not_collect" 的声明
    not_collect_triplets = [
        t for t in matching_triplets 
        if t.get('action', '').lower() == 'not_collect'
    ]
    
    if not_collect_triplets:
        # Policy 声明不收集，但 network 有 → Incorrect Disclosure
        return {
            'is_violation': True,
            'violation_type': 'incorrect_disclosure',
            'collected_type': network_data_type,
            'expected_apple_types': get_apple_types_for_traffic(network_data_type),
            'declared_types': [],
            'policy_action': 'not_collect',
            'has_ontology_mapping': True
        }
    
    # 如果 policy 中没有该 data type 的 triplet
    if not matching_triplets:
        # Policy 没有声明，但 network 有 → Omit (Neglect Disclosure)
        return {
            'is_violation': True,
            'violation_type': 'neglect_disclosure',
            'collected_type': network_data_type,
            'expected_apple_types': get_apple_types_for_traffic(network_data_type),
            'declared_types': [],
            'policy_action': None,  # 没有 triplet
            'has_ontology_mapping': True
        }
    
    # Policy 有 "collect" 声明 → 无 violation
    return None


def detect_violation_unified(
    collected_data_type: str,
    declared_types: Set[str],
    data_not_collected: bool = False
) -> Dict:
    """
    统一的 violation 检测函数（用于 Label/Manifest）
    
    核心逻辑：只比较 ontology 上的 data type 节点关系
    - 不需要知道数据来源（network/label/manifest/policy）
    - 所有 data types 都已映射到 ontology 节点
    - 基于 ontology 图上的父子关系、祖先关系判断是否相符
    
    Args:
        collected_data_type: 收集到的 data type (已映射到 ontology 节点)
        declared_types: 声明的 data types (已映射到 ontology 节点)
        data_not_collected: 是否声明 "Data Not Collected" (仅用于 Label)
    
    Returns:
        {
            'is_violation': bool,
            'violation_type': 'neglect_disclosure' | 'contrary_disclosure' | None,
            'collected_type': str,
            'expected_apple_types': list,
            'declared_types': list,
            'missing_types': list,
            'has_ontology_mapping': bool
        }
    """
    
    # 使用统一的 ontology 检测逻辑
    details = get_violation_details(collected_data_type, declared_types)
    
    violation_type = None
    if details['is_violation']:
        if data_not_collected:
            violation_type = 'contrary_disclosure'  # 声明不收集但实际收集
        else:
            violation_type = 'neglect_disclosure'   # 收集但未声明
    
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
    app_id: str,  # 用于加载 policy triplets
    label_data_not_collected: bool = False,
    manifest_data_not_collected: bool = False
) -> Dict:
    """
    比较 Network 与其他 3 个来源的 violations
    
    Args:
        network_types: Network 收集到的 data types (已映射到 ontology)
        label_declared: Label 声明的 data types (已映射到 ontology)
        manifest_declared: Manifest 声明的 data types (已映射到 ontology)
        app_id: App ID，用于加载 policy triplets
        label_data_not_collected: Label 是否声明 "Data Not Collected"
        manifest_data_not_collected: Manifest 是否声明 "Data Not Collected"
        policy_data_type_mapper: 可选，将 policy data_type 映射到 ontology 的函数
    
    Returns:
        {
            'network_vs_label': [...],
            'network_vs_manifest': [...],
            'network_vs_policy': [...],
            'summary': {...}
        }
    """
    # 加载 policy triplets
    policy_triplets = load_policy_triplets_for_app(app_id)
    
    network_vs_label = []
    network_vs_manifest = []
    network_vs_policy = []
    
    for network_type in network_types:
        # Network vs Label
        result = detect_violation_network_vs_label_manifest(
            network_type,
            label_declared,
            label_data_not_collected
        )
        if result:
            network_vs_label.append(result)
        
        # Network vs Manifest
        result = detect_violation_network_vs_label_manifest(
            network_type,
            manifest_declared,
            manifest_data_not_collected
        )
        if result:
            network_vs_manifest.append(result)
        
        # Network vs Policy
        result = detect_violation_network_vs_policy(
            network_type,
            policy_triplets
        )
        if result:
            network_vs_policy.append(result)
    
    # 统计
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
    # 示例
    print("=" * 70)
    print("Unified Violation Detection - Network vs Other Sources")
    print("=" * 70)
    
    # 示例数据
    app_id = "1365531024"  # 1Blocker
    network_types = ['device id', 'geo location', 'browsing']
    label_declared = {'User ID', 'Purchase History'}
    manifest_declared = {'User ID'}
    label_data_not_collected = True  # Label 声明 "Data Not Collected"
    manifest_data_not_collected = False
    
    print("\nApp ID:", app_id)
    print("Network types:", network_types)
    print("Label declared:", label_declared)
    print("Label data_not_collected:", label_data_not_collected)
    print("Manifest declared:", manifest_declared)
    
    # 加载 policy triplets
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
