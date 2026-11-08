# Rule Calibration and Validation

Issue #7 evaluates a compact set of transparent alternatives to the baseline
histogram-enhancement rules. It is a sensitivity study, not a learned model or an
unbounded parameter search.

## Reproduce

```powershell
python scripts/run_calibration.py --max-side 960
```

The runner evaluates every configuration against the same 54-record manifest and
writes the per-image evidence to `outputs/calibration/results.csv`, aggregate
comparison to `summary.csv`, and the ranking context to `selection.json`.

Calibration images are capped at 960 pixels on their longest side to make the
five-configuration comparison practical. This affects only calibration; the
committed benchmark runner remains full-resolution.

## Candidate configurations

| ID | Change relative to baseline |
| --- | --- |
| `baseline` | Mean `< 85`, standard deviation `< 45`, gamma `0.60`, stretch `2–98%`. |
| `gentle_detection` | Stricter triggering (`75`, `40`) and gentler gamma (`0.70`). |
| `balanced_gamma` | Baseline trigger for darkness, contrast threshold `40`, gamma `0.65`. |
| `strong_recovery` | Broader triggering (`95`, `50`) and stronger gamma (`0.50`). |
| `narrow_percentile_stretch` | Baseline rules with a `5–95%` contrast-stretch interval. |

## Reading the result

The output ranking balances average brightness, robust-range, and entropy gains
on low-light-labelled samples against unnecessary changes to normal, control, and
overexposed samples. Canny edge density is reported separately as a stability
diagnostic, never as a quality reward.

The leading candidate in `selection.json` is not automatically promoted to the
final configuration. Before changing `src/analysis.py`, review its representative
images for clipping, noise amplification, and colour artefacts, then confirm the
selected configuration with a full-resolution `scripts/run_benchmark.py` run.

## Validation decision

The first calibration run ranked `narrow_percentile_stretch` highest on aggregate
tonal metrics. Qualitative review rejected it as the default: it increased average
near-black clipping from **7%** to **8%**, average near-white clipping from **3%**
to **4%**, and the average absolute Canny edge-ratio change from **0.06** to
**0.07**. In the high-clipping representative (`LCV_03`), its near-black clipping
reached **5.3%**, compared with **2.1%** for the baseline.

`strong_recovery` was also rejected because it modified a normal/control image
(`SICE_14`), reducing its mean gray level from **202.4** to **188.0** and adding
black clipping. The baseline, `mean < 85`, `std < 45`, gamma `0.60`, and a
`2–98%` stretch, preserves the examined controls while producing substantial
improvements on the low-light cases. It is therefore retained as the final rule
configuration for the project.

The review figures and per-image clipping metrics are stored in
`outputs/calibration/review/`; they make this decision auditable rather than
claiming that a higher edge count is inherently better.
