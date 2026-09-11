"""Reference-consistency checks for synthesized tracking rows.

Each synthesized row is evaluated using its bracketing observed rows.
Reference assignment is computed from the observed state, with the IoU gate
applied before assignment.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .rows import Row, RowId, iou

DEFAULT_IOU_GATE = 0.5

ANCHOR_UNMATCHED = "ANCHOR_UNMATCHED"
ANCHOR_ID_MISMATCH = "ANCHOR_ID_MISMATCH"
TARGET_REFERENCE_ABSENT = "TARGET_REFERENCE_ABSENT"
ADMITTED = "ADMITTED"

# Evaluated in this order, so a row with one unresolvable anchor is never also
# counted as a mismatch. The four classes are exhaustive and mutually exclusive.
CLASSES: Tuple[str, ...] = (ANCHOR_UNMATCHED, ANCHOR_ID_MISMATCH,
                            TARGET_REFERENCE_ABSENT, ADMITTED)

# Non-admission is a statement about a matching rule, not a demonstrated error.
CLASS_MEANING = {
    ANCHOR_UNMATCHED:
        "at least one bracketing observation matched no scoreable reference; "
        "this is non-admission under the matcher, NOT a demonstrated error and "
        "NOT a false-positive determination",
    ANCHOR_ID_MISMATCH:
        "the two bracketing observations resolve, under this matcher, to "
        "different reference identities",
    TARGET_REFERENCE_ABSENT:
        "both anchors agree, but that reference identity is absent at the "
        "synthesized row's own frame",
    ADMITTED:
        "admitted under the reference-consistency rule",
}


def _assign_one_to_one(cost: List[List[float]]) -> List[Tuple[int, int]]:
    """Minimum-cost one-to-one assignment.

    Uses SciPy when it is available and falls back to an exact brute-force
    search otherwise, so the package has no hard numerical dependency. The
    fallback is exponential and is only reasonable for the small per-frame
    problems this module produces.
    """
    if not cost or not cost[0]:
        return []
    try:
        import numpy as np
        from scipy.optimize import linear_sum_assignment
        r, c = linear_sum_assignment(np.array(cost, dtype=float))
        return list(zip(r.tolist(), c.tolist()))
    except Exception:
        import itertools
        n, m = len(cost), len(cost[0])
        best, pairs = None, []
        for perm in itertools.permutations(range(m), min(n, m)):
            total = sum(cost[i][perm[i]] for i in range(len(perm)))
            if best is None or total < best:
                best = total
                pairs = [(i, perm[i]) for i in range(len(perm))]
        return pairs


def assign_reference(observed: Sequence[Row], reference: Sequence[Row],
                     gate: float = DEFAULT_IOU_GATE) -> Dict[RowId, int]:
    """Per-frame one-to-one map from observed rows to reference track ids.

    Rows are sorted by track id before the assignment so that ties resolve
    deterministically rather than by input order.
    """
    by_frame_obs: Dict[int, List[Row]] = {}
    by_frame_ref: Dict[int, List[Row]] = {}
    for r in observed:
        by_frame_obs.setdefault(r.frame, []).append(r)
    for g in reference:
        by_frame_ref.setdefault(g.frame, []).append(g)

    out: Dict[RowId, int] = {}
    BLOCKED = 1e6
    for frame, obs in by_frame_obs.items():
        refs = by_frame_ref.get(frame, [])
        if not refs:
            continue
        obs = sorted(obs, key=lambda r: r.track_id)
        refs = sorted(refs, key=lambda g: g.track_id)
        ious = [[iou(o, g) for g in refs] for o in obs]
        # Gate first: an ineligible pair is unreachable, not merely expensive.
        cost = [[(1.0 - ious[i][j]) if ious[i][j] >= gate else BLOCKED
                 for j in range(len(refs))] for i in range(len(obs))]
        for i, j in _assign_one_to_one(cost):
            if i < len(obs) and j < len(refs) and cost[i][j] < BLOCKED:
                out[obs[i].rid] = refs[j].track_id
    return out


def bracketing_anchors(rid: RowId, frames_by_track: Dict[int, List[int]]
                       ) -> Optional[Tuple[int, int]]:
    """The nearest observed frames on either side of a synthesized row.

    Returns ``None`` when the row is not bracketed on both sides — an
    extrapolation rather than an interpolation, which this rule does not admit.
    """
    _, frame, track = rid
    frames = frames_by_track.get(track)
    if not frames:
        return None
    left = max((f for f in frames if f < frame), default=None)
    right = min((f for f in frames if f > frame), default=None)
    if left is None or right is None:
        return None
    return (left, right)


def classify(synthesized: Iterable[RowId], observed: Sequence[Row],
             reference: Sequence[Row], gate: float = DEFAULT_IOU_GATE
             ) -> Dict[RowId, str]:
    """Assign every synthesized row exactly one class, in priority order."""
    assignment = assign_reference(observed, reference, gate)

    frames_by_track: Dict[int, List[int]] = {}
    for r in observed:
        frames_by_track.setdefault(r.track_id, []).append(r.frame)
    for k in frames_by_track:
        frames_by_track[k].sort()

    ref_ids_by_frame: Dict[int, set] = {}
    for g in reference:
        ref_ids_by_frame.setdefault(g.frame, set()).add(g.track_id)

    out: Dict[RowId, str] = {}
    for rid in synthesized:
        seq, frame, track = rid
        anchors = bracketing_anchors(rid, frames_by_track)
        if anchors is None:
            out[rid] = ANCHOR_UNMATCHED
            continue
        left, right = anchors
        a = assignment.get((seq, left, track))
        b = assignment.get((seq, right, track))
        if a is None or b is None:
            out[rid] = ANCHOR_UNMATCHED
        elif a != b:
            out[rid] = ANCHOR_ID_MISMATCH
        elif a not in ref_ids_by_frame.get(frame, set()):
            out[rid] = TARGET_REFERENCE_ABSENT
        else:
            out[rid] = ADMITTED
    return out


def partition_counts(classes: Dict[RowId, str]) -> Dict[str, int]:
    """Counts per class, asserting the partition is exact."""
    counts = {c: 0 for c in CLASSES}
    for v in classes.values():
        counts[v] += 1
    if sum(counts.values()) != len(classes):
        raise AssertionError("admission classes do not partition the input")
    return counts
