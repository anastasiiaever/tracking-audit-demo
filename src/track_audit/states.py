"""The three states of a post-processed tracking submission.

===============  ==========================================================
``observed``     what the tracker emitted
``admitted``     observed rows plus only the synthesized rows the reference
                 supports
``submitted``    what was scored: observed rows plus every synthesized row
===============  ==========================================================

``observed`` is a subset of ``admitted`` is a subset of ``submitted`` by
canonical row identity, and :func:`build_admitted` asserts it.

The intermediate state is a **diagnostic, not a deployable correction**: it is
constructed with knowledge of the reference, which a deployed filter would not
have. It answers "how much of the scored difference rests on rows the reference
supports?", not "here is a better post-processor".
"""
from __future__ import annotations

from typing import Dict, Tuple

from .admission import ADMITTED
from .rows import Row, RowId

STRUCTURALLY_UNDEFINED = "STRUCTURALLY_UNDEFINED"
CONSTRUCTED = "ADMITTED_STATE_CONSTRUCTED"


def build_admitted(observed: Dict[RowId, Row], submitted: Dict[RowId, Row],
                   classes: Dict[RowId, str]) -> Dict[RowId, Row]:
    """Observed rows plus the synthesized rows classified ``ADMITTED``."""
    admitted = dict(observed)
    for rid, cls in classes.items():
        if cls == ADMITTED:
            admitted[rid] = submitted[rid]
    if not (set(observed) <= set(admitted) <= set(submitted)):
        raise AssertionError(
            "observed <= admitted <= submitted violated by row identity")
    return admitted


def undefined_for_non_row_additive(family: str) -> Tuple[str, str]:
    """Why a non-row-additive operator gets no intermediate state.

    Some operators rewrite values that their own fit consumes. Withholding a
    subset of the rows they generated would change the fit itself, so the
    subset is not a well-defined intervention and no intermediate state is
    synthesized for it. Reporting one anyway would report a number produced by
    a procedure the operator never runs.
    """
    reason = {
        "REGRESSION_REWRITE":
            "the regression stage consumes the generated rows as its own input, "
            "so removing a subset would alter the fit",
        "LINK_PLUS_SMOOTHING":
            "smoothing refits every row of every track, so removing a subset "
            "would alter the surviving rows too",
    }.get(family, "the operator is not row-additive")
    return (STRUCTURALLY_UNDEFINED, reason)
