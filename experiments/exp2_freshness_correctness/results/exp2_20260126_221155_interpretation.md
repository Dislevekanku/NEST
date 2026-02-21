# Experiment 2: Freshness Correctness — Interpretation

Experiment 2 demonstrates that TTL is not cosmetic: when consumers use Data Facts (TTL + last_updated), they reject stale data in proportion to metadata honesty, reducing stale-use and decision error relative to the no–Data Facts baseline.

Without Data Facts, consumers always use whatever they fetch; the stale-use rate equals the injected stale ratio, and decision error reflects only the binary fresh/stale ground truth.

With Data Facts, freshness checks reduce stale-use whenever metadata is honest. When metadata is dishonest (last_updated lied), false freshness persists and stale-use remains; the experiment injects both honest and dishonest cases.

Across TTL windows, error rates for the Data Facts mode are consistently lower than the baseline when a meaningful fraction of stale trials have honest metadata, and the detected-stale rate quantifies how often we correctly reject stale data.

These results support the claim that TTL and last_updated provide real correctness benefits, not merely cosmetic metadata, for dataset consumers.

