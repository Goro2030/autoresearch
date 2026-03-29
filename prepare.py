"""
prepare.py - FIXED infrastructure file. The agent must NEVER modify this file.

Data management, backtesting engine, scoring function, and utilities for the
autoresearch trading strategy optimization system.
"""

import argparse
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_TICKERS = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "VNQ", "XLE"]

DATA_DIR = Path(__file__).parent / "data"

# Temporal splits - STRICT, HARDCODED
SPLITS = {
    "train": ("2014-01-01", "2019-12-31"),
    "validation": ("2020-01-01", "2022-12-31"),
    "test": ("2023-01-01", "2025-03-01"),
}

# Backtester settings
INITIAL_CAPITAL = 100_000
TRANSACTION_COST = 0.001  # 0.1% round trip
SLIPPAGE = 0.0005  # 0.05% per trade

# ============================================================================
# DATA MANAGEMENT
# ============================================================================


def download_data(tickers: list[str] = None, refresh: bool = False) -> None:
    """Download daily OHLCV data for tickers and cache as parquet files."""
    import yfinance as yf

    tickers = tickers or DEFAULT_TICKERS
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for ticker in tickers:
        filepath = DATA_DIR / f"{ticker}.csv"
        if filepath.exists() and not refresh:
            print(f"  {ticker}: cached (use --refresh to re-download)")
            continue

        print(f"  {ticker}: downloading...", end=" ", flush=True)
        try:
            df = yf.download(ticker, period="max", auto_adjust=True, progress=False)
            if df.empty:
                print("WARNING: no data returned")
                continue
            # Flatten multi-level columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.to_csv(filepath)
            print(f"OK ({len(df)} rows, {df.index[0].date()} to {df.index[-1].date()})")
        except Exception as e:
            print(f"ERROR: {e}")


def load_data(
    tickers: list[str] = None, split: str = "train"
) -> dict[str, pd.DataFrame]:
    """
    Load cached data for the given tickers and temporal split.

    Returns a dict of {ticker: DataFrame} filtered to the requested date range.
    """
    if split == "test":
        # Check if this is an automated run (not evaluate_test.py)
        caller = os.path.basename(sys.argv[0]) if sys.argv else ""
        if caller != "evaluate_test.py":
            warnings.warn(
                "\n⚠️  WARNING: Accessing TEST split outside of evaluate_test.py!\n"
                "   The test set is sacred and must only be used for final human evaluation.\n"
                "   If this is an automated run, this is a BUG.\n",
                stacklevel=2,
            )

    tickers = tickers or DEFAULT_TICKERS
    start, end = SPLITS[split]
    result = {}

    for ticker in tickers:
        # Prefer parquet (predownloaded), fall back to CSV
        parquet_path = DATA_DIR / f"{ticker}.parquet"
        csv_path = DATA_DIR / f"{ticker}.csv"

        if parquet_path.exists():
            df = pd.read_parquet(parquet_path)
        elif csv_path.exists():
            df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        else:
            print(f"  WARNING: No data for {ticker}. Run `python prepare.py` first.")
            continue
        df.index = pd.to_datetime(df.index)
        mask = (df.index >= start) & (df.index <= end)
        filtered = df.loc[mask].copy()

        if filtered.empty:
            print(f"  WARNING: No data for {ticker} in {split} period ({start} to {end})")
            continue

        result[ticker] = filtered

    return result


# ============================================================================
# BACKTESTING ENGINE
# ============================================================================


