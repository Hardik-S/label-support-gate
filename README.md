# Label Support Gate

An offline Python 3.10+ command-line check that compares synthetic or otherwise locally held JSONL records with an explicitly declared label list and minimum support policy. It reports only whether the policy passed, total record count, and one-based indices of labels below the threshold.

```powershell
python -m pip install .
label-support-gate examples/policy.json examples/rows.jsonl
```

The policy is exactly `{"labels":["billing","technical"],"minimum":2}`. Labels must be nonempty unique strings, the array must contain 1–10,000 labels, and minimum must be an integer from 0 through 1,000,000 (booleans are not integers for this contract). Each JSONL record is exactly `{"id":"...","label":"..."}` with unique nonempty IDs and a label declared by the policy. An empty ROWS.jsonl file is permitted, but blank physical rows are invalid; every declared label passes when minimum is zero. Label matching uses exact Unicode strings without normalization, and policy order determines output indices.

Exit codes: `0` policy valid, `1` valid input with insufficient support, `2` invalid input or arguments. Invalid input always prints `{"status":"invalid_input"}` and no diagnostics to stderr. The checker does not echo IDs, labels, paths, exception details, or per-label counts.

This is a narrow precondition check against a user-supplied policy. It does not measure accuracy, balance, fairness, statistical significance, quality, or novelty, and passing does not establish any of those properties.

All example records are synthetic. See [LAUNCH.md](LAUNCH.md) for a reproducible fresh-install acceptance run.
