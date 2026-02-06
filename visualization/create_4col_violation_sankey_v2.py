


import pandas as pd
import plotly.graph_objects as go
import json
import glob
import os
import pickle
import networkx as nx
from urllib.parse import urlparse


VIOLATIONS_FILE = "/mnt/ssd2/VR_monkey/large_scale_analysis_306/violations_all_apps.csv"
DATA_FLOWS_FILE = "/mnt/ssd2/VR_monkey/ppaudit_analysis/data_flows_output_v2/data_flows_with_appid_cleaned.csv"
APP_STORE_DIR = "/mnt/ssd2/VR_monkey/app_store_data"
IPA_INFO_FILE = "/mnt/ssd2/VR_monkey/ipa_info_extraction.csv"
OUTPUT_HTML = "/mnt/ssd2/VR_monkey/ppaudit_analysis/violation_sankey_4col_v2.html"
ONTOLOGY_PICKLE = "/mnt/ssd2/PPAudit/other_data/data_ontology_policheck.pickle"






def build_ontology_category_map():
    
    with open(ONTOLOGY_PICKLE, 'rb') as f:
        G = pickle.load(f)

    node_lower = {n.lower(): n for n in G.nodes()}

    
    FUNCTIONAL_PARENTS = {'account', 'identifier', 'device info', 'sensor', 'usage info', 'biometric'}

    
    APPLE_TO_FUNCTIONAL = {
        'Advertising Data': 'identifier',   
        'Audio Data': 'sensor',             
        'Coarse Location': 'sensor',        
        'Contacts': 'account',              
        'Credit Info': 'account',           
        'Customer Support': 'usage info',   
        'Device ID': 'identifier',          
        'Email Address': 'identifier',      
        'Emails or Text Messages': 'usage info',  
        'Name': 'account',                  
        'Other Financial Info': 'account',
        'Other User Contact Info': 'account',
        'Other User Content': 'usage info',
        'Payment Info': 'account',
        'Phone Number': 'identifier',
        'Photos or Videos': 'sensor',       
        'Physical Address': 'account',
        'Precise Location': 'sensor',
        'Purchase History': 'usage info',
        'Search History': 'usage info',
        'Sensitive Info': 'biometric',      
        'User ID': 'identifier',
    }

    def find_functional_parent(node_name):
        
        actual = node_lower.get(node_name.lower())
        if not actual:
            return None

        
        if actual.lower() in FUNCTIONAL_PARENTS:
            return actual.lower()

        
        visited = set()
        queue = [actual]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            for parent in G.predecessors(current):
                parent_lower = parent.lower()
                
                if parent_lower in FUNCTIONAL_PARENTS:
                    return parent_lower
                
                if parent in APPLE_TO_FUNCTIONAL:
                    return APPLE_TO_FUNCTIONAL[parent]
                queue.append(parent)

        return None

    
    category_map = {}
    for node in G.nodes():
        cat = find_functional_parent(node)
        if cat:
            category_map[node.lower()] = cat

    
    for apple_node, func_parent in APPLE_TO_FUNCTIONAL.items():
        category_map[apple_node.lower()] = func_parent

    
    NOT_IN_ONTOLOGY = {
        'app_version': 'device info',    
        'device_id': 'identifier',       
        'device_model': 'device info',   
        'email': 'identifier',           
        'ip_address': 'identifier',      
        'location': 'sensor',            
        'os_version': 'device info',     
        'phone': 'identifier',           
        'platform': 'device info',       
        'sdk_version': 'device info',    
        'system_version': 'device info', 
        'tracking': 'usage info',        
        'tracking_domains': 'identifier',
        'user_id': 'identifier',         
        'username': 'account',           
        'zip_code': 'account',           
    }
    category_map.update(NOT_IN_ONTOLOGY)

    
    category_map['pii'] = 'account'          
    category_map['information'] = 'usage info'  
    category_map['non-pii'] = 'device info'     

    return category_map


DATA_TYPE_CATEGORIES = build_ontology_category_map()


