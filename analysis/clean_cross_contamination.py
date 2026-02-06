#!/usr/bin/env python3
"""
清洗 data_flows_with_appid.csv 中的交叉污染流量。

策略:
1. 从 per-app JSONL 文件中找出每个 app 的 unique domain（仅出现在该 app 的 JSONL 中）
2. 对 data_flows_with_appid.csv 中的每条记录:
   - 如果 destination 匹配某个 app X 的 unique domain，但当前记录的 app 不是 X
     → 这是交叉污染，移除
   - 如果 destination 匹配当前 app 的 unique domain → 确认是 1st party，保留
   - 其他情况 → 保留（3rd party 或未知）
3. 输出清洗后的 CSV
"""

import json
import os
import glob
import pandas as pd
from collections import defaultdict

# ==================== 配置 ====================
PER_APP_JSONL_DIR = "/mnt/ssd2/VR_monkey/app_traffic_dataset_requests_v5/per_app_keyvals_jsonl"
INPUT_FILE = "/mnt/ssd2/VR_monkey/ppaudit_analysis/data_flows_output_v2/data_flows_with_appid.csv"
OUTPUT_FILE = "/mnt/ssd2/VR_monkey/ppaudit_analysis/data_flows_output_v2/data_flows_with_appid_cleaned.csv"

# 已知 3rd party 服务 — 不参与 unique domain 判定
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
    """从 URL 或 destination 提取 base domain。"""
    s = str(url_or_dest).lower()
    if '://' in s:
        s = s.split('://')[1]
    s = s.split('/')[0].split(':')[0]
    return s


def build_unique_domain_map():
    """
    扫描所有 per-app JSONL，找出每个 domain 出现在哪些 app 中。
    返回: unique_domain → owner_app_name 的映射（仅包含只出现在 1 个 app 中的 domain）
    """
    print("Step 1: 扫描 per-app JSONL 文件...")
    domain_to_apps = defaultdict(set)

    jsonl_files = sorted(glob.glob(os.path.join(PER_APP_JSONL_DIR, '*.jsonl')))
    print(f"  找到 {len(jsonl_files)} 个 per-app JSONL 文件")

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

    # 找 unique domains（只出现在 1 个 app 中的）
    unique_map = {}
    for domain, apps in domain_to_apps.items():
        if len(apps) == 1:
            unique_map[domain] = list(apps)[0]

    # 统计
    shared_2 = sum(1 for apps in domain_to_apps.values() if len(apps) == 2)
    shared_many = sum(1 for apps in domain_to_apps.values() if len(apps) > 2)
    print(f"  总 non-3P domains: {len(domain_to_apps)}")
    print(f"  Unique to 1 app: {len(unique_map)}")
    print(f"  Shared by 2 apps: {shared_2}")
    print(f"  Shared by 3+ apps: {shared_many}")

    # 按 app 汇总
    app_unique_count = defaultdict(int)
    for domain, app in unique_map.items():
        app_unique_count[app] += 1
    apps_with_unique = len(app_unique_count)
    print(f"  Apps with unique domains: {apps_with_unique}")

    return unique_map, domain_to_apps


