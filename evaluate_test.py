"""
evaluate_test.py - Holdout test evaluation. Run ONLY on your final strategy.

⚠️  WARNING: This script evaluates against the TEST split.
   Run this ONLY ONCE on your final winning strategy.
   Running it multiple times defeats the purpose of a holdout set.
"""

import importlib
import sys

from prepare import run_backtest, print_report, compute_score, count_strategy_complexity


def main():
    print("\n" + "!" * 60)
    print("!  ⚠️  HOLDOUT TEST EVALUATION")
    print("!  This is the sacred test set.")
    print("!  Run this ONLY on your FINAL strategy.")
    print("!  If you run this and then keep optimizing, your results are invalid.")
    print("!" * 60)

    response = input("\nAre you sure you want to evaluate on the test set? (type 'YES' to confirm): ")
    if response.strip() != "YES":
        print("Aborted. Good discipline.")
        sys.exit(0)

    print("\nLoading strategy...")
    if "strategy" in sys.modules:
        strategy_module = importlib.reload(sys.modules["strategy"])
    else:
        strategy_module = importlib.import_module("strategy")

    config = getattr(strategy_module, "CONFIG", {})
    complexity = count_strategy_complexity(strategy_module)
    print(f"CONFIG: {config}")
    print(f"Complexity: {complexity}")

    # Run on all three splits for comparison
    print("\n--- TRAIN ---")
    train_results = run_backtest(strategy_module, split="train")
    print_report(train_results, "TRAIN Results")

    print("\n--- VALIDATION ---")
    val_results = run_backtest(strategy_module, split="validation")
    print_report(val_results, "VALIDATION Results")

    print("\n--- TEST (HOLDOUT) ---")
    test_results = run_backtest(strategy_module, split="test")
    print_report(test_results, "TEST Results (HOLDOUT)")

    # Compute scores for comparison
    train_val_score = compute_score(train_results, val_results, complexity)
    train_test_score = compute_score(train_results, test_results, complexity)

    print(f"\n{'='*60}")
    print(f"  FINAL EVALUATION SUMMARY")
    print(f"{'='*60}")
    print(f"  Train-Val Score:   {train_val_score:.4f}")
    print(f"  Train-Test Score:  {train_test_score:.4f}")
    print(f"  Score Degradation: {train_val_score - train_test_score:.4f}")
    print()
    print(f"  Train Sharpe:      {train_results['sharpe']:.4f}")
    print(f"  Val Sharpe:        {val_results['sharpe']:.4f}")
    print(f"  Test Sharpe:       {test_results['sharpe']:.4f}")
    print()

    # Overfitting assessment
    sharpe_drop = val_results["sharpe"] - test_results["sharpe"]
    if sharpe_drop > 0.5:
        print("  🔴 LIKELY OVERFIT: Large Sharpe drop from validation to test")
    elif sharpe_drop > 0.2:
        print("  🟡 POSSIBLE OVERFIT: Moderate Sharpe drop from validation to test")
    else:
        print("  🟢 LOOKS ROBUST: Small or no Sharpe drop from validation to test")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
