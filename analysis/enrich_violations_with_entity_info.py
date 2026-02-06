#!/usr/bin/env python3
"""
Enrich violations_all_apps.csv with entity information:

1. Traffic flow domain information:
   - traffic_destination: destination domain from data_flows
   - traffic_entity: simplified entity name (e.g., Apple, Google APIs, Mixpanel)
   - traffic_is_1st_party: boolean (True if destination matches app's bundle_id domain)

2. Policy claim entity information:
   - policy_entity: entity from policy_cus_triplets (e.g., "we", "third party", "microsoft")
   - policy_is_1st_party: boolean (True for "we", "our", "us", "ourselves" only)
   - Note: Apple, Unity are considered 3rd party (special platform)

This allows distinguishing between:
- Where data is actually sent (traffic domain)
- Where policy claims data is sent (policy entity)
"""

import pandas as pd
from pathlib import Path
from urllib.parse import urlparse
import re

# Paths
ROOT = Path('/mnt/ssd2/VR_monkey')
ROOT_306 = Path('/mnt/ssd2/VR_monkey/large_scale_analysis_306')
VIOLATIONS_FILE = ROOT_306 / 'violations_all_apps.csv'
DATA_FLOWS_FILE = ROOT_306 / 'data_flows_with_appid.csv'
POLICY_FILE = ROOT_306 / 'policy_cus_triplets_234.csv'
IPA_INFO_FILE = ROOT / 'ipa_info_extraction.csv'
OUTPUT_FILE = ROOT_306 / 'violations_all_apps_enriched.csv'

# 1st party entities (from policy) - only first person pronouns
FIRST_PARTY_POLICY_ENTITIES = {
    'we', 'our', 'us', 'ourselves'
}


def simplify_entity(destination: str) -> str:
    """Simplify destination domain to entity name."""
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
        'microsoft': 'Microsoft',
        'office': 'Microsoft',
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


def extract_domain_from_bundle_id(bundle_id: str) -> str:
    """Extract domain from bundle_id (reverse domain notation).
    
    Examples:
        com.company.appname -> company.com
        de.inovation.NewTube -> inovation.de
        com.studioamanga.airgrenoble -> studioamanga.com
    """
    if pd.isna(bundle_id) or not isinstance(bundle_id, str):
        return None
    
    parts = bundle_id.split('.')
    if len(parts) >= 2:
        # Take first two parts and reverse
        domain_parts = parts[:2]
        domain_parts.reverse()
        return '.'.join(domain_parts)
    return None


def is_1st_party_domain(destination: str, app_domain: str) -> bool:
    """Check if destination is 1st party based on app's bundle_id domain.
    
    Args:
        destination: The destination domain from traffic
        app_domain: The domain extracted from app's bundle_id (e.g., "company.com")
    
    Returns:
        True if destination contains app_domain, False otherwise
    """
    if not isinstance(destination, str) or not app_domain:
        return False
    
    d = destination.lower()
    app_d = app_domain.lower()
    
    # Check if destination contains the app's domain
    # e.g., if app_domain is "company.com", check if destination contains "company.com"
    return app_d in d


def is_1st_party_policy_entity(entity: str) -> bool:
    """Check if policy entity is 1st party.
    
    Rules:
    - 1st party: "we", "our", "us", "ourselves" (first person pronouns)
    - 3rd party: everything else, including:
      * "apple", "unity" (special platforms, but still 3rd party)
      * "third party", "microsoft", "google", etc.
    """
    if pd.isna(entity):
        return False
    e = str(entity).lower().strip()
    # Only first person pronouns are 1st party
    return e in FIRST_PARTY_POLICY_ENTITIES


