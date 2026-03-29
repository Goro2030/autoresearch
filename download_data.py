"""
Download historical OHLCV data for autoresearch-trading.
Run once, then the system works entirely offline.

Usage: python download_data.py
"""
import os
import yfinance as yf

TICKERS = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "VNQ", "XLE"]
OUTPUT_DIR = "data"
START = "2013-01-01"
END = "2025-03-29"

os.makedirs(OUTPUT_DIR, exist_ok=True)

for ticker in TICKERS:
    print(f"Downloading {ticker}...")
    df = yf.download(ticker, start=START, end=END, auto_adjust=True)
    path = os.path.join(OUTPUT_DIR, f"{ticker}.parquet")
    df.to_parquet(path)
    print(f"  -> {path} ({len(df)} rows, {df.index.min().date()} to {df.index.max().date()})")

print("\nDone. All data cached in data/ directory.")
