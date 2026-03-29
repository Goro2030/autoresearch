# Research Directions for Trading Strategy Optimization

## Current Baseline
Simple SMA crossover (20/50). Start by understanding its score, then improve.

## Directions to Explore (in rough priority order)

### 1. Indicator Selection
- Try RSI-based mean reversion (buy oversold, sell overbought)
- Try MACD signal line crossovers
- Try Bollinger Band breakout/mean-reversion
- Try ADX as a trend filter (only trade when trend is strong)
- Try volume confirmation (require above-average volume for entries)

### 2. Combining Indicators
- Trend + filter combos (e.g., SMA crossover but only when ADX > 25)
- Momentum + mean-reversion (e.g., RSI for timing within SMA trend)
- Keep combinations to 2-3 indicators max. More is almost always overfit.

### 3. Exit Logic
- Trailing stops based on ATR
- Time-based exits (exit after N bars if no profit target hit)
- Profit targets as a multiple of ATR

### 4. Parameter Tuning
- Once a good indicator combo is found, tune parameters
- Prefer round/robust numbers (20, 50, 200) over precise ones (17, 53, 187)
- If the strategy is sensitive to small parameter changes, it is overfit

### 5. Cross-Asset Behavior
- The strategy runs on each ticker independently
- Strategies that work across multiple asset classes are more robust
- If a strategy only works on 1-2 tickers, it is likely overfit

## Things to AVOID
- Do NOT add more than 6 parameters to CONFIG. Complexity penalty will kill your score.
- Do NOT try to fit specific historical events (COVID crash, 2022 bear). These are one-time.
- Do NOT use lookahead bias. Signals at time T must use only data available at time T.
- Do NOT modify prepare.py or run_experiment.py.
- If train Sharpe is much higher than validation Sharpe, you are overfitting. Simplify.