KNOWN_3RD_PARTY = {
    'revenuecat', 'telemetrydeck', 'mixpanel', 'amplitude', 'firebase', 'crashlytics',
    'googleapis', 'google.com', 'google-analytics', 'googlesyndication', 'googletagmanager',
    'googlevideo', 'gstatic', 'doubleclick', 'googleadservices',
    'facebook', 'fb.com', 'segment', 'braze', 'unity3d', 'unity',
    'youtube', 'sentry', 'datadoghq', 'appsflyer', 'adjust',
    'branch', 'customer.io', 'shopify', 'reddit', 'dynamicyield',
    'impact', 'amazonaws', 'conviva', 'liadm', 'akamaihd',
    'icloud', 'apple.com', 'microsoft', 'office',
    'clarity.ms', 'bing.com', 'linkedin', 'twitter', 'pinterest',
    'snapchat', 'tiktok', 'amazon', 'pubmatic', 'rubiconproject',
    'demdex', 'cloudfront', 'adobedtm', 'omtrdc', 'everesttech',
    'agkn', 'rfihub', 'onetrust', 'cookielaw', 'launchdarkly',
    'bugsnag', 'newrelic', 'dotomi', 'flashtalking', 'media.net',
    'bidswitch', 'adnxs', 'openx', 'adsrvr', 'tapad', 'sharethrough',
    'outbrain', 'zemanta', 'treasuredata', 'quantserve', 'scorecardresearch',
    'contentsquare', 'posthog', 'optimizely', 'qualtrics', 'gigya',
    'evergage', 'feroot', 'qualified', 'cookieyes', 'appdynamics',
    'nr-data', 'go-mpulse', 'akstat', 'medallia', 'paypal', 'stripe',
    'adapty', 'pawwalls', 'bamgrid', 'warnermediacdn', 'featureassets',
    'prodregistryv2', 'beyondwickedmapping', 'wispr', 'whatsapp',
    'ipredictive', 'hsprotect', 'px-cloud', 'stickyadstv', 'yieldmo',
    'gumgum', 'opera', 'criteo', 'smartadserver', 'connatix',
    'sonobi', 'taboola', 'inmobi', 'mfadsrvr', 'eyeota',
    'crwdcntrl', 'boomtrain', 'salesforce', 'hubspot',
    'contentful', 'cloudflare', 'fastly', 'jsdelivr',
    'restockrocket', 'rebuyengine', 'gorgias',
    'noaa.gov',  
    'pypestream',  
    'radio-browser',  
}


GENERIC_WORDS = {
    'vision', 'vison', 'apple', 'iphone', 'ipad', 'watch',
    'spatial', 'about', 'their', 'these', 'those', 'other',
    'tracker', 'timer', 'notes', 'music', 'video', 'photo',
    'weather', 'camera', 'daily', 'space', 'world', 'focus',
    'studio', 'player', 'browser', 'clock', 'guide', 'board',
    'quest', 'match', 'super', 'pixel', 'voice', 'check',
    'media', 'social', 'stream', 'smart', 'simple', 'light',
    'clean', 'quick', 'prime', 'ultra', 'extra', 'basic',
    'buddy', 'craft', 'maker', 'builder', 'master', 'helper',
    'tools', 'games', 'livre', 'libre', 'learn', 'train',
    'power', 'speed', 'radar', 'alert', 'sound', 'track',
    'scores', 'chart', 'table', 'radio', 'store', 'tides',
}



DTYPE_NORMALIZE = {
    'app_version': 'app ver',
    'device_id': 'device id',
    'device_model': 'model',
    'email': 'email addr',
    'ip_address': 'ip addr',
    'location': 'geo location',
    'name': 'person name',
    'os_version': 'system ver',
    'phone': 'phone num',
    'platform': 'device info',
    'sdk_version': 'sdk ver',
    'system_version': 'system ver',
    'user_id': 'user id',
    'username': 'user id',
}


def normalize_data_type(dtype):
    
    dtype_stripped = dtype.lower().strip()
    return DTYPE_NORMALIZE.get(dtype_stripped, dtype_stripped)


def categorize_data_type(dtype):
    
    dtype_lower = normalize_data_type(dtype)
    cat = DATA_TYPE_CATEGORIES.get(dtype_lower)
    if cat:
        return cat
    
    dtype_space = dtype_lower.replace('_', ' ')
    cat = DATA_TYPE_CATEGORIES.get(dtype_space)
    if cat:
        return cat
    return 'device info'  