def run_backtest(
    strategy_module,
    tickers: list[str] = None,
    split: str = "train",
) -> dict:
    """
    Run a vectorized backtest for the given strategy on the specified split.

    The strategy_module must expose:
      - generate_signals(df: pd.DataFrame) -> pd.Series of 0/1

    Signals at time T are executed at T+1 open (no lookahead bias).

    Returns a results dict with all metrics.
    """
    tickers = tickers or DEFAULT_TICKERS
    data = load_data(tickers, split)

    if not data:
        return _empty_results()

    # Run strategy on each ticker independently, then combine
    all_daily_returns = []
    total_trades = 0
    trade_log = []
    start_date = None
    end_date = None

    for ticker, df in data.items():
        if len(df) < 2:
            continue

        # Generate signals
        try:
            raw_signals = strategy_module.generate_signals(df)
        except Exception as e:
            print(f"  ERROR generating signals for {ticker}: {e}")
            continue

        # Ensure signals are 0 or 1
        signals = raw_signals.clip(0, 1).fillna(0).astype(int)

        # Shift signals by 1 day (signal on T, execute on T+1)
        # This prevents lookahead bias
        signals = signals.shift(1).fillna(0).astype(int)

        # Calculate daily returns
        close = df["Close"].values
        daily_returns = np.diff(close) / close[:-1]  # len = N-1

        # Align signals with returns (signals[:-1] determines position for returns)
        position = signals.values[:-1]  # position held during each return period

        # Detect trades (position changes)
        position_changes = np.diff(np.concatenate([[0], position]))
        trade_indices = np.where(position_changes != 0)[0]
        n_trades = len(trade_indices)
        total_trades += n_trades

        # Apply transaction costs and slippage on trade days
        costs = np.zeros(len(daily_returns))
        for idx in trade_indices:
            if idx < len(costs):
                costs[idx] = TRANSACTION_COST + SLIPPAGE

        # Strategy returns = position * market_return - costs
        strategy_returns = position * daily_returns - costs

        # Build a series with proper date index (excluding first day used for signal shift)
        dates = df.index[1:]
        sr = pd.Series(strategy_returns, index=dates, name=ticker)
        all_daily_returns.append(sr)

        # Track trade log
        for idx in trade_indices:
            if idx < len(dates):
                trade_log.append({
                    "ticker": ticker,
                    "date": str(dates[idx].date()),
                    "action": "BUY" if position_changes[idx] > 0 else "SELL",
                })

        if start_date is None or dates[0] < start_date:
            start_date = dates[0]
        if end_date is None or dates[-1] > end_date:
            end_date = dates[-1]

    if not all_daily_returns:
        return _empty_results()

    # Combine: equal-weight across tickers
    combined = pd.concat(all_daily_returns, axis=1)
    portfolio_returns = combined.mean(axis=1).fillna(0)

    # Compute portfolio value series
    portfolio_value = INITIAL_CAPITAL * (1 + portfolio_returns).cumprod()

    # Compute metrics
    results = _compute_metrics(
        portfolio_returns, portfolio_value, total_trades, trade_log,
        start_date, end_date, data, split
    )

    return results


