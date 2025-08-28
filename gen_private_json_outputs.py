import os, json, argparse, time, re
from typing import Dict, Any, Optional

# 统一白名单
ALLOW = {"home","school","hospital","market","shoppingMall","office","officeParking","parking","railway","highspeed"}

R_SYSTEM = (
    'You are an autonomous driving voice assistant. Extract ONLY start and end. '
    'Output STRICT JSON: {"start":"...","end":"..."}. '
    'Allowed places (MUST choose from, output in English): '
    'home, school, hospital, market, shoppingMall, office, officeParking, parking, railway, highspeed. '
    'Do NOT output Chinese. Do NOT add explanations.'
)

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infile", default="../prompts/mybiz_100.jsonl")
    ap.add_argument("--outfile", default="../outputs/mybiz_deepseek.jsonl")
    ap.add_argument("--provider", choices=["deepseek","openai","llamacpp_http"], default="deepseek")
    ap.add_argument("--model", default="deepseek-chat")
    ap.add_argument("--base_url", default=os.environ.get("OPENAI_API_BASE",""))
    ap.add_argument("--api_key", default=os.environ.get("OPENAI_API_KEY",""))
    ap.add_argument("--max_new_tokens", type=int, default=int(os.environ.get("MAX_NEW_TOKENS","128")))
    ap.add_argument("--temperature", type=float, default=float(os.environ.get("TEMP","0")))
    return ap.parse_args()

def get_client(provider, base_url, api_key):
    # 走 OpenAI 兼容SDK；pip install openai>=1.30
    from openai import OpenAI
    if provider in ["deepseek","openai","llamacpp_http"]:
        return OpenAI(api_key=api_key, base_url=base_url if base_url else None)
    raise ValueError("unknown provider")

def extract_json(text: str) -> Optional[Dict[str,Any]]:
    try:
        jt = re.search(r"\{.*\}", text, re.DOTALL).group(0)
        jt = jt.replace("'", '"')
        obj = json.loads(jt)
        if isinstance(obj, dict) and "start" in obj and "end" in obj:
            return {"start": str(obj["start"]), "end": str(obj["end"])}
    except Exception:
        return None
    return None

def main():
    args = parse_args()
    client = get_client(args.provider, args.base_url, args.api_key)

    outs = []
    with open(args.infile, "r", encoding="utf-8") as f:
        lines = [json.loads(x) for x in f if x.strip()]

    for item in lines:
        pid = item["id"]; prompt = item["prompt"]
        t0 = time.time()
        try:
            resp = client.chat.completions.create(
                model=args.model,
                messages=[
                    {"role":"system","content":R_SYSTEM},
                    {"role":"user","content":f"从{prompt}出发"}
                ],
                temperature=args.temperature,
                max_tokens=args.max_new_tokens
            )
            text = resp.choices[0].message.content
        except Exception as e:
            text = f"__ERROR__: {e}"

        parsed = extract_json(text) if not text.startswith("__ERROR__") else None
        outs.append({
            "id": pid,
            "prompt": prompt,
            "raw": text,
            "parsed": parsed,
            "latency_s": round(time.time()-t0,3)
        })

    os.makedirs(os.path.dirname(args.outfile), exist_ok=True)
    with open(args.outfile, "w", encoding="utf-8") as w:
        for row in outs:
            w.write(json.dumps(row, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()
