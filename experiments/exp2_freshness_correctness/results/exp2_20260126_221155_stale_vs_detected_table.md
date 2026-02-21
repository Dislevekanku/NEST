## Experiment 2: Stale vs Detected

| Mode | TTL (s) | Stale-use rate | False freshness rate | Decision error | Detected stale % |
|------|---------|----------------|----------------------|----------------|------------------|
| Without Data Facts | 60 | 0.376 | 0.376 | 0.376 | 0.0% |
| With Data Facts | 60 | 0.124 | 0.124 | 0.088 | 76.6% |
| Without Data Facts | 300 | 0.376 | 0.376 | 0.376 | 0.0% |
| With Data Facts | 300 | 0.124 | 0.124 | 0.088 | 76.6% |
| Without Data Facts | 600 | 0.376 | 0.376 | 0.376 | 0.0% |
| With Data Facts | 600 | 0.124 | 0.124 | 0.088 | 76.6% |

### Confusion matrix (example TTL=60s)

**Without Data Facts** (always use): TP=312, TN=0, FP=188, FN=0.

**With Data Facts** (use only if fresh by TTL): TP=312, TN=144, FP=44, FN=0.
