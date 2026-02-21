"""
Corruption injector for Experiment 3: Trust / Integrity.

Simulates dataset payloads and corrupts a configurable percentage of bytes.
Outputs per-trial metadata needed to evaluate checksum-based detection
versus a baseline with no checksum (Data Facts disabled).
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class Trial:
    """Single integrity trial."""
    corruption_percent: float
    corrupted: bool
    expected_checksum: str
    delivered_checksum: str
    bytes_changed: int
    payload_len: int


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _random_payload(length: int, rng: random.Random) -> bytes:
    return bytes(rng.getrandbits(8) for _ in range(length))


def _corrupt_payload(payload: bytes, corruption_percent: float, rng: random.Random) -> tuple[bytes, int]:
    """Flip random bytes according to corruption_percent."""
    if corruption_percent <= 0:
        return payload, 0
    n = max(1, int(round(len(payload) * (corruption_percent / 100.0))))
    idxs = rng.sample(range(len(payload)), k=min(n, len(payload)))
    corrupted = bytearray(payload)
    for i in idxs:
        corrupted[i] ^= rng.randint(1, 255)  # flip bits with non-zero delta
    return bytes(corrupted), len(idxs)


def generate_trials(
    n_trials: int,
    corruption_percent: float,
    payload_len: int,
    rng_seed: int | None = None,
) -> List[Trial]:
    """Generate n_trials with the specified corruption percentage."""
    rng = random.Random(rng_seed)
    trials: List[Trial] = []
    for _ in range(n_trials):
        payload = _random_payload(payload_len, rng)
        expected_checksum = _sha256(payload)
        delivered, changed = _corrupt_payload(payload, corruption_percent, rng)
        delivered_checksum = _sha256(delivered)
        trials.append(
            Trial(
                corruption_percent=corruption_percent,
                corrupted=changed > 0,
                expected_checksum=expected_checksum,
                delivered_checksum=delivered_checksum,
                bytes_changed=changed,
                payload_len=payload_len,
            )
        )
    return trials


def detect_with_data_facts(trial: Trial) -> bool:
    """Detect corruption by comparing delivered checksum to expected checksum."""
    return trial.expected_checksum != trial.delivered_checksum


def detect_without_data_facts(trial: Trial) -> bool:
    """
    Baseline without Data Facts / checksum: no integrity guard,
    so corruption goes unnoticed (detect=False).
    """
    return False