def main():
    print("="*60)
    print("Enriching violations with entity information")
    print("="*60)
    
    # 1. Load IPA info to get bundle_id -> domain mapping
    print("\n1. Loading IPA info to extract bundle_id domains...")
    df_ipa = pd.read_csv(IPA_INFO_FILE)
    print(f"   Total IPA files: {len(df_ipa)}")
    
    # Extract app_id from filename (format: bundle_id-version-app_id-xxx.ipa)
    def extract_app_id_from_filename(filename):
        if pd.isna(filename):
            return None
        parts = str(filename).split('-')
        if len(parts) >= 3:
            try:
                return int(float(parts[2]))  # Handle scientific notation
            except:
                return None
        return None
    
    df_ipa['app_id'] = df_ipa['IPA_File'].apply(extract_app_id_from_filename)
    df_ipa['domain'] = df_ipa['Bundle_Identifier'].apply(extract_domain_from_bundle_id)
    
    # Create mapping: app_id -> domain
    app_domain_map = {}
    for _, row in df_ipa.iterrows():
        if pd.notna(row['app_id']) and pd.notna(row['domain']):
            app_id = int(row['app_id'])
            domain = str(row['domain'])
            app_domain_map[app_id] = domain
    
    print(f"   Successfully mapped {len(app_domain_map)} apps to domains")
    print(f"   Example mappings: {list(app_domain_map.items())[:5]}")
    
    # 2. Load violations
    print("\n2. Loading violations...")
    df_violations = pd.read_csv(VIOLATIONS_FILE)
    print(f"   Total violations: {len(df_violations)}")
    
    # 3. Load data flows to get traffic destination
    print("\n3. Loading data flows...")
    df_flows = pd.read_csv(DATA_FLOWS_FILE)
    print(f"   Total flows: {len(df_flows)}")
    
    # Create mapping: (app_id, data_type) -> set of destinations
    flow_map = {}
    for _, row in df_flows.iterrows():
        key = (int(row['app_id']), str(row['data_type']))
        if key not in flow_map:
            flow_map[key] = set()
        flow_map[key].add(row['destination'])
    
    print(f"   Unique (app_id, data_type) pairs: {len(flow_map)}")
    
    # 4. Load policy triplets to get policy entity
    print("\n4. Loading policy triplets...")
    df_policy = pd.read_csv(POLICY_FILE)
    print(f"   Total policy triplets: {len(df_policy)}")
    
    # Create mapping: (app_id, data_type) -> set of policy entities
    policy_map = {}
    for _, row in df_policy.iterrows():
        key = (int(row['app_id']), str(row['data_type']))
        if key not in policy_map:
            policy_map[key] = set()
        policy_map[key].add(str(row['entity']))
    
    print(f"   Unique (app_id, data_type) pairs in policy: {len(policy_map)}")
    
    # 5. Enrich violations
    print("\n5. Enriching violations...")
    
    def get_traffic_info(row):
        """Get traffic destination and entity info."""
        key = (int(row['app_id']), str(row['collected_type']))
        destinations = flow_map.get(key, set())
        
        if not destinations:
            return pd.Series({
                'traffic_destination': None,
                'traffic_entity': None,
                'traffic_is_1st_party': None
            })
        
        # Use first destination (or could aggregate)
        dest = list(destinations)[0] if destinations else None
        entity = simplify_entity(dest) if dest else None
        
        # Check if 1st party based on app's bundle_id domain
        app_id = int(row['app_id'])
        app_domain = app_domain_map.get(app_id)
        is_1st = is_1st_party_domain(dest, app_domain) if dest and app_domain else False
        
        return pd.Series({
            'traffic_destination': dest,
            'traffic_entity': entity,
            'traffic_is_1st_party': is_1st
        })
    
    def get_policy_info(row):
        """Get policy entity info."""
        if row['source'] != 'policy':
            return pd.Series({
                'policy_entity': None,
                'policy_is_1st_party': None
            })
        
        key = (int(row['app_id']), str(row['collected_type']))
        entities = policy_map.get(key, set())
        
        if not entities:
            return pd.Series({
                'policy_entity': None,
                'policy_is_1st_party': None
            })
        
        # Use first entity (or could aggregate)
        entity = list(entities)[0] if entities else None
        is_1st = is_1st_party_policy_entity(entity) if entity else None
        
        return pd.Series({
            'policy_entity': entity,
            'policy_is_1st_party': is_1st
        })
    
    # Apply enrichment
    traffic_info = df_violations.apply(get_traffic_info, axis=1)
    policy_info = df_violations.apply(get_policy_info, axis=1)
    
    # Combine
    df_enriched = pd.concat([
        df_violations,
        traffic_info,
        policy_info
    ], axis=1)
    
    # 6. Statistics
    print("\n6. Statistics:")
    print(f"   Violations with traffic_destination: {df_enriched['traffic_destination'].notna().sum()}")
    print(f"   Violations with traffic_is_1st_party=True: {df_enriched['traffic_is_1st_party'].sum()}")
    print(f"   Violations with policy_entity: {df_enriched['policy_entity'].notna().sum()}")
    print(f"   Violations with policy_is_1st_party=True: {df_enriched['policy_is_1st_party'].sum()}")
    
    # Check coverage
    violations_with_app_domain = df_enriched['app_id'].isin(app_domain_map.keys()).sum()
    print(f"   Violations with app domain mapping: {violations_with_app_domain} ({100*violations_with_app_domain/len(df_enriched):.1f}%)")
    
    # 7. Check for mismatches
    print("\n7. Entity mismatches (policy vs traffic):")
    policy_violations = df_enriched[df_enriched['source'] == 'policy']
    policy_violations = policy_violations[
        policy_violations['traffic_entity'].notna() & 
        policy_violations['policy_entity'].notna()
    ]
    
    if len(policy_violations) > 0:
        mismatches = policy_violations[
            policy_violations['traffic_entity'] != policy_violations['policy_entity']
        ]
        print(f"   Total policy violations with both entities: {len(policy_violations)}")
        print(f"   Entity mismatches: {len(mismatches)} ({100*len(mismatches)/len(policy_violations):.1f}%)")
        
        # 1st/3rd party mismatches
        party_mismatches = policy_violations[
            policy_violations['traffic_is_1st_party'] != policy_violations['policy_is_1st_party']
        ]
        print(f"   1st/3rd party mismatches: {len(party_mismatches)} ({100*len(party_mismatches)/len(policy_violations):.1f}%)")
    
    # 8. Save
    print(f"\n8. Saving enriched data...")
    df_enriched.to_csv(OUTPUT_FILE, index=False)
    print(f"   ✓ Saved to: {OUTPUT_FILE}")
    print(f"   New columns added:")
    print(f"     - traffic_destination")
    print(f"     - traffic_entity")
    print(f"     - traffic_is_1st_party")
    print(f"     - policy_entity")
    print(f"     - policy_is_1st_party")
    
    print("\n" + "="*60)
    print("✅ Enrichment complete!")
    print("="*60)


if __name__ == '__main__':
    main()
