"""End-to-end: parse two states, audit the difference, record the result."""
import pytest

from track_audit import (ADMITTED, assert_row_additive, build, build_admitted,
                         classify, content_hash, inventory, parse_reference,
                         parse_rows, partition_counts)
from track_audit import classify_materiality
from track_audit.admission import ANCHOR_ID_MISMATCH, DEFAULT_IOU_GATE

SEQ = "P-01"

OBSERVED = """\
1,1,100,100,40,80
3,1,140,100,40,80
1,2,400,100,40,80
3,2,480,100,40,80
"""

SUBMITTED = """\
1,1,100,100,40,80
2,1,120,100,40,80
3,1,140,100,40,80
1,2,400,100,40,80
2,2,440,100,40,80
3,2,480,100,40,80
"""

# Identity 1 is continuous; track 2's two anchors resolve to identities 2 and 9.
REFERENCE = """\
1,1,100,100,40,80,1,1
2,1,120,100,40,80,1,1
3,1,140,100,40,80,1,1
1,2,400,100,40,80,1,1
2,2,405,100,40,80,1,1
2,9,480,100,40,80,1,1
3,9,480,100,40,80,1,1
"""


@pytest.fixture
def audited():
    observed = parse_rows(OBSERVED, SEQ)
    submitted = parse_rows(SUBMITTED, SEQ)
    reference = parse_reference(REFERENCE, SEQ)
    synthesized = sorted(set(submitted) - set(observed))
    classes = classify(synthesized, list(observed.values()), reference,
                       gate=DEFAULT_IOU_GATE)
    return observed, submitted, reference, synthesized, classes


def test_the_post_processor_only_inserted(audited):
    observed, submitted, _, _, _ = audited
    t = inventory(observed, submitted)
    assert t.inserted_rows == 2 and t.deleted_rows == 0
    assert t.rewritten_coordinate_rows == 0
    assert_row_additive(t)                       # must not raise


def test_the_two_gaps_land_in_different_classes(audited):
    _, _, _, synthesized, classes = audited
    assert classes[(SEQ, 2, 1)] == ADMITTED
    assert classes[(SEQ, 2, 2)] == ANCHOR_ID_MISMATCH
    assert len(synthesized) == 2


def test_the_composition_partitions_the_synthesized_set(audited):
    _, _, _, synthesized, classes = audited
    counts = partition_counts(classes)
    assert sum(counts.values()) == len(synthesized) == 2


def test_half_the_inserted_rows_are_not_admitted(audited):
    _, submitted, _, synthesized, classes = audited
    counts = partition_counts(classes)
    non_admitted = len(synthesized) - counts[ADMITTED]
    verdict = classify_materiality(non_admitted, len(synthesized), len(submitted))
    # One of two synthesized rows is not admitted, but that one row is only
    # one of six submitted rows. The gap between 50% and 17% is exactly why
    # both denominators are reported together.
    assert verdict["fraction_of_synthesized"] == pytest.approx(0.5)
    assert verdict["fraction_of_submitted"] == pytest.approx(1 / 6)
    assert verdict["status"] == "DESCRIPTIVE"


def test_the_admitted_state_sits_between_the_other_two(audited):
    observed, submitted, _, _, classes = audited
    admitted = build_admitted(observed, submitted, classes)
    assert len(observed) == 4 and len(admitted) == 5 and len(submitted) == 6
    assert set(observed) <= set(admitted) <= set(submitted)


def test_the_whole_audit_produces_a_reproducible_certificate(audited):
    observed, submitted, _, synthesized, classes = audited
    t = inventory(observed, submitted)
    counts = partition_counts(classes)
    verdict = classify_materiality(len(synthesized) - counts[ADMITTED],
                                   len(synthesized), len(submitted))

    def make():
        return build(sequence=SEQ, gate=DEFAULT_IOU_GATE,
                     transitions=t.to_dict(), admission_partition=counts,
                     state_construction_status="ADMITTED_STATE_CONSTRUCTED",
                     materiality=verdict, reason_codes=[])

    assert content_hash(make()) == content_hash(make())


def test_a_stricter_gate_can_only_reduce_admissions(audited):
    observed, submitted, reference, synthesized, _ = audited
    admitted_at = []
    for gate in (0.3, 0.5, 0.7, 0.9):
        c = classify(synthesized, list(observed.values()), reference, gate=gate)
        admitted_at.append(partition_counts(c)[ADMITTED])
    assert admitted_at == sorted(admitted_at, reverse=True)
