"""State differences for tracking outputs.

Differences are represented as insertions, deletions, and coordinate rewrites
over canonical row identities. No gap-based inference is used.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List

from .rows import Row, RowId


@dataclass
class Transitions:
    n_observed_rows: int
    n_submitted_rows: int
    inserted_rows: int
    deleted_rows: int
    rewritten_coordinate_rows: int
    uniquely_attributable_id_rewrites: int
    id_change_attribution_ambiguous: int
    unchanged_existing_rows: int
    inserted_ids: List[RowId] = field(default_factory=list)
    deleted_ids: List[RowId] = field(default_factory=list)
    coordinate_rewritten_ids: List[RowId] = field(default_factory=list)
    observed_subset_of_submitted: bool = True

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ("inserted_ids", "deleted_ids", "coordinate_rewritten_ids"):
            d[k] = [list(x) for x in sorted(d[k])]
        return d


def inventory(observed: Dict[RowId, Row], submitted: Dict[RowId, Row]) -> Transitions:
    """Inventory state changes and conservatively attribute unambiguous ID rewrites."""
    inserted = sorted(set(submitted) - set(observed))
    deleted = sorted(set(observed) - set(submitted))
    common = sorted(set(observed) & set(submitted))
    coord_rewritten = [i for i in common
                       if not observed[i].coords_equal(submitted[i])]

    del_by_frame: Dict[tuple, List[RowId]] = {}
    ins_by_frame: Dict[tuple, List[RowId]] = {}
    for rid in deleted:
        del_by_frame.setdefault(rid[:2], []).append(rid)
    for rid in inserted:
        ins_by_frame.setdefault(rid[:2], []).append(rid)

    unique_rewrites, ambiguous = 0, 0
    for frame_key in set(del_by_frame) | set(ins_by_frame):
        d = del_by_frame.get(frame_key, [])
        i = ins_by_frame.get(frame_key, [])
        if not d:
            continue                       # pure insertion: not an id rewrite
        if len(d) == 1 and len(i) == 1 and observed[d[0]].coords_equal(submitted[i[0]]):
            unique_rewrites += 1
        else:
            ambiguous += len(d)

    return Transitions(
        n_observed_rows=len(observed),
        n_submitted_rows=len(submitted),
        inserted_rows=len(inserted),
        deleted_rows=len(deleted),
        rewritten_coordinate_rows=len(coord_rewritten),
        uniquely_attributable_id_rewrites=unique_rewrites,
        id_change_attribution_ambiguous=ambiguous,
        unchanged_existing_rows=len(common) - len(coord_rewritten),
        inserted_ids=inserted,
        deleted_ids=deleted,
        coordinate_rewritten_ids=coord_rewritten,
        observed_subset_of_submitted=not deleted,
    )


class RowAdditiveViolation(Exception):
    """The submitted state is not the observed state plus inserted rows."""

    def __init__(self, reason_code: str, detail: str):
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


DECOMPOSITION_UNAVAILABLE = "STRUCTURAL_DECOMPOSITION_UNAVAILABLE"


def assert_row_additive(t: Transitions) -> None:
    """Raise unless the observed rows survive unchanged inside the submitted state.

    An operator that deletes or rewrites pre-existing rows has no row-subset
    decomposition: removing a subset of the rows it produced would change the
    rows it kept. Callers that catch this must report
    ``STRUCTURAL_DECOMPOSITION_UNAVAILABLE`` and must not build an intermediate
    state — see :mod:`track_audit.states`.
    """
    if t.deleted_rows:
        raise RowAdditiveViolation(
            DECOMPOSITION_UNAVAILABLE,
            f"{t.deleted_rows} observed row identities are absent from the submitted state")
    if t.rewritten_coordinate_rows:
        raise RowAdditiveViolation(
            DECOMPOSITION_UNAVAILABLE,
            f"{t.rewritten_coordinate_rows} pre-existing rows have rewritten coordinates")