def extract_app_categories():
    
    app_categories = {}

    for json_file in glob.glob(os.path.join(APP_STORE_DIR, 'app_*.json')):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            if 'data' not in data or len(data['data']) == 0:
                continue

            app_data = data['data'][0]
            app_id = str(app_data.get('id', ''))
            attrs = app_data.get('attributes', {})

            genre_name = None
            chart_positions = attrs.get('chartPositions', {})
            if 'appStore' in chart_positions:
                genre_name = chart_positions['appStore'].get('genreName')
            elif 'messages' in chart_positions:
                genre_name = chart_positions['messages'].get('genreName')

            if not genre_name:
                genre_name = attrs.get('genreDisplayName')

            if not genre_name:
                platform_attrs = attrs.get('platformAttributes', {})
                for platform, pattr in platform_attrs.items():
                    if 'genreDisplayName' in pattr:
                        genre_name = pattr['genreDisplayName']
                        break

            if genre_name and app_id:
                app_categories[app_id] = genre_name

        except Exception:
            continue

    return app_categories


def simplify_entity(domain):
    
    patterns = {
        'mixpanel': 'Mixpanel', 'amplitude': 'Amplitude', 'revenuecat': 'RevenueCat',
        'telemetrydeck': 'TelemetryDeck', 'firebase': 'Firebase', 'crashlytics': 'Firebase',
        'googleapis': 'Google APIs', 'google.com': 'Google', 'facebook': 'Facebook',
        'segment': 'Segment', 'braze': 'Braze', 'microsoft': 'Microsoft', 'office': 'Microsoft',
        'unity': 'Unity', 'icloud': 'Apple', 'apple.com': 'Apple', 'youtube': 'YouTube',
        'baidu': 'Baidu', 'disney': 'Disney', 'impact': 'Impact', 'dynamicyield': 'DynamicYield',
        'reddit': 'Reddit', 'customer.io': 'Customer.io', 'datadoghq': 'Datadog',
        'shopify': 'Shopify', 'ctrip': 'Ctrip', 'sentry': 'Sentry', 'branch': 'Branch',
        'appsflyer': 'AppsFlyer', 'adjust': 'Adjust', 'loggly': 'Loggly',
    }

    domain_lower = domain.lower()
    for p, name in patterns.items():
        if p in domain_lower:
            return name

    parts = domain.split('.')
    return parts[-2].capitalize() if len(parts) >= 2 else domain


PER_APP_JSONL_DIR = "/mnt/ssd2/VR_monkey/app_traffic_dataset_requests_v5/per_app_keyvals_jsonl"


