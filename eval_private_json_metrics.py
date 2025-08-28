import json, argparse

ALLOW = {"home","school","hospital","market","shoppingMall","office","officeParking","parking","railway","highspeed"}

def load_jsonl(path):
    with open(path,"r",encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if line:
                yield json.loads(line)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True)  # gen_private_json_outputs.py 的输出
    ap.add_argument("--alias_map", default="../prompts/alias_map.json")
    ap.add_argument("--refs", default=None)   # 可选：refs_optional.jsonl
    args = ap.parse_args()

    alias = json.load(open(args.alias_map,"r",encoding="utf-8"))
    preds = list(load_jsonl(args.pred))
    ref_map = {}
    if args.refs:
        ref_map = {x["id"]:(x["start"],x["end"]) for x in load_jsonl(args.refs)}

    n = len(preds)
    valid = 0
    both_in_allow = 0
    out_of_allow = 0
    norm_correct = 0
    total_latency = 0.0

    for r in preds:
        p = r.get("parsed")
        total_latency += float(r.get("latency_s",0))
        if isinstance(p, dict) and set(p.keys())=={"start","end"}:
            valid += 1
            s = str(p["start"]).strip()
            e = str(p["end"]).strip()
            # 命中白名单
            in_allow = (s in ALLOW) and (e in ALLOW)
            if in_allow:
                both_in_allow += 1
            else:
                # 记录是否越权（有任一不在白名单）
                if s not in ALLOW or e not in ALLOW:
                    out_of_allow += 1

            # 归一化准确率（需要参考答案）
            if ref_map:
                # 先用 alias_map 归一化
                s_norm = alias.get(s, s)
                e_norm = alias.get(e, e)
                gold = ref_map.get(r["id"])
                if gold:
                    norm_correct += int((s_norm==gold[0]) and (e_norm==gold[1]))

    print(json.dumps({
        "count": n,
        "valid_json_rate": round(valid/n,4) if n else 0.0,
        "both_fields_in_allow_rate": round(both_in_allow/n,4) if n else 0.0,
        "out_of_allow_rate": round(out_of_allow/n,4) if n else 0.0,
        "avg_latency_s": round(total_latency/n,3) if n else 0.0,
        "normalized_accuracy_if_refs_provided": (round(norm_correct/n,4) if ref_map else None)
    }, ensure_ascii=False, indent=2))

if __name__=="__main__":
    main()
