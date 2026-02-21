# Experiment 2: Freshness Correctness

**Goal:** Prove TTL is not cosmetic — with Data Facts (TTL + last_updated), consumers detect and reject stale data; without, they blindly use it.

## Setup

- **Dataset with simulated updates:** injector generates trials with ground-truth freshness.
- **Staleness injection:** we control `actual_stale` and metadata honesty. When **dishonest**, we set `last_updated` to now despite data being stale (“change data without updating metadata”).
- **Modes:**
  - **Without Data Facts:** No TTL; always use fetched data.
  - **With Data Facts:** TTL + last_updated; use only if fresh by metadata.

## Metrics

- **Stale-use rate:** Among uses, fraction where data was actually stale.
- **False freshness rate:** Among “said fresh” (used), fraction actually stale.
- **Decision error:** (FP + FN) / total.
- **Detected stale %:** Among actually stale, fraction we rejected.

## Usage

```bash
# From NEST root
cd experiments/exp2_freshness_correctness
python run.py [--config config.json] [--out-dir results]
```

## Config

- `ttl_windows_seconds`: e.g. [60, 300, 600].
- `n_trials`: e.g. 500.
- `stale_ratio`: fraction of trials that are stale (e.g. 0.4).
- `dishonest_ratio`: among stale, fraction with lied metadata (e.g. 0.25).
- `rng_seed`: for reproducibility.

## Deliverables

| Deliverable | Location |
|-------------|----------|
| **Stale vs detected table** | `results/exp2_*_stale_vs_detected_table.md` |
| **Error-rate comparison** | `results/exp2_*_error_rate_comparison.png` |
| **Interpretation (paper-ready)** | `results/exp2_*_interpretation.md` |
| **Structured log** | `results/exp2_*_results.json` |

## Artifacts

- **`injector.py`:** Staleness injector; generates trials with honest/dishonest metadata.
- **`run.py`:** Runner; without/with Data Facts, multiple TTL windows, confusion-matrix stats.
