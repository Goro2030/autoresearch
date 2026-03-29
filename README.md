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

The agent only modifies `strategy.py`. Everything else is fixed infrastructure. Each experiment is compared against a **Buy & Hold** benchmark to measure real alpha.

## Prerequisites

- **[Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)** installed and authenticated
- **Python 3.10+** with pip

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/Goro2030/autoresearch.git
cd autoresearch
pip install yfinance pandas numpy pyarrow
```

### 2. Download market data

```bash
python prepare.py
```

Downloads daily OHLCV data for 8 tickers (SPY, QQQ, IWM, TLT, GLD, EFA, VNQ, XLE) and caches them in `data/`. If you already have `.parquet` files there, they'll be used automatically.

```bash
# Check data status
python prepare.py --info
```

### 3. Launch the live dashboard

In a separate terminal:

```bash
cd autoresearch/results
python -m http.server 8088
```

Open **http://localhost:8088/dashboard.html** in your browser. It auto-refreshes every 10 seconds with charts showing score progression, Sharpe ratios, drawdowns, and a full experiment log table with Buy & Hold comparisons.

### 4. Run the autoresearch loop with Claude Code

From the project root:

```bash
cd autoresearch
claude
```

Claude Code will read `CLAUDE.md` automatically. Then tell it:

```
Run 20 iterations of the autoresearch loop
```

> **Cost optimization:** The loop runs as a Sonnet subagent (configured in `CLAUDE.md`).
> Sonnet is sufficient for the mechanical hypothesis/test/commit cycle and uses significantly fewer tokens than Opus.

The agent will autonomously:
1. Read the current strategy and past experiment results
2. Form a hypothesis for improvement
3. Modify `strategy.py` (one change at a time)
4. Run `python run_experiment.py` and check the score
5. Keep improvements (git commit), revert failures
6. Compare every experiment against Buy & Hold benchmark
7. Repeat for the requested number of iterations

Watch the dashboard update in real time as experiments run.

#### Non-interactive mode

You can also run it headlessly without entering the REPL:

```bash
claude -p "Read CLAUDE.md and run 10 iterations of the autoresearch loop"
```

Or chain multiple sessions:

```bash
for i in $(seq 1 5); do
  claude -p "Read CLAUDE.md and run 10 iterations of the autoresearch loop"
done
```

### 5. Evaluate the final strategy

Once you're satisfied with the best score, run the holdout test:

```bash
python evaluate_test.py
```

This evaluates against the sacred test set (2023-2025) and requires typing `YES` to confirm. It compares train/validation/test performance to assess overfitting.

## Project Structure

```
autoresearch/
├── prepare.py           # Data download, backtesting engine, scoring (FIXED)
├── strategy.py          # Trading strategy - the ONLY file the agent edits
├── run_experiment.py    # Experiment harness: backtest + score + log (FIXED)
├── evaluate_test.py     # Holdout test evaluation (manual, human-only)
├── program.md           # Research directions for the agent
├── CLAUDE.md            # Agent loop instructions
├── results/
│   ├── experiment_log.jsonl   # All experiment results (append-only)
│   ├── best_strategy.py       # Current best strategy checkpoint
│   └── dashboard.html         # Live web dashboard
└── data/                      # Price data (gitignored)
```

## Overfitting Prevention

| Safeguard | How it works |
|-----------|-------------|
| **Train/Val/Test splits** | Agent only sees train + validation. Test is holdout for final human evaluation. |
| **Buy & Hold baseline** | Every experiment is compared against passive investing. No alpha = no point. |
| **Consistency penalty** | If train Sharpe >> validation Sharpe, the score is penalized. |
| **Complexity penalty** | Each tunable parameter costs points. Max 6 parameters allowed. |
| **Drawdown penalty** | Deep drawdowns (>25%) on validation are penalized. |
| **Trade frequency sanity** | Too few (<5/yr) or too many (>200/yr) trades are penalized. |
| **Regime robustness bonus** | Strategies profitable in both up and down markets score higher. |
| **Sharpe cap** | Validation Sharpe is capped at 3.0 to prevent outlier chasing. |

## Temporal Splits

| Split | Period | Purpose |
|-------|--------|---------|
| **Train** | 2014-01-01 to 2019-12-31 | Strategy development (6 years) |
| **Validation** | 2020-01-01 to 2022-12-31 | Score optimization (3 years, includes COVID + 2022 bear) |
| **Test** | 2023-01-01 to 2025-03-01 | Final evaluation only (NEVER exposed to agent) |

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
- Equal weight across all 8 tickers

## License

MIT
