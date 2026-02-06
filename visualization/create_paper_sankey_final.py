


import pandas as pd
import plotly.graph_objects as go
from collections import defaultdict
import json


INPUT_FILE = "/mnt/ssd2/VR_monkey/ppaudit_analysis/data_flows_output_v2/data_flows_with_appid.csv"
OUTPUT_FILE = "/mnt/ssd2/VR_monkey/ppaudit_analysis/paper_sankey_final.html"


TOP_N_APPS = 12
TOP_N_DATA_TYPES = 20
TOP_N_DESTINATIONS = 15



PII_SENSORY_DATA = {
    'user id', 'email addr', 'person name', 'phone num', 'password',
    'account', 'pii', 'ethnic', 'biographical', 'education', 'billing',
    'employment', 'face', 'body measure', 'height', 'health biometric',
    'truedepth data', 'facial expression', 'face biometric',
    'eye tracking data', 'gaze data', 'hand tracking data',
    'geo location', 'ip addr', 'message log',
    
    'surrounding environment', '3d model', 'spatial map', 'spatial content'
}


FINGERPRINTING_DATA = {
    'device id', 'device info', 'ad id', 'identifier', 'model',
    'manufacturer', 'system ver', 'app ver', 'build', 'sdk ver',
    'language', 'browser type', 'screen', 'network', 'type'
}


DESTINATION_PURPOSE = {
    
    'mixpanel': 'analytics',
    'amplitude': 'analytics', 
    'firebase': 'analytics',
    'crashlytics': 'analytics',
    'segment': 'analytics',
    'telemetrydeck': 'analytics',
    'braze': 'analytics',
    'customer.io': 'analytics',
    'datadoghq': 'analytics',
    'sentry': 'analytics',
    'newrelic': 'analytics',
    'loggly': 'analytics',
    'analytics': 'analytics',
    
    
    'facebook': 'advertising',
    'fb.com': 'advertising',
    'doubleclick': 'advertising',
    'googlesyndication': 'advertising',
    'googleadservices': 'advertising',
    'appsflyer': 'advertising',
    'adjust.com': 'advertising',
    'unity3d': 'advertising',
    'unity': 'advertising',
    'admob': 'advertising',
    'mopub': 'advertising',
    
    
    'impact.com': 'marketing',
    'dynamicyield': 'marketing',
    'branch': 'marketing',
    'kochava': 'marketing',
    
    
    'googleapis': 'first party',
    'icloud': 'first party',
    'apple.com': 'first party',
    'microsoft': 'first party',
    'office': 'first party',
    
    
    'revenuecat': 'additional feature',
    'shopify': 'additional feature',
    'stripe': 'additional feature',
    
    
    'youtube': 'basic feature',
    'spotify': 'basic feature',
    'disney': 'basic feature',
    'nba.com': 'basic feature',
    'baidu': 'basic feature',
    'ctrip': 'basic feature',
    'decathlon': 'basic feature',
    
    
    'recaptcha': 'security',
    'captcha': 'security',
    
    
    'legal': 'legal',
    'privacy': 'legal',
    'terms': 'legal',
    
    
    'personali': 'personalization',
    'recommend': 'personalization',
}


def classify_purpose(dest):
    
    dest_lower = dest.lower()
    
    for pattern, purpose in DESTINATION_PURPOSE.items():
        if pattern in dest_lower:
            return purpose
    
    
    if any(x in dest_lower for x in ['analytic', 'metric', 'track', 'log', 'telemetry']):
        return 'analytics'
    elif any(x in dest_lower for x in ['ad', 'market', 'campaign']):
        return 'advertising'
    
    return 'other'


def simplify_destination(dest):
    
    entity_patterns = {
        'mixpanel': 'Mixpanel',
        'amplitude': 'Amplitude', 
        'revenuecat': 'RevenueCat',
        'telemetrydeck': 'TelemetryDeck',
        'firebase': 'Firebase',
        'crashlytics': 'Firebase',
        'googleapis': 'Google APIs',
        'google.com': 'Google',
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
        'sentry': 'Sentry',
        'branch': 'Branch',
        'appsflyer': 'AppsFlyer',
        'adjust': 'Adjust',
    }
    
    dest_lower = dest.lower()
    for pattern, name in entity_patterns.items():
        if pattern in dest_lower:
            return name
    
    
    parts = dest.split('.')
    if len(parts) >= 2:
        return parts[-2].capitalize()
    return dest


def classify_data_type_color(dtype):
    
    dtype_lower = dtype.lower().strip()
    
    if dtype_lower in PII_SENSORY_DATA:
        return 'pii'  
    elif dtype_lower in FINGERPRINTING_DATA:
        return 'fingerprint'  
    else:
        return 'other'


def load_and_process_data():
    
    print("Loading data...")
    df = pd.read_csv(INPUT_FILE)
    
    
    df['entity'] = df['destination'].apply(simplify_destination)
    df['data_color'] = df['data_type'].apply(classify_data_type_color)
    df['purpose'] = df['destination'].apply(classify_purpose)
    
    print(f"Total data flows: {len(df)}")
    print(f"Unique apps: {df['app'].nunique()}")
    print(f"Unique data types: {df['data_type'].nunique()}")
    print(f"Unique destinations: {df['destination'].nunique()}")
    print(f"Unique entities: {df['entity'].nunique()}")
    
    return df