def build_1st_party_detector():
    
    import glob as _glob

    KNOWN_3P_FOR_JSONL = [
        'revenuecat', 'telemetrydeck', 'mixpanel', 'amplitude', 'firebase', 'crashlytics',
        'googleapis', 'google.com', 'google-analytics', 'googlesyndication', 'googletagmanager',
        'googlevideo', 'gstatic', 'googleusercontent', 'doubleclick', 'googleadservices',
        'facebook', 'fb.com', 'segment.io', 'segment.com', 'braze', 'unity3d',
        'youtube.com', 'sentry', 'datadoghq', 'appsflyer', 'adjust.com',
        'branch.io', 'customer.io', 'shopify', 'reddit', 'dynamicyield',
        'impact.com', 'impactcdn', 'amazonaws', 'cloudfront', 'conviva',
        'liadm', 'akamaihd', 'akamaized', 'apple.com', 'icloud',
        'microsoft.com', 'office.com', 'officeapps', 'clarity.ms', 'bing.com',
        'linkedin', 'twitter', 'twimg', 'pinterest', 'snapchat', 'tiktok',
        'amazon', 'pubmatic', 'rubiconproject', 'demdex', 'openx',
        'adsrvr', 'tapad', 'sharethrough', 'bidswitch', 'outbrain',
        'media.net', 'gumgum', 'criteo', 'smartadserver', 'ipredictive',
        'dotomi', 'flashtalking', 'scorecardresearch', 'quantserve',
        'agkn', 'rfihub', 'everesttech', 'contentsquare', 'crwdcntrl',
        'onetrust', 'cookielaw', 'launchdarkly', 'bugsnag', 'newrelic',
        'nr-data', 'go-mpulse', 'akstat', 'medallia', 'paypal', 'stripe',
        'adapty', 'pawwalls', 'optimizely', 'qualtrics', 'gigya',
        'auth0', 'posthog', 'aptabase', 'plausible', 'cloudflare',
        'jsdelivr', 'featureassets', 'prodregistryv2', 'beyondwickedmapping',
        'digicert', 'comodoca', 'usertrust', 'yahoo', 'yimg', 'aol',
        'contentful', 'ctfassets', 'omtrdc', 'admanmedia', 'emxdgt',
        'lijit', 'contextweb', 'treasuredata', 'hsprotect', 'px-cloud',
        'cookieyes', 'privacymanager', 'wbdprivacy', 'trustcommander',
        'typekit', 'fonts.googleapis', 'fonts.gstatic', 'klaviyo',
        'hubspot', 'salesforce', 'gorgias', 'restockrocket', 'rebuyengine',
        'ocsp.', 'captive.apple', 'i.ytimg.com', 'yt3.ggpht', 'i1.ytimg',
        
        'wikimedia.org', 'wikipedia.org', 'wix.com', 'wixstatic', 'wixapps',
        'parastorage', 'squarespace', 'medium.com', 'cdn-client.medium',
        'noaa.gov', 'pypestream', 'radio-browser', 'apple-mapkit',
        '192.168.',  
    ]

    def _is_known_3p(domain):
        d = domain.lower()
        for p in KNOWN_3P_FOR_JSONL:
            if p in d:
                return True
        return False

    
    from collections import defaultdict
    domain_to_apps = defaultdict(set)  

    for jf in sorted(_glob.glob(os.path.join(PER_APP_JSONL_DIR, '*.jsonl'))):
        app_fname = os.path.basename(jf).replace('.jsonl', '')
        with open(jf) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    url = rec.get('url', '') or rec.get('request_url', '')
                    if '://' in url:
                        domain = url.split('://')[1].split('/')[0].split(':')[0]
                    else:
                        domain = url.split('/')[0].split(':')[0]
                    if domain and not _is_known_3p(domain):
                        domain_to_apps[domain].add(app_fname)
                except Exception:
                    pass

    
    
    unique_1p_domains = {}  
    for domain, apps in domain_to_apps.items():
        if len(apps) == 1:
            unique_1p_domains[domain] = list(apps)[0]

    
    app_1p_domains = defaultdict(set)
    for domain, app_fname in unique_1p_domains.items():
        app_name = app_fname.replace('_', ' ')
        app_1p_domains[app_name].add(domain)

    print(f"  Built 1st party map: {len(app_1p_domains)} apps, {len(unique_1p_domains)} unique domains")

    
    
    def is_1st_party(app_name, destination):
        
        if not isinstance(destination, str) or not isinstance(app_name, str):
            return False
        dest_lower = destination.lower().split(':')[0]  
        domains = app_1p_domains.get(app_name, set())
        for d in domains:
            if d.lower() in dest_lower or dest_lower in d.lower():
                return True
        return False

    return is_1st_party, app_1p_domains


def classify_violation_type(row):
    
    source = str(row.get('source', '')).lower()
    violation_type = str(row.get('violation_type', '')).lower()

    if source == 'policy':
        if violation_type == 'neglect_disclosure':
            return 'Omit Disclosure'
        elif violation_type == 'incorrect_disclosure':
            return 'Incorrect Disclosure'
        elif violation_type == 'mismatched_entity_disclosure':
            return 'Mismatched Entity Disclosure'

    elif source == 'label':
        if violation_type == 'neglect_disclosure':
            return 'Neglect Disclosure'
        elif violation_type == 'incorrect_disclosure':
            return 'Contrary Disclosure'

    elif source == 'manifest':
        if violation_type == 'neglect_disclosure':
            return 'Neglect Disclosure'
        elif violation_type in ('incorrect_disclosure', 'contrary_disclosure'):
            return 'Contrary Disclosure'

    return 'Neglect Disclosure'


