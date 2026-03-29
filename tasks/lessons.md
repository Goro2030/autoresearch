# Lessons Learned

## 2026-03-29 — Autoresearch Build

- **Pattern**: yfinance parquet output caused pyarrow "Column cannot have more than one dictionary" error
- **Rule**: Use CSV for yfinance downloads, only use parquet for predownloaded/pre-processed data

- **Pattern**: numpy bool/int/float types are not JSON serializable
- **Rule**: Always add a `_jsonify()` helper when writing numpy-derived data to JSON

- **Pattern**: User prefers token cost awareness — generating Pine Script on every KEEP wastes tokens
- **Rule**: Defer expensive generation steps (Pine Script, reports) to end-of-loop, not per-iteration

- **Pattern**: Haiku is too weak for hypothesis-driven research loops, Opus is overkill
- **Rule**: Use Sonnet for autoresearch loops — good balance of reasoning ability and token cost

- **Pattern**: User wants richer descriptions in experiment log, not just the agent's terse one-liner
- **Rule**: Auto-append CONFIG params to descriptions in run_experiment.py for self-documenting logs
