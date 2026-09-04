# ClimbVision

Computer-vision **telemetry** for indoor bouldering. ClimbVision measures what a camera can
observe about a climb and records where every number came from. It does not judge, score or
coach.

The pipeline, in build order:

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

**Current state: Stage 1 of 8 complete.** Ingest works: a video file becomes a content-addressed
manifest. **Stages 2 through 8 do not exist yet** - no pose, no hold detection, no calibration,
no annotations, no models, no application. See [Status](#status) and [Roadmap](#roadmap).

## What it is / what it is not

| ClimbVision is | ClimbVision is not |
| --- | --- |
| A telemetry system: intervals, counts, durations, sequences | An AI coach or a text generator |
| Provenance-first: every value names its source | A grade predictor |
| Deterministic where determinism is possible | A technique, efficiency or quality scorer |
| Explicit about uncertainty (`unknown`, `abstained`, `insufficient_data`) | A 3D biomechanics or force/load estimator |
| Offline batch processing | A mobile app or a distributed service |

Full out-of-scope list: [`docs/mvp-contract.md`](docs/mvp-contract.md).

## Operating envelope

Status tags: `[FIXED]` fixed now, changing it requires an explicit decision. `[PILOT]` not yet
estimated. `[PLANNING]` illustrative guidance, not a commitment. `[VAL]` selected on
training/validation data - **unused today, no validation data exists.**

| Condition | Requirement |
| --- | --- |
| Climbers in frame | Exactly one `[FIXED]` |
| Discipline | Indoor bouldering |
| Camera | Single static phone camera, no pan, no zoom, no handheld reframing |
| Framing | Full body and full problem visible for the whole attempt |
| Resolution | At least 1080p `[FIXED]` |
| Frame rate | At least 30 fps `[FIXED]` |
| Wall geometry | One approximately planar wall facet |
| Reference imagery | A clean wall image, or a usable reference frame from the recording |
| Hold map | User-confirmed hold masks |
| Problem identity | Explicitly user-confirmed |
| Processing | Offline batch is acceptable |

Recordings that violate the envelope are **flagged**, not rejected. Ingest hard-fails only on
malformed input.

## Status

| Stage | State |
| --- | --- |
| 0 - Frozen contract and documentation | complete |
| 1 - Deterministic ingest | complete |
| 2 - Annotation harness and splits | not started |
| 3 - Wall calibration and hold map | not started |
| 4 - Pose trajectories | not started |
| 5 - Contact intervals | not started |
| 6 - Attempts, moves, beta, falls | not started |
| 7 - Repeated-attempt analytics | not started |
| 8 - Minimal application surface | not started |

Stage 1 implements ingest only: a video file becomes a content-addressed manifest. No pose, no
hold detection, no calibration, no models. Per-stage gates and measured evidence live in
[`docs/status.md`](docs/status.md).

## Roadmap

Each stage has a gate. **A stage does not start until the previous stage's gate is measured and
reported** in [`docs/status.md`](docs/status.md). The constraint on each line is what keeps this
a telemetry system rather than a coaching product.

| Stage | Delivers | Constraint |
| --- | --- | --- |
| 2 | Annotation harness, CVAT adapter, group-aware split manifests | CVAT is an **adapter**; the internal schema stays the source of truth. Splits are group-aware and frozen, and leakage is **tested, not assumed**. |
| 3 | Wall calibration and the hold map | Manual hold polygons and explicit problem membership **first**. Automatic segmentation only as **assistive preannotation**, behind a documented model adapter. |
| 4 | Climber pose trajectories | **One** pretrained pose backend, chosen by an ADR and benchmarked on the ClimbVision gold set, **not** by generic COCO AP. Raw keypoints and visibility stored **before** any filtering. |
| 5 | Limb-hold contact intervals and stable contact-state transitions | An **interpretable geometry and temporal baseline before any learned model**. Hands and feet evaluated as **separate slices**. |
| 6 | Attempts, moves, beta sequences, fall events, and comparison of two attempts by contact-event alignment | Moves are **derived from contact transitions**. **No generated coaching text.** |
| 7 | Repeated-attempt descriptive analytics: projected hip trajectory, move duration, contact dwell, explicitly defined hesitation observations, foot-adjustment counts, success/failure grouping, transition failure hazard with uncertainty | Only metrics derived from **validated primitives**. Returns `insufficient_data` when support is inadequate. |
| 8 | Minimal application surface: upload/job API, web review timeline, correction workflow, repeated-attempt comparison as a view over Stage 6 and 7 output, consent and retention controls | Application surface only **after the telemetry gates pass**. **No mobile app** until real web usage validates the workflow. |

## Install

Requires Python 3.11, [uv](https://docs.astral.sh/uv/), and `ffprobe` (FFmpeg) on `PATH`.

```bash
uv sync
```

## Usage

These are the only two commands that exist.

```bash
# Ingest one video into a content-addressed recording manifest.
uv run climbvision ingest <video> --out artifacts

# Validate one or more emitted JSON documents against the declared schema version.
uv run climbvision validate <json>...
```

`artifacts/` is git-ignored: it is regenerated, never hand-edited.

## Documentation

| Document | Contents |
| --- | --- |
| [`docs/mvp-contract.md`](docs/mvp-contract.md) | The frozen contract: envelope, scope, ontology, definitions, acceptance gates |
| [`docs/data-schema.md`](docs/data-schema.md) | Canonical entities, Stage 1 field tables, ID/provenance/serialization rules, ingest protocol |
| [`docs/annotation-guide.md`](docs/annotation-guide.md) | Human decision rules for annotators |
| [`docs/evaluation.md`](docs/evaluation.md) | Metric definitions, split and leakage policy, the Stage 1 gate |
| [`docs/model-registry.md`](docs/model-registry.md) | Model policy and current contents (zero models) |
| [`docs/status.md`](docs/status.md) | Stage ledger with measured evidence |

## Privacy

No real user video, faces, consent records or model weights are stored in this repository. The
boundary is enforced by a path-scoped `.gitignore`. Participants appear only as pseudonyms and
consent records are referenced by opaque ID. Test fixtures are synthetic and contain no people.
See the privacy section of [`docs/mvp-contract.md`](docs/mvp-contract.md).
