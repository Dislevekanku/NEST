# Experiment 1: Discovery Efficiency — Results Summary

- Experiment 1 (Discovery Efficiency): simulated N agent queries per mode (Baseline vs Treatment).
- Baseline: 1 step/query (direct GET); Treatment: 3 steps/query (registry → Data Facts → dataset).
- Metrics: time-to-first-data (s), failed lookups, % successful retrievals.
- Baseline N=50: 50/50 successful (100.0%), failed=0, mean TTD=0.120s.
- Treatment N=50: 50/50 successful (100.0%), failed=0, mean TTD=0.380s.
- Baseline N=200: 200/200 successful (100.0%), failed=0, mean TTD=0.130s.
- Treatment N=200: 200/200 successful (100.0%), failed=0, mean TTD=0.400s.
- Structured results: `exp1_sweep_50_200_*_results.json`; table: `exp1_sweep_50_200_*_table.md`.
- Plot: `exp1_sweep_50_200_plot.png` (run `python plot_exp1.py` from `experiments/exp1_discovery_efficiency/` or `run.py --dry-run`).

## Baseline vs Data Facts

| Mode | N | Mean time-to-first-data (s) | Failed lookups | Steps/query | % successful |
|------|---|-----------------------------|----------------|-------------|--------------|
| baseline | 50 | 0.120 | 0 | 1 | 100.0% |
| treatment | 50 | 0.380 | 0 | 3 | 100.0% |
| baseline | 200 | 0.130 | 0 | 1 | 100.0% |
| treatment | 200 | 0.400 | 0 | 3 | 100.0% |
