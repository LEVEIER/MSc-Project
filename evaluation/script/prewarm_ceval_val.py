# scripts/prewarm_ceval_val.py
import time, random
from datasets import load_dataset, get_dataset_config_names

def main():
    configs = get_dataset_config_names("ceval/ceval-exam")
    print(f"Total subjects: {len(configs)}")
    ok, fail = 0, []
    for i, cfg in enumerate(configs, 1):
        try:
            ds = load_dataset("ceval/ceval-exam", cfg, split="val")
            print(f"[{i:02d}/{len(configs)}] {cfg:<40} -> {len(ds)} rows")
            ok += 1
            time.sleep(0.6 + random.random()*0.4)  # 轻微限速，减小被限流概率
        except Exception as e:
            print(f"[FAIL] {cfg}: {e}")
            fail.append(cfg)
    print(f"Done. ok={ok}, fail={len(fail)}; fails={fail}")

if __name__ == "__main__":
    main()
