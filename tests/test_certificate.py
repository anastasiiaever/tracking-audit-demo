"""Determinism and completeness of the audit record."""
import json

import pytest

from track_audit import build, content_hash, serialize
from track_audit.certificate import REQUIRED, SCHEMA_VERSION, canonical_json


def minimal(**over):
    kw = dict(sequence="S", gate=0.5, transitions={"inserted_rows": 1},
              admission_partition={"ADMITTED": 1},
              state_construction_status="ADMITTED_STATE_CONSTRUCTED",
              materiality={"classification": "COMPOSITION_NOT_MATERIAL"},
              reason_codes=[])
    kw.update(over)
    return build(**kw)


def test_a_certificate_carries_every_required_field():
    assert set(REQUIRED) <= set(minimal())


def test_the_schema_version_is_stamped():
    assert minimal()["schema_version"] == SCHEMA_VERSION


def test_a_missing_required_field_is_refused():
    with pytest.raises(ValueError) as e:
        build(sequence="S", gate=0.5)
    assert "missing required fields" in str(e.value)


def test_identical_content_hashes_identically():
    assert content_hash(minimal()) == content_hash(minimal())


def test_key_order_does_not_change_the_hash():
    a = minimal()
    b = {k: a[k] for k in reversed(list(a))}
    assert content_hash(a) == content_hash(b)


def test_different_content_hashes_differently():
    assert content_hash(minimal()) != content_hash(minimal(gate=0.7))


def test_reason_codes_are_sorted_so_order_cannot_leak_in():
    a = minimal(reason_codes=["B", "A"])
    b = minimal(reason_codes=["A", "B"])
    assert a["reason_codes"] == ["A", "B"]
    assert content_hash(a) == content_hash(b)


def test_optional_fields_are_absent_unless_supplied():
    assert "ordering" not in minimal()
    assert "ordering" in minimal(ordering={"n_cells": 3})


def test_omitting_an_optional_field_keeps_the_hash_stable():
    """Adding an optional field later must not silently rewrite old hashes."""
    assert content_hash(minimal()) == content_hash(minimal(notes=None))


def test_serialize_round_trips_and_embeds_its_own_digest():
    cert = minimal()
    blob = serialize(cert)
    parsed = json.loads(blob)
    assert parsed["content"] == cert
    assert parsed["content_sha256"] == content_hash(cert)


def test_serialization_is_byte_stable():
    assert serialize(minimal()) == serialize(minimal())


def test_canonical_json_refuses_nan():
    with pytest.raises(ValueError):
        canonical_json({"x": float("nan")})
