"""Canonical row identity for multi-object tracking states.

A tracking state is a set of rows. Each row is identified by
``(sequence, frame, track_id)`` and carries a box plus optional trailing fields.
Identity is deliberately narrow: two rows with the same identity are the same
row even if their coordinates differ, which is what lets a state difference be
expressed as insertions, deletions and coordinate rewrites rather than as an
unstructured diff.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

RowId = Tuple[str, int, int]          # (sequence, frame, track_id)

#: Fields an evaluator is assumed not to read. Changing one of these is a
#: metadata normalisation rather than a change of scored content. Callers that
#: know their evaluator reads a field should not treat it as non-evaluated.
NON_EVALUATED_FIELDS = ("score",)

#: Tolerance for round-tripping coordinates through a text writer.
COORD_TOL = 1e-6


@dataclass(frozen=True)
class Row:
    sequence: str
    frame: int
    track_id: int
    x: float
    y: float
    w: float
    h: float
    score: float = 1.0
    cls: float = 1.0
    extra: Tuple[float, ...] = ()

    @property
    def rid(self) -> RowId:
        return (self.sequence, self.frame, self.track_id)

    @property
    def coords(self) -> Tuple[float, float, float, float]:
        return (self.x, self.y, self.w, self.h)

    def coords_equal(self, other: "Row", tol: float = COORD_TOL) -> bool:
        return all(abs(a - b) <= tol for a, b in zip(self.coords, other.coords))


class DuplicateRowIdentity(ValueError):
    """Two rows in one state share a canonical row identity."""


def parse_rows(text: str, sequence: str) -> Dict[RowId, Row]:
    """Parse a comma-separated tracking state into rows keyed by identity.

    Column order is ``frame, track_id, x, y, w, h[, score, class, ...]``.

    A repeated identity is an error, not something to silently resolve: a state
    in which one row identity appears twice has no well-defined membership, and
    every downstream set operation would be arbitrary.
    """
    out: Dict[RowId, Row] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 6:
            raise ValueError(f"malformed row (need at least 6 fields): {line!r}")
        v = [float(p) for p in parts]
        row = Row(sequence, int(v[0]), int(v[1]), v[2], v[3], v[4], v[5],
                  v[6] if len(v) > 6 else 1.0,
                  v[7] if len(v) > 7 else 1.0,
                  tuple(v[8:]))
        if row.rid in out:
            raise DuplicateRowIdentity(f"duplicate row identity {row.rid}")
        out[row.rid] = row
    return out


def parse_reference(text: str, sequence: str, scoreable_only: bool = True) -> List[Row]:
    """Parse a reference (ground-truth) state.

    Column order is ``frame, track_id, x, y, w, h[, flag, class, ...]``. When
    ``scoreable_only`` is set, only rows with ``flag == 1`` and ``class == 1``
    are kept.

    The result is a list, not a dict: a reference may legitimately repeat a
    ``(frame, track_id)`` pair — for instance across overlapping ignore regions —
    so reference rows are not assumed to have unique identity.
    """
    rows: List[Row] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        v = [float(x) for x in line.split(",")]
        flag = v[6] if len(v) > 6 else 1.0
        cls = v[7] if len(v) > 7 else 1.0
        if scoreable_only and not (int(flag) == 1 and int(cls) == 1):
            continue
        rows.append(Row(sequence, int(v[0]), int(v[1]), v[2], v[3], v[4], v[5],
                        flag, cls, tuple(v[8:])))
    return rows


def iou(a: Row, b: Row) -> float:
    """Intersection over union of two axis-aligned boxes."""
    ax2, ay2 = a.x + a.w, a.y + a.h
    bx2, by2 = b.x + b.w, b.y + b.h
    ix = max(0.0, min(ax2, bx2) - max(a.x, b.x))
    iy = max(0.0, min(ay2, by2) - max(a.y, b.y))
    inter = ix * iy
    union = a.w * a.h + b.w * b.h - inter
    return inter / union if union > 0 else 0.0