def load_and_process_data():
    
    print("Loading violation data...")
    df_violations = pd.read_csv(VIOLATIONS_FILE)
    print(f"  Total violations: {len(df_violations)}")

    print("\nLoading data flows...")
    df_flows = pd.read_csv(DATA_FLOWS_FILE)
    print(f"  Total data flows: {len(df_flows)}")

    print("\nBuilding 1st party detector (from per-app JSONL)...")
    is_1st_party_fn, app_1p_domains = build_1st_party_detector()

    
    df_flows['entity'] = df_flows['destination'].apply(simplify_entity)
    df_flows['is_1st_party'] = df_flows.apply(
        lambda r: is_1st_party_fn(r['app'], r['destination']), axis=1
    )

    first_party_count = df_flows['is_1st_party'].sum()
    first_party_apps = df_flows[df_flows['is_1st_party']]['app'].nunique()
    print(f"  1st party flows: {first_party_count} from {first_party_apps} apps")

    
    print("\nExtracting app categories...")
    app_categories = extract_app_categories()
    print(f"  Found {len(app_categories)} app categories")

    
    app_id_to_name = dict(zip(df_flows['app_id'], df_flows['app']))
    df_violations['app_name'] = df_violations['app_id'].map(app_id_to_name)

    
    df_violations['app_id_str'] = df_violations['app_id'].astype(str)
    df_violations['category'] = df_violations['app_id_str'].map(app_categories).fillna('Other')

    
    
    rows_expanded = []
    for _, row in df_violations.iterrows():
        collected_type = str(row['collected_type'])
        if ',' in collected_type:
            
            types = [t.strip() for t in collected_type.split(',')]
            for t in types:
                new_row = row.copy()
                new_row['data_type'] = t
                rows_expanded.append(new_row)
        else:
            row_copy = row.copy()
            row_copy['data_type'] = collected_type
            rows_expanded.append(row_copy)

    df_violations = pd.DataFrame(rows_expanded)
    print(f"  After expanding comma-separated types: {len(df_violations)} rows")

    
    df_violations['data_type_category'] = df_violations['data_type'].apply(categorize_data_type)

    
    
    from collections import Counter, defaultdict
    key_entities = defaultdict(Counter)  
    key_has_1p = defaultdict(bool)  

    for _, row in df_flows.iterrows():
        key = (row['app_id'], row['data_type'])
        key_entities[key][row['entity']] += 1
        if row['is_1st_party']:
            key_has_1p[key] = True

    entity_map = {k: counter.most_common(1)[0][0] for k, counter in key_entities.items()}
    entity_1st_party_map = dict(key_has_1p)

    
    app_entity_counter = {}
    for _, row in df_flows.iterrows():
        aid = row['app_id']
        if aid not in app_entity_counter:
            app_entity_counter[aid] = Counter()
        app_entity_counter[aid][row['entity']] += 1

    def get_entity(row):
        aid = row['app_id']
        dtype = row['data_type']
        
        key = (aid, dtype)
        ent = entity_map.get(key)
        if ent:
            return ent
        
        normalized = normalize_data_type(dtype)
        if normalized != dtype:
            key2 = (aid, normalized)
            ent = entity_map.get(key2)
            if ent:
                return ent
        
        counter = app_entity_counter.get(aid)
        if counter:
            return counter.most_common(1)[0][0]
        return 'Unknown'

    def get_is_1st_party(row):
        
        aid = row['app_id']
        dtype = row['data_type']
        key = (aid, dtype)
        if key in entity_1st_party_map:
            return entity_1st_party_map[key]
        
        normalized = normalize_data_type(dtype)
        if normalized != dtype:
            key2 = (aid, normalized)
            if key2 in entity_1st_party_map:
                return entity_1st_party_map[key2]
        
        app_name = row.get('app_name', '')
        entity = get_entity(row)
        if app_name and entity != 'Unknown':
            
            return is_1st_party_fn(app_name, entity)
        return False

    df_violations['entity'] = df_violations.apply(get_entity, axis=1)
    df_violations['entity_is_1st_party'] = df_violations.apply(get_is_1st_party, axis=1)

    
    before_count = len(df_violations)
    df_violations = df_violations[df_violations['entity'] != 'Unknown']
    after_count = len(df_violations)
    print(f"  After filtering unknown entities: {after_count} (removed {before_count - after_count})")

    
    df_violations['violation_type_classified'] = df_violations.apply(classify_violation_type, axis=1)
    df_violations['source_violation'] = (
        df_violations['source'].str.title() + ': ' + df_violations['violation_type_classified']
    )

    print(f"\nProcessed data:")
    print(f"  Total violations: {len(df_violations)}")
    print(f"  Unique apps: {df_violations['app_id'].nunique()}")
    print(f"  Unique categories: {df_violations['category'].nunique()}")
    print(f"  Unique data type categories: {df_violations['data_type_category'].nunique()}")
    print(f"  1st party violations: {df_violations['entity_is_1st_party'].sum()}")

    print(f"\nData Type Category distribution:")
    print(df_violations['data_type_category'].value_counts())

    print(f"\nSource + Violation Type distribution:")
    print(df_violations['source_violation'].value_counts())

    print(f"\n1st party entity distribution:")
    first_party_v = df_violations[df_violations['entity_is_1st_party']]
    if len(first_party_v) > 0:
        print(first_party_v['entity'].value_counts())
    else:
        print("  (none)")

    return df_violations


