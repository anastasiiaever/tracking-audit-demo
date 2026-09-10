"""Pairwise relations, their transitions, and the completeness of the matrix."""
import pytest

from track_audit import flips, matrix, relation, summary, transition
from track_audit.ordering import (A_GREATER, A_LESS, FLIP, METRIC_NOT_AVAILABLE,
                                  TIE, TIE_BROKEN, TIE_CREATED, UNCHANGED,
                                  smallest_margin)


@pytest.mark.parametrize("a,b,want", [
    (2.0, 1.0, A_GREATER),
    (1.0, 2.0, A_LESS),
    (1.0, 1.0, TIE),
])
def test_relation(a, b, want):
    assert relation(a, b) == want


def test_relation_tolerance_creates_a_tie():
    assert relation(1.0, 1.001) == A_LESS
    assert relation(1.0, 1.001, tol=0.01) == TIE


@pytest.mark.parametrize("before,after,want", [
    (A_GREATER, A_GREATER, UNCHANGED),
    (A_LESS, A_LESS, UNCHANGED),
    (TIE, TIE, UNCHANGED),
    (A_GREATER, A_LESS, FLIP),
    (A_LESS, A_GREATER, FLIP),
    (A_GREATER, TIE, TIE_CREATED),
    (TIE, A_LESS, TIE_BROKEN),
])
def test_transition(before, after, want):
    assert transition(before, after) == want


def test_matrix_reports_every_pair_not_only_the_flips():
    before = {"a": {"m": 2.0}, "b": {"m": 1.0}, "c": {"m": 3.0}}
    after = {"a": {"m": 1.0}, "b": {"m": 2.0}, "c": {"m": 3.0}}
    rows = matrix(before, after, ["a", "b", "c"], ["m"])
    assert len(rows) == 3                       # C(3,2) pairs x 1 metric
    assert summary(rows)["n_pairs"] == 3


def test_matrix_covers_the_cartesian_product_of_pairs_and_metrics():
    before = {s: {"m1": 1.0, "m2": 2.0} for s in "abcd"}
    after = dict(before)
    rows = matrix(before, after, list("abcd"), ["m1", "m2"])
    assert len(rows) == 6 * 2
    assert summary(rows)["unchanged"] == 12


def test_margins_are_a_minus_b_at_both_states():
    before = {"a": {"m": 5.0}, "b": {"m": 3.0}}
    after = {"a": {"m": 1.0}, "b": {"m": 4.0}}
    r = matrix(before, after, ["a", "b"], ["m"])[0]
    assert r["margin_before"] == pytest.approx(2.0)
    assert r["margin_after"] == pytest.approx(-3.0)


def test_a_missing_metric_is_reported_not_imputed():
    rows = matrix({"a": {"m": 1.0}, "b": {}}, {"a": {"m": 1.0}, "b": {}},
                  ["a", "b"], ["m"])
    assert rows[0]["transition"] == METRIC_NOT_AVAILABLE
    assert rows[0]["before"] is None and rows[0]["after"] is None
    assert rows[0]["margin_before"] is None


def test_summary_counts_add_up_to_the_cell_count():
    before = {"a": {"m": 2.0}, "b": {"m": 1.0}, "c": {"m": 1.0}}
    after = {"a": {"m": 1.0}, "b": {"m": 2.0}, "c": {"m": 1.0}}
    rows = matrix(before, after, ["a", "b", "c"], ["m"])
    s = summary(rows)
    total = (s["unchanged"] + s["flips"] + s["ties_created"] + s["ties_broken"]
             + s["metric_not_available"])
    assert total == s["n_cells"] == len(rows)


def test_flips_are_strict_reversals():
    before = {"a": {"m": 2.0}, "b": {"m": 1.0}}
    after = {"a": {"m": 1.0}, "b": {"m": 2.0}}
    rows = matrix(before, after, ["a", "b"], ["m"])
    got = flips(rows)
    assert len(got) == 1
    assert got[0]["before"] != TIE and got[0]["after"] != TIE
    assert got[0]["before"] != got[0]["after"]


def test_smallest_margin_finds_the_closest_pair():
    before = {"a": {"m": 10.0}, "b": {"m": 10.05}, "c": {"m": 3.0}}
    after = dict(before)
    rows = matrix(before, after, ["a", "b", "c"], ["m"])
    assert smallest_margin(rows) == pytest.approx(0.05)


def test_smallest_margin_is_none_without_comparable_cells():
    rows = matrix({"a": {}, "b": {}}, {"a": {}, "b": {}}, ["a", "b"], ["m"])
    assert smallest_margin(rows) is None


def test_a_single_system_produces_no_pairs():
    rows = matrix({"a": {"m": 1.0}}, {"a": {"m": 1.0}}, ["a"], ["m"])
    assert rows == []
    assert summary(rows)["n_cells"] == 0
