"""Row identity, parsing and geometry."""
import pytest

from track_audit import DuplicateRowIdentity, Row, iou, parse_reference, parse_rows
from track_audit.rows import COORD_TOL

SEQ = "T-01"


def test_identity_is_sequence_frame_track(row):
    assert row(3, 7, 0.0, 0.0).rid == (SEQ, 3, 7)


def test_identity_ignores_coordinates(row):
    assert row(3, 7, 0.0, 0.0).rid == row(3, 7, 999.0, 999.0).rid


def test_parse_reads_all_columns():
    rows = parse_rows("5,2,10,20,30,40,0.9,1,7.5", SEQ)
    r = rows[(SEQ, 5, 2)]
    assert (r.x, r.y, r.w, r.h) == (10.0, 20.0, 30.0, 40.0)
    assert r.score == pytest.approx(0.9)
    assert r.extra == (7.5,)


def test_parse_tolerates_blank_lines():
    assert len(parse_rows("1,1,0,0,10,20\n\n2,1,0,0,10,20\n", SEQ)) == 2


def test_parse_rejects_a_repeated_identity():
    with pytest.raises(DuplicateRowIdentity):
        parse_rows("1,1,0,0,10,20\n1,1,5,5,10,20\n", SEQ)


def test_parse_rejects_a_short_row():
    with pytest.raises(ValueError):
        parse_rows("1,1,0,0,10", SEQ)


def test_reference_keeps_only_scoreable_rows():
    text = ("1,1,0,0,10,20,1,1\n"      # kept
            "1,2,0,0,10,20,0,1\n"      # flag 0
            "1,3,0,0,10,20,1,7\n")     # class 7
    assert [r.track_id for r in parse_reference(text, SEQ)] == [1]


def test_reference_can_keep_everything():
    text = "1,1,0,0,10,20,0,1\n"
    assert len(parse_reference(text, SEQ, scoreable_only=False)) == 1


def test_reference_may_repeat_an_identity():
    text = "1,1,0,0,10,20,1,1\n1,1,5,5,10,20,1,1\n"
    assert len(parse_reference(text, SEQ)) == 2


def test_coords_equal_uses_a_tolerance(row):
    a = row(1, 1, 0.0, 0.0)
    b = row(1, 1, COORD_TOL / 2, 0.0)
    c = row(1, 1, 1.0, 0.0)
    assert a.coords_equal(b)
    assert not a.coords_equal(c)


def test_iou_bounds(row):
    assert iou(row(1, 1, 0.0, 0.0), row(1, 2, 500.0, 500.0)) == 0.0
    assert iou(row(1, 1, 0.0, 0.0), row(1, 2, 0.0, 0.0)) == pytest.approx(1.0)


def test_iou_is_symmetric_and_fractional(row):
    a, b = row(1, 1, 0.0, 0.0), row(1, 2, 0.0, 5.0)
    assert iou(a, b) == pytest.approx(iou(b, a))
    assert 0.0 < iou(a, b) < 1.0


def test_rows_are_immutable(row):
    with pytest.raises(Exception):
        row(1, 1, 0.0, 0.0).x = 5.0
