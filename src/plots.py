import argparse
import json
from pathlib import Path
 
import pandas as pd
import matplotlib.pyplot as plt
 
QUALITY_ORDER = ["basic", "medium", "premium"]
QUALITY_COLORS = {"basic": "#d62728", "medium": "#ff7f0e", "premium": "#2ca02c"}
 
 
def load_all_records(raw_dir):
    """Reads every *.jsonl file in raw_dir into one long-format DataFrame,
    one row per individual product purchased."""
    rows = []
    for path in sorted(Path(raw_dir).glob("*.jsonl")):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                persona = rec["persona"]
                seed = rec["seed"]
                day = rec["day"]
                for meal_type, items in rec["meals"].items():
                    for item in items:
                        rows.append({
                            "persona": persona,
                            "seed": seed,
                            "day": day,
                            "meal_type": meal_type,
                            "product_id": item["product_id"],
                            "quality": item["quality"],
                            "price": item["price"],
                        })
    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError(f"No data found in {raw_dir} - did the experiment produce any .jsonl files?")
    df["quality"] = pd.Categorical(df["quality"], categories=QUALITY_ORDER, ordered=True)
    return df
 
 
def plot_overall_quality_counts(df, plots_dir):
    """1) Total premium/medium/basic count per persona, across all seeds/days."""
    counts = df.groupby(["persona", "quality"], observed=True).size().unstack(fill_value=0)
    counts = counts.reindex(columns=QUALITY_ORDER, fill_value=0)
 
    fig, ax = plt.subplots(figsize=(8, 5))
    counts.plot(kind="bar", stacked=True, ax=ax,
                color=[QUALITY_COLORS[q] for q in QUALITY_ORDER])
    ax.set_title("Total items purchased by quality tier, per persona")
    ax.set_xlabel("Persona")
    ax.set_ylabel("Number of items purchased")
    ax.legend(title="Quality")
    plt.xticks(rotation=0)
    plt.tight_layout()
 
    out_path = Path(plots_dir) / "overall_quality_counts.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")
 
    # also print raw numbers to console for a quick sanity check
    print("\nOverall counts:")
    print(counts)
    print()
 
 
def plot_over_time_per_persona(df, plots_dir):
    """2) For each persona: quality mix per day, averaged (summed) over seeds."""
    for persona in sorted(df["persona"].unique()):
        sub = df[df["persona"] == persona]
        daily_counts = (
            sub.groupby(["day", "quality"], observed=True)
            .size()
            .unstack(fill_value=0)
            .reindex(columns=QUALITY_ORDER, fill_value=0)
            .sort_index()
        )
 
        fig, ax = plt.subplots(figsize=(10, 5))
        daily_counts.plot(kind="bar", stacked=True, ax=ax,
                           color=[QUALITY_COLORS[q] for q in QUALITY_ORDER])
        ax.set_title(f"Quality mix over time - {persona} (summed across all seeds)")
        ax.set_xlabel("Day")
        ax.set_ylabel("Number of items purchased")
        ax.legend(title="Quality")
        plt.tight_layout()
 
        out_path = Path(plots_dir) / f"over_time_{persona}.png"
        plt.savefig(out_path, dpi=150)
        plt.close()
        print(f"Saved {out_path}")
 
 
def plot_per_seed(df, plots_dir):
    """3) One plot per (persona, seed) combination: quality mix per day."""
    for persona in sorted(df["persona"].unique()):
        for seed in sorted(df[df["persona"] == persona]["seed"].unique()):
            sub = df[(df["persona"] == persona) & (df["seed"] == seed)]
            daily_counts = (
                sub.groupby(["day", "quality"], observed=True)
                .size()
                .unstack(fill_value=0)
                .reindex(columns=QUALITY_ORDER, fill_value=0)
                .sort_index()
            )
 
            fig, ax = plt.subplots(figsize=(10, 5))
            daily_counts.plot(kind="bar", stacked=True, ax=ax,
                               color=[QUALITY_COLORS[q] for q in QUALITY_ORDER])
            ax.set_title(f"Quality mix over time - {persona}, seed={seed}")
            ax.set_xlabel("Day")
            ax.set_ylabel("Number of items purchased")
            ax.legend(title="Quality")
            plt.tight_layout()
 
            out_path = Path(plots_dir) / f"per_seed_{persona}_seed{seed}.png"
            plt.savefig(out_path, dpi=150)
            plt.close()
            print(f"Saved {out_path}")
 
 
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw_dir", default="results/exp_01/raw")
    parser.add_argument("--plots_dir", default="plots/exp_01")
    parser.add_argument("--metrics_dir", default="results/exp_01/metrics")
    args = parser.parse_args()
 
    Path(args.plots_dir).mkdir(parents=True, exist_ok=True)
    Path(args.metrics_dir).mkdir(parents=True, exist_ok=True)
 
    df = load_all_records(args.raw_dir)
    print(f"Loaded {len(df)} purchased items from {df['persona'].nunique()} personas, "
          f"{df['seed'].nunique()} seeds, {df['day'].nunique()} days")
 
    # save tidy long-format table for later stats work
    csv_path = Path(args.metrics_dir) / "purchases_long.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved tidy data to {csv_path}")
 
    plot_overall_quality_counts(df, args.plots_dir)
    plot_over_time_per_persona(df, args.plots_dir)
    plot_per_seed(df, args.plots_dir)
 
 
if __name__ == "__main__":
    main()