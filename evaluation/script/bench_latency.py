import os, time, json, argparse, statistics
from openai import OpenAI

parser = argparse.ArgumentParser()
parser.add_argument("--base_url", type=str, default=os.getenv("OPENAI_API_BASE"))
parser.add_argument("--api_key", type=str, default=os.getenv("OPENAI_API_KEY"))
parser.add_argument("--model", type=str, default="deepseek-chat")
parser.add_argument("--prompt", type=str, default="从公司停车场去购物中心")
parser.add_argument("--concurrency", type=int, default=8)
parser.add_argument("--n_requests", type=int, default=100)
parser.add_argument("--max_new_tokens", type=int, default=128)
parser.add_argument("--temperature", type=float, default=0.0)
args = parser.parse_args()

client = OpenAI(api_key=args.api_key, base_url=args.base_url)

def one_call():
    t0 = time.time()
    stream = client.chat.completions.create(
        model=args.model,
        messages=[{"role":"system","content":"Output JSON only: {\"start\":\"...\",\"end\":\"...\"} Allowed: home,school,hospital,market,shoppingMall,office,officeParking,parking,railway,highspeed."},
                  {"role":"user","content":f"从{args.prompt}出发"}],
        temperature=args.temperature,
        stream=True,
        max_tokens=args.max_new_tokens
    )
    ttft = None
    n_chars = 0
    for chunk in stream:
        if ttft is None:
            ttft = time.time() - t0
        delta = chunk.choices[0].delta.content or ""
        n_chars += len(delta)
    total = time.time() - t0
    # 以字符近似token速率（相对比较足够）
    tpot = (total - ttft) / max(n_chars,1)
    return {"ttft": ttft, "tpot": tpot, "total": total, "n_chars": n_chars}

import concurrent.futures as cf
lat, tp, tot = [], [], []
with cf.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
    futs=[ex.submit(one_call) for _ in range(args.n_requests)]
    for f in cf.as_completed(futs):
        r = f.result()
        lat.append(r["ttft"]); tp.append(r["tpot"]); tot.append(r["total"])
print(json.dumps({
    "concurrency": args.concurrency,
    "n_requests": args.n_requests,
    "TTFT_avg_s": statistics.mean(lat),
    "GenCharSec_avg": 1.0/statistics.mean(tp) if statistics.mean(tp)>0 else None,
    "Latency_avg_s": statistics.mean(tot),
}, indent=2, ensure_ascii=False))
