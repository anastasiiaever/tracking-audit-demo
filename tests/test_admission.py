"""The admission rule: bracketing anchors, the gate, and the four classes."""
import itertools
import sys

import pytest

from track_audit import (ADMITTED, ANCHOR_ID_MISMATCH, ANCHOR_UNMATCHED, CLASSES,
                         TARGET_REFERENCE_ABSENT, assign_reference, classify,
                         partition_counts)
from track_audit.admission import (CLASS_MEANING, DEFAULT_IOU_GATE,
                                   _assign_one_to_one, bracketing_anchors)

SEQ = "T-01"


@pytest.fixture
def continuous(row):
    """Track 1 observed at frames 1 and 3; reference identity 1 throughout."""
    observed = [row(1, 1, 0.0, 0.0), row(3, 1, 0.0, 0.0)]
    reference = [row(1, 1, 0.0, 0.0), row(2, 1, 0.0, 0.0), row(3, 1, 0.0, 0.0)]
    return observed, reference


def test_a_row_between_two_agreeing_anchors_is_admitted(continuous):
    observed, reference = continuous
    got = classify([(SEQ, 2, 1)], observed, reference)
    assert got[(SEQ, 2, 1)] == ADMITTED


def test_anchors_resolving_to_different_identities_are_a_mismatch(row):
    observed = [row(1, 1, 0.0, 0.0), row(3, 1, 100.0, 0.0)]
    reference = [row(1, 1, 0.0, 0.0), row(2, 1, 0.0, 0.0),
                 row(2, 2, 100.0, 0.0), row(3, 2, 100.0, 0.0)]
    assert classify([(SEQ, 2, 1)], observed, reference)[(SEQ, 2, 1)] \
        == ANCHOR_ID_MISMATCH


def test_an_anchor_matching_nothing_is_unmatched(row):
    observed = [row(1, 1, 900.0, 900.0), row(3, 1, 900.0, 900.0)]
    reference = [row(1, 5, 0.0, 0.0), row(2, 5, 0.0, 0.0), row(3, 5, 0.0, 0.0)]
    assert classify([(SEQ, 2, 1)], observed, reference)[(SEQ, 2, 1)] \
        == ANCHOR_UNMATCHED


def test_an_absent_reference_at_the_target_frame_is_its_own_class(continuous, row):
    observed, reference = continuous
    reference = [g for g in reference if g.frame != 2]
    assert classify([(SEQ, 2, 1)], observed, reference)[(SEQ, 2, 1)] \
        == TARGET_REFERENCE_ABSENT


@pytest.mark.parametrize("frames,target,expected", [
    ([1, 3], 2, (1, 3)),
    ([1, 2, 5], 3, (2, 5)),
    ([1, 2], 3, None),          # nothing after the target: extrapolation
    ([5, 6], 3, None),          # nothing before it
    ([], 3, None),
])
def test_bracketing_anchors(frames, target, expected):
    assert bracketing_anchors((SEQ, target, 1), {1: frames}) == expected


def test_a_row_without_two_bracketing_anchors_is_unmatched(row):
    observed = [row(1, 1, 0.0, 0.0)]
    reference = [row(1, 1, 0.0, 0.0), row(2, 1, 0.0, 0.0)]
    assert classify([(SEQ, 2, 1)], observed, reference)[(SEQ, 2, 1)] \
        == ANCHOR_UNMATCHED


def test_the_gate_is_applied_before_assignment(row):
    """0.6 overlap: admitted at the default gate, refused above it.

    Raising the gate must only ever remove matches. If the gate were applied
    after the assignment, a pair rejected at a high gate could free a slot and
    let a different pair match, which would not be monotone.
    """
    observed = [row(1, 1, 0.0, 0.0), row(3, 1, 0.0, 0.0)]
    reference = [row(1, 1, 0.0, 5.0), row(2, 1, 0.0, 5.0), row(3, 1, 0.0, 5.0)]
    assert classify([(SEQ, 2, 1)], observed, reference, gate=0.5)[(SEQ, 2, 1)] \
        == ADMITTED
    assert classify([(SEQ, 2, 1)], observed, reference, gate=0.7)[(SEQ, 2, 1)] \
        == ANCHOR_UNMATCHED


def test_raising_the_gate_never_adds_a_match(row):
    observed = [row(1, 1, 0.0, 0.0), row(1, 2, 0.0, 6.0)]
    reference = [row(1, 7, 0.0, 3.0)]
    matched = [len(assign_reference(observed, reference, gate=g))
               for g in (0.1, 0.3, 0.5, 0.7, 0.9)]
    assert matched == sorted(matched, reverse=True)


def test_reference_assignment_is_one_to_one(row):
    observed = [row(1, 1, 0.0, 0.0), row(1, 2, 0.0, 1.0)]
    reference = [row(1, 9, 0.0, 0.0)]
    assert len(assign_reference(observed, reference)) == 1


def test_assignment_is_deterministic_under_input_order(row):
    observed = [row(1, 1, 0.0, 0.0), row(1, 2, 0.0, 2.0), row(1, 3, 0.0, 4.0)]
    reference = [row(1, 7, 0.0, 1.0), row(1, 8, 0.0, 3.0)]
    a = assign_reference(observed, reference)
    b = assign_reference(list(reversed(observed)), list(reversed(reference)))
    assert a == b


