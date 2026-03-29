# Autoresearch: Trading Strategy Optimization

## Your Role
You are a quantitative researcher optimizing a trading strategy. You modify ONLY `strategy.py`.
DO NOT modify `prepare.py`, `run_experiment.py`, or any infrastructure files.

## The Loop
1. Read `program.md` for research directions and context.
2. Read current `strategy.py` and understand the current approach.
3. Read `results/experiment_log.jsonl` to understand what has been tried and what scores resulted.
4. Form a hypothesis: what change might improve the score?
5. Modify `strategy.py` with your proposed change. Change ONE thing at a time.
6. Run: `python run_experiment.py`
7. Read the RESULT line. If score improved over the current best, commit with a descriptive message: `git add strategy.py && git commit -m "KEEP: [description of change] score=X.XXXX"`
8. If score did NOT improve, revert: `git checkout strategy.py` and commit log: `git commit --allow-empty -m "DISCARD: [description of change] score=X.XXXX"`
9. Go back to step 2 and try the next idea.

## Decision Rules
- Only KEEP changes that strictly improve the composite score.
- If you have made 3 consecutive DISCARDs in the same direction, try a completely different approach.
- After every 10 experiments, review experiment_log.jsonl and write a brief analysis as a git commit message summarizing what you have learned.
- If validation Sharpe is below 0.5 after 20 experiments, reconsider the fundamental approach.

## Constraints
- CONFIG dict must have at most 6 keys.
- generate_signals() must not use future data (no lookahead).
- Only use pandas and numpy.
- Only return signals of 0 or 1 (long or flat).

## Current Best Score
Check the last KEEP commit or results/experiment_log.jsonl for the current best.
