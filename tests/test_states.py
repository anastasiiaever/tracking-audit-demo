"""Construction of the intermediate state, and when it does not exist."""
import pytest

from track_audit import ADMITTED, build_admitted, undefined_for_non_row_additive
from track_audit.admission import ANCHOR_ID_MISMATCH, ANCHOR_UNMATCHED
from track_audit.states import CONSTRUCTED, STRUCTURALLY_UNDEFINED

SEQ = "T-01"


def state(rows):
    return {r.rid: r for r in rows}


def test_admitted_is_observed_plus_admitted_rows_only(row):
    observed = state([row(1, 1, 0.0, 0.0)])
    submitted = state([row(1, 1, 0.0, 0.0), row(2, 1, 0.0, 0.0), row(3, 1, 0.0, 0.0)])
    classes = {(SEQ, 2, 1): ADMITTED, (SEQ, 3, 1): ANCHOR_UNMATCHED}
    admitted = build_admitted(observed, submitted, classes)
    assert set(admitted) == {(SEQ, 1, 1), (SEQ, 2, 1)}


def test_the_subset_chain_holds(row):
    observed = state([row(1, 1, 0.0, 0.0)])
    submitted = state([row(1, 1, 0.0, 0.0), row(2, 1, 0.0, 0.0), row(3, 1, 0.0, 0.0)])
    classes = {(SEQ, 2, 1): ADMITTED, (SEQ, 3, 1): ANCHOR_ID_MISMATCH}
    admitted = build_admitted(observed, submitted, classes)
    assert set(observed) <= set(admitted) <= set(submitted)


def test_admitting_nothing_leaves_the_observed_state(row):
    observed = state([row(1, 1, 0.0, 0.0)])
    submitted = state([row(1, 1, 0.0, 0.0), row(2, 1, 0.0, 0.0)])
    admitted = build_admitted(observed, submitted, {(SEQ, 2, 1): ANCHOR_UNMATCHED})
    assert admitted == observed


def test_admitting_everything_reaches_the_submitted_state(row):
    observed = state([row(1, 1, 0.0, 0.0)])
    submitted = state([row(1, 1, 0.0, 0.0), row(2, 1, 0.0, 0.0)])
    admitted = build_admitted(observed, submitted, {(SEQ, 2, 1): ADMITTED})
    assert set(admitted) == set(submitted)


def test_an_admitted_row_missing_from_submitted_is_an_error(row):
    observed = state([row(1, 1, 0.0, 0.0)])
    submitted = dict(observed)
    with pytest.raises(KeyError):
        build_admitted(observed, submitted, {(SEQ, 9, 9): ADMITTED})


@pytest.mark.parametrize("family", ["REGRESSION_REWRITE", "LINK_PLUS_SMOOTHING"])
def test_non_row_additive_families_get_no_intermediate_state(family):
    status, reason = undefined_for_non_row_additive(family)
    assert status == STRUCTURALLY_UNDEFINED
    assert reason and "alter" in reason


def test_an_unknown_family_still_gets_a_reason():
    status, reason = undefined_for_non_row_additive("SOMETHING_ELSE")
    assert status == STRUCTURALLY_UNDEFINED
    assert "not row-additive" in reason


def test_the_constructed_status_is_a_named_constant():
    assert CONSTRUCTED == "ADMITTED_STATE_CONSTRUCTED"