def test_a_frame_with_no_reference_matches_nothing(row):
    observed = [row(4, 1, 0.0, 0.0)]
    reference = [row(1, 1, 0.0, 0.0)]
    assert assign_reference(observed, reference) == {}


def test_the_classes_partition_the_input(continuous):
    observed, reference = continuous
    counts = partition_counts(classify([(SEQ, 2, 1)], observed, reference))
    assert set(counts) == set(CLASSES)
    assert sum(counts.values()) == 1


def test_every_class_documents_what_it_licenses():
    assert set(CLASS_MEANING) == set(CLASSES)
    assert "NOT a demonstrated error" in CLASS_MEANING[ANCHOR_UNMATCHED]


def test_the_default_gate_is_explicit():
    assert DEFAULT_IOU_GATE == 0.5


@pytest.fixture
def force_fallback(monkeypatch):
    """Make the SciPy import inside _assign_one_to_one fail for one test.

    _assign_one_to_one imports SciPy lazily, so putting None under the module
    key is enough to send it down the brute-force branch without touching
    production code or the installed environment.
    """
    monkeypatch.setitem(sys.modules, "scipy.optimize", None)


def test_the_fixture_really_reaches_the_fallback(force_fallback, monkeypatch):
    """Guard: without this, the fallback tests could silently run under SciPy."""
    used = []
    real = itertools.permutations
    monkeypatch.setattr(itertools, "permutations",
                        lambda *a, **k: (used.append(1), real(*a, **k))[1])
    _assign_one_to_one([[1.0, 2.0]])
    assert used


def test_fallback_picks_the_cheaper_row_when_rows_outnumber_columns(force_fallback):
    """More rows than columns: the assignment must search over row subsets.

    Taking the first min(n, m) rows would return [(0, 0)] at cost 100.0 and
    ignore the cheaper second row.
    """
    assert _assign_one_to_one([[100.0], [0.1]]) == [(1, 0)]


def test_fallback_returns_min_n_m_pairs_for_both_shapes(force_fallback):
    assert len(_assign_one_to_one([[1.0], [2.0], [3.0]])) == 1
    assert len(_assign_one_to_one([[1.0, 2.0, 3.0]])) == 1
    assert len(_assign_one_to_one([[1.0, 9.0], [9.0, 1.0]])) == 2


def test_fallback_pairs_are_one_to_one(force_fallback):
    cost = [[4.0, 9.0], [1.0, 7.0], [8.0, 2.0]]
    pairs = _assign_one_to_one(cost)
    assert len({i for i, _ in pairs}) == len(pairs)
    assert len({j for _, j in pairs}) == len(pairs)


def test_fallback_finds_the_optimum_when_rows_outnumber_columns(force_fallback):
    """The optimum uses rows 1 and 2; rows {0,1} and {0,2} are both worse."""
    cost = [[9.0, 8.0], [1.0, 6.0], [5.0, 2.0]]
    pairs = _assign_one_to_one(cost)
    assert sorted(pairs) == [(1, 0), (2, 1)]
    assert sum(cost[i][j] for i, j in pairs) == pytest.approx(3.0)


def test_fallback_is_deterministic(force_fallback):
    cost = [[3.0, 1.0], [2.0, 5.0], [7.0, 4.0]]
    assert _assign_one_to_one(cost) == _assign_one_to_one(cost)


def test_a_gated_out_row_does_not_consume_the_only_reference(force_fallback, row):
    """Two observed rows, one reference, the first blocked by the gate.

    Under a first-n-rows search the blocked row wins the single column and is
    then discarded, leaving the valid row unmatched.
    """
    observed = [row(1, 1, 900.0, 900.0), row(1, 2, 0.0, 0.0)]
    reference = [row(1, 7, 0.0, 0.0)]
    assignment = assign_reference(observed, reference)
    assert assignment == {(SEQ, 1, 2): 7}
    assert (SEQ, 1, 1) not in assignment


def _brute_force(cost):
    """The fallback branch, reached by disabling the SciPy import."""
    saved = sys.modules.get("scipy.optimize", "absent")
    sys.modules["scipy.optimize"] = None
    try:
        return _assign_one_to_one(cost)
    finally:
        if saved == "absent":
            del sys.modules["scipy.optimize"]
        else:
            sys.modules["scipy.optimize"] = saved


@pytest.mark.parametrize("cost", [
    [[1.0, 5.0, 9.0], [7.0, 2.0, 8.0]],            # n < m
    [[9.0, 8.0], [1.0, 6.0], [5.0, 2.0]],          # n > m
    [[4.0, 9.0], [8.0, 3.0]],                      # n == m
])
def test_fallback_matches_scipy_on_rectangular_matrices(cost):
    """Both branches must reach the same total cost. Matrices have no ties."""
    scipy_optimize = pytest.importorskip("scipy.optimize")
    np = pytest.importorskip("numpy")

    r, c = scipy_optimize.linear_sum_assignment(np.array(cost, dtype=float))
    scipy_pairs = list(zip(r.tolist(), c.tolist()))
    fallback_pairs = _brute_force(cost)

    assert len(fallback_pairs) == len(scipy_pairs) == min(len(cost), len(cost[0]))
    assert (sum(cost[i][j] for i, j in fallback_pairs)
            == pytest.approx(sum(cost[i][j] for i, j in scipy_pairs)))
