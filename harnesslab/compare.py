"""Paired evaluation statistics, independent of agent runtime or provider."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import isfinite
import random
from statistics import mean
from typing import Iterable


@dataclass(frozen=True)
class Outcome:
    task_id: str
    trial: int
    passed: bool
    task_revision: str
    verifier_sha256: str
    status: str = "scored"

    def __post_init__(self) -> None:
        if not all(isinstance(s, str) and s for s in (
            self.task_id, self.task_revision, self.verifier_sha256
        )):
            raise ValueError("Task identity, revision and verifier are required")
        if type(self.trial) is not int or self.trial < 0:
            raise ValueError("trial must be a nonnegative integer")
        if type(self.passed) is not bool:
            raise ValueError("passed must be a boolean")
        if self.status != "scored":
            raise ValueError("Infrastructure errors are not scored outcomes")


@dataclass(frozen=True)
class Comparison:
    tasks: int
    pairs: int
    baseline_rate: float
    candidate_rate: float
    delta: float
    lower: float
    upper: float
    margin: float
    confidence: float
    resamples: int
    seed: int
    verdict: str
    method: str = "paired_task_cluster_percentile_bootstrap"


def _index(items: Iterable[Outcome]) -> dict[tuple[str, int], Outcome]:
    result = {}
    for item in items:
        key = (item.task_id, item.trial)
        if key in result:
            raise ValueError(f"Duplicate task/trial: {key}")
        result[key] = item
    if not result:
        raise ValueError("No outcomes")
    return result


def _quantile(values: list[float], p: float) -> float:
    # Linear interpolation, with endpoints included.
    n = (len(values) - 1) * p
    lo = int(n)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (n - lo)


def compare(
    baseline: Iterable[Outcome],
    candidate: Iterable[Outcome],
    *,
    margin: float = 0.05,
    confidence: float = 0.95,
    resamples: int = 10000,
    seed: int = 0,
    min_tasks: int = 20,
) -> Comparison:
    """Compare fixed paired trials, bootstrapping independent task clusters.

    Each task is equally weighted, even if repeat counts differ by task.
    Trial keys and verifier identities must match across configurations.
    The interval describes this task sample, not all possible coding tasks.
    Thresholds and sample sizes must be specified before the measured run.
    """
    if not isfinite(margin) or not 0 <= margin <= 1:
        raise ValueError("margin must be finite and between 0 and 1")
    if not isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    if type(resamples) is not int or resamples < 100:
        raise ValueError("At least 100 bootstrap resamples required")
    if type(min_tasks) is not int or min_tasks < 2:
        raise ValueError("min_tasks must be at least 2")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    left, right = _index(baseline), _index(candidate)
    if left.keys() != right.keys():
        raise ValueError("Paired task/trial keys must match exactly")
    groups: dict[str, list[tuple[int, int]]] = defaultdict(list)
    identities: dict[str, tuple[str, str]] = {}
    for key in sorted(left):
        a, b = left[key], right[key]
        identity = (a.task_revision, a.verifier_sha256)
        if identity != (b.task_revision, b.verifier_sha256):
            raise ValueError(f"Changed task/verifier identity: {key[0]}")
        if key[0] in identities and identities[key[0]] != identity:
            raise ValueError(f"Task identity changed across trials: {key[0]}")
        identities[key[0]] = identity
        groups[key[0]].append((int(a.passed), int(b.passed)))
    rates = [
        (mean(a for a, _ in trials), mean(b for _, b in trials))
        for _, trials in sorted(groups.items())
    ]
    differences = [b - a for a, b in rates]
    rng = random.Random(seed)
    n = len(rates)
    boot = sorted(mean(rng.choices(differences, k=n)) for _ in range(resamples))
    alpha = (1 - confidence) / 2
    lower, upper = _quantile(boot, alpha), _quantile(boot, 1 - alpha)
    # A degenerate all-same-effect sample cannot establish population certainty.
    # A lower-than-minimum sample always abstains, whatever the apparent effect.
    if n < min_tasks or len(set(differences)) < 2:
        verdict = "insufficient_evidence"
    elif upper < -margin:
        verdict = "regression"
    elif lower >= -margin:
        verdict = "no_detected_regression"
    else:
        verdict = "insufficient_evidence"
    return Comparison(
        tasks=n,
        pairs=len(left),
        baseline_rate=mean(a for a, _ in rates),
        candidate_rate=mean(b for _, b in rates),
        delta=mean(differences),
        lower=lower,
        upper=upper,
        margin=margin,
        confidence=confidence,
        resamples=resamples,
        seed=seed,
        verdict=verdict,
    )
