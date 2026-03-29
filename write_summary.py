"""
write_summary.py - Generate run_summary.json for the dashboard completion popup.
Run this after all experiment rounds are complete.
"""

import json
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"
LOG_FILE = RESULTS_DIR / "experiment_log.jsonl"
SUMMARY_FILE = RESULTS_DIR / "run_summary.json"


def main():
    entries = []
    with open(LOG_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    if not entries:
        print("No experiments found.")
        return

    kept = [e for e in entries if e.get("kept")]
    best = max(kept, key=lambda e: e["score"]) if kept else entries[0]
    first_kept = kept[0] if kept else entries[0]

    initial_score = first_kept["score"]
    best_score = best["score"]
    improvement_pct = ((best_score - initial_score) / abs(initial_score) * 100) if initial_score != 0 else 0

    summary = {
        "total_experiments": len(entries),
        "total_kept": len(kept),
        "total_discarded": len(entries) - len(kept),
        "initial_score": round(initial_score, 4),
        "best_score": round(best_score, 4),
        "best_experiment": best["experiment"],
        "best_description": best.get("description", ""),
        "best_val_sharpe": best.get("val_sharpe", 0),
        "best_val_return": best.get("val_return", 0),
        "best_max_drawdown": best.get("max_drawdown", 0),
        "best_trades_per_year": best.get("trades_per_year", 0),
        "best_complexity": best.get("complexity", 0),
        "best_config": best.get("config", {}),
        "improvement_pct": round(improvement_pct, 1),
        "bh_score": best.get("bh_score"),
        "bh_val_sharpe": best.get("bh_val_sharpe"),
        "bh_val_return": best.get("bh_val_return"),
    }

    with open(SUMMARY_FILE, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Summary written to {SUMMARY_FILE}")
    print(f"  {len(entries)} experiments, best score {best_score:.4f} (#{best['experiment']})")


if __name__ == "__main__":
    main()
