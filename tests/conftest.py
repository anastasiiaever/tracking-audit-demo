"""Shared row helpers for the test suite."""
import pytest

from track_audit import Row

SEQ = "T-01"


@pytest.fixture
def row():
    def make(frame, track, x, y, w=10.0, h=20.0, score=1.0, cls=1.0):
        return Row(SEQ, frame, track, x, y, w, h, score, cls, ())
    return make
