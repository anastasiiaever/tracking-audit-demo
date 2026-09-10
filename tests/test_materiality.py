"""The descriptive size rule and its companion denominator."""
import pytest

from track_audit import DEFAULT_THRESHOLD, MATERIAL, NOT_MATERIAL, UNDEFINED
from track_audit import classify_materiality as classify


def test_the_default_threshold_is_explicit():
    assert DEFAULT_THRESHOLD == 0.10


def test_at_and_above_the_threshold_is_material():
    assert classify(10, 100, 1000)["classification"] == MATERIAL
    assert classify(50, 100, 1000)["classification"] == MATERIAL


def test_below_the_threshold_is_not_material():
    assert classify(9, 100, 1000)["classification"] == NOT_MATERIAL


def test_a_custom_threshold_is_honoured():
    assert classify(10, 100, 1000, threshold=0.5)["classification"] == NOT_MATERIAL


def test_both_denominators_are_always_reported():
    out = classify(10, 100, 1000)
    assert out["fraction_of_synthesized"] == pytest.approx(0.10)
    assert out["fraction_of_submitted"] == pytest.approx(0.01)


def test_the_two_rates_can_differ_by_orders_of_magnitude():
    """The reason both are reported: one is conditional, one is submission-wide."""
    out = classify(250, 1000, 100000)
    assert out["fraction_of_synthesized"] == pytest.approx(0.25)
    assert out["fraction_of_submitted"] == pytest.approx(0.0025)


def test_no_synthesized_rows_is_undefined_not_zero():
    out = classify(0, 0, 100)
    assert out["classification"] == UNDEFINED
    assert out["fraction_of_synthesized"] is None
    assert out["fraction_of_submitted"] == pytest.approx(0.0)


def test_an_empty_submission_leaves_the_companion_rate_undefined():
    assert classify(0, 0, 0)["fraction_of_submitted"] is None


def test_every_verdict_is_labelled_descriptive():
    for args in [(10, 100, 1000), (0, 100, 1000), (0, 0, 0)]:
        assert classify(*args)["status"] == "DESCRIPTIVE"


@pytest.mark.parametrize("args", [(-1, 10, 10), (1, -10, 10), (1, 10, -10), (11, 10, 100)])
def test_impossible_counts_are_rejected(args):
    with pytest.raises(ValueError):
        classify(*args)
