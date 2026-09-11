"""Construction of observed, admitted, and submitted tracking states.

The admitted state contains the observed rows plus synthesized rows classified
as ADMITTED. The subset relation observed <= admitted <= submitted is checked
by canonical row identity.
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
    """Return the reason an intermediate state is undefined for this operator."""
    reason = {
        "REGRESSION_REWRITE":
            "the regression stage consumes the generated rows as its own input, "
            "so removing a subset would alter the fit",
        "LINK_PLUS_SMOOTHING":
            "smoothing refits every row of every track, so removing a subset "
            "would alter the surviving rows too",
    }.get(family, "the operator is not row-additive")
    return (STRUCTURALLY_UNDEFINED, reason)
