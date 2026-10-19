# Adaptive extension protocol: CEC2017 F16/F22, 20 paired seeds at 100k evaluations

Date: 2026-10-19. This protocol was registered **after** the first five 100k-FE trajectories were published; it is not a prospectively independent confirmation.

## Why extend?

At 100k function evaluations, the first five paired repeats (0–4) gave mean F16 error 1732.43 (ABC), 2076.05 (EDBF), 1797.66 (RE). On F22, RE mean 5180.38 was lower than ABC 5780.24, but their standard deviations were approximately 2844 and 2904, respectively. This high dispersion makes an enlarged **descriptive/adaptive** sensitivity analysis appropriate. No claim of significance follows from the five-seed means.

## Locked protocol and provenance

- CEC2017 F16 and F22, D=30; pinned reference-derived Python backend revision `424a9fa2757914c3e4cfdd8f59a268b1aeb3197f`, **not** the official organizers' C implementation.
- ABC, EDBF, RE; N=100, M=15, K=5, L=1; each trial has **100,000** function evaluations inclusive of initialization.
- Seeds: `20261037 + function_id × 10,000 + repeat`, repeats 0 through 19. The entire cohort is **the same 20-seed cohort** as v0.10's independent 10k holdout, extended to a larger budget. It is NOT 20 novel independent test seeds.
- Preserve the original 30 fully verified 100k trials for repeats 0–4 from `docs/experiments/cec2017-paperbudget-30d-100k-2026-10-18/`, whose original Actions source SHA was `66a5c36288772260543ec59cacbb37edfd5f8b14`.
- Run only repeats 5–19 for each F16/F22 and ABC/EDBF/RE, a total of **90 newly computed trials**. Shard into six independent 5-repeat jobs. Expected final dataset **120 trials**, exactly 20 matched repeats × 3 methods × 2 functions.
- Record best-so-far 100..100k history and require an exact FE=10,000 checkpoint within every trajectory. Reject any mismatch with the prior committed 10k errors, duplicate trial, missing job, nonfinite error, early end, lost checkpoint, or worsening best-so-far performance.
- Report group means, medians, SD, 10,000 fixed-seed bootstrap replicates of 100k mean error, paired log1p advantage and 95% percentile intervals, and exact paired two-sided sign tests of ABC vs EDBF and RE on each function, with Holm correction across **four** comparisons. Note exploratory multiplicity across earlier work remains uncorrected.
- Do not pool the 3-, 10-, 20-seed historical cohorts. The 100k comparisons intentionally pair the same seed IDs to the 10k results.
- Publish CSV trials, CSV histories, paired tests, reproducibility manifests, plots computed from the actual CSV, EN/CN README sections, and archived GitHub Actions artifacts only after complete independent validation. No result fabrication or extrapolation.
- Release gate: the expanded findings, or any lower average error on just F16/F22, do not by themselves justify a universal algorithm-performance claim or a versioned v0.11 release. Further broader tests require a separate protocol.

The expansion was chosen after viewing initial results. Its uncertainty intervals and Holm-adjusted sign tests quantify variation **within this selected adaptive study**; they are not confirmatory evidence against all previous experiment choices.
