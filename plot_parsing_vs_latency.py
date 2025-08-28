# Project/evaluation/plot_parsing_vs_latency.py
import csv, argparse
import matplotlib.pyplot as plt
from collections import defaultdict

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="evaluation/parsing_results.csv")
    ap.add_argument("--out", default="evaluation/parsing_parbars.png")
    args = ap.parse_args()

    by_model = defaultdict(list)
    with open(args.csv, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            by_model[row["model"]].append(row)

    models = []
    accs = []
    lats = []
    for m, rows in by_model.items():
        total = len(rows)
        correct = sum(1 for x in rows if x["correct"] in ("True","true","1", "yes"))
        acc = correct/total*100 if total else 0
        lat_list = [float(x["latency_s"]) for x in rows if x["latency_s"] not in ("", "None")]
        avg_lat = sum(lat_list)/len(lat_list) if lat_list else 0
        models.append(m)
        accs.append(acc)
        lats.append(avg_lat)

    # 画两个子图（不共享坐标）
    plt.figure(figsize=(8,4))
    # 准确率条形
    plt.subplot(1,2,1)
    plt.bar(models, accs)
    plt.title("Parsing Accuracy (%)")
    plt.xlabel("Model"); plt.ylabel("Accuracy")

    # 平均延迟散点
    plt.subplot(1,2,2)
    plt.scatter(models, lats)
    plt.title("Average Latency (s)")
    plt.xlabel("Model"); plt.ylabel("Latency")

    plt.tight_layout()
    plt.savefig(args.out, dpi=200)
    print("✓ Saved figure:", args.out)

if __name__ == "__main__":
    main()
