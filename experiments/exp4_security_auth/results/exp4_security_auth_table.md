## Experiment 4: Security & Auth — Results

| Scenario | Auth success % | Mean auth latency (ms) | Errors (expired / malformed / missing) |
|----------|----------------|------------------------|----------------------------------------|
| Owner agent, valid token | 100.0% | 4.711 | 0 / 0 / 0 |
| Inquiry agent, short-lived valid token | 100.0% | 4.719 | 0 / 0 / 0 |
| Expired token | 0.0% | — | 50 / 0 / 0 |
| Malformed token | 0.0% | — | 0 / 50 / 0 |
