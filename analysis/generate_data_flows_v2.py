#!/usr/bin/env python3
"""
Generate Data Flows (V2)
------------------------
从已提取的 per_app_keyvals_jsonl 生成 data flows，定义为 <app, data_type, destination>

输入：
- per_app_keyvals_jsonl: 已提取好的 key/value pairs (from build_app_requests_dataset_from_jsonl.py)

输出：
- data_flows.csv: 所有 unique data flows
- data_flows_summary.json: 统计信息
"""

import json
import os
import csv
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any
import sys

sys.path.insert(0, '/mnt/ssd2/VR_monkey/ppaudit_analysis')
from key_to_datatype_mapper import create_default_mapper


# ========== 配置 ==========
KEYVALS_DIR = "/mnt/ssd2/VR_monkey/app_traffic_dataset_requests_v6/per_app_keyvals_jsonl"
OUTPUT_DIR = "/mnt/ssd2/VR_monkey/ppaudit_analysis/data_flows_output_v2"


def load_app_keyvals(app_file: str) -> List[dict]:
    """加载一个 app 的所有 key/value pairs"""
    keyvals = []
    with open(app_file, 'r') as f:
        for line in f:
            try:
                kv = json.loads(line)
                keyvals.append(kv)
            except:
                pass
    return keyvals


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 加载 mapper
    print("Loading mapper...")
    mapper = create_default_mapper()
    
    # 获取所有 app 文件
    app_files = [f for f in os.listdir(KEYVALS_DIR) if f.endswith('.jsonl')]
    print(f"Found {len(app_files)} app keyval files")
    
    # 存储所有 data flows
    all_data_flows: Set[Tuple[str, str, str]] = set()  # (app, data_type, destination)
    app_flow_details: Dict[str, List[dict]] = defaultdict(list)
    app_stats = {}
    
    print("\nProcessing apps...")
    
    for app_file in app_files:
        # 从文件名提取 app name
        app_name = app_file[:-6].replace('_', ' ')  # 去掉 .jsonl，下划线变空格
        
        # 加载 key/value pairs
        keyvals = load_app_keyvals(os.path.join(KEYVALS_DIR, app_file))
        
        if not keyvals:
            app_stats[app_name] = {'keyvals': 0, 'data_types': 0, 'destinations': 0, 'flows': 0}
            continue
        
        # 提取 data flows
        app_data_types = set()
        app_destinations = set()
        app_flows_set = set()
        
        for kv in keyvals:
            key = kv.get('key', '')
            value = kv.get('value', '')
            domain = kv.get('domain', '')
            
            if not domain:
                continue
            
            # 映射到 data type
            result = mapper.map_key(key, value)
            if result:
                data_type, evidence = result
                
                # 记录 data flow
                flow_tuple = (app_name, data_type, domain)
                all_data_flows.add(flow_tuple)
                app_flows_set.add(flow_tuple)
                app_data_types.add(data_type)
                app_destinations.add(domain)
                
                # 记录详情
                app_flow_details[app_name].append({
                    'data_type': data_type,
                    'destination': domain,
                    'key': key,
                    'value': value[:100] if len(str(value)) > 100 else value,
                    'evidence': evidence,
                })
        
        app_stats[app_name] = {
            'keyvals': len(keyvals),
            'data_types': len(app_data_types),
            'destinations': len(app_destinations),
            'flows': len(app_flows_set)
        }
    
    # 输出统计
    print("\n" + "=" * 70)
    print("Data Flow Statistics (V2 - from per_app_keyvals_jsonl)")
    print("=" * 70)
    
    apps_with_flows = [a for a, s in app_stats.items() if s['flows'] > 0]
    total_flows = len(all_data_flows)
    total_data_types = len(set(f[1] for f in all_data_flows))
    total_destinations = len(set(f[2] for f in all_data_flows))
    total_keyvals = sum(s['keyvals'] for s in app_stats.values())
    
    print(f"Total apps: {len(app_stats)}")
    print(f"Total key/value pairs processed: {total_keyvals}")
    print(f"Apps with data flows: {len(apps_with_flows)}")
    print(f"Total unique data flows: {total_flows}")
    print(f"Total unique data types: {total_data_types}")
    print(f"Total unique destinations: {total_destinations}")
    
    # 保存 data flows
    flows_csv = os.path.join(OUTPUT_DIR, 'data_flows.csv')
    with open(flows_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['app', 'data_type', 'destination'])
        for flow in sorted(all_data_flows):
            writer.writerow(flow)
    print(f"\nSaved data flows to: {flows_csv}")
    
    # 统计每个 data type 的 flow 数量
    data_type_counts = defaultdict(int)
    for flow in all_data_flows:
        data_type_counts[flow[1]] += 1
    
    # 保存 summary
    summary = {
        'total_apps': len(app_stats),
        'total_keyvals_processed': total_keyvals,
        'apps_with_flows': len(apps_with_flows),
        'total_unique_flows': total_flows,
        'total_data_types': total_data_types,
        'total_destinations': total_destinations,
        'app_stats': app_stats,
        'data_types_count': dict(sorted(data_type_counts.items(), key=lambda x: -x[1]))
    }
    
    summary_path = os.path.join(OUTPUT_DIR, 'data_flows_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"Saved summary to: {summary_path}")
    
    # 保存详细信息
    details_path = os.path.join(OUTPUT_DIR, 'data_flows_details.json')
    with open(details_path, 'w') as f:
        json.dump(app_flow_details, f, indent=2)
    print(f"Saved details to: {details_path}")
    
    # Top data types
    print("\nTop 20 Data Types:")
    for dt, count in list(summary['data_types_count'].items())[:20]:
        print(f"  {dt:<25} {count:>5} flows")
    
    # Top apps by flows
    print("\nTop 10 Apps by Data Flows:")
    apps_sorted = sorted(app_stats.items(), key=lambda x: -x[1]['flows'])[:10]
    for app, stats in apps_sorted:
        print(f"  {app:<40} {stats['flows']:>4} flows, {stats['data_types']:>3} types, {stats['destinations']:>3} dests")


if __name__ == "__main__":
    main()
