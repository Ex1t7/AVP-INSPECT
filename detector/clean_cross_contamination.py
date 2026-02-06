


import json
import os
import glob
import pandas as pd
from collections import defaultdict


PER_APP_JSONL_DIR = "/mnt/ssd2/VR_monkey/app_traffic_dataset_requests_v5/per_app_keyvals_jsonl"
INPUT_FILE = "/mnt/ssd2/VR_monkey/ppaudit_analysis/data_flows_output_v2/data_flows_with_appid.csv"
OUTPUT_FILE = "/mnt/ssd2/VR_monkey/ppaudit_analysis/data_flows_output_v2/data_flows_with_appid_cleaned.csv"


KNOWN_3P_PATTERNS = [
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
]


def is_known_3p(domain):
    d = domain.lower()
    for p in KNOWN_3P_PATTERNS:
        if p in d:
            return True
    return False


def extract_domain(url_or_dest):
    
    s = str(url_or_dest).lower()
    if '://' in s:
        s = s.split('://')[1]
    s = s.split('/')[0].split(':')[0]
    return s


def build_unique_domain_map():

    domain_to_apps = defaultdict(set)

    jsonl_files = sorted(glob.glob(os.path.join(PER_APP_JSONL_DIR, '*.jsonl')))

    for jf in jsonl_files:
        app_fname = os.path.basename(jf).replace('.jsonl', '')
        app_name = app_fname.replace('_', ' ')

        with open(jf) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    url = rec.get('url', '') or rec.get('request_url', '')
                    domain = extract_domain(url)
                    if domain and not is_known_3p(domain):
                        domain_to_apps[domain].add(app_name)
                except Exception:
                    pass

    
    unique_map = {}
    for domain, apps in domain_to_apps.items():
        if len(apps) == 1:
            unique_map[domain] = list(apps)[0]

    return unique_map, domain_to_apps


def clean_data_flows(unique_domain_map):

    df = pd.read_csv(INPUT_FILE)

    
    df['dest_domain'] = df['destination'].apply(extract_domain)

    
    
    
    

    removed_rows = []
    kept_rows = []
    contamination_stats = defaultdict(lambda: defaultdict(int))  

    for idx, row in df.iterrows():
        dest = row['dest_domain']
        app = row['app']

        
        owner = unique_domain_map.get(dest)

        if owner and owner != app:
            
            removed_rows.append(idx)
            contamination_stats[app][owner] += 1
        else:
            
            
            found_contam = False
            for unique_domain, unique_owner in unique_domain_map.items():
                if unique_owner == app:
                    continue
                
                if (dest.endswith('.' + unique_domain) or
                    unique_domain.endswith('.' + dest) or
                    dest == unique_domain):
                    removed_rows.append(idx)
                    contamination_stats[app][unique_owner] += 1
                    found_contam = True
                    break

            if not found_contam:
                kept_rows.append(idx)

    df_cleaned = df.loc[kept_rows].drop(columns=['dest_domain'])

    return df_cleaned


def main():
    unique_domain_map, domain_to_apps = build_unique_domain_map()
    df_cleaned = clean_data_flows(unique_domain_map)
    df_cleaned.to_csv(OUTPUT_FILE, index=False)


if __name__ == "__main__":
    main()
