


import pandas as pd
from pathlib import Path
import re


ROOT = Path('/mnt/ssd2/VR_monkey')
ROOT_306 = Path('/mnt/ssd2/VR_monkey/large_scale_analysis_306')
DATA_FLOWS_FILE = ROOT_306 / 'data_flows_with_appid.csv'
POLICY_FILE = ROOT_306 / 'policy_cus_triplets_234.csv'
IPA_INFO_FILE = ROOT / 'ipa_info_extraction.csv'
VIOLATIONS_FILE = ROOT_306 / 'violations_all_apps.csv'
OUTPUT_FILE = ROOT_306 / 'mismatched_entity_violations.csv'


def extract_domain_from_bundle_id(bundle_id: str) -> str:
    
    if pd.isna(bundle_id) or not isinstance(bundle_id, str):
        return None
    parts = bundle_id.split('.')
    if len(parts) >= 2:
        domain_parts = parts[:2]
        domain_parts.reverse()
        return '.'.join(domain_parts)
    return None


def simplify_entity(destination: str) -> str:
    
    if not isinstance(destination, str):
        return 'Unknown'
    
    d = destination.lower()
    patterns = {
        'mixpanel': 'Mixpanel',
        'amplitude': 'Amplitude',
        'revenuecat': 'RevenueCat',
        'telemetrydeck': 'TelemetryDeck',
        'firebase': 'Firebase',
        'crashlytics': 'Firebase',
        'googleapis': 'Google APIs',
        'google.com': 'Google',
        'analytics.google': 'Google Analytics',
        'facebook': 'Facebook',
        'segment': 'Segment',
        'braze': 'Braze',
        'unity3d': 'Unity',
        'unity': 'Unity',
        'icloud': 'Apple',
        'apple.com': 'Apple',
        'youtube': 'YouTube',
        'baidu': 'Baidu',
        'disney': 'Disney',
        'impact.com': 'Impact',
        'dynamicyield': 'DynamicYield',
        'reddit': 'Reddit',
        'customer.io': 'Customer.io',
        'datadoghq': 'Datadog',
        'shopify': 'Shopify',
        'ctrip': 'Ctrip',
        'nba.com': 'NBA',
        'sentry': 'Sentry',
        'branch': 'Branch',
        'appsflyer': 'AppsFlyer',
        'adjust': 'Adjust',
        'loggly': 'Loggly',
    }
    
    for pat, name in patterns.items():
        if pat in d:
            return name
    
    parts = destination.split('.')
    return parts[-2].capitalize() if len(parts) >= 2 else destination


def is_1st_party_domain(destination: str, app_domain: str) -> bool:
    
    if not isinstance(destination, str) or not app_domain:
        return False
    d = destination.lower()
    app_d = app_domain.lower()
    return app_d in d


def is_1st_party_policy_entity(entity: str) -> bool:
    
    if pd.isna(entity):
        return False
    e = str(entity).lower().strip()
    first_party_entities = {'we', 'our', 'us', 'ourselves'}
    return e in first_party_entities