def create_sankey(df):
    

    
    print("\nMerging small categories and entities...")
    df = df.copy()

    
    TOP_N_CATEGORIES = 10
    cat_counts_raw = df['category'].value_counts()
    top_categories = cat_counts_raw.head(TOP_N_CATEGORIES).index.tolist()
    cats_to_merge = [c for c in cat_counts_raw.index if c not in top_categories]
    print(f"  App categories: {len(cat_counts_raw)}, keeping top {TOP_N_CATEGORIES}, merging {len(cats_to_merge)} into 'Other'")
    df.loc[df['category'].isin(cats_to_merge), 'category'] = 'Other'

    df['entity_merged'] = df['entity'].copy()

    
    df.loc[df['entity_is_1st_party'] == True, 'entity_merged'] = '1st Party'

    
    FORCE_MERGE_ENTITIES = {'Microsoft', 'Apple', 'YouTube', 'Disney', 'Segment', 'Braze', 'Datadog'}
    df.loc[df['entity_merged'].isin(FORCE_MERGE_ENTITIES), 'entity_merged'] = 'Other 3rd Party'

    
    TOP_N_ENTITIES = 8
    third_party_entities = df[(df['entity_is_1st_party'] == False) & (df['entity_merged'] != 'Other 3rd Party')]['entity_merged'].value_counts()
    top_entities = third_party_entities.head(TOP_N_ENTITIES).index.tolist()
    entities_to_merge = [e for e in third_party_entities.index if e not in top_entities]
    print(f"  3rd party entities: {len(third_party_entities)}")
    print(f"  Keeping top {TOP_N_ENTITIES}, merging {len(entities_to_merge)} into 'Other 3rd Party'")
    df.loc[df['entity_merged'].isin(entities_to_merge), 'entity_merged'] = 'Other 3rd Party'

    
    category_counts = df['category'].value_counts()
    source_violation_counts = df['source_violation'].value_counts()
    dtype_cat_counts = df['data_type_category'].value_counts()
    entity_counts = df['entity_merged'].value_counts()

    
    all_combinations = [
        'Policy: Omit Disclosure',
        'Policy: Incorrect Disclosure',
        'Policy: Mismatched Entity Disclosure',
        'Label: Neglect Disclosure',
        'Label: Contrary Disclosure',
        'Manifest: Neglect Disclosure',
        'Manifest: Contrary Disclosure'
    ]
    for combo in all_combinations:
        if combo not in source_violation_counts.index:
            source_violation_counts[combo] = 0

    
    categories = category_counts.index.tolist()
    
    if 'Other' in categories:
        categories.remove('Other')
        categories.append('Other')

    source_violations = sorted(
        [c for c in all_combinations if source_violation_counts.get(c, 0) > 0],
        key=lambda x: -source_violation_counts.get(x, 0)
    )

    dtype_cats = dtype_cat_counts.index.tolist()  

    entities = entity_counts.index.tolist()
    
    if 'Other 3rd Party' in entities:
        entities.remove('Other 3rd Party')
        entities.append('Other 3rd Party')

    
    nodes = []
    colors = []

    
    category_colors = [
        '#1f77b4', '#2ca02c', '#ff7f0e', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
    ]

    for i, cat in enumerate(categories):
        cnt = category_counts[cat]
        nodes.append(f"{cat} ({cnt})")
        colors.append(category_colors[i % len(category_colors)])

    cat_idx = {c: i for i, c in enumerate(categories)}

    
    sv_start = len(categories)
    source_violation_colors = {
        'Policy: Omit Disclosure': '#95E1D3',
        'Policy: Incorrect Disclosure': '#F38181',
        'Policy: Mismatched Entity Disclosure': '#FFA07A',
        'Label: Neglect Disclosure': '#4ECDC4',
        'Label: Contrary Disclosure': '#FF6B6B',
        'Manifest: Neglect Disclosure': '#AA96DA',
        'Manifest: Incorrect Disclosure': '#C9B1FF',
    }

    for sv in source_violations:
        cnt = source_violation_counts[sv]
        nodes.append(f"{sv} ({cnt})")
        colors.append(source_violation_colors.get(sv, '#CCCCCC'))

    sv_idx = {sv: sv_start + i for i, sv in enumerate(source_violations)}

    
    dtype_start = sv_start + len(source_violations)
    
    dtype_cat_colors = {
        'account': '#FFD54F',        
        'identifier': '#81C784',     
        'device info': '#64B5F6',    
        'sensor': '#FF8A65',         
        'usage info': '#CE93D8',     
        'biometric': '#EF5350',      
    }

    for dc in dtype_cats:
        cnt = dtype_cat_counts[dc]
        nodes.append(f"{dc} ({cnt})")
        colors.append(dtype_cat_colors.get(dc, '#BDBDBD'))

    dc_idx = {dc: dtype_start + i for i, dc in enumerate(dtype_cats)}

    
    entity_start = dtype_start + len(dtype_cats)
    for ent in entities:
        cnt = entity_counts[ent]
        nodes.append(f"{ent} ({cnt})")
        if ent == '1st Party':
            colors.append('#42A5F5')  
        elif ent == 'Other 3rd Party':
            colors.append('#FFAB91')  
        else:
            colors.append('#EF5350')  

    ent_idx = {e: entity_start + i for i, e in enumerate(entities)}

    
    sources, targets, values, link_colors = [], [], [], []

    
    for (cat, sv), grp in df.groupby(['category', 'source_violation']):
        if cat in cat_idx and sv in sv_idx:
            sources.append(cat_idx[cat])
            targets.append(sv_idx[sv])
            values.append(len(grp))
            link_colors.append('rgba(31, 119, 180, 0.35)')

    
    for (sv, dc), grp in df.groupby(['source_violation', 'data_type_category']):
        if sv in sv_idx and dc in dc_idx:
            sources.append(sv_idx[sv])
            targets.append(dc_idx[dc])
            values.append(len(grp))
            if 'Contrary' in sv:
                link_colors.append('rgba(255, 107, 107, 0.5)')
            elif 'Neglect' in sv or 'Omit' in sv:
                link_colors.append('rgba(78, 205, 196, 0.5)')
            elif 'Incorrect' in sv:
                link_colors.append('rgba(255, 230, 109, 0.5)')
            elif 'Mismatched' in sv:
                link_colors.append('rgba(255, 160, 122, 0.5)')
            else:
                link_colors.append('rgba(200, 200, 200, 0.4)')

    
    for (dc, ent), grp in df.groupby(['data_type_category', 'entity_merged']):
        if dc in dc_idx and ent in ent_idx:
            sources.append(dc_idx[dc])
            targets.append(ent_idx[ent])
            values.append(len(grp))
            if ent == '1st Party':
                link_colors.append('rgba(66, 165, 245, 0.5)')  
            else:
                link_colors.append('rgba(239, 83, 80, 0.4)')  

    
    node_x = []
    node_y = []
    x_positions = [0.01, 0.30, 0.62, 0.99]  

    def assign_y_positions(items, count_dict, x_col):
        
        n = len(items)
        for i, item in enumerate(items):
            node_x.append(x_positions[x_col])
            
            if n == 1:
                node_y.append(0.5)
            else:
                node_y.append(0.01 + i * 0.98 / (n - 1))

    assign_y_positions(categories, category_counts, 0)
    assign_y_positions(source_violations, source_violation_counts, 1)
    assign_y_positions(dtype_cats, dtype_cat_counts, 2)
    assign_y_positions(entities, entity_counts, 3)

    return {
        'nodes': nodes,
        'colors': colors,
        'node_x': node_x,
        'node_y': node_y,
        'sources': sources,
        'targets': targets,
        'values': values,
        'link_colors': link_colors,
        'stats': {
            'categories': len(categories),
            'source_violations': len(source_violations),
            'dtype_categories': len(dtype_cats),
            'entities': len(entities),
        }
    }


