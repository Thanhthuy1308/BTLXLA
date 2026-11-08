# Benchmark Result Analysis

Issue #5 analyses the output of the fixed benchmark runner rather than changing the
enhancement rules. Run the following after a benchmark execution:

```powershell
python scripts/analyze_benchmark.py
```

The command reads `outputs/benchmark/metrics.csv` and regenerates:

- `outputs/analysis/group_summary.csv` — source-, condition-, and operation-level statistics;
- `outputs/analysis/representative_cases.csv` — data-driven cases for qualitative review;
- `outputs/analysis/summary.json` and `findings.md` — aggregate evidence and a report draft;
- `outputs/analysis/figures/` — report-ready metric and edge-response charts, plus
  complete original/enhanced/histogram/Canny comparisons for the selected representative cases.

Interpret Canny edge density alongside the image and histogram evidence. A higher edge
count can mean newly visible structure, but it can also indicate noise or excessive
local contrast; it is not an image-quality score by itself.
