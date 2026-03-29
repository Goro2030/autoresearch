"""
Plot autoresearch experiment progress.
Reads results/experiment_log.jsonl and generates a multi-panel chart.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

LOG_FILE = Path(__file__).parent / "results" / "experiment_log.jsonl"
OUTPUT_FILE = Path(__file__).parent / "results" / "progress.png"


def load_experiments():
    entries = []
    with open(LOG_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def plot(entries):
    n = len(entries)
    xs = [e["experiment"] for e in entries]
    scores = [e["score"] for e in entries]
    kept = [e["kept"] for e in entries]
    val_sharpes = [e["val_sharpe"] for e in entries]
    train_sharpes = [e["train_sharpe"] for e in entries]
    max_dds = [e["max_drawdown"] for e in entries]
    complexities = [e["complexity"] for e in entries]
    trades_yr = [e["trades_per_year"] for e in entries]
    descriptions = [e.get("description", "") for e in entries]

    # Running best score
    best_so_far = []
    current_best = float("-inf")
    for s, k in zip(scores, kept):
        if k and s > current_best:
            current_best = s
        best_so_far.append(current_best)

    # Color scheme
    colors_score = ["#2ecc71" if k else "#e74c3c" for k in kept]
    bg_color = "#1a1a2e"
    panel_color = "#16213e"
    text_color = "#e0e0e0"
    grid_color = "#2a2a4a"
    accent_green = "#2ecc71"
    accent_red = "#e74c3c"
    accent_blue = "#3498db"
    accent_orange = "#f39c12"
    accent_purple = "#9b59b6"

    fig, axes = plt.subplots(3, 2, figsize=(16, 12), facecolor=bg_color)
    fig.suptitle("Autoresearch: Trading Strategy Optimization",
                 color=text_color, fontsize=18, fontweight="bold", y=0.98)

    for ax in axes.flat:
        ax.set_facecolor(panel_color)
        ax.tick_params(colors=text_color, labelsize=9)
        ax.xaxis.label.set_color(text_color)
        ax.yaxis.label.set_color(text_color)
        ax.title.set_color(text_color)
        for spine in ax.spines.values():
            spine.set_color(grid_color)
        ax.grid(True, alpha=0.2, color=grid_color)

    # Panel 1: Composite Score per experiment
    ax1 = axes[0, 0]
    ax1.bar(xs, scores, color=colors_score, alpha=0.8, width=0.7, edgecolor="none")
    ax1.plot(xs, best_so_far, color=accent_orange, linewidth=2.5, marker="",
             linestyle="--", label="Best so far", zorder=5)
    ax1.set_xlabel("Experiment #")
    ax1.set_ylabel("Composite Score")
    ax1.set_title("Score per Experiment")
    ax1.legend(facecolor=panel_color, edgecolor=grid_color, labelcolor=text_color, fontsize=9)
    # Add keep/discard labels
    for i, (x, s, k) in enumerate(zip(xs, scores, kept)):
        label = "KEEP" if k else "DISC"
        ax1.text(x, s + 0.02, label, ha="center", va="bottom", fontsize=7,
                 color=accent_green if k else accent_red, fontweight="bold")

    # Panel 2: Train vs Validation Sharpe
    ax2 = axes[0, 1]
    w = 0.35
    ax2.bar([x - w/2 for x in xs], train_sharpes, w, color=accent_blue, alpha=0.7, label="Train Sharpe")
    ax2.bar([x + w/2 for x in xs], val_sharpes, w, color=accent_green, alpha=0.7, label="Val Sharpe")
    ax2.axhline(y=0, color=text_color, linewidth=0.5, alpha=0.3)
    ax2.set_xlabel("Experiment #")
    ax2.set_ylabel("Sharpe Ratio")
    ax2.set_title("Train vs Validation Sharpe (overfit gap)")
    ax2.legend(facecolor=panel_color, edgecolor=grid_color, labelcolor=text_color, fontsize=9)

    # Panel 3: Max Drawdown
    ax3 = axes[1, 0]
    ax3.bar(xs, [dd * 100 for dd in max_dds], color=accent_red, alpha=0.7, width=0.7)
    ax3.axhline(y=-25, color=accent_orange, linewidth=1, linestyle="--", alpha=0.6, label="Penalty threshold (-25%)")
    ax3.set_xlabel("Experiment #")
    ax3.set_ylabel("Max Drawdown (%)")
    ax3.set_title("Validation Max Drawdown")
    ax3.legend(facecolor=panel_color, edgecolor=grid_color, labelcolor=text_color, fontsize=9)

    # Panel 4: Complexity & Trades/Year
    ax4 = axes[1, 1]
    ax4_twin = ax4.twinx()
    ax4.bar([x - 0.2 for x in xs], complexities, 0.4, color=accent_purple, alpha=0.7, label="Complexity")
    ax4_twin.plot(xs, trades_yr, color=accent_orange, marker="o", markersize=5, linewidth=1.5, label="Trades/yr")
    ax4.set_xlabel("Experiment #")
    ax4.set_ylabel("Complexity (params)")
    ax4_twin.set_ylabel("Trades/Year")
    ax4.set_title("Complexity & Trade Frequency")
    ax4.yaxis.label.set_color(accent_purple)
    ax4_twin.yaxis.label.set_color(accent_orange)
    ax4_twin.tick_params(colors=text_color)
    ax4_twin.spines["right"].set_color(grid_color)
    # Combined legend
    lines1, labels1 = ax4.get_legend_handles_labels()
    lines2, labels2 = ax4_twin.get_legend_handles_labels()
    ax4.legend(lines1 + lines2, labels1 + labels2,
               facecolor=panel_color, edgecolor=grid_color, labelcolor=text_color, fontsize=9)

    # Panel 5: Score evolution with descriptions
    ax5 = axes[2, 0]
    for i, (x, s, k, desc) in enumerate(zip(xs, scores, kept, descriptions)):
        color = accent_green if k else accent_red
        ax5.scatter(x, s, color=color, s=80, zorder=5, edgecolors="white", linewidth=0.5)
        # Truncate long descriptions
        short = desc[:30] + "..." if len(desc) > 30 else desc
        ax5.annotate(short, (x, s), textcoords="offset points", xytext=(5, 8),
                     fontsize=6.5, color=text_color, alpha=0.85, rotation=15)
    ax5.plot(xs, best_so_far, color=accent_orange, linewidth=2, linestyle="--", alpha=0.8)
    ax5.set_xlabel("Experiment #")
    ax5.set_ylabel("Score")
    ax5.set_title("Experiment Timeline (annotated)")

    # Panel 6: Summary stats
    ax6 = axes[2, 1]
    ax6.axis("off")
    kept_count = sum(kept)
    discard_count = n - kept_count
    best_idx = max(range(n), key=lambda i: scores[i] if kept[i] else float("-inf"))
    best_entry = entries[best_idx]

    summary_lines = [
        f"Total Experiments:  {n}",
        f"Kept / Discarded:   {kept_count} / {discard_count}",
        f"",
        f"Best Score:         {best_entry['score']:.4f}  (Exp #{best_entry['experiment']})",
        f"Best Val Sharpe:    {best_entry['val_sharpe']:.4f}",
        f"Best Train Sharpe:  {best_entry['train_sharpe']:.4f}",
        f"Best Max Drawdown:  {best_entry['max_drawdown']:.2%}",
        f"Best Trades/Year:   {best_entry['trades_per_year']:.0f}",
        f"Best Complexity:    {best_entry['complexity']}",
        f"",
        f"Best Config:",
    ]
    for k, v in best_entry.get("config", {}).items():
        summary_lines.append(f"  {k}: {v}")

    summary_text = "\n".join(summary_lines)
    ax6.text(0.05, 0.95, summary_text, transform=ax6.transAxes,
             fontsize=11, verticalalignment="top", fontfamily="monospace",
             color=text_color, bbox=dict(boxstyle="round,pad=0.5", facecolor=panel_color,
                                          edgecolor=grid_color, alpha=0.9))
    ax6.set_title("Summary", color=text_color)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight", facecolor=bg_color)
    plt.close()
    print(f"Chart saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    entries = load_experiments()
    if not entries:
        print("No experiments found in log.")
    else:
        print(f"Plotting {len(entries)} experiments...")
        plot(entries)
