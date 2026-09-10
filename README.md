# tracking-audit-demo

A small, self-contained audit for **post-processed multi-object tracking
submissions**, with a synthetic worked example and a focused test suite.

> **Scope.** This is a standalone research code sample built on **synthetic
> inputs only**. It contains no unpublished experimental results, no manuscript
> artifacts, no datasets and no model weights. Every number any command here
> prints is computed from strings defined in this repository.

## The problem it addresses

A tracking submission is not the same object as the tracker's output. Between
them sits post-processing — gap filling, tracklet linking, smoothing — that
inserts rows the tracker never observed. An evaluator scores those rows exactly
like observed ones and cannot tell them apart.

So a submission carries two kinds of row, and the usual metric reports one
number over both. This package separates them and asks a question the evaluator
does not: for each inserted row, does a reference actually support the claim
that it describes one continuous object?

## What is here

| module | what it does |
|---|---|
| `rows.py` | canonical row identity `(sequence, frame, track_id)`, parsing, IoU |
| `transitions.py` | the difference between two states as insertions, deletions and coordinate rewrites — and whether that difference is row-additive at all |
| `admission.py` | classifies each inserted row against a reference, under a gate applied *before* assignment |
| `states.py` | the observed / admitted / submitted triple and its subset invariant |
| `ordering.py` | how pairwise system orderings move between two states |
| `materiality.py` | a descriptive size rule that always reports both denominators |
| `certificate.py` | a deterministic, hashable record of a run |

Roughly 700 lines of library code and 104 tests.

## Quick start

Python 3.9 or newer. No install step is required.

```bash
git clone <this repository>
cd tracking-audit-demo
pip install -r requirements.txt

python examples/synthetic_demo.py
python -m pytest tests/ -q
```

The example runs the whole audit over a small synthetic tracking scenario
and prints each step. `scipy` is optional — see [Dependencies](#dependencies).

## The idea, in one example

A tracker observed a track at frames 1 and 3. A post-processor filled frame 2.
The filled row is geometrically plausible and fully scoreable. Whether it
*means* anything depends on the reference:

```python
from track_audit import classify, parse_reference, parse_rows

observed  = parse_rows("1,1,100,100,40,80\n3,1,140,100,40,80\n", "SEQ")
submitted = parse_rows("1,1,100,100,40,80\n2,1,120,100,40,80\n"
                       "3,1,140,100,40,80\n", "SEQ")
reference = parse_reference("1,1,100,100,40,80,1,1\n"
                            "2,1,120,100,40,80,1,1\n"
                            "3,1,140,100,40,80,1,1\n", "SEQ")

synthesized = sorted(set(submitted) - set(observed))
classify(synthesized, list(observed.values()), reference)
# {('SEQ', 2, 1): 'ADMITTED'}
```

Change the reference so the track's two anchors resolve to *different*
identities, and the same row becomes `ANCHOR_ID_MISMATCH`: the gap was bridged
across an identity change, and the interpolated row does not describe one
continuous object. The evaluator's score does not move; the audit's verdict
does.

## Design decisions worth reading the code for

**The gate is applied before assignment.** The IoU gate is a hard admissibility
mask on the cost matrix, not a filter over the winning pairs. That makes the
matcher monotone in the gate: raising it can only ever remove matches, never
create one. `test_admission.py` asserts this directly.

**The reference assignment is frozen before the rows under test exist.** It is
computed on the observed state only. Assigning after insertion would let the
rows being tested influence the reference they are tested against.

**Four classes, exhaustive and mutually exclusive, in priority order.** A row
with one unresolvable anchor is never *also* counted as a mismatch.
`partition_counts` raises if the partition is not exact.

**Non-admission is not error.** `ANCHOR_UNMATCHED` says a matching rule did not
resolve, which can happen because the tracker was wrong *or* because the matcher
was strict. The evidence does not separate those, and `CLASS_MEANING` says so in
the code rather than leaving it to a reader's charity.

**Ambiguous attribution is reported, not resolved.** Because row identity
contains the track id, an id change surfaces as a deletion plus an insertion.
Pairing them is only licensed when exactly one of each occurs at the same frame
with identical geometry; every other configuration is counted as ambiguous
rather than resolved by a heuristic.

**Some operators have no intermediate state at all.** An operator that rewrites
values its own fit consumes has no row-subset decomposition — removing a subset
of the rows it produced would change the rows it kept. `assert_row_additive`
raises, and `states.undefined_for_non_row_additive` returns
`STRUCTURALLY_UNDEFINED` with a reason instead of synthesizing a number.

**Both denominators, always.** A large non-admitted fraction *of the inserted
rows* is a different statement from a large fraction *of the submission*.
`materiality.classify` returns both, and an empty denominator yields `UNDEFINED`
rather than `0.0`.

**Deterministic records.** `certificate` serialises with sorted keys and compact
separators, sorts reason codes, and keeps clock readings out of hashed content,
so two runs over the same input produce byte-identical output.

## Tests

```bash
python -m pytest tests/ -q          # 104 tests
python -m pytest tests/ -v          # per-test names
```

The suite covers row identity and parsing, the four admission classes, gate
monotonicity, assignment determinism, id-rewrite attribution, the row-additive
invariant, the subset chain, ordering transitions, both materiality
denominators, certificate determinism, and one end-to-end pass.

## Dependencies

The package imports only the standard library. `admission.py` uses
`scipy.optimize.linear_sum_assignment` when SciPy is importable and falls back
to an exact brute-force assignment otherwise, so the library works without it —
the fallback is exponential and is only reasonable for the small per-frame
problems this code produces. `pytest` is needed only for the tests.

## Layout

```
tracking-audit-demo/
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
├── conftest.py
├── src/track_audit/          library
├── examples/                 synthetic demonstration
└── tests/                    unit and end-to-end tests
```

## Licence

MIT — see [LICENSE](LICENSE).
