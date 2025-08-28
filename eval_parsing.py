# Project/evaluation/eval_parsing.py
import os, sys, re, json, time, argparse
from typing import Dict, Tuple, Any, List, Optional
import csv
from pathlib import Path

# 确保能 import 项目内模块（把 Project 根目录加入 sys.path）
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# === 项目内依赖 ===
# nlp.instruction_parser 中已有 alias_map / normalize_place_name / chat_with_deepseek
from nlp.instruction_parser import alias_map, normalize_place_name, chat_with_deepseek


# ---------- 路径解析 ----------
def resolve_data_path(p: str) -> str:
    """
    稳健解析数据集路径的工具：
    1) 若是绝对路径且存在，直接用；
    2) 先按当前工作目录解析；
    3) 再按脚本所在目录（evaluation/）解析；
    4) 再按 Project 根目录解析。
    """
    pth = Path(p)
    if pth.is_absolute() and pth.exists():
        return str(pth)

    if pth.exists():  # 相对 CWD
        return str(pth)

    here = Path(__file__).resolve().parent                  # .../Project/evaluation
    candidate = (here / p).resolve()
    if candidate.exists():
        return str(candidate)

    project_root = here  # evaluation 的上级就是 Project
    candidate2 = (project_root / p).resolve()
    if candidate2.exists():
        return str(candidate2)

    raise FileNotFoundError(f"Dataset not found. Tried: {pth}, {candidate}, {candidate2}")


# ---------- 工具 ----------
def read_jsonl(path: str) -> List[Dict[str, Any]]:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def robust_extract_json(text: str) -> Dict[str, Any]:
    """从模型输出里抽取 {"start": "...", "end": "..."}，容忍代码块/噪声。"""
    try:
        m = re.search(r"\{.*?\}", text, flags=re.S)
        if not m:
            return {}
        obj = json.loads(m.group(0).replace("'", '"'))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def norm_place(x: Optional[str]) -> Optional[str]:
    if x is None:
        return None
    return normalize_place_name(x)