def _compute_metrics(
    portfolio_returns: pd.Series,
    portfolio_value: pd.Series,
    total_trades: int,
    trade_log: list,
    start_date,
    end_date,
    data: dict,
    split: str,
) -> dict:
    """Compute all backtest metrics from daily returns."""
    n_days = len(portfolio_returns)
    n_years = n_days / 252 if n_days > 0 else 1

    # Annualized return
    total_return = (portfolio_value.iloc[-1] / INITIAL_CAPITAL - 1) if n_days > 0 else 0
    ann_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0

    # Sharpe ratio (annualized, assuming 0 risk-free rate)
    daily_mean = portfolio_returns.mean()
    daily_std = portfolio_returns.std()
    sharpe = (daily_mean / daily_std * np.sqrt(252)) if daily_std > 0 else 0

    # Maximum drawdown
    cummax = portfolio_value.cummax()
    drawdown = (portfolio_value - cummax) / cummax
    max_drawdown = drawdown.min()

    # Trades per year
    trades_per_year = total_trades / n_years if n_years > 0 else 0

    # Win rate
    winning_days = (portfolio_returns > 0).sum()
    total_active_days = (portfolio_returns != 0).sum()
    win_rate = winning_days / total_active_days if total_active_days > 0 else 0

    # Calmar ratio
    calmar = ann_return / abs(max_drawdown) if max_drawdown != 0 else 0

    # Regime robustness: compute monthly returns and compare with SPY
    monthly_portfolio = portfolio_returns.resample("ME").sum()

    # Get SPY monthly returns for regime classification
    spy_data = data.get("SPY")
    if spy_data is not None and len(spy_data) > 1:
        spy_returns = spy_data["Close"].pct_change().dropna()
        spy_monthly = spy_returns.resample("ME").sum()

        # Align indices
        common_months = monthly_portfolio.index.intersection(spy_monthly.index)
        if len(common_months) > 0:
            mp = monthly_portfolio.loc[common_months]
            sm = spy_monthly.loc[common_months]

            up_months = sm > 0
            down_months = sm <= 0

            if up_months.sum() > 0:
                pct_profitable_up = (mp[up_months] > 0).mean()
            else:
                pct_profitable_up = 0.5

            if down_months.sum() > 0:
                pct_profitable_down = (mp[down_months] > 0).mean()
            else:
                pct_profitable_down = 0.5
        else:
            pct_profitable_up = 0.5
            pct_profitable_down = 0.5
    else:
        pct_profitable_up = 0.5
        pct_profitable_down = 0.5

    return {
        "split": split,
        "total_return": round(total_return * 100, 2),  # percentage
        "ann_return": round(ann_return * 100, 2),
        "sharpe": round(sharpe, 4),
        "max_drawdown": round(max_drawdown, 4),
        "trades_per_year": round(trades_per_year, 1),
        "total_trades": total_trades,
        "win_rate": round(win_rate, 4),
        "calmar": round(calmar, 4),
        "n_days": n_days,
        "n_years": round(n_years, 2),
        "final_value": round(portfolio_value.iloc[-1], 2) if len(portfolio_value) > 0 else INITIAL_CAPITAL,
        "pct_profitable_up_months": round(pct_profitable_up, 4),
        "pct_profitable_down_months": round(pct_profitable_down, 4),
        "portfolio_value": portfolio_value,
        "daily_returns": portfolio_returns,
        "trade_log": trade_log,
    }


def _empty_results() -> dict:
    """Return an empty results dict when no data is available."""
    return {
        "split": "unknown",
        "total_return": 0.0,
        "ann_return": 0.0,
        "sharpe": 0.0,
        "max_drawdown": 0.0,
        "trades_per_year": 0.0,
        "total_trades": 0,
        "win_rate": 0.0,
        "calmar": 0.0,
        "n_days": 0,
        "n_years": 0,
        "final_value": INITIAL_CAPITAL,
        "pct_profitable_up_months": 0.5,
        "pct_profitable_down_months": 0.5,
        "portfolio_value": pd.Series(dtype=float),
        "daily_returns": pd.Series(dtype=float),
        "trade_log": [],
    }


# ============================================================================
# SCORING FUNCTION
# ============================================================================


def compute_score(
    train_results: dict, val_results: dict, strategy_complexity: int
) -> float:
    """
    Composite score the agent optimizes. Higher is better.

    Components:
    1. Validation Sharpe ratio (primary signal, annualized)
    2. Train-validation consistency penalty (overfitting detection)
    3. Complexity penalty (fewer parameters = better)
    4. Drawdown penalty (max drawdown on validation)
    5. Trade frequency sanity check
    6. Regime robustness bonus
    """
    val_sharpe = val_results["sharpe"]
    train_sharpe = train_results["sharpe"]
    max_dd = val_results["max_drawdown"]  # negative number
    n_trades_per_year = val_results["trades_per_year"]
    complexity = strategy_complexity

    # Primary: validation Sharpe (capped to reduce outlier chasing)
    sharpe_score = min(val_sharpe, 3.0)

    # Consistency: penalize if train >> validation (overfitting signal)
    overfit_gap = max(0, train_sharpe - val_sharpe - 0.3)
    consistency_penalty = -0.5 * overfit_gap

    # Complexity: each parameter/condition costs points
    complexity_penalty = -0.05 * max(0, complexity - 3)

    # Drawdown: penalize deep drawdowns
    drawdown_penalty = 0.0
    if max_dd < -0.25:
        drawdown_penalty = 2.0 * (max_dd + 0.25)  # negative contribution

    # Trade frequency: penalize extremes
    freq_penalty = 0.0
    if n_trades_per_year < 5:
        freq_penalty = -0.5
    elif n_trades_per_year > 200:
        freq_penalty = -0.3

    # Regime robustness: check up-months vs down-months on SPY
    up_months_profitable = val_results.get("pct_profitable_up_months", 0.5)
    down_months_profitable = val_results.get("pct_profitable_down_months", 0.5)
    regime_bonus = 0.3 * min(up_months_profitable, down_months_profitable)

    total = (
        sharpe_score
        + consistency_penalty
        + complexity_penalty
        + drawdown_penalty
        + freq_penalty
        + regime_bonus
    )

    return round(total, 4)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def count_strategy_complexity(strategy_module) -> int:
    """
    Count strategy complexity by inspecting its CONFIG dict.
    Complexity = number of keys in CONFIG (each is a tunable parameter).
    """
    config = getattr(strategy_module, "CONFIG", {})
    return len(config)