def clean_data_flows(unique_domain_map):
    """
    清洗 data_flows_with_appid.csv:
    - 如果 destination 的 domain 匹配某 app X 的 unique domain，但当前 app 不是 X → 移除
    """
    print(f"\nStep 2: 清洗 data flows...")
    df = pd.read_csv(INPUT_FILE)
    print(f"  原始行数: {len(df)}")

    # 预处理: 为每条 flow 提取 destination domain
    df['dest_domain'] = df['destination'].apply(extract_domain)

    # 构建 domain → owner lookup，支持子域匹配
    # 对于 data_flows 中的 destination (如 publishers.biltapp.com)
    # 需要匹配 unique_domain_map 中的 domain (如 publishers.biltapp.com)
    # 用精确匹配 + 子域匹配

    removed_rows = []
    kept_rows = []
    contamination_stats = defaultdict(lambda: defaultdict(int))  # victim_app -> {contam_source_app: count}

    for idx, row in df.iterrows():
        dest = row['dest_domain']
        app = row['app']

        # 检查是否匹配某个 unique domain
        owner = unique_domain_map.get(dest)

        if owner and owner != app:
            # 交叉污染！这个 destination 属于另一个 app
            removed_rows.append(idx)
            contamination_stats[app][owner] += 1
        else:
            # 也检查子域: dest 可能是 xxx.biltapp.com，unique domain 可能是 publishers.biltapp.com
            # 或反过来，unique domain 可能是 biltapp.com，dest 是 publishers.biltapp.com
            found_contam = False
            for unique_domain, unique_owner in unique_domain_map.items():
                if unique_owner == app:
                    continue
                # 检查是否有包含关系（子域匹配）
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
    df_removed = df.loc[removed_rows]

    print(f"  移除行数: {len(removed_rows)} ({100*len(removed_rows)/len(df):.1f}%)")
    print(f"  保留行数: {len(kept_rows)}")

    # 受影响的 app
    affected_apps = df_removed['app'].nunique()
    print(f"  受影响的 apps: {affected_apps}")

    # Top contamination sources
    print(f"\n  Top 污染来源 (destination 属于哪个 app 但出现在其他 app 中):")
    source_counts = defaultdict(int)
    for victim, sources in contamination_stats.items():
        for source, count in sources.items():
            source_counts[source] += count
    for source, count in sorted(source_counts.items(), key=lambda x: -x[1])[:15]:
        victims = sum(1 for v in contamination_stats.values() if source in v)
        print(f"    {source}: {count} flows 污染了 {victims} 个 app")

    # Top 受害者
    print(f"\n  Top 受害 app (被移除最多 flows 的):")
    victim_counts = {app: sum(sources.values()) for app, sources in contamination_stats.items()}
    for app, count in sorted(victim_counts.items(), key=lambda x: -x[1])[:15]:
        sources_str = ', '.join(f"{s}({c})" for s, c in
                                sorted(contamination_stats[app].items(), key=lambda x: -x[1])[:3])
        print(f"    {app}: -{count} flows (来自: {sources_str})")

    return df_cleaned


def main():
    print("=" * 60)
    print("清洗 data_flows_with_appid.csv 中的交叉污染流量")
    print("=" * 60)

    unique_domain_map, domain_to_apps = build_unique_domain_map()
    df_cleaned = clean_data_flows(unique_domain_map)

    # 保存
    df_cleaned.to_csv(OUTPUT_FILE, index=False)
    print(f"\n已保存清洗后的数据到: {OUTPUT_FILE}")

    # 对比统计
    df_orig = pd.read_csv(INPUT_FILE)
    print(f"\n{'='*60}")
    print("清洗前后对比:")
    print(f"{'='*60}")
    print(f"  原始 flows: {len(df_orig):,}")
    print(f"  清洗后 flows: {len(df_cleaned):,}")
    print(f"  移除: {len(df_orig) - len(df_cleaned):,} ({100*(len(df_orig)-len(df_cleaned))/len(df_orig):.1f}%)")
    print(f"  原始 unique apps: {df_orig['app'].nunique()}")
    print(f"  清洗后 unique apps: {df_cleaned['app'].nunique()}")
    print(f"  原始 unique destinations: {df_orig['destination'].nunique()}")
    print(f"  清洗后 unique destinations: {df_cleaned['destination'].nunique()}")

    # Per-app 统计变化
    print(f"\n  Per-app flow count 变化 (变化最大的):")
    orig_counts = df_orig.groupby('app').size()
    clean_counts = df_cleaned.groupby('app').size()
    diff = (orig_counts - clean_counts.reindex(orig_counts.index, fill_value=0)).sort_values(ascending=False)
    for app in diff.head(20).index:
        o = orig_counts.get(app, 0)
        c = clean_counts.get(app, 0)
        if o > c:
            print(f"    {app}: {o} → {c} (-{o-c}, {100*(o-c)/o:.0f}%)")


if __name__ == "__main__":
    main()
