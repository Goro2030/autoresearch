"""
run_experiment.py - FIXED experiment harness. The agent must NEVER modify this file.

Runs one experiment cycle: import strategy, backtest train+val, score, log results.
"""

import importlib
import json
import signal
import sys
import traceback

import numpy as np
from datetime import datetime, timezone
from pathlib import Path

# Timeout for each experiment (seconds)
EXPERIMENT_TIMEOUT = 60

RESULTS_DIR = Path(__file__).parent / "results"
LOG_FILE = RESULTS_DIR / "experiment_log.jsonl"
BEST_STRATEGY_FILE = RESULTS_DIR / "best_strategy.py"


class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("Experiment timed out (>60s). Strategy too slow or has infinite loop.")


def _get_experiment_number() -> int:
    """Get the next experiment number from the log file."""
    if not LOG_FILE.exists():
        return 1
    count = 0
    with open(LOG_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                count += 1
    return count + 1


def _get_current_best_score() -> float:
    """Read the current best score from the log file."""
    if not LOG_FILE.exists():
        return float("-inf")
    best = float("-inf")
    with open(LOG_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("kept", False) and entry.get("score", float("-inf")) > best:
                    best = entry["score"]
            except json.JSONDecodeError:
                continue
    return best


def run_experiment(description: str = "manual run") -> float:
    """
    Run a single experiment cycle.

    1. Import/reload strategy.py
    2. Run backtest on TRAIN split
    3. Run backtest on VALIDATION split
    4. Compute composite score
    5. Log results
    6. Return score
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    experiment_num = _get_experiment_number()
    current_best = _get_current_best_score()
    timestamp = datetime.now(timezone.utc).isoformat()

    print(f"\n{'#'*60}")
    print(f"  EXPERIMENT #{experiment_num}")
    print(f"  {timestamp}")
    print(f"  Description: {description}")
    print(f"  Current best score: {current_best}")
    print(f"{'#'*60}")

    # Set timeout (Unix only; on Windows, skip timeout)
    has_alarm = hasattr(signal, "SIGALRM")
    if has_alarm:
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(EXPERIMENT_TIMEOUT)

    try:
        # Step 1: Import/reload strategy
        print("\n[1/4] Loading strategy...")
        if "strategy" in sys.modules:
            strategy_module = importlib.reload(sys.modules["strategy"])
        else:
            strategy_module = importlib.import_module("strategy")

        config = getattr(strategy_module, "CONFIG", {})
        print(f"  CONFIG: {config}")

        # Step 2: Count complexity
        from prepare import count_strategy_complexity
        complexity = count_strategy_complexity(strategy_module)
        print(f"  Complexity: {complexity} parameters")

        # Step 3: Run backtest on TRAIN
        print("\n[2/5] Running backtest on TRAIN split...")
        from prepare import run_backtest, run_buy_and_hold, print_report, compute_score
        train_results = run_backtest(strategy_module, split="train")
        print_report(train_results, "TRAIN Results")

        # Step 4: Run backtest on VALIDATION
        print("\n[3/5] Running backtest on VALIDATION split...")
        val_results = run_backtest(strategy_module, split="validation")
        print_report(val_results, "VALIDATION Results")

        # Step 5: Buy & Hold benchmark
        print("\n[4/5] Computing Buy & Hold benchmark...")
        bh_val = run_buy_and_hold(split="validation")
        print_report(bh_val, "BUY & HOLD Benchmark (Validation)")

        # Step 6: Compute score
        print("\n[5/5] Computing composite score...")
        score = compute_score(train_results, val_results, complexity)

        improved = score > current_best
        kept = improved

        # Print score breakdown
        val_sharpe = val_results["sharpe"]
        train_sharpe = train_results["sharpe"]
        max_dd = val_results["max_drawdown"]
        trades_yr = val_results["trades_per_year"]

        print(f"\n  Score Breakdown:")
        print(f"    Val Sharpe (capped):    {min(val_sharpe, 3.0):.4f}")
        overfit_gap = max(0, train_sharpe - val_sharpe - 0.3)
        print(f"    Consistency penalty:    {-0.5 * overfit_gap:.4f}")
        print(f"    Complexity penalty:     {-0.05 * max(0, complexity - 3):.4f}")
        dd_pen = 2.0 * (max_dd + 0.25) if max_dd < -0.25 else 0.0
        print(f"    Drawdown penalty:       {dd_pen:.4f}")
        freq_pen = -0.5 if trades_yr < 5 else (-0.3 if trades_yr > 200 else 0.0)
        print(f"    Frequency penalty:      {freq_pen:.4f}")
        regime_bonus = 0.3 * min(
            val_results.get("pct_profitable_up_months", 0.5),
            val_results.get("pct_profitable_down_months", 0.5),
        )
        print(f"    Regime bonus:           {regime_bonus:.4f}")

        print(f"\n  {'='*40}")
        print(f"  COMPOSITE SCORE: {score:.4f}")
        if improved:
            print(f"  ✅ NEW BEST (previous: {current_best})")
        else:
            print(f"  ❌ No improvement (best: {current_best})")
        print(f"  {'='*40}")

    except TimeoutError as e:
        print(f"\n  ⏰ TIMEOUT: {e}")
        score = -999.0
        config = {}
        complexity = 0
        train_results = {"sharpe": 0, "total_return": 0, "max_drawdown": 0, "trades_per_year": 0}
        val_results = {"sharpe": 0, "total_return": 0, "max_drawdown": 0, "trades_per_year": 0,
                       "pct_profitable_up_months": 0, "pct_profitable_down_months": 0}
        bh_val = {"sharpe": 0, "total_return": 0, "max_drawdown": 0}
        kept = False
        improved = False

    except Exception as e:
        print(f"\n  💥 ERROR: {e}")
        traceback.print_exc()
        score = -999.0
        config = {}
        complexity = 0
        train_results = {"sharpe": 0, "total_return": 0, "max_drawdown": 0, "trades_per_year": 0}
        val_results = {"sharpe": 0, "total_return": 0, "max_drawdown": 0, "trades_per_year": 0,
                       "pct_profitable_up_months": 0, "pct_profitable_down_months": 0}
        bh_val = {"sharpe": 0, "total_return": 0, "max_drawdown": 0}
        kept = False
        improved = False

    finally:
        if has_alarm:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    # Save best strategy if improved
    if kept:
        strategy_path = Path(__file__).parent / "strategy.py"
        if strategy_path.exists():
            BEST_STRATEGY_FILE.write_text(strategy_path.read_text())
            print(f"\n  💾 Best strategy saved to {BEST_STRATEGY_FILE}")

    # Log experiment
    log_entry = {
        "experiment": experiment_num,
        "timestamp": timestamp,
        "description": description,
        "score": score,
        "kept": kept,
        "config": config,
        "complexity": complexity,
        "train_sharpe": train_results.get("sharpe", 0),
        "val_sharpe": val_results.get("sharpe", 0),
        "train_return": train_results.get("total_return", 0),
        "val_return": val_results.get("total_return", 0),
        "max_drawdown": val_results.get("max_drawdown", 0),
        "trades_per_year": val_results.get("trades_per_year", 0),
        "pct_profitable_up_months": val_results.get("pct_profitable_up_months", 0),
        "pct_profitable_down_months": val_results.get("pct_profitable_down_months", 0),
        "bh_val_sharpe": bh_val.get("sharpe", 0),
        "bh_val_return": bh_val.get("total_return", 0),
        "bh_val_max_dd": bh_val.get("max_drawdown", 0),
    }

    # Ensure all values are JSON-serializable (convert numpy types)
    def _jsonify(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, dict):
            return {k: _jsonify(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_jsonify(v) for v in obj]
        return obj

    log_entry = _jsonify(log_entry)

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Print parseable result line (last line of stdout)
    print(
        f"\nRESULT: score={score:.4f} val_sharpe={val_results.get('sharpe', 0):.4f} "
        f"train_sharpe={train_results.get('sharpe', 0):.4f} "
        f"val_return={val_results.get('total_return', 0):.1f}% "
        f"max_dd={val_results.get('max_drawdown', 0):.1f}% "
        f"trades_per_year={val_results.get('trades_per_year', 0):.0f} "
        f"complexity={complexity}"
    )

    return score


if __name__ == "__main__":
    desc = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "manual run"
    score = run_experiment(description=desc)
    sys.exit(0)