def aggregate_small_apps(df, top_n):
    
    app_counts = df['app'].value_counts()
    top_apps = app_counts.head(top_n).index.tolist()
    
    
    df['app_display'] = df['app'].apply(
        lambda x: x if x in top_apps else 'Other Apps'
    )
    return df, top_apps


def create_sankey_data(df):
    
    
    
    
    app_counts = df.groupby('app_display').size().sort_values(ascending=False)
    apps_list = app_counts.index.tolist()
    if 'Other Apps' in apps_list:
        apps_list.remove('Other Apps')
        apps_list.append('Other Apps')
    
    
    dtype_counts = df['data_type'].value_counts().head(TOP_N_DATA_TYPES)
    dtypes_list = dtype_counts.index.tolist()
    
    
    entity_counts = df['entity'].value_counts().head(TOP_N_DESTINATIONS)
    entities_list = entity_counts.index.tolist()
    
    
    purpose_order = ['advertising', 'analytics', 'marketing', 'additional feature', 
                     'basic feature', 'first party', 'personalization', 'security', 'legal', 'other']
    purpose_counts = df['purpose'].value_counts()
    purposes_list = [p for p in purpose_order if p in purpose_counts.index]
    
    
    nodes = []
    node_colors = []
    
    
    for app in apps_list:
        count = app_counts.get(app, 0)
        display = app[:22] + '..' if len(app) > 24 else app
        nodes.append(f"{display} {count}")
        node_colors.append('#4169E1')  
    
    app_idx = {a: i for i, a in enumerate(apps_list)}
    
    
    dtype_start = len(apps_list)
    dtype_colors_map = {
        'pii': '#FFD54F',       
        'fingerprint': '#81C784',  
        'other': '#90CAF9'      
    }
    
    for dtype in dtypes_list:
        count = dtype_counts.get(dtype, 0)
        nodes.append(f"{dtype} {count}")
        color_cat = classify_data_type_color(dtype)
        node_colors.append(dtype_colors_map.get(color_cat, '#90CAF9'))
    
    dtype_idx = {d: dtype_start + i for i, d in enumerate(dtypes_list)}
    
    
    entity_start = dtype_start + len(dtypes_list)
    first_party_entities = {'Google APIs', 'Apple', 'Microsoft'}
    
    for entity in entities_list:
        count = entity_counts.get(entity, 0)
        nodes.append(f"{entity} {count}")
        if entity in first_party_entities:
            node_colors.append('#64B5F6')  
        else:
            node_colors.append('#E57373')  
    
    entity_idx = {e: entity_start + i for i, e in enumerate(entities_list)}
    
    
    purpose_start = entity_start + len(entities_list)
    purpose_colors = {
        'advertising': '#EF5350',      
        'analytics': '#EC407A',        
        'marketing': '#AB47BC',        
        'additional feature': '#7E57C2',  
        'basic feature': '#42A5F5',    
        'first party': '#26A69A',      
        'personalization': '#66BB6A',  
        'security': '#78909C',         
        'legal': '#8D6E63',            
        'other': '#BDBDBD',            
    }
    
    for purpose in purposes_list:
        count = purpose_counts.get(purpose, 0)
        display_name = purpose.title()
        nodes.append(f"{display_name} {count}")
        node_colors.append(purpose_colors.get(purpose, '#BDBDBD'))
    
    purpose_idx = {p: purpose_start + i for i, p in enumerate(purposes_list)}
    
    
    sources = []
    targets = []
    values = []
    link_colors = []
    
    
    link_color_map = {
        'app_dtype': 'rgba(65, 105, 225, 0.35)',  
        'pii': 'rgba(255, 167, 38, 0.5)',          
        'fingerprint': 'rgba(102, 187, 106, 0.5)', 
        'other': 'rgba(144, 202, 249, 0.35)',      
        '1st_party': 'rgba(66, 165, 245, 0.5)',   
        '3rd_party': 'rgba(239, 83, 80, 0.5)',    
    }
    
    
    app_dtype_grp = df.groupby(['app_display', 'data_type']).size().reset_index(name='count')
    for _, row in app_dtype_grp.iterrows():
        if row['app_display'] in app_idx and row['data_type'] in dtype_idx:
            sources.append(app_idx[row['app_display']])
            targets.append(dtype_idx[row['data_type']])
            values.append(row['count'])
            link_colors.append(link_color_map['app_dtype'])
    
    
    dtype_entity_grp = df.groupby(['data_type', 'entity', 'data_color']).size().reset_index(name='count')
    for _, row in dtype_entity_grp.iterrows():
        if row['data_type'] in dtype_idx and row['entity'] in entity_idx:
            sources.append(dtype_idx[row['data_type']])
            targets.append(entity_idx[row['entity']])
            values.append(row['count'])
            link_colors.append(link_color_map.get(row['data_color'], link_color_map['other']))
    
    
    entity_purpose_grp = df.groupby(['entity', 'purpose']).size().reset_index(name='count')
    for _, row in entity_purpose_grp.iterrows():
        if row['entity'] in entity_idx and row['purpose'] in purpose_idx:
            sources.append(entity_idx[row['entity']])
            targets.append(purpose_idx[row['purpose']])
            values.append(row['count'])
            if row['entity'] in first_party_entities:
                link_colors.append(link_color_map['1st_party'])
            else:
                link_colors.append(link_color_map['3rd_party'])
    
    return {
        'labels': nodes,
        'colors': node_colors,
        'sources': sources,
        'targets': targets,
        'values': values,
        'link_colors': link_colors,
        'stats': {
            'apps': len(apps_list),
            'dtypes': len(dtypes_list),
            'entities': len(entities_list),
            'purposes': len(purposes_list),
            'total_links': len(sources)
        }
    }


