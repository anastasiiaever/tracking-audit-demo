"""Descriptive size classification for non-admitted synthesized rows.

Both the synthesized-row rate and the submission-wide rate are returned.
"""
from __future__ import annotations

from typing import Optional

DEFAULT_THRESHOLD = 0.10

MATERIAL = "COMPOSITION_MATERIAL"
NOT_MATERIAL = "COMPOSITION_NOT_MATERIAL"
UNDEFINED = "UNDEFINED_NO_SYNTHESIZED_ROWS"


def classify(non_admitted: int, synthesized: int, submitted_rows: int,
             threshold: float = DEFAULT_THRESHOLD) -> dict:
    """Classify a composition and return both rates.

    ``synthesized == 0`` yields ``UNDEFINED`` rather than zero: a conditional
    fraction with an empty denominator has no value, and reporting ``0.0`` would
    claim the composition was measured and found clean.
    """
    if synthesized < 0 or non_admitted < 0 or submitted_rows < 0:
        raise ValueError("counts must be non-negative")
    if non_admitted > synthesized:
        raise ValueError("non-admitted rows cannot exceed synthesized rows")

    of_submitted: Optional[float] = (
        non_admitted / submitted_rows if submitted_rows else None)

    if synthesized == 0:
        return dict(classification=UNDEFINED,
                    fraction_of_synthesized=None,
                    fraction_of_submitted=of_submitted,
                    threshold=threshold,
                    status="DESCRIPTIVE",
                    note="no synthesized rows; the conditional fraction is undefined")

    fraction = non_admitted / synthesized
    return dict(
        classification=MATERIAL if fraction >= threshold else NOT_MATERIAL,
        fraction_of_synthesized=fraction,
        fraction_of_submitted=of_submitted,
        threshold=threshold,
        status="DESCRIPTIVE",
        note=("descriptive only; carries no significance or generalisation claim. "
              "The submission-wide fraction is reported alongside so a large "
              "conditional fraction is not read as a submission-wide effect."))
