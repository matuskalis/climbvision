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
| 2 - Annotation harness, CVAT adapter, split manifests (next) | not started |
| 3 through 8 | not started |

Stage 1 implements ingest only: a video file becomes a content-addressed manifest. No pose, no
hold detection, no calibration, no models. Per-stage gates and measured evidence live in
[`docs/status.md`](docs/status.md).

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
