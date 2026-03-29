# Session: autoresearch-trading-system-build — 2026-03-29

## Status: In Progress

## Accomplished
- [x] Built complete autoresearch trading strategy optimizer system from scratch
- [x] `prepare.py` — Data download (yfinance), temporal splits (train/val/test), vectorized backtester with transaction costs/slippage/1-day delay, composite scoring with overfitting penalties, Buy & Hold benchmark function
- [x] `strategy.py` — Editable strategy file with CONFIG dict + generate_signals(). Current best: SMA 40/200 + ATR volatility filter
- [x] `run_experiment.py` — Experiment harness: backtest train+val, compute B&H score, rich descriptions with CONFIG params, JSONL logging, 60s timeout, error handling
- [x] `evaluate_test.py` — Sacred holdout test evaluator with YES confirmation prompt
- [x] `generate_pine.py` — Translates strategy.py to TradingView Pine Script v5 (detects SMA, EMA, RSI, MACD, ATR, Bollinger, ADX, volume, Donchian, Stochastic patterns)
- [x] `results/dashboard.html` — Live Chart.js dashboard with auto-refresh: score/Sharpe/return/drawdown charts, B&H as Run #0, ETF universe info, temporal splits panel, experiment log table with B&H comparison columns (vs delta), Pine Script modal on winner row pill
- [x] `CLAUDE.md` + `program.md` — Agent loop instructions + research directions
- [x] Ran 10-iteration loop with Sonnet: best score 1.1802 (SMA 40/200 + ATR 1.5x filter)
- [x] Launched 100-iteration loop with Sonnet (STILL RUNNING in background)
- [x] GitHub repo created (public): https://github.com/Goro2030/autoresearch
- [x] Data CSVs committed to repo (8 tickers: SPY, QQQ, IWM, TLT, GLD, EFA, VNQ, XLE)
- [x] Drafted email in Chilean Spanish for Hernán (stock trader friend)

## Key Decisions
- **Parquet→CSV fallback**: yfinance parquet had pyarrow dictionary encoding issues; switched to CSV as download format, parquet as preferred load format for predownloaded data
- **Sonnet for loop agent**: Opus is overkill for the mechanical hypothesis/test/commit cycle. Sonnet is sufficient and much cheaper. Haiku considered too weak for hypothesis formation.
- **Pine Script at end only**: Generating Pine Script per-KEEP wastes tokens. Now only generated after all rounds complete via `python generate_pine.py -o results/best_strategy.pine`
- **B&H as Run #0**: Buy & Hold scored through the same composite scoring function (-0.2551 due to -29.6% max drawdown penalty), displayed as first row in dashboard
- **Equal-weight portfolio**: Strategy runs independently per ticker, combined as equal-weight average daily returns

## Blockers
- [ ] 100-round Sonnet loop still running in background (agent `autoresearch-100`)

## Next Steps
- [ ] Check results of 100-round loop when it completes
- [ ] Generate Pine Script for final winner: `python generate_pine.py -o results/best_strategy.pine`
- [ ] Run holdout test evaluation: `python evaluate_test.py`
- [ ] Push final results + Pine Script to GitHub
- [ ] Consider adding short-selling support (v2)
- [ ] Consider per-ticker optimization mode
- [ ] Consider adding equity curve chart to dashboard

## Context to Resume
- HTTP server running on port 8088 serving dashboard: `cd results && python -m http.server 8088`
- Background agent `autoresearch-100` is running 100 Sonnet iterations — check output file or dashboard for progress
- Current best score from prior 10-round run: 1.1802 (SMA 40/200 + ATR vol filter 1.5x, 3 params)
- Working directory: `/mnt/c/Development/autoresearch`
- Git remote: `origin` → `https://github.com/Goro2030/autoresearch.git` (public, master branch)

## Files Modified This Session
- `prepare.py` — Data download, backtester, scoring, `run_buy_and_hold()` function
- `strategy.py` — Agent-editable strategy (currently SMA 40/200 + ATR filter)
- `run_experiment.py` — Experiment harness with B&H scoring, rich descriptions, numpy JSON fix
- `evaluate_test.py` — Holdout test evaluator
- `generate_pine.py` — TradingView Pine Script generator from strategy.py
- `program.md` — Research directions for agent
- `CLAUDE.md` — Agent loop instructions (Sonnet model, post-loop Pine Script step)
- `results/dashboard.html` — Full live dashboard with charts, B&H Run #0, ETF/splits info, Pine Script modal, wide Description column
- `results/experiment_log.jsonl` — Experiment results (being written by running agent)
- `.gitignore` — Removed `data/` exclusion
- `data/*.csv` — 8 ticker CSV files committed
- `README.md` — Full setup docs assuming Claude Code CLI
