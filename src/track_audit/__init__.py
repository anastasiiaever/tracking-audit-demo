"""Utilities for auditing post-processed multi-object tracking outputs."""
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
