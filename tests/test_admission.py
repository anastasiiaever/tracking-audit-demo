"""The admission rule: bracketing anchors, the gate, and the four classes."""
import pytest

from track_audit import (ADMITTED, ANCHOR_ID_MISMATCH, ANCHOR_UNMATCHED, CLASSES,
                         TARGET_REFERENCE_ABSENT, assign_reference, classify,
                         partition_counts)
from track_audit.admission import (CLASS_MEANING, DEFAULT_IOU_GATE,
                                   bracketing_anchors)

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