def create_figure(data, total_violations, n_apps):
    

    fig = go.Figure(go.Sankey(
        arrangement='snap',
        node=dict(
            pad=12,
            thickness=18,
            line=dict(color='#333', width=0.5),
            label=data['nodes'],
            color=data['colors'],
            x=data['node_x'],
            y=data['node_y'],
            hovertemplate='%{label}<extra></extra>'
        ),
        link=dict(
            source=data['sources'],
            target=data['targets'],
            value=data['values'],
            color=data['link_colors'],
            hovertemplate='%{source.label} → %{target.label}<br>%{value} violations<extra></extra>'
        )
    ))

    
    fig.update_layout(
        title=dict(text='', font=dict(size=1)),
        font=dict(size=11, family='Times New Roman'),
        height=700,
        width=1400,
        paper_bgcolor='white',
        margin=dict(l=5, r=5, t=50, b=60)
    )

    
    headers = [
        (0.01, '<b>App Category</b>'),
        (0.30, '<b>Violation Type</b>'),
        (0.62, '<b>Data Type</b>'),
        (0.99, '<b>Destination</b>')
    ]
    for x, txt in headers:
        fig.add_annotation(x=x, y=1.04, xref='paper', yref='paper',
                          text=txt, showarrow=False, font=dict(size=12, family='Times New Roman'))

    
    legend = (
        "<b>Link Colors:</b> &nbsp;"
        "<span style='color:#4ECDC4'>━</span> Neglect/Omit &nbsp;&nbsp;"
        "<span style='color:#FF6B6B'>━</span> Contrary &nbsp;&nbsp;"
        "<span style='color:#FFE66D'>━</span> Incorrect &nbsp;&nbsp;"
        "<span style='color:#FFA07A'>━</span> Mismatched Entity &nbsp;&nbsp;"
        "<span style='color:#42A5F5'>━</span> 1st Party &nbsp;&nbsp;"
        "<span style='color:#EF5350'>━</span> 3rd Party"
    )
    fig.add_annotation(x=0.5, y=-0.05, xref='paper', yref='paper',
                      text=legend, showarrow=False, font=dict(size=10, family='Times New Roman'), align='center')

    return fig


def main():
    df = load_and_process_data()

    print(f"\n{'='*60}")
    print("Creating 4-column Sankey diagram (V2)...")
    print(f"{'='*60}")

    sankey_data = create_sankey(df)

    print(f"\nNode statistics:")
    print(f"  Categories: {sankey_data['stats']['categories']}")
    print(f"  Source+Violation Types: {sankey_data['stats']['source_violations']}")
    print(f"  Data Type Categories: {sankey_data['stats']['dtype_categories']}")
    print(f"  Entities: {sankey_data['stats']['entities']}")
    print(f"  Total nodes: {len(sankey_data['nodes'])}")
    print(f"  Total links: {len(sankey_data['sources'])}")

    fig = create_figure(sankey_data, len(df), df['app_id'].nunique())

    fig.write_html(OUTPUT_HTML)
    print(f"\nSaved to: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
