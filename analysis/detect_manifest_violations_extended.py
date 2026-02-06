#!/usr/bin/env python3
"""
Detect extended Manifest Violations:

1. NSPrivacyTracking = False but actually tracking
   - Manifest声明NSPrivacyTracking=False，但实际网络流量中有tracking行为

2. Domain list: incorrect or missing
   - NSPrivacyTrackingDomains不正确或缺失
   - 实际tracking domains与manifest声明的不匹配

3. Data missing
   - NSPrivacyCollectedDataTypes中缺失的数据
   - 实际收集了但manifest中没有声明
"""

import plistlib
import pandas as pd
from pathlib import Path
from collections import defaultdict
import re

ROOT = Path('/mnt/ssd2/VR_monkey')
ROOT_306 = ROOT / 'large_scale_analysis_306'
MANIFEST_DIR = ROOT / 'privacy_manifests_extracted'
DATA_FLOWS_FILE = ROOT_306 / 'data_flows_with_appid.csv'
OUTPUT_FILE = ROOT_306 / 'manifest_violations_extended.csv'

# 已知的tracking domains（用于判断是否tracking）
TRACKING_DOMAINS = {
    'doubleclick', 'googlesyndication', 'googleadservices', 'facebook.com',
    'twitter.com', 'linkedin.com', 'pinterest.com', 'snapchat.com',
    'tiktok.com', 'advertising', 'ads', 'tracking', 'analytics',
    'mixpanel', 'amplitude', 'segment', 'braze', 'adjust', 'appsflyer'
}

def extract_app_id_from_manifest_filename(filename):
    """从manifest文件名提取app_id"""
    # 格式: PrivacyInfo_<app_id>_<app_name>.xcprivacy
    match = re.search(r'PrivacyInfo_(\d+)_', filename)
    if match:
        return int(match.group(1))
    return None

def is_tracking_domain(domain):
    """判断domain是否是tracking domain"""
    if not isinstance(domain, str):
        return False
    domain_lower = domain.lower()
    return any(td in domain_lower for td in TRACKING_DOMAINS)

def simplify_entity(domain):
    """简化domain为entity名称"""
    patterns = {
        'mixpanel': 'Mixpanel', 'amplitude': 'Amplitude', 'revenuecat': 'RevenueCat',
        'telemetrydeck': 'TelemetryDeck', 'firebase': 'Firebase',
        'googleapis': 'Google APIs', 'google.com': 'Google', 'facebook': 'Facebook',
        'segment': 'Segment', 'braze': 'Braze', 'unity': 'Unity',
        'icloud': 'Apple', 'apple.com': 'Apple', 'youtube': 'YouTube',
    }
    domain_lower = domain.lower()
    for p, name in patterns.items():
        if p in domain_lower:
            return name
    parts = domain.split('.')
    return parts[-2].capitalize() if len(parts) >= 2 else domain

def load_manifest_data():
    """加载所有manifest文件的数据"""
    manifest_data = {}
    
    for manifest_file in MANIFEST_DIR.glob('*.xcprivacy'):
        app_id = extract_app_id_from_manifest_filename(manifest_file.name)
        if not app_id:
            continue
        
        try:
            with open(manifest_file, 'rb') as f:
                plist = plistlib.load(f)
            
            manifest_info = {
                'ns_privacy_tracking': plist.get('NSPrivacyTracking', False),
                'ns_privacy_tracking_domains': plist.get('NSPrivacyTrackingDomains', []),
                'ns_privacy_collected_data_types': [],
                'has_manifest': True
            }
            
            # 提取收集的数据类型
            collected_types = plist.get('NSPrivacyCollectedDataTypes', [])
            for item in collected_types:
                if isinstance(item, dict):
                    data_type = item.get('NSPrivacyCollectedDataType', '')
                    if data_type:
                        # 简化数据类型名称
                        data_type_clean = data_type.replace('NSPrivacyCollectedDataType', '')
                        manifest_info['ns_privacy_collected_data_types'].append(data_type_clean)
            
            manifest_data[app_id] = manifest_info
            
        except Exception as e:
            print(f"Error loading {manifest_file}: {e}")
            continue
    
    return manifest_data

