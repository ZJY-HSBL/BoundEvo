# BoundEvo CEC2017 pilot validation

## Experiment protocol

- Benchmark: CEC2017 through opfunu, D=10.
- Functions: F1, F3, F5, F20.
- Methods: abc, edbf, re.
- Repetitions: 5 per function and method.
- Maximum function evaluations: 1500 per trial (initial 100 included).
- Optimizer: population N=100; parent count M=15; elite parents K=5; offspring L=1.
- Same RNG seed for all methods in a function/repetition pair.
- Offspring outside the search box are clipped by the existing optimizer.
- Error = obtained objective - benchmark known optimum; lower is better.
- A trial whose objective is below the declared benchmark optimum is rejected.
- F10 and F30 are excluded from this pilot due to observed opfunu numerical inconsistencies.
- Runtime is measured wall-clock time on a shared GitHub Actions runner.
- This is a limited-budget pilot and is NOT a full reproduction of the paper.

## Observed results

| Function | Method | Mean error | SD | Mean runtime (s) | Mean evaluations | Mean attempts / child |
|:---|:---|---:|---:|---:|---:|---:|
| F1 | ABC | 1.18838e+08 | 7.19e+07 | 0.321 | 1500 | 1.000 |
| F1 | EDBF | 3.94723e+09 | 2.14e+09 | 2.691 | 1500 | 4.957 |
| F1 | RE | 2.2794e+09 | 5.05e+08 | 2.958 | 1500 | 209.205 |
| F3 | ABC | 666.692 | 226 | 0.319 | 1500 | 1.000 |
| F3 | EDBF | 18447.5 | 5.4e+03 | 2.701 | 1500 | 4.975 |
| F3 | RE | 9957.88 | 4.27e+03 | 3.020 | 1500 | 214.364 |
| F5 | ABC | 331.258 | 62.5 | 0.322 | 1500 | 1.000 |
| F5 | EDBF | 5587.19 | 1.6e+03 | 2.697 | 1500 | 4.956 |
| F5 | RE | 3672.93 | 915 | 2.970 | 1500 | 210.373 |
| F20 | ABC | 200.924 | 88.1 | 0.613 | 1500 | 1.000 |
| F20 | EDBF | 699.225 | 261 | 3.006 | 1500 | 4.970 |
| F20 | RE | 419.052 | 129 | 3.278 | 1500 | 211.781 |

## Per-function error leaders

- F1: abc (mean error 1.18838e+08).
- F3: abc (mean error 666.692).
- F5: abc (mean error 331.258).
- F20: abc (mean error 200.924).

Functions with lowest observed mean error (ties counted for all leaders): abc=4, edbf=0, re=0.

## Validation checks

- All methods share the same seed within each function/repetition pair.
- All methods executed the same number of function evaluations within each pair.
- All 60 requested trials completed and produced finite results.

## Interpretation and limitations

The ABC generator must use exactly one coefficient-vector proposal, whereas RE and EDBF require rejection sampling. This guarantees a generation-attempt advantage, not necessarily a lower final objective error.

With only a handful of repeats and a limited evaluation budget, differences can be sampling noise. A proper paper-level replication requires the original function dimension and stopping rule, substantially longer runs, more seeds, confirmed baseline implementations, and uncertainty analysis.

The three methods use identical starting seeds, but their random-number streams diverge after initialization because each generator consumes different numbers of draws. CPU load, interpreter overhead, and implementation differences also affect wall-clock runtime.

See validation_trials.csv, validation_summary.csv, and environment.json for the machine-readable data.
