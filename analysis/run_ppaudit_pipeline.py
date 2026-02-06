#!/usr/bin/env python3
"""
PPAudit Pipeline Runner for VR_monkey Privacy Policies

将 VR_monkey 的 cleaned_policies 通过 PPAudit pipeline 进行分析：
1. 复制 cleaned_policies → PPAudit/output/pp_txts
2. 预处理（分句）→ PPAudit/output/pp_txts_processed
3. 组件分类 → PPAudit/output/pp_components
4. CUS 三元组提取 → PPAudit/output/cus_phrase_tuples
5. Phrase 到 Term 映射 → PPAudit/output/cus_term_tuples

Usage:
    python run_ppaudit_pipeline.py [--step STEP] [--force]

    --step: 从指定步骤开始 (1-5), 默认从头开始
    --force: 强制重新处理已存在的文件
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path

# 路径配置
VR_MONKEY_ROOT = Path("/mnt/ssd2/VR_monkey")
PPAUDIT_ROOT = Path("/mnt/ssd2/PPAudit")

CLEANED_POLICIES = VR_MONKEY_ROOT / "privacy_policies_valid"
PP_TXTS = PPAUDIT_ROOT / "output" / "pp_txts"
PP_TXTS_PROCESSED = PPAUDIT_ROOT / "output" / "pp_txts_processed"
PP_COMPONENTS = PPAUDIT_ROOT / "output" / "pp_components"
CUS_PHRASE_TUPLES = PPAUDIT_ROOT / "output" / "cus_phrase_tuples"
CUS_TERM_TUPLES = PPAUDIT_ROOT / "output" / "cus_term_tuples"


def step1_copy_policies(force=False):
    """Step 1: 复制 cleaned_policies 到 PPAudit/output/pp_txts"""
    print("\n" + "="*60)
    print("Step 1: 复制 cleaned_policies → pp_txts")
    print("="*60)

    PP_TXTS.mkdir(parents=True, exist_ok=True)

    txt_files = list(CLEANED_POLICIES.glob("*.txt"))
    print(f"找到 {len(txt_files)} 个 cleaned policy 文件")

    copied = 0
    skipped = 0
    empty = 0

    for src_file in txt_files:
        dst_file = PP_TXTS / src_file.name

        # 跳过空文件
        if src_file.stat().st_size < 100:
            empty += 1
            continue

        if dst_file.exists() and not force:
            skipped += 1
            continue

        shutil.copy2(src_file, dst_file)
        copied += 1

    print(f"  复制: {copied}, 跳过: {skipped}, 空文件: {empty}")
    return True


def step2_preprocess(force=False):
    """Step 2: 预处理（分句）"""
    print("\n" + "="*60)
    print("Step 2: 预处理（分句）→ pp_txts_processed")
    print("="*60)

    import nltk
    from nltk.tokenize import sent_tokenize

    try:
        nltk.data.find('tokenizers/punkt')
    except:
        nltk.download('punkt')
        nltk.download('punkt_tab')

    PP_TXTS_PROCESSED.mkdir(parents=True, exist_ok=True)

    txt_files = list(PP_TXTS.glob("*.txt"))
    print(f"找到 {len(txt_files)} 个文件待处理")

    processed = 0
    skipped = 0

    for txt_file in txt_files:
        output_file = PP_TXTS_PROCESSED / txt_file.name

        if output_file.exists() and not force:
            skipped += 1
            continue

        with open(txt_file, 'r', encoding='utf-8', errors='ignore') as rf:
            content = rf.read()

        # 清理文本
        content = ' '.join(content.split())

        # 分句
        sentences = sent_tokenize(content)

        # 写入，每行一句
        with open(output_file, 'w', encoding='utf-8') as wf:
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence.split()) >= 3:
                    wf.write(sentence + '\n')

        processed += 1
        if processed % 50 == 0:
            print(f"  已处理: {processed}")

    print(f"  处理: {processed}, 跳过: {skipped}")
    return True


def step3_component_infer(force=False):
    """Step 3: 运行组件分类"""
    print("\n" + "="*60)
    print("Step 3: 组件分类 → pp_components")
    print("="*60)

    script_path = PP_COMPONENTS / "component_infer.py"

    if not script_path.exists():
        print(f"  错误: 找不到 {script_path}")
        return False

    # 切换到脚本目录运行
    os.chdir(PP_COMPONENTS)
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=False
    )

    return result.returncode == 0


def step4_extract_cus_tuples(force=False):
    """Step 4: 提取 CUS phrase 三元组"""
    print("\n" + "="*60)
    print("Step 4: 提取 CUS phrase 三元组 → cus_phrase_tuples")
    print("="*60)

    script_path = PPAUDIT_ROOT / "cus_extract" / "extract_cus_phrase_tuple.py"

    if not script_path.exists():
        print(f"  错误: 找不到 {script_path}")
        return False

    os.chdir(PPAUDIT_ROOT / "cus_extract")
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=False
    )

    return result.returncode == 0


def step5_phrase_to_term(force=False):
    """Step 5: Phrase 到 Term 映射"""
    print("\n" + "="*60)
    print("Step 5: Phrase 到 Term 映射 → cus_term_tuples")
    print("="*60)

    script_path = PPAUDIT_ROOT / "phrase_to_term" / "phrase_to_term.py"

    if not script_path.exists():
        print(f"  错误: 找不到 {script_path}")
        return False

    os.chdir(PPAUDIT_ROOT / "phrase_to_term")
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=False
    )

    return result.returncode == 0


def print_summary():
    """打印处理结果统计"""
    print("\n" + "="*60)
    print("Pipeline 完成统计")
    print("="*60)

    def count_files(path, pattern="*.json"):
        if path.exists():
            return len(list(path.glob(pattern)))
        return 0

    print(f"  pp_txts:           {count_files(PP_TXTS, '*.txt')} 文件")
    print(f"  pp_txts_processed: {count_files(PP_TXTS_PROCESSED, '*.txt')} 文件")
    print(f"  pp_components:     {count_files(PP_COMPONENTS)} 文件")
    print(f"  cus_phrase_tuples: {count_files(CUS_PHRASE_TUPLES)} 文件")
    print(f"  cus_term_tuples:   {count_files(CUS_TERM_TUPLES)} 文件")


def main():
    parser = argparse.ArgumentParser(description="PPAudit Pipeline Runner")
    parser.add_argument("--step", type=int, default=1, choices=[1,2,3,4,5],
                        help="从指定步骤开始 (1-5)")
    parser.add_argument("--force", action="store_true",
                        help="强制重新处理已存在的文件")
    parser.add_argument("--only", type=int, choices=[1,2,3,4,5],
                        help="只运行指定步骤")
    args = parser.parse_args()

    print("="*60)
    print("PPAudit Pipeline for VR_monkey Privacy Policies")
    print("="*60)

    steps = [
        (1, "复制 policies", step1_copy_policies),
        (2, "预处理（分句）", step2_preprocess),
        (3, "组件分类", step3_component_infer),
        (4, "提取 CUS 三元组", step4_extract_cus_tuples),
        (5, "Phrase → Term", step5_phrase_to_term),
    ]

    if args.only:
        steps = [(n, name, func) for n, name, func in steps if n == args.only]
    else:
        steps = [(n, name, func) for n, name, func in steps if n >= args.step]

    for step_num, step_name, step_func in steps:
        success = step_func(force=args.force)
        if not success:
            print(f"\n步骤 {step_num} ({step_name}) 失败!")
            sys.exit(1)

    print_summary()
    print("\n✅ Pipeline 完成!")


if __name__ == "__main__":
    main()
