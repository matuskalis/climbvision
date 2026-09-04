# ClimbVision

Computer-vision **telemetry** for indoor bouldering. It looks at a video of someone bouldering
and writes down what it saw, and where every number came from. It does not tell you how to
climb. It does not grade or score the route. It does not care. The pipeline, in build order:

```
video
  -> timestamped recording
  -> calibrated wall + user-confirmed hold map
  -> climber pose trajectories
  -> limb-hold contact intervals
  -> stable contact-state transitions
  -> attempts, moves, beta, falls
  -> comparison of repeated attempts
```

**Traceability rule.** Every output must be traceable to one of: pixels, a human annotation, a
named model, a deterministic derivation, or a measured aggregate. Nothing else may be emitted.

**Stage 1 of 8 is complete.** A video file becomes a content-addressed manifest. **Stages 2
through 8 do not exist yet**: no pose, no hold detection, no calibration, no annotations, no
models, no application. There are no accuracy numbers in this repository. There is also no
model. These two facts are related.

## What it is / what it is not

| ClimbVision is | ClimbVision is not |
| --- | --- |
| A telemetry system: intervals, counts, durations, sequences | An AI coach or a text generator |
| Provenance-first: every value names its source | A grade predictor |
| Deterministic where determinism is possible | A technique, efficiency or quality scorer |
| Explicit about uncertainty (`unknown`, `abstained`, `insufficient_data`) | A 3D biomechanics or force/load estimator |
| Offline batch processing | A mobile app or a distributed service |

## Operating envelope

Every number in this repository carries a status tag, because an untagged number is how a guess
becomes a fact. `[FIXED]` means fixed now: changing it takes an explicit, recorded decision. The
other tags are defined in the legend at the top of [`docs/mvp-contract.md`](docs/mvp-contract.md).
Recordings outside the envelope are flagged, not rejected; ingest hard-fails only on malformed input.

| Condition | Requirement |
| --- | --- |
| Climbers in frame | Exactly one `[FIXED]` |
| Discipline | Indoor bouldering |
| Camera | Single static phone camera, no pan, no zoom, no handheld reframing |
| Framing | Full body and full problem visible for the whole attempt |
| Video | At least 1080p `[FIXED]`, at least 30 fps `[FIXED]` |
| Wall | One approximately planar facet, with a clean wall image or a usable reference frame from the recording |
| Hold map | User-confirmed hold masks |
| Problem identity | Explicitly user-confirmed |
| Processing | Offline batch is acceptable |

## Status

| Stage | State |
| --- | --- |
| 0 - Frozen contract and documentation | complete |
| 1 - Deterministic ingest: video to content-addressed manifest | complete |
| 2 - Annotation harness, CVAT adapter, group-aware split manifests | not started |
| 3 - Wall calibration and confirmed hold map | not started |
| 4 - Climber pose trajectories | not started |
| 5 - Limb-hold contact intervals and stable contact-state transitions | not started |
| 6 - Attempts, moves, beta sequences, fall events | not started |
| 7 - Descriptive aggregates | not started |
| 8 - Minimal application surface | not started |

Measured for Stage 1: 423 tests pass, `ruff` is clean, the hermetic run with `ffprobe` absent is
372 passed and 51 skipped, zero models are registered, and `ffprobe` 8.0 is the only external
tool. Nothing else has been measured, so nothing else is claimed.

## Roadmap

Stages 2 through 8 do not exist. Here is what they would be, in order, if anyone gets to them. A
stage does not start until the previous stage's gate is measured and reported in
[`docs/status.md`](docs/status.md).

| Stage | Delivers | Constraint that keeps this telemetry, not coaching |
| --- | --- | --- |
| 2 | Annotation harness, CVAT adapter, group-aware split manifests | CVAT is an **adapter**; the internal schema stays the source of truth. Splits are group-aware and frozen, and leakage is **tested, not assumed**. The agreement target is `[PILOT]`, and with a single annotator it is blind intra-annotator test-retest, reported as `self_agreement`. |
| 3 | Wall calibration and the confirmed hold map | Manual hold polygons and explicit problem membership **first**. Automatic segmentation only as **assistive preannotation**, behind a documented model adapter. The hold map is user-confirmed by contract, so no segmenter is required to reach the gate. |
| 4 | Climber pose trajectories | **One** pretrained pose backend, chosen by an ADR and benchmarked on the ClimbVision gold set, **not** by generic COCO AP. Raw keypoints and visibility stored **before** any filtering. |
| 5 | Limb-hold contact intervals and stable contact-state transitions | An **interpretable geometry and temporal baseline before any learned model**. Hands and feet evaluated as **separate slices**. |
| 6 | Attempts, moves, beta sequences, fall events, comparison of two attempts by contact-event alignment | Moves are **derived from contact transitions**. **No generated coaching text.** |
| 7 | Repeated-attempt descriptive analytics: projected hip trajectory, move duration, contact dwell, explicitly defined hesitation observations, foot-adjustment counts, success/failure grouping, transition failure hazard with uncertainty | Only metrics derived from **validated primitives**. Returns `insufficient_data` when support is inadequate. |
| 8 | Upload/job API, web review timeline, correction workflow, repeated-attempt comparison as a view over Stage 6 and 7 output, consent and retention controls | Application surface only **after the telemetry gates pass**. **No mobile app** until real web usage validates the workflow. |

## Install and run

Python 3.11, [uv](https://docs.astral.sh/uv/), and `ffprobe` (FFmpeg) on `PATH`, then `uv sync`.
These are the only two commands that exist. `artifacts/` is git-ignored: regenerated, never
hand-edited.

```bash
uv run climbvision ingest <video> --out artifacts  # video -> content-addressed manifest
uv run climbvision validate <json>...              # documents against their declared schema
```

## Documentation

| Document | Contents |
| --- | --- |
| [`docs/mvp-contract.md`](docs/mvp-contract.md) | The frozen contract: envelope, the full out-of-scope list, ontology, definitions, privacy boundary, acceptance gates |
| [`docs/data-schema.md`](docs/data-schema.md) | Canonical entities, Stage 1 field tables, ID/provenance/serialization rules, ingest protocol |
| [`docs/annotation-guide.md`](docs/annotation-guide.md) | Human decision rules for annotators |
| [`docs/evaluation.md`](docs/evaluation.md) | Metric definitions, split and leakage policy, the Stage 1 gate |
| [`docs/model-registry.md`](docs/model-registry.md) | Model policy and current contents (zero models) |
| [`docs/status.md`](docs/status.md) | Stage ledger with measured evidence |
| [`AGENTS.md`](AGENTS.md) | Operating rules for coding agents |
| [`docs/agents/00-operating-manual.md`](docs/agents/00-operating-manual.md) | How the owner drives the project: filming, consent, annotation, the per-stage loop |
| [`docs/agents/briefs/`](docs/agents/briefs/) | One complete brief per remaining stage |

## Privacy

No real user video, faces, consent records or model weights are stored here. A path-scoped
`.gitignore` enforces that boundary, not good intentions. Participants appear only as pseudonyms,
consent records are referenced by opaque ID, and test fixtures are synthetic and contain no people.