def detect_manifest_violations():
    """检测manifest violations"""
    print("="*60)
    print("Detecting Extended Manifest Violations")
    print("="*60)
    
    # 1. Load manifest data
    print("\n1. Loading manifest data...")
    manifest_data = load_manifest_data()
    print(f"   Loaded {len(manifest_data)} manifests")
    
    # 2. Load data flows
    print("\n2. Loading data flows...")
    df_flows = pd.read_csv(DATA_FLOWS_FILE)
    print(f"   Total flows: {len(df_flows)}")
    
    # 3. Group flows by app_id
    flows_by_app = df_flows.groupby('app_id')
    
    violations = []
    
    # 4. Detect violations for each app with manifest
    print("\n3. Detecting violations...")
    for app_id, manifest_info in manifest_data.items():
        app_flows = flows_by_app.get_group(app_id) if app_id in flows_by_app.groups else pd.DataFrame()
        
        if len(app_flows) == 0:
            continue
        
        # 4.1. NSPrivacyTracking = False but actually tracking
        if manifest_info['ns_privacy_tracking'] == False:
            # 检查是否有tracking domains
            tracking_domains = []
            for _, row in app_flows.iterrows():
                if is_tracking_domain(row['destination']):
                    tracking_domains.append(row['destination'])
            
            if tracking_domains:
                # 获取唯一的tracking domains
                unique_tracking_domains = list(set(tracking_domains))
                violation = {
                    'app_id': app_id,
                    'source': 'manifest',
                    'violation_type': 'contrary_disclosure',  # 声明不tracking但实际tracking
                    'collected_type': 'tracking',
                    'expected_apple_types': None,
                    'declared_types': None,
                    'data_not_collected': True,  # Manifest声明不tracking
                    'policy_action': None,
                    'manifest_violation_subtype': 'NSPrivacyTracking_False_But_Tracking',
                    'manifest_tracking_declared': False,
                    'manifest_tracking_actual': True,
                    'tracking_domains_found': ', '.join(unique_tracking_domains[:5])  # 前5个
                }
                violations.append(violation)
        
        # 4.1b. NSPrivacyTracking = True but actually no tracking
        elif manifest_info['ns_privacy_tracking'] == True:
            # 检查是否真的有tracking domains
            tracking_domains = []
            for _, row in app_flows.iterrows():
                if is_tracking_domain(row['destination']):
                    tracking_domains.append(row['destination'])
            
            if not tracking_domains:
                # 声明tracking但实际没有tracking
                violation = {
                    'app_id': app_id,
                    'source': 'manifest',
                    'violation_type': 'incorrect_disclosure',  # 声明tracking但实际没有
                    'collected_type': 'tracking',
                    'expected_apple_types': None,
                    'declared_types': ', '.join(manifest_info['ns_privacy_tracking_domains'][:5]) if manifest_info['ns_privacy_tracking_domains'] else 'None',
                    'data_not_collected': False,  # Manifest声明tracking
                    'policy_action': None,
                    'manifest_violation_subtype': 'NSPrivacyTracking_True_But_No_Tracking',
                    'manifest_tracking_declared': True,
                    'manifest_tracking_actual': False,
                    'tracking_domains_found': None,
                    'manifest_tracking_domains_declared': len(manifest_info['ns_privacy_tracking_domains'])
                }
                violations.append(violation)
        
        # 4.2. Domain list: incorrect or missing
        declared_domains = set(manifest_info['ns_privacy_tracking_domains'])
        
        # 获取实际的tracking domains
        actual_tracking_domains = set()
        for _, row in app_flows.iterrows():
            if is_tracking_domain(row['destination']):
                # 简化domain
                domain_simple = row['destination'].split('/')[0].split(':')[0]  # 移除路径和端口
                actual_tracking_domains.add(domain_simple)
        
        # 检查domain list是否缺失或不正确
        missing_domains = actual_tracking_domains - declared_domains
        if missing_domains:
            violation = {
                'app_id': app_id,
                'source': 'manifest',
                'violation_type': 'neglect_disclosure',  # 缺失声明
                'collected_type': 'tracking_domains',
                'expected_apple_types': None,
                'declared_types': ', '.join(list(declared_domains)[:5]) if declared_domains else 'None',
                'data_not_collected': False,
                'policy_action': None,
                'manifest_violation_subtype': 'Domain_List_Missing_Or_Incorrect',
                'manifest_domains_declared': len(declared_domains),
                'manifest_domains_actual': len(actual_tracking_domains),
                'missing_domains': ', '.join(list(missing_domains)[:10])  # 前10个
            }
            violations.append(violation)
        
        # 4.3. Data missing (实际收集了但manifest中没有声明)
        # 只检测有NSPrivacyCollectedDataTypes字段的manifest
        if len(manifest_info['ns_privacy_collected_data_types']) > 0:
            # 获取manifest中声明的数据类型（简化后的）
            declared_data_types = set(manifest_info['ns_privacy_collected_data_types'])
            
            # 获取实际收集的数据类型
            actual_data_types = set(app_flows['data_type'].unique())
            
            # 检查缺失的数据类型
            # 需要将traffic的data_type映射到manifest的data_type格式
            # 这里简化处理，直接比较
            missing_data_types = actual_data_types - declared_data_types
            
            if missing_data_types:
                violation = {
                    'app_id': app_id,
                    'source': 'manifest',
                    'violation_type': 'neglect_disclosure',  # 缺失声明
                    'collected_type': ', '.join(list(missing_data_types)[:5]),  # 前5个
                    'expected_apple_types': None,
                    'declared_types': ', '.join(list(declared_data_types)[:5]) if declared_data_types else 'None',
                    'data_not_collected': False,
                    'policy_action': None,
                    'manifest_violation_subtype': 'Data_Missing_In_Manifest',
                    'manifest_data_types_declared': len(declared_data_types),
                    'manifest_data_types_actual': len(actual_data_types),
                    'missing_data_types': ', '.join(list(missing_data_types)[:10])  # 前10个
                }
                violations.append(violation)
    
    # 5. Create DataFrame
    if violations:
        df_violations = pd.DataFrame(violations)
        
        print(f"\n4. Statistics:")
        print(f"   Total violations: {len(df_violations)}")
        print(f"\n   By violation subtype:")
        print(df_violations['manifest_violation_subtype'].value_counts())
        
        print(f"\n   By violation type:")
        print(df_violations['violation_type'].value_counts())
        
        # 6. Save
        print(f"\n5. Saving violations...")
        df_violations.to_csv(OUTPUT_FILE, index=False)
        print(f"   ✓ Saved to: {OUTPUT_FILE}")
        
        print("\n" + "="*60)
        print("✅ Detection complete!")
        print("="*60)
    else:
        print("\n   No violations found.")
        # Create empty DataFrame
        df_violations = pd.DataFrame(columns=[
            'app_id', 'source', 'violation_type', 'collected_type',
            'expected_apple_types', 'declared_types', 'data_not_collected', 'policy_action',
            'manifest_violation_subtype', 'manifest_tracking_declared', 'manifest_tracking_actual',
            'tracking_domains_found', 'manifest_domains_declared', 'manifest_domains_actual',
            'missing_domains', 'manifest_data_types_declared', 'manifest_data_types_actual',
            'missing_data_types'
        ])
        df_violations.to_csv(OUTPUT_FILE, index=False)
        print(f"   ✓ Created empty file: {OUTPUT_FILE}")

if __name__ == '__main__':
    detect_manifest_violations()