def create_figure(data, total_flows):
    
    
    fig = go.Figure(data=[go.Sankey(
        arrangement='snap',
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color='#333', width=0.5),
            label=data['labels'],
            color=data['colors'],
            hovertemplate='%{label}<extra></extra>'
        ),
        link=dict(
            source=data['sources'],
            target=data['targets'],
            value=data['values'],
            color=data['link_colors'],
            hovertemplate='%{source.label} → %{target.label}<br>Flows: %{value}<extra></extra>'
        )
    )])
    
    fig.update_layout(
        title=dict(
            text=f"<b>Data Flows in visionOS Apps</b><br><sup>Total: {total_flows:,} data flows from {data['stats']['apps']} apps</sup>",
            font=dict(size=18, family='Arial, sans-serif'),
            x=0.5, y=0.98
        ),
        font=dict(size=10, family='Arial, sans-serif'),
        height=1000,
        width=1600,
        paper_bgcolor='#FAFAFA',
        margin=dict(l=20, r=20, t=90, b=100)
    )
    
    
    headers = [
        (0.07, '<b>App</b>'),
        (0.33, '<b>Data Type</b>'),
        (0.62, '<b>Destination (Entity)</b>'),
        (0.92, '<b>Purpose</b>')
    ]
    for x, text in headers:
        fig.add_annotation(x=x, y=1.04, xref='paper', yref='paper',
                          text=text, showarrow=False, font=dict(size=13))
    
    
    legend = """
<b>Link Colors:</b> &nbsp;
<span style="color:#4169E1">━</span> App Store &nbsp;&nbsp;
<span style="color:#FFA726">━</span> PII/Sensory Data &nbsp;&nbsp;
<span style="color:#66BB6A">━</span> Fingerprinting &nbsp;&nbsp;
<span style="color:#42A5F5">━</span> 1st Party &nbsp;&nbsp;
<span style="color:#EF5350">━</span> 3rd Party
"""
    fig.add_annotation(x=0.5, y=-0.07, xref='paper', yref='paper',
                      text=legend, showarrow=False, font=dict(size=11), align='center')
    
    return fig


def main():
    df = load_and_process_data()
    
    
    df, top_apps = aggregate_small_apps(df, TOP_N_APPS)
    
    
    sankey_data = create_sankey_data(df)
    
    print(f"\nSankey stats:")
    print(f"  Apps: {sankey_data['stats']['apps']}")
    print(f"  Data Types: {sankey_data['stats']['dtypes']}")
    print(f"  Entities: {sankey_data['stats']['entities']}")
    print(f"  Purposes: {sankey_data['stats']['purposes']}")
    print(f"  Total links: {sankey_data['stats']['total_links']}")
    
    
    fig = create_figure(sankey_data, len(df))
    fig.write_html(OUTPUT_FILE)
    print(f"\n✅ Final Sankey saved to: {OUTPUT_FILE}")
    
    
    print("\n" + "="*60)
    print("SUMMARY STATISTICS FOR PAPER")
    print("="*60)
    
    print(f"\nTotal data flows: {len(df):,}")
    print(f"Unique apps: {df['app'].nunique()}")
    print(f"Unique data types: {df['data_type'].nunique()}")
    print(f"Unique destinations: {df['destination'].nunique()}")
    
    print("\n--- Data Type Categories ---")
    color_counts = df['data_color'].value_counts()
    for cat, count in color_counts.items():
        pct = 100 * count / len(df)
        print(f"  {cat}: {count:,} ({pct:.1f}%)")
    
    print("\n--- Purposes ---")
    purpose_counts = df['purpose'].value_counts()
    for purpose, count in purpose_counts.items():
        pct = 100 * count / len(df)
        print(f"  {purpose}: {count:,} ({pct:.1f}%)")
    
    print("\n--- Top 10 Destination Entities ---")
    entity_counts = df['entity'].value_counts().head(10)
    for entity, count in entity_counts.items():
        print(f"  {entity}: {count:,}")
    
    print("\n--- Top 10 Data Types ---")
    dtype_counts = df['data_type'].value_counts().head(10)
    for dtype, count in dtype_counts.items():
        print(f"  {dtype}: {count:,}")


if __name__ == "__main__":
    main()