def print_report(results: dict, label: str) -> None:
    """Print a human-readable backtest summary."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Period:           {results['split']} ({results['n_years']:.1f} years, {results['n_days']} trading days)")
    print(f"  Total Return:     {results['total_return']:+.2f}%")
    print(f"  Ann. Return:      {results['ann_return']:+.2f}%")
    print(f"  Sharpe Ratio:     {results['sharpe']:.4f}")
    print(f"  Max Drawdown:     {results['max_drawdown']:.2%}")
    print(f"  Calmar Ratio:     {results['calmar']:.4f}")
    print(f"  Win Rate:         {results['win_rate']:.2%}")
    print(f"  Trades/Year:      {results['trades_per_year']:.1f}")
    print(f"  Total Trades:     {results['total_trades']}")
    print(f"  Final Value:      ${results['final_value']:,.2f}")
    print(f"  Regime (Up):      {results['pct_profitable_up_months']:.2%} months profitable")
    print(f"  Regime (Down):    {results['pct_profitable_down_months']:.2%} months profitable")
    print(f"{'='*60}")


# ============================================================================
# CLI
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="Prepare data for autoresearch trading")
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=DEFAULT_TICKERS,
        help=f"Tickers to download (default: {DEFAULT_TICKERS})",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force re-download of all data",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show data info and split details",
    )
    args = parser.parse_args()

    if args.info:
        print("\n📊 Temporal Splits:")
        for name, (start, end) in SPLITS.items():
            print(f"  {name:12s}: {start} to {end}")
        print(f"\n💰 Backtest Settings:")
        print(f"  Initial Capital:   ${INITIAL_CAPITAL:,}")
        print(f"  Transaction Cost:  {TRANSACTION_COST:.2%}")
        print(f"  Slippage:          {SLIPPAGE:.2%}")
        print(f"\n📁 Data Directory: {DATA_DIR}")

        # Show cached data status
        print(f"\n📦 Cached Data:")
        for ticker in args.tickers:
            parquet_path = DATA_DIR / f"{ticker}.parquet"
            csv_path = DATA_DIR / f"{ticker}.csv"
            if parquet_path.exists():
                df = pd.read_parquet(parquet_path)
                print(f"  {ticker}: {len(df)} rows ({df.index[0].date()} to {df.index[-1].date()}) [parquet]")
            elif csv_path.exists():
                df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
                print(f"  {ticker}: {len(df)} rows ({df.index[0].date()} to {df.index[-1].date()}) [csv]")
            else:
                print(f"  {ticker}: not downloaded")
        return

    print(f"\n📥 Downloading data for {len(args.tickers)} tickers...")
    download_data(args.tickers, refresh=args.refresh)
    print("\n✅ Data preparation complete.")
    print(f"   Files stored in: {DATA_DIR.resolve()}")
    print(f"   Run `python prepare.py --info` to see data details.")


if __name__ == "__main__":
    main()
