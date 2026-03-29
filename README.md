# Autoresearch: Trading Strategy Optimizer

An autonomous research system inspired by [Karpathy's autoresearch pattern](https://github.com/karpathy/autoresearch), adapted for stock/ETF trading strategy optimization. An AI agent iterates on trading strategies using backtesting as the evaluation loop — modifying strategy parameters and logic, running backtests, scoring results, and keeping only improvements.

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
│  strategy.py │────▶│  Backtester  │────▶│  Scoring    │────▶│  Keep or │
│  (AI edits)  │     │  (train+val) │     │  (anti-     │     │  Discard │
│              │◀────│              │     │   overfit)  │     │          │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────┘
       ▲                                                           │
       └───────────────────────────────────────────────────────────┘
                            loop N times
```

The agent only modifies `strategy.py`. Everything else is fixed infrastructure.

## Project Structure

```
autoresearch/
├── prepare.py           # Data download, backtesting engine, scoring (FIXED)
├── strategy.py          # Trading strategy - the ONLY file the agent edits
├── run_experiment.py    # Experiment harness: backtest + score + log (FIXED)
├── evaluate_test.py     # Holdout test evaluation (manual, human-only)
├── program.md           # Research directions for the agent
├── CLAUDE.md            # Agent loop instructions
├── plot_progress.py     # Generate static PNG chart of progress
├── results/
│   ├── experiment_log.jsonl   # All experiment results (append-only)
│   ├── best_strategy.py       # Current best strategy checkpoint
│   └── dashboard.html         # Live web dashboard
└── data/                      # Price data (gitignored)
```

## Quick Start

### 1. Clone and install dependencies

```bash
git clone https://github.com/Goro2030/autoresearch.git
cd autoresearch
pip install yfinance pandas numpy pyarrow
```

### 2. Download market data

```bash
python prepare.py
```

This downloads daily OHLCV data for 8 tickers (SPY, QQQ, IWM, TLT, GLD, EFA, VNQ, XLE) and caches them in `data/`. Use `--refresh` to force re-download.

If you already have parquet files in `data/`, those will be used automatically.

```bash
# Check data status
python prepare.py --info
```

### 3. Run the baseline experiment

```bash
python run_experiment.py "Baseline"
```

This backtests the current `strategy.py` on train and validation splits, computes a composite score, and logs everything to `results/experiment_log.jsonl`.

### 4. Launch the live dashboard

```bash
cd results
python -m http.server 8088
```

Then open **http://localhost:8088/dashboard.html** in your browser.

The dashboard auto-refreshes every 10 seconds and shows:
- Composite score per experiment (with keep/discard coloring)
- Train vs Validation Sharpe ratio comparison
- Max drawdown history
- Strategy complexity and trade frequency
- Full experiment log table

### 5. Run the autoresearch loop

Using [Claude Code](https://claude.com/claude-code):

```bash
cd autoresearch
claude
# Then tell it: "Read CLAUDE.md and run 20 iterations of the autoresearch loop"
```

The agent will autonomously:
1. Read the current strategy and past experiment results
2. Form a hypothesis for improvement
3. Modify `strategy.py` (one change at a time)
4. Run the experiment and check the score
5. Keep improvements, revert failures
6. Commit each step to git history

You can watch progress live on the dashboard.

## Overfitting Prevention

This is the core architectural concern. The system uses multiple safeguards:

| Safeguard | How it works |
|-----------|-------------|
| **Train/Val/Test splits** | Agent only sees train + validation. Test is holdout for final human evaluation. |
| **Consistency penalty** | If train Sharpe >> validation Sharpe, the score is penalized. |
| **Complexity penalty** | Each tunable parameter costs points. Max 6 parameters allowed. |
| **Drawdown penalty** | Deep drawdowns on validation are penalized. |
| **Trade frequency sanity** | Too few (<5/yr) or too many (>200/yr) trades are penalized. |
| **Regime robustness bonus** | Strategies profitable in both up and down markets score higher. |
| **Sharpe cap** | Validation Sharpe is capped at 3.0 to prevent outlier chasing. |

## Temporal Splits

| Split | Period | Purpose |
|-------|--------|---------|
| **Train** | 2014-01-01 to 2019-12-31 | Strategy development (6 years) |
| **Validation** | 2020-01-01 to 2022-12-31 | Score optimization (3 years, includes COVID + 2022 bear) |
| **Test** | 2023-01-01 to 2025-03-01 | Final evaluation only (NEVER exposed to agent) |

## Final Evaluation

When you're done optimizing, evaluate the winning strategy on the holdout test set:

```bash
python evaluate_test.py
```

This requires typing `YES` to confirm, and compares train/validation/test performance to assess overfitting.

## Scoring Formula

```
score = min(val_sharpe, 3.0)                          # Primary signal
      - 0.5 * max(0, train_sharpe - val_sharpe - 0.3) # Overfit penalty
      - 0.05 * max(0, complexity - 3)                  # Complexity penalty
      + drawdown_penalty                                # If max_dd < -25%
      + frequency_penalty                               # If trades/yr < 5 or > 200
      + 0.3 * min(up_month_pct, down_month_pct)        # Regime bonus
```

## Backtest Settings

- Initial capital: $100,000
- Long only (no shorting)
- Transaction cost: 0.1% round trip
- Slippage: 0.05% per trade
- 1-day execution delay (signal on T, trade on T+1 open)
- Equal weight across all tickers

## License

MIT
