#!/usr/bin/env python3
"""Synthetic end-to-end example for track_audit.

The example uses three short tracks and a synthetic reference to exercise
state transitions, admission classes, ordering changes, and certificate
generation.

Run with:
    python examples/synthetic_demo.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from track_audit import (build_admitted, certificate, classify, inventory,
                         materiality, ordering, parse_reference, parse_rows,
                         partition_counts)
from track_audit.admission import CLASSES, DEFAULT_IOU_GATE

SEQUENCE = "SYNTH-01"

# frame, track, x, y, w, h
OBSERVED = """\
1,1,100,100,40,80
3,1,140,100,40,80
1,2,400,100,40,80
3,2,480,100,40,80
1,3,700,100,40,80
3,3,700,100,40,80
"""

# The post-processor filled frame 2 of every track.
SUBMITTED = """\
1,1,100,100,40,80
2,1,120,100,40,80
3,1,140,100,40,80
1,2,400,100,40,80
2,2,440,100,40,80
3,2,480,100,40,80
1,3,700,100,40,80
2,3,700,100,40,80
3,3,700,100,40,80
"""

# Synthetic reference cases:
# identity 1 stays continuous
# identity 2 changes to identity 9
# identity 3 is missing at frame 2
REFERENCE = """\
1,1,100,100,40,80,1,1
2,1,120,100,40,80,1,1
3,1,140,100,40,80,1,1
1,2,400,100,40,80,1,1
2,2,405,100,40,80,1,1
2,9,480,100,40,80,1,1
3,9,480,100,40,80,1,1
1,3,700,100,40,80,1,1
3,3,700,100,40,80,1,1
"""


def main() -> int:
    observed = parse_rows(OBSERVED, SEQUENCE)
    submitted = parse_rows(SUBMITTED, SEQUENCE)
    reference = parse_reference(REFERENCE, SEQUENCE)

    print(f"observed rows  : {len(observed)}")
    print(f"submitted rows : {len(submitted)}")

    # State transition
    t = inventory(observed, submitted)
    print(f"\ninserted {t.inserted_rows}, deleted {t.deleted_rows}, "
          f"coordinate rewrites {t.rewritten_coordinate_rows}")
    print(f"observed rows survive inside the submitted state: "
          f"{t.observed_subset_of_submitted}")

    synthesized = sorted(set(submitted) - set(observed))

    # Reference consistency
    classes = classify(synthesized, list(observed.values()), reference,
                       gate=DEFAULT_IOU_GATE)
    print(f"\nadmission at gate {DEFAULT_IOU_GATE}:")
    for rid in synthesized:
        print(f"  frame {rid[1]}, track {rid[2]}  ->  {classes[rid]}")

    counts = partition_counts(classes)
    print("\ncomposition:")
    for cls in CLASSES:
        print(f"  {cls:<26s} {counts[cls]}")

    non_admitted = len(synthesized) - counts["ADMITTED"]
    verdict = materiality.classify(non_admitted, len(synthesized), len(submitted))
    print(f"\n  {non_admitted} of {len(synthesized)} synthesized rows are not admitted "
          f"({verdict['fraction_of_synthesized']:.0%} of what the post-processor "
          f"produced, {verdict['fraction_of_submitted']:.1%} of the submission)")
    print(f"  verdict: {verdict['classification']} ({verdict['status']})")

    # Admitted state
    admitted = build_admitted(observed, submitted, classes)
    print(f"\nadmitted state: {len(admitted)} rows "
          f"(observed {len(observed)} <= admitted {len(admitted)} <= submitted "
          f"{len(submitted)})")

    # Ordering changes
    # Illustrative metric tables: three systems, one metric, before and after.
    before = {"alpha": {"score": 70.10}, "beta": {"score": 70.02}, "gamma": {"score": 66.40}}
    after = {"alpha": {"score": 71.05}, "beta": {"score": 71.30}, "gamma": {"score": 67.90}}
    rows = ordering.matrix(before, after, ["alpha", "beta", "gamma"], ["score"])
    s = ordering.summary(rows)
    print(f"\nordering: {s['n_cells']} cells over {s['n_pairs']} pairs — "
          f"{s['unchanged']} unchanged, {s['flips']} reversed")
    for r in ordering.flips(rows):
        print(f"  {r['a']} vs {r['b']} [{r['metric']}]: {r['before']} -> {r['after']} "
              f"(margin {r['margin_before']:+.2f} -> {r['margin_after']:+.2f})")
    print(f"  smallest margin before: {ordering.smallest_margin(rows):.2f}")

    # Reproducibility certificate
    cert = certificate.build(
        sequence=SEQUENCE,
        gate=DEFAULT_IOU_GATE,
        transitions=t.to_dict(),
        admission_partition=counts,
        state_construction_status="ADMITTED_STATE_CONSTRUCTED",
        materiality=verdict,
        ordering=s,
        reason_codes=[],
    )
    h = certificate.content_hash(cert)
    again = certificate.content_hash(certificate.build(
        sequence=SEQUENCE, gate=DEFAULT_IOU_GATE, transitions=t.to_dict(),
        admission_partition=counts,
        state_construction_status="ADMITTED_STATE_CONSTRUCTED",
        materiality=verdict, ordering=s, reason_codes=[]))
    print(f"\ncertificate sha256: {h[:16]}...  reproducible: {h == again}")

    print("\nsummary:")
    print("  one synthesized row is admitted")
    print("  one spans different reference identities")
    print("  one has no reference support at the filled frame")
    return 0


if __name__ == "__main__":
    sys.exit(main())
