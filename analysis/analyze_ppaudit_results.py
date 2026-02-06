


import json
import csv
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any


PPAUDIT_ROOT = Path("/mnt/ssd2/PPAudit")
VR_MONKEY_ROOT = Path("/mnt/ssd2/VR_monkey")
CUS_TERM_TUPLES = PPAUDIT_ROOT / "output" / "cus_term_tuples"
OUTPUT_DIR = VR_MONKEY_ROOT / "ppaudit_analysis"


def load_all_term_tuples() -> Dict[str, List[Dict]]:
    
    all_data = {}

    for json_file in CUS_TERM_TUPLES.glob("*.json"):
        
        if ".error-" in json_file.name:
            continue

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            
            
            app_id = json_file.stem.split("_")[0]
            all_data[app_id] = data

        except Exception as e:
            print(f"Error loading {json_file.name}: {e}")

    return all_data


def analyze_single_app(app_id: str, tuples: List[Dict]) -> Dict[str, Any]:
    

    
    first_party_collect = set()
    first_party_not_collect = set()
    third_party_collect = set()
    third_party_not_collect = set()

    all_data_terms = set()
    verbs_used = Counter()

    for t in tuples:
        entity = t.get("entity_term", "")
        action = t.get("cus_or_not", "")
        data_term = t.get("dataobj_term", "")
        verb = t.get("cus_verb", "")

        if not data_term:
            continue

        all_data_terms.add(data_term)
        verbs_used[verb] += 1

        is_first_party = entity in ["we", "first party", "we_implicit"]
        is_collect = action == "collect"

        if is_first_party:
            if is_collect:
                first_party_collect.add(data_term)
            else:
                first_party_not_collect.add(data_term)
        else:
            if is_collect:
                third_party_collect.add(data_term)
            else:
                third_party_not_collect.add(data_term)

    return {
        "app_id": app_id,
        "total_tuples": len(tuples),
        "unique_data_types": len(all_data_terms),
        "first_party_collect": sorted(first_party_collect),
        "first_party_not_collect": sorted(first_party_not_collect),
        "third_party_collect": sorted(third_party_collect),
        "third_party_not_collect": sorted(third_party_not_collect),
        "all_data_terms": sorted(all_data_terms),
        "top_verbs": verbs_used.most_common(5)
    }


def generate_summary_report(all_analysis: List[Dict]) -> Dict:
    

    
    total_apps = len(all_analysis)
    total_tuples = sum(a["total_tuples"] for a in all_analysis)

    
    data_type_freq = Counter()
    first_party_data_freq = Counter()
    third_party_data_freq = Counter()

    for analysis in all_analysis:
        for dt in analysis["first_party_collect"]:
            data_type_freq[dt] += 1
            first_party_data_freq[dt] += 1
        for dt in analysis["third_party_collect"]:
            data_type_freq[dt] += 1
            third_party_data_freq[dt] += 1

    return {
        "total_apps": total_apps,
        "total_tuples": total_tuples,
        "avg_tuples_per_app": total_tuples / total_apps if total_apps > 0 else 0,
        "unique_data_types": len(data_type_freq),
        "top_data_types": data_type_freq.most_common(30),
        "top_first_party_data": first_party_data_freq.most_common(20),
        "top_third_party_data": third_party_data_freq.most_common(20),
    }


def export_per_app_csv(all_analysis: List[Dict], output_file: Path):
    

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "app_id",
            "total_tuples",
            "unique_data_types",
            "1st_party_collect_count",
            "1st_party_not_collect_count",
            "3rd_party_collect_count",
            "3rd_party_not_collect_count",
            "1st_party_collect_types",
            "3rd_party_collect_types"
        ])

        for a in all_analysis:
            writer.writerow([
                a["app_id"],
                a["total_tuples"],
                a["unique_data_types"],
                len(a["first_party_collect"]),
                len(a["first_party_not_collect"]),
                len(a["third_party_collect"]),
                len(a["third_party_not_collect"]),
                "|".join(a["first_party_collect"]),
                "|".join(a["third_party_collect"])
            ])

    print(f"Exported: {output_file}")


def export_data_types_csv(summary: Dict, output_file: Path):
    

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["data_type", "total_apps", "1st_party_apps", "3rd_party_apps"])

        all_types = set(dt for dt, _ in summary["top_data_types"])
        first_party_dict = dict(summary["top_first_party_data"])
        third_party_dict = dict(summary["top_third_party_data"])
        total_dict = dict(summary["top_data_types"])

        for dt in sorted(all_types, key=lambda x: total_dict.get(x, 0), reverse=True):
            writer.writerow([
                dt,
                total_dict.get(dt, 0),
                first_party_dict.get(dt, 0),
                third_party_dict.get(dt, 0)
            ])

    print(f"Exported: {output_file}")


def export_detailed_json(all_analysis: List[Dict], summary: Dict, output_file: Path):
    

    output = {
        "summary": summary,
        "per_app": {a["app_id"]: a for a in all_analysis}
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Exported: {output_file}")


def main():
    print("="*60)
    print("PPAudit Results Analyzer")
    print("="*60)

    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    
    print("\n1. 加载 CUS Term Tuples...")
    all_data = load_all_term_tuples()
    print(f"   加载了 {len(all_data)} 个 app 的数据")

    
    print("\n2. 分析每个 app...")
    all_analysis = []
    for app_id, tuples in all_data.items():
        analysis = analyze_single_app(app_id, tuples)
        all_analysis.append(analysis)

    
    all_analysis.sort(key=lambda x: x["app_id"])

    
    print("\n3. 生成汇总报告...")
    summary = generate_summary_report(all_analysis)

    
    print(f"\n{'='*60}")
    print("汇总统计")
    print("="*60)
    print(f"  总 Apps: {summary['total_apps']}")
    print(f"  总 Tuples: {summary['total_tuples']}")
    print(f"  平均 Tuples/App: {summary['avg_tuples_per_app']:.1f}")
    print(f"  唯一数据类型: {summary['unique_data_types']}")

    print(f"\n最常见的数据类型 (Top 15):")
    for dt, count in summary["top_data_types"][:15]:
        print(f"    {dt:30s} : {count} apps")

    print(f"\n第一方最常收集的数据 (Top 10):")
    for dt, count in summary["top_first_party_data"][:10]:
        print(f"    {dt:30s} : {count} apps")

    print(f"\n第三方最常收集的数据 (Top 10):")
    for dt, count in summary["top_third_party_data"][:10]:
        print(f"    {dt:30s} : {count} apps")

    
    print("\n4. 导出结果...")
    export_per_app_csv(all_analysis, OUTPUT_DIR / "ppaudit_per_app_summary.csv")
    export_data_types_csv(summary, OUTPUT_DIR / "ppaudit_data_types_freq.csv")
    export_detailed_json(all_analysis, summary, OUTPUT_DIR / "ppaudit_detailed_analysis.json")

    print(f"\n✅ 分析完成! 结果保存在: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
