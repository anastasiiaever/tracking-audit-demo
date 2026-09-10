"""A small audit for post-processed multi-object tracking submissions.

A tracking submission is not the same object as the tracker's output. Between
them sits post-processing — gap filling, tracklet linking, smoothing — that
inserts rows the tracker never observed. An evaluator scores those rows exactly
like observed ones and cannot tell them apart.

This package can:

* :mod:`~track_audit.rows` — canonical row identity and parsing
* :mod:`~track_audit.transitions` — what changed between two states, and whether
  the change is row-additive at all
* :mod:`~track_audit.admission` — whether each synthesized row describes a
  continuous reference object, under a gate applied before assignment
* :mod:`~track_audit.states` — the observed / admitted / submitted triple
* :mod:`~track_audit.ordering` — how pairwise system orderings move between states
* :mod:`~track_audit.materiality` — a descriptive size rule with its companion rate
* :mod:`~track_audit.certificate` — a deterministic, hashable record of a run

It is an evaluation artifact: it introduces no metric and no post-processing
operator, and it ranks nothing on its own.
"""
from .admission import (ADMITTED, ANCHOR_ID_MISMATCH, ANCHOR_UNMATCHED, CLASSES,
                        DEFAULT_IOU_GATE, TARGET_REFERENCE_ABSENT,
                        assign_reference, classify, partition_counts)
from .certificate import SCHEMA_VERSION, build, content_hash, serialize
from .materiality import DEFAULT_THRESHOLD, MATERIAL, NOT_MATERIAL, UNDEFINED
from .materiality import classify as classify_materiality
from .ordering import flips, matrix, relation, summary, transition
from .rows import DuplicateRowIdentity, Row, RowId, iou, parse_reference, parse_rows
from .states import build_admitted, undefined_for_non_row_additive
from .transitions import RowAdditiveViolation, Transitions, assert_row_additive, inventory

__all__ = [
    "Row", "RowId", "parse_rows", "parse_reference", "iou", "DuplicateRowIdentity",
    "inventory", "Transitions", "assert_row_additive", "RowAdditiveViolation",
    "classify", "assign_reference", "partition_counts", "CLASSES",
    "ADMITTED", "ANCHOR_UNMATCHED", "ANCHOR_ID_MISMATCH", "TARGET_REFERENCE_ABSENT",
    "DEFAULT_IOU_GATE",
    "build_admitted", "undefined_for_non_row_additive",
    "matrix", "summary", "relation", "transition", "flips",
    "classify_materiality", "DEFAULT_THRESHOLD", "MATERIAL", "NOT_MATERIAL", "UNDEFINED",
    "build", "serialize", "content_hash", "SCHEMA_VERSION",
]

__version__ = "0.1.0"
