"""
Staleness injector for Experiment 2: Freshness Correctness.

Simulates:
- Dataset with ground-truth freshness (actual_stale).
- Data Facts metadata: honest (last_updated = true generation time) or
  dishonest (last_updated = now when stale — "change data without updating metadata"
  interpreted as we serve old data but claim fresh via metadata).

Inject staleness: we control actual_stale and metadata honesty. When dishonest,
we set last_updated to now despite data being stale (false freshness).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Tuple


@dataclass
class Trial:
    """Single simulated trial."""
    actual_stale: bool
    metadata_honest: bool
    last_updated_iso: str
    ttl_seconds: int
    age_seconds: float


def _iso(t: datetime) -> str:
    return t.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def generate_trials(
    n: int,
    ttl_seconds: int,
    stale_ratio: float,
    dishonest_ratio: float,
    rng_seed: int | None = None,
) -> List[Trial]:
    """
    Generate n trials with injected staleness.

    - actual_stale: with prob stale_ratio. When stale, true age > ttl_seconds.
    - metadata_honest: when stale, with prob (1 - dishonest_ratio) we set
      last_updated to true time (honest). Otherwise we lie (last_updated = now).
    """
    rng = random.Random(rng_seed)
    now = datetime.now(timezone.utc)
    trials: List[Trial] = []

    for _ in range(n):
        is_stale = rng.random() < stale_ratio
        if is_stale:
            true_age = ttl_seconds + rng.uniform(1, 2 * ttl_seconds)
            honest = rng.random() >= dishonest_ratio
            if honest:
                last_updated = now - timedelta(seconds=true_age)
                last_iso = _iso(last_updated)
            else:
                last_iso = _iso(now)
            age = true_age
        else:
            age = rng.uniform(0, ttl_seconds * 0.9)
            last_updated = now - timedelta(seconds=age)
            last_iso = _iso(last_updated)
            honest = True

        trials.append(
            Trial(
                actual_stale=is_stale,
                metadata_honest=honest,
                last_updated_iso=last_iso,
                ttl_seconds=ttl_seconds,
                age_seconds=age,
            )
        )
    return trials


def is_fresh_by_ttl(last_updated_iso: str, ttl_seconds: int, now: datetime | None = None) -> bool:
    """Same logic as nanda_core.dataset.client.check_freshness."""
    from datetime import datetime, timezone
    n = now or datetime.now(timezone.utc)
    last = datetime.fromisoformat(last_updated_iso.replace("Z", "+00:00"))
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    age = (n - last).total_seconds()
    return age <= ttl_seconds
