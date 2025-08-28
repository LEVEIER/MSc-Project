# Project/evaluation/plot_route_gap.py
import csv, argparse
import matplotlib.pyplot as plt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="evaluation/routes_results.csv")
    ap.add_argument("--out", default="evaluation/route_gap.png")
    args = ap.parse_args()

    labels, gaps = [], []
    with open(args.csv, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            labels.append(f'{row["start"]}->{row["end"]}')
            gaps.append(float(row["delta_percent"]))

    plt.figure(figsize=(9,4))
    plt.bar(labels, gaps)
    plt.xticks(rotation=35, ha="right")
    plt.ylabel("ΔL (%)")
    plt.title("System vs Shortest Path Gap")
    plt.tight_layout()
    plt.savefig(args.out, dpi=200)
    print("✓ Saved figure:", args.out)

if __name__ == "__main__":
    main()
