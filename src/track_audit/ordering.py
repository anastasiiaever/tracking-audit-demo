"""Pairwise ordering between systems, and how it moves between two states.

Two systems can be compared only within one dataset, one population, one
evaluator configuration and one metric. Given metric tables for two states, this
module reports the relation for *every* eligible pair on *every* metric — not
only the pairs that change — and classifies how each relation moves.

Reporting all cells is the point: "post-processing reversed three orderings" is
only interpretable next to how many orderings there were.
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Sequence

A_GREATER = "A_GREATER"
TIE = "TIE"
A_LESS = "A_LESS"

UNCHANGED = "UNCHANGED"
FLIP = "FLIP"
TIE_CREATED = "TIE_CREATED"
TIE_BROKEN = "TIE_BROKEN"
METRIC_NOT_AVAILABLE = "METRIC_NOT_AVAILABLE"


def relation(a: float, b: float, tol: float = 0.0) -> str:
    """Order two values, with an optional tie tolerance."""
    if abs(a - b) <= tol:
        return TIE
    return A_GREATER if a > b else A_LESS


def transition(before: str, after: str) -> str:
    """Classify how a relation moved between two states."""
    if before == after:
        return UNCHANGED
    if before != TIE and after == TIE:
        return TIE_CREATED
    if before == TIE and after != TIE:
        return TIE_BROKEN
    return FLIP


def matrix(before: Dict[str, Dict[str, float]],
           after: Dict[str, Dict[str, float]],
           systems: Sequence[str],
           metrics: Sequence[str],
           tol: float = 0.0) -> List[dict]:
    """Every unordered pair of systems, on every metric, at both states.

    A metric missing for either system in a pair is reported as
    ``METRIC_NOT_AVAILABLE`` and never imputed: an absent number is a different
    thing from a number that happens to be equal.
    """
    rows: List[dict] = []
    for i in range(len(systems)):
        for j in range(i + 1, len(systems)):
            a, b = systems[i], systems[j]
            for m in metrics:
                try:
                    r0 = relation(before[a][m], before[b][m], tol)
                    r2 = relation(after[a][m], after[b][m], tol)
                except KeyError:
                    rows.append(dict(a=a, b=b, metric=m, before=None, after=None,
                                     margin_before=None, margin_after=None,
                                     transition=METRIC_NOT_AVAILABLE))
                    continue
                rows.append(dict(a=a, b=b, metric=m, before=r0, after=r2,
                                 margin_before=before[a][m] - before[b][m],
                                 margin_after=after[a][m] - after[b][m],
                                 transition=transition(r0, r2)))
    return rows


def summary(rows: Sequence[dict]) -> dict:
    """Headline counts over an ordering matrix."""
    c = Counter(r["transition"] for r in rows)
    pairs = {(r["a"], r["b"]) for r in rows}
    return dict(n_pairs=len(pairs), n_cells=len(rows),
                unchanged=c.get(UNCHANGED, 0),
                flips=c.get(FLIP, 0),
                ties_created=c.get(TIE_CREATED, 0),
                ties_broken=c.get(TIE_BROKEN, 0),
                metric_not_available=c.get(METRIC_NOT_AVAILABLE, 0))


def flips(rows: Sequence[dict]) -> List[dict]:
    """The cells whose strict ordering reversed."""
    return [r for r in rows if r["transition"] == FLIP]


def smallest_margin(rows: Sequence[dict], state: str = "before") -> Optional[float]:
    """The smallest absolute margin anywhere in the matrix.

    Useful as a sanity check on whether an ordering is decided by a difference
    larger than the precision at which the metric is reported.
    """
    key = f"margin_{state}"
    seen = [abs(r[key]) for r in rows if r.get(key) is not None]
    return min(seen) if seen else None
