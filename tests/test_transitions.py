"""State differences, id-rewrite attribution and the row-additive invariant."""
import pytest

from track_audit import RowAdditiveViolation, assert_row_additive, inventory
from track_audit.transitions import DECOMPOSITION_UNAVAILABLE

SEQ = "T-01"


def state(rows):
    return {r.rid: r for r in rows}


def test_pure_insertion(row):
    observed = state([row(1, 1, 0.0, 0.0), row(3, 1, 0.0, 0.0)])
    submitted = state([row(1, 1, 0.0, 0.0), row(2, 1, 0.0, 0.0), row(3, 1, 0.0, 0.0)])
    t = inventory(observed, submitted)
    assert (t.inserted_rows, t.deleted_rows, t.rewritten_coordinate_rows) == (1, 0, 0)
    assert t.observed_subset_of_submitted
    assert t.unchanged_existing_rows == 2


def test_identical_states_report_no_change(row):
    s = state([row(1, 1, 0.0, 0.0)])
    t = inventory(s, dict(s))
    assert (t.inserted_rows, t.deleted_rows, t.rewritten_coordinate_rows) == (0, 0, 0)


def test_a_coordinate_rewrite_is_counted_separately(row):
    observed = state([row(1, 1, 0.0, 0.0)])
    submitted = state([row(1, 1, 5.0, 0.0)])
    t = inventory(observed, submitted)
    assert t.rewritten_coordinate_rows == 1
    assert t.unchanged_existing_rows == 0
    assert t.inserted_rows == 0


def test_a_deletion_breaks_the_subset_relation(row):
    observed = state([row(1, 1, 0.0, 0.0), row(2, 1, 0.0, 0.0)])
    submitted = state([row(1, 1, 0.0, 0.0)])
    t = inventory(observed, submitted)
    assert t.deleted_rows == 1
    assert not t.observed_subset_of_submitted


def test_an_unambiguous_id_rewrite_is_attributed(row):
    """One deletion, one insertion, same frame, identical geometry."""
    observed = state([row(1, 1, 0.0, 0.0)])
    submitted = state([row(1, 2, 0.0, 0.0)])
    t = inventory(observed, submitted)
    assert t.uniquely_attributable_id_rewrites == 1
    assert t.id_change_attribution_ambiguous == 0


def test_an_id_rewrite_with_moved_geometry_is_ambiguous(row):
    observed = state([row(1, 1, 0.0, 0.0)])
    submitted = state([row(1, 2, 50.0, 0.0)])
    t = inventory(observed, submitted)
    assert t.uniquely_attributable_id_rewrites == 0
    assert t.id_change_attribution_ambiguous == 1


def test_two_for_two_at_one_frame_is_ambiguous(row):
    """Attribution would require inventing a correspondence, so it is refused."""
    observed = state([row(1, 1, 0.0, 0.0), row(1, 2, 100.0, 0.0)])
    submitted = state([row(1, 3, 0.0, 0.0), row(1, 4, 100.0, 0.0)])
    t = inventory(observed, submitted)
    assert t.uniquely_attributable_id_rewrites == 0
    assert t.id_change_attribution_ambiguous == 2


def test_a_pure_insertion_is_not_an_id_rewrite(row):
    observed = state([row(1, 1, 0.0, 0.0), row(3, 1, 0.0, 0.0)])
    submitted = state([row(1, 1, 0.0, 0.0), row(2, 1, 0.0, 0.0), row(3, 1, 0.0, 0.0)])
    t = inventory(observed, submitted)
    assert t.uniquely_attributable_id_rewrites == 0
    assert t.id_change_attribution_ambiguous == 0


def test_row_additive_passes_for_insertion_only(row):
    observed = state([row(1, 1, 0.0, 0.0), row(3, 1, 0.0, 0.0)])
    submitted = state([row(1, 1, 0.0, 0.0), row(2, 1, 0.0, 0.0), row(3, 1, 0.0, 0.0)])
    assert_row_additive(inventory(observed, submitted))


@pytest.mark.parametrize("submitted_rows,fragment", [
    ("deleted", "absent from the submitted state"),
    ("rewritten", "rewritten coordinates"),
])
def test_row_additive_refuses_deletion_and_rewrite(row, submitted_rows, fragment):
    observed = state([row(1, 1, 0.0, 0.0), row(2, 1, 0.0, 0.0)])
    if submitted_rows == "deleted":
        submitted = state([row(1, 1, 0.0, 0.0)])
    else:
        submitted = state([row(1, 1, 0.0, 0.0), row(2, 1, 9.0, 0.0)])
    with pytest.raises(RowAdditiveViolation) as e:
        assert_row_additive(inventory(observed, submitted))
    assert e.value.reason_code == DECOMPOSITION_UNAVAILABLE
    assert fragment in e.value.detail


def test_to_dict_is_json_friendly_and_sorted(row):
    observed = state([row(3, 1, 0.0, 0.0)])
    submitted = state([row(1, 1, 0.0, 0.0), row(2, 1, 0.0, 0.0), row(3, 1, 0.0, 0.0)])
    d = inventory(observed, submitted).to_dict()
    assert d["inserted_ids"] == [[SEQ, 1, 1], [SEQ, 2, 1]]
    assert all(isinstance(x, list) for x in d["inserted_ids"])
