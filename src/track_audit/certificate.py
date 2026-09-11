"""Deterministic audit records and SHA-256 content hashes."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

SCHEMA_VERSION = "track-audit/certificate/1"

# Required fields. A missing field raises rather than serialising a null.
REQUIRED = (
    "schema_version",
    "sequence",
    "gate",
    "transitions",
    "admission_partition",
    "state_construction_status",
    "materiality",
    "reason_codes",
)

# Emitted only when supplied, so a minimal certificate keeps a stable hash.
OPTIONAL = ("metric_table", "ordering", "notes")


def canonical_json(obj: Any) -> str:
    """Sorted keys, compact separators, no NaN — stable across runs."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def content_hash(content: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()


def build(**kw: Any) -> Dict[str, Any]:
    """Assemble a certificate, refusing to emit one that is incomplete."""
    content = {k: kw.get(k) for k in REQUIRED}
    content["schema_version"] = SCHEMA_VERSION
    for k in OPTIONAL:
        if kw.get(k) is not None:
            content[k] = kw[k]
    missing = [k for k in REQUIRED if content.get(k) is None and k != "reason_codes"]
    if missing:
        raise ValueError(f"certificate missing required fields: {missing}")
    if content.get("reason_codes") is None:
        content["reason_codes"] = []
    content["reason_codes"] = sorted(content["reason_codes"])
    return content


def serialize(content: Dict[str, Any]) -> str:
    """Serialise content together with its SHA-256 content hash."""
    return canonical_json({"content": content,
                           "content_sha256": content_hash(content)})
