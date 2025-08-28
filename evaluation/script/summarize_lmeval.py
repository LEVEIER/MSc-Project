#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
汇总 lm-eval 结果：
- 支持一次性读取多个 outputs/*.json
- 自动提取 model / tasks / seed / limit / n-shot 等配置
- 展开指标（acc, acc_norm, exact_match, mc1, mc2, ...）
- 按 (model, task, metric, limit, num_fewshot) 分组，计算多次运行的 mean/std/count
- 终端打印简表，并可 --csv 导出
"""
import argparse, glob, json, os, re, statistics, sys
from collections import defaultdict

PRIMARY_METRICS_ORDER = ["acc", "acc_norm", "exact_match", "mc1", "mc2", "f1"]

def redact_model_args(s: str) -> str:
    if not s:
        return s
    # 隐去 api_key
    s = re.sub(r"api_key\s*=\s*[^,\)]+", "api_key=***", s)
    s = re.sub(r"api_key\s*:\s*[^,\}]+", "api_key: ***", s)
    return s

def is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)

def flatten_metrics(prefix, obj, out):
    """
    递归展开 metrics，记录成 {'metric_path': value}
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten_metrics(f"{prefix}{k}." if prefix else f"{k}.", v, out)
    else:
        if is_number(obj):
            key = prefix[:-1]  # 去掉末尾点
            out[key] = float(obj)

def load_one(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cfg = data.get("config", {})
    model = cfg.get("model") or ""
    model_args = redact_model_args(cfg.get("model_args") or "")
    gen_kwargs = cfg.get("gen_kwargs") or ""
    seed = cfg.get("seed")
    limit = cfg.get("limit")
    num_fewshot = cfg.get("num_fewshot")
    tasks = list((data.get("results") or {}).keys())

    rows = []
    results = data.get("results", {})
    for task, metrics in results.items():
        flat = {}
        flatten_metrics("", metrics, flat)
        # 生成 (metric, value) 行
        for m, v in flat.items():
            # 尝试把与 stderr 配对：如果存在同路径加 '.stderr' 就读取
            stderr_key = f"{m}.stderr"
            stderr_val = flat.get(stderr_key)
            rows.append({
                "file": os.path.basename(path),
                "model": model,
                "model_args": model_args,
                "gen_kwargs": gen_kwargs,
                "task": task,
                "metric": m,
                "value": v,
                "stderr": stderr_val if isinstance(stderr_val, float) else None,
                "seed": seed,
                "limit": limit,
                "num_fewshot": num_fewshot,
            })
    return rows

def summarize(rows, group_keys):
    groups = defaultdict(list)
    for r in rows:
        key = tuple(r[k] for k in group_keys)
        groups[key].append(r["value"])
    summary = []
    for key, vs in groups.items():
        mean = statistics.mean(vs)
        std = statistics.pstdev(vs) if len(vs) > 1 else 0.0
        cnt = len(vs)
        item = dict(zip(group_keys, key))
        item.update({"mean": mean, "std": std, "n": cnt})
        summary.append(item)
    # 按 model, task, metric 排序
    summary.sort(key=lambda x: (str(x.get("model")), str(x.get("task")), str(x.get("metric"))))
    return summary

def print_table(summary, cols):
    # 计算列宽
    widths = [max(len(c), max(len(f"{row.get(c, '')}") for row in summary) if summary else len(c)) for c in cols]
    def line(row=None):
        vals = [str(row.get(c, "")) if row else c for c in cols]
        return " | ".join(v.ljust(w) for v, w in zip(vals, widths))
    print(line())
    print("-|-".join("-" * w for w in widths))
    for r in summary:
        print(line(r))

def choose_primary_rows(summary):
    """
    从同一 (model, task, limit, num_fewshot) 中，优先挑选 PRIMARY_METRICS_ORDER 中最先出现的指标
    """
    buckets = defaultdict(list)
    for r in summary:
        key = (r.get("model"), r.get("task"), r.get("limit"), r.get("num_fewshot"))
        buckets[key].append(r)
    picked = []
    for key, arr in buckets.items():
        # 找最优先的 metric
        by_metric = {x["metric"]: x for x in arr}
        chosen = None
        for m in PRIMARY_METRICS_ORDER:
            # 允许子路径：比如 "flexible-extract.exact_match"
            cands = [v for k, v in by_metric.items() if k.endswith(m)]
            if cands:
                # 挑第一个
                chosen = cands[0]
                break
        chosen = chosen or arr[0]
        picked.append(chosen)
    picked.sort(key=lambda x: (str(x.get("model")), str(x.get("task"))))
    return picked

def main():
    ap = argparse.ArgumentParser(description="Summarize lm-eval outputs")
    ap.add_argument("patterns", nargs="*", default=["outputs/*.json"], help="Glob patterns of result files")
    ap.add_argument("--csv", default="", help="Path to save CSV summary (optional)")
    ap.add_argument("--primary", action="store_true", help="Only print a primary metric per (model,task,limit,num_fewshot)")
    args = ap.parse_args()

    files = []
    for p in args.patterns:
        files.extend(glob.glob(p))
    files = sorted(set(files))
    if not files:
        print("No files matched. Try: scripts/summarize_lmeval.py outputs/*.json", file=sys.stderr)
        sys.exit(1)

    all_rows = []
    for f in files:
        try:
            all_rows.extend(load_one(f))
        except Exception as e:
            print(f"[WARN] Failed to parse {f}: {e}", file=sys.stderr)

    # 聚合：按 (model, task, metric, limit, num_fewshot)
    group_keys = ["model", "task", "metric", "limit", "num_fewshot"]
    summary = summarize(all_rows, group_keys)

    # 仅主指标时，先挑选主指标再打印
    if args.primary:
        primary_rows = choose_primary_rows(summary)
        cols = ["model", "task", "metric", "limit", "num_fewshot", "mean", "std", "n"]
        print_table(primary_rows, cols)
        if args.csv:
            import csv
            with open(args.csv, "w", newline="", encoding="utf-8") as wf:
                w = csv.DictWriter(wf, fieldnames=cols)
                w.writeheader()
                for r in primary_rows:
                    w.writerow(r)
    else:
        cols = ["model", "task", "metric", "limit", "num_fewshot", "mean", "std", "n"]
        print_table(summary, cols)
        if args.csv:
            import csv
            with open(args.csv, "w", newline="", encoding="utf-8") as wf:
                w = csv.DictWriter(wf, fieldnames=cols)
                w.writeheader()
                for r in summary:
                    w.writerow(r)

if __name__ == "__main__":
    main()