def main():
    print("="*60)
    print("Detecting Mismatched Entity Disclosure Violations")
    print("="*60)
    
    
    print("\n1. Loading IPA info...")
    df_ipa = pd.read_csv(IPA_INFO_FILE)
    def extract_app_id_from_filename(filename):
        if pd.isna(filename):
            return None
        parts = str(filename).split('-')
        if len(parts) >= 3:
            try:
                return int(float(parts[2]))
            except:
                return None
        return None
    
    df_ipa['app_id'] = df_ipa['IPA_File'].apply(extract_app_id_from_filename)
    df_ipa['domain'] = df_ipa['Bundle_Identifier'].apply(extract_domain_from_bundle_id)
    app_domain_map = {int(row['app_id']): str(row['domain']) for _, row in df_ipa.iterrows() 
                     if pd.notna(row['app_id']) and pd.notna(row['domain'])}
    print(f"   Mapped {len(app_domain_map)} apps to domains")
    
    
    print("\n2. Loading data flows...")
    df_flows = pd.read_csv(DATA_FLOWS_FILE)
    print(f"   Total flows: {len(df_flows)}")
    
    
    df_flows['traffic_entity'] = df_flows['destination'].apply(simplify_entity)
    df_flows['traffic_is_1st_party'] = df_flows.apply(
        lambda row: is_1st_party_domain(row['destination'], app_domain_map.get(int(row['app_id']))),
        axis=1
    )
    
    
    flow_entity_map = {}
    for _, row in df_flows.iterrows():
        key = (int(row['app_id']), str(row['data_type']))
        if key not in flow_entity_map:
            flow_entity_map[key] = {
                'entities': set(),
                'is_1st_party': False,
                'destinations': set()
            }
        flow_entity_map[key]['entities'].add(row['traffic_entity'])
        flow_entity_map[key]['destinations'].add(row['destination'])
        if row['traffic_is_1st_party']:
            flow_entity_map[key]['is_1st_party'] = True
    
    print(f"   Unique (app_id, data_type) pairs in flows: {len(flow_entity_map)}")
    
    
    print("\n3. Loading policy triplets...")
    df_policy = pd.read_csv(POLICY_FILE)
    print(f"   Total policy triplets: {len(df_policy)}")
    
    
    policy_entity_map = {}
    for _, row in df_policy.iterrows():
        key = (int(row['app_id']), str(row['data_type']))
        if key not in policy_entity_map:
            policy_entity_map[key] = {
                'entities': set(),
                'is_1st_party': False
            }
        entity = str(row['entity'])
        policy_entity_map[key]['entities'].add(entity)
        if is_1st_party_policy_entity(entity):
            policy_entity_map[key]['is_1st_party'] = True
    
    print(f"   Unique (app_id, data_type) pairs in policy: {len(policy_entity_map)}")
    
    
    print("\n4. Finding compliant cases (exist in both policy and flow)...")
    compliant_keys = set(flow_entity_map.keys()) & set(policy_entity_map.keys())
    print(f"   Compliant (app_id, data_type) pairs: {len(compliant_keys)}")
    
    
    print("\n5. Detecting mismatched entity violations...")
    mismatched_violations = []
    
    for key in compliant_keys:
        app_id, data_type = key
        flow_info = flow_entity_map[key]
        policy_info = policy_entity_map[key]
        
        
        if flow_info['is_1st_party'] != policy_info['is_1st_party']:
            
            flow_entity = list(flow_info['entities'])[0] if flow_info['entities'] else None
            policy_entity = list(policy_info['entities'])[0] if policy_info['entities'] else None
            flow_destination = list(flow_info['destinations'])[0] if flow_info['destinations'] else None
            
            violation = {
                'app_id': app_id,
                'data_type': data_type,
                'source': 'policy',
                'violation_type': 'mismatched_entity_disclosure',
                'collected_type': data_type,
                'policy_entity': policy_entity,
                'policy_is_1st_party': policy_info['is_1st_party'],
                'traffic_entity': flow_entity,
                'traffic_is_1st_party': flow_info['is_1st_party'],
                'traffic_destination': flow_destination,
                'mismatch_type': '1st_to_3rd' if policy_info['is_1st_party'] and not flow_info['is_1st_party'] else '3rd_to_1st'
            }
            mismatched_violations.append(violation)
    
    print(f"   Found {len(mismatched_violations)} mismatched entity violations")
    
    
    if mismatched_violations:
        df_mismatched = pd.DataFrame(mismatched_violations)
        
        
        print("\n6. Statistics:")
        print(f"   Total mismatched violations: {len(df_mismatched)}")
        print(f"   Policy 1st party -> Flow 3rd party: {len(df_mismatched[df_mismatched['mismatch_type'] == '1st_to_3rd'])}")
        print(f"   Policy 3rd party -> Flow 1st party: {len(df_mismatched[df_mismatched['mismatch_type'] == '3rd_to_1st'])}")
        print(f"   Unique apps: {df_mismatched['app_id'].nunique()}")
        print(f"   Unique data types: {df_mismatched['data_type'].nunique()}")
        
        
        print("\n   Top 10 policy entities (mismatched):")
        print(df_mismatched['policy_entity'].value_counts().head(10))
        print("\n   Top 10 traffic entities (mismatched):")
        print(df_mismatched['traffic_entity'].value_counts().head(10))
        
        
        print(f"\n7. Saving mismatched entity violations...")
        df_mismatched.to_csv(OUTPUT_FILE, index=False)
        print(f"   ✓ Saved to: {OUTPUT_FILE}")
        
        print("\n" + "="*60)
        print("✅ Detection complete!")
        print("="*60)
    else:
        print("\n   No mismatched entity violations found.")
        print("   Creating empty CSV file...")
        
        df_mismatched = pd.DataFrame(columns=[
            'app_id', 'data_type', 'source', 'violation_type', 'collected_type',
            'policy_entity', 'policy_is_1st_party', 'traffic_entity', 
            'traffic_is_1st_party', 'traffic_destination', 'mismatch_type'
        ])
        df_mismatched.to_csv(OUTPUT_FILE, index=False)
        print(f"   ✓ Created empty file: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