# ---------- 解析器实现 ----------
def rule_based_parser(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    规则基线：利用 alias_map 全词匹配，简单抽取 start/end。
    支持模式：
      - "从X去Y" / "X到Y"
      - "go to Y from X" / "Y from X"
    """
    t = text.strip().lower()
    # 映射词表（键统一为小写，按长度降序，避免短词抢先匹配）
    keys = sorted(set([k.lower() for k in alias_map.keys()]), key=len, reverse=True)

    # 先尝试中式：“从X去Y” / “X到Y”
    m = re.search(r"从(.*?)[去到到](.*)", t)
    if m:
        cand_start = m.group(1).strip()
        cand_end = m.group(2).strip()
        start = next((alias_map[k] for k in keys if k in cand_start), cand_start)
        end = next((alias_map[k] for k in keys if k in cand_end), cand_end)
        return norm_place(start), norm_place(end)

    # 再尝试英式：“go to Y from X”
    m = re.search(r"go\s+to\s+(.*?)\s+from\s+(.*)", t)
    if m:
        end = m.group(1).strip()
        start = m.group(2).strip()
        start = next((alias_map[k] for k in keys if k in start), start)
        end = next((alias_map[k] for k in keys if k in end), end)
        return norm_place(start), norm_place(end)

    # “Y from X”
    m = re.search(r"(.*?)\s+from\s+(.*)", t)
    if m:
        end = m.group(1).strip()
        start = m.group(2).strip()
        start = next((alias_map[k] for k in keys if k in start), start)
        end = next((alias_map[k] for k in keys if k in end), end)
        return norm_place(start), norm_place(end)

    # fallback：在句中按出现顺序找两个地名
    found = []
    for k in keys:
        if k in t:
            found.append(alias_map[k])
    found = [normalize_place_name(x) for x in found if x]
    if len(found) >= 2:
        return found[0], found[1]
    return None, None


def local_llm_parser(text: str, endpoint: str, model: str) -> Tuple[Optional[str], Optional[str], float]:
    """
    调本地 LLM（OpenAI 格式兼容接口，如 llama.cpp/ollama/oobabooga 的 /v1/chat/completions）
    通过环境变量配置：LOCAL_LLM_ENDPOINT, LOCAL_LLM_MODEL
    """
    try:
        import requests
    except Exception as e:
        raise RuntimeError("requests not installed for local LLM parser") from e

    system = (
        'You extract start and end landmarks from user navigation commands. '
        'Return strict JSON: {"start":"...", "end":"..."} using ONLY these tokens: '
        'home, school, hospital, market, shoppingMall, office, officeParking, parking, railway, cottageArea, highspeed.'
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
        "max_tokens": 64,
    }
    t0 = time.time()
    r = requests.post(endpoint.rstrip("/") + "/v1/chat/completions", json=payload, timeout=60)
    latency = time.time() - t0
    r.raise_for_status()
    msg = r.json()["choices"][0]["message"]["content"]
    obj = robust_extract_json(msg)
    return norm_place(obj.get("start")), norm_place(obj.get("end")), latency


def cloud_llm_parser(text: str) -> Tuple[Optional[str], Optional[str], float]:
    """
    复用项目里的 chat_with_deepseek()。
    """
    t0 = time.time()
    obj = chat_with_deepseek(text) or {}
    latency = time.time() - t0
    return norm_place(obj.get("start")), norm_place(obj.get("end")), latency


# ---------- 主评测 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="dataset/prompts.jsonl")
    ap.add_argument("--out_csv", default="evaluation/parsing_results.csv")
    ap.add_argument("--out_txt", default="evaluation/parsing_summary.txt")
    ap.add_argument("--run_rule", action="store_true")
    ap.add_argument("--run_local", action="store_true")
    ap.add_argument("--run_cloud", action="store_true")
    ap.add_argument("--local_endpoint", default=os.getenv("LOCAL_LLM_ENDPOINT", ""))
    ap.add_argument("--local_model", default=os.getenv("LOCAL_LLM_MODEL", ""))
    args = ap.parse_args()

    # 解析并显示最终使用的数据集路径
    data_path = resolve_data_path(args.data)
    print(f"[INFO] Using dataset: {data_path}")
    data_raw = read_jsonl(data_path)

    # 兼容两种数据格式：
    # A) {"text": "...", "gold_start":"...", "gold_end":"..."}
    # B) {"instruction": "...", "expected":{"start":"...","end":"..."}}
    data: List[Dict[str, Any]] = []
    for item in data_raw:
        if "text" in item and "gold_start" in item and "gold_end" in item:
            data.append({
                "text": item["text"],
                "gold_start": item["gold_start"],
                "gold_end": item["gold_end"],
                "tags": item.get("tags", []),
            })
        elif "instruction" in item and "expected" in item and isinstance(item["expected"], dict):
            data.append({
                "text": item["instruction"],
                "gold_start": item["expected"].get("start"),
                "gold_end": item["expected"].get("end"),
                "tags": item.get("tags", []),
            })
        else:
            # 跳过不符合结构的样本
            continue

    rows = []
    summary = []

    # 逐条样本测试
    for item in data:
        text = item["text"]
        gold_s = item["gold_start"]
        gold_e = item["gold_end"]
        tag = ",".join(item.get("tags", []))

        if args.run_rule:
            s, e = rule_based_parser(text)
            ok = (s == gold_s and e == gold_e)
            rows.append(["rule", text, gold_s, gold_e, s, e, ok, None, tag])

        if args.run_local and args.local_endpoint and args.local_model:
            try:
                s, e, lat = local_llm_parser(text, args.local_endpoint, args.local_model)
                ok = (s == gold_s and e == gold_e)
                rows.append(["local", text, gold_s, gold_e, s, e, ok, round(lat, 3), tag])
            except Exception as ex:
                rows.append(["local", text, gold_s, gold_e, None, None, False, None, f"ERR:{ex}"])

        if args.run_cloud:
            try:
                s, e, lat = cloud_llm_parser(text)
                ok = (s == gold_s and e == gold_e)
                rows.append(["cloud", text, gold_s, gold_e, s, e, ok, round(lat, 3), tag])
            except Exception as ex:
                rows.append(["cloud", text, gold_s, gold_e, None, None, False, None, f"ERR:{ex}"])

    # 写 CSV
    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "text", "gold_start", "gold_end", "pred_start", "pred_end", "correct", "latency_s", "tags"])
        w.writerows(rows)

    # 汇总
    def summarize(kind):
        subset = [r for r in rows if r[0] == kind]
        if not subset:
            return None
        total = len(subset)
        correct = sum(1 for r in subset if bool(r[6]))
        latencies = [r[7] for r in subset if isinstance(r[7], (int, float))]
        avg_lat = round(sum(latencies) / len(latencies), 3) if latencies else None
        return kind, total, correct, round(correct / total * 100, 1), avg_lat

    for m in ["rule", "local", "cloud"]:
        s = summarize(m)
        if s:
            summary.append(s)

    with open(args.out_txt, "w", encoding="utf-8") as f:
        f.write("Model, Total, Correct, Accuracy(%), AvgLatency(s)\n")
        for kind, total, correct, acc, avg_lat in summary:
            f.write(f"{kind}, {total}, {correct}, {acc}, {avg_lat}\n")

    print("✓ Saved:", args.out_csv, "and", args.out_txt)


if __name__ == "__main__":
    main()
