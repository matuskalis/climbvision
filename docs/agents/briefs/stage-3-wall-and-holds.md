# Stage 3 brief: wall calibration and confirmed hold map

Paste this whole file into the coding agent. It is written for an agent with **zero prior
context**: everything it needs is here or is named by an exact repository-relative path it must
read. Completeness beats brevity. Nothing in this brief may be skimmed on the grounds that it
looks like boilerplate.

Status tags as defined in the preamble of [`../../mvp-contract.md`](../../mvp-contract.md):
`[FIXED]`, `[VAL]` (unused — no validation data exists), `[PILOT]`, `[PLANNING]`. **An untagged
number is a defect**, except for identifiers, schema versions, stage numbers, test counts,
already-measured observations, and arithmetic inside a hand-calculated test fixture. Nothing in
this brief is `[VAL]`. No accuracy figure in this brief is a result.

---

## Section 0. Standing context, identical in every stage brief

This section is reproduced **verbatim** in every brief under `docs/agents/briefs/`. If you have
read it in another brief, read it again anyway: the numbered rules and conventions are cited by
number throughout the rest of this document. If two copies differ, the discrepancy is a defect:
report it, do not resolve it silently.

### 0.1 The fifteen truth rules

These are the rules the project exists to enforce. They are not style preferences. They are
reproduced verbatim from `AGENTS.md` Section 2.

1. Do not invent confidence values, probabilities or metrics.
2. Do not create a composite climbing score.
3. Every decision threshold must live in versioned configuration, include units, and record how it was selected on validation data.
4. Preserve raw model output before smoothing, interpolation or heuristic correction.
5. Predictions, preannotations, reviewed annotations, adjudicated ground truth and derived data must have separate provenance.
6. If evidence is insufficient, output `unknown`, `review`, `abstained` or `insufficient_data`.
7. "Hip trajectory" means the midpoint of the observed 2D hip joints. Never call it center of mass.
8. Wall-plane coordinates are not physical 3D body coordinates.
9. Visual proximity is not automatically intentional hold use.
10. Never claim the cause of a fall without a separately defined and validated label.
11. Do not download, train or bundle a model without recording its source, version, weights checksum, code license, checkpoint license, known training datasets and intended use.
12. Never commit real user video, faces, consent records or model weights.
13. Default tests must not require a network connection or large model download.
14. A production adapter must never silently fall back to synthetic or fake predictions.
15. An upstream `abstained` result cannot become a confident downstream result.

### 0.2 Conventions C1 through C10

Cited elsewhere in this brief as "C1", "C4" and so on.

**C1. All ratios are exact integer rationals.** A shared `RatioValue{num: int, den: int}`, always
reduced by `math.gcd`, with `den >= 1`. Every metric in `docs/evaluation.md` is naturally a ratio
of integer counts, so no float ever enters a schema and byte-identity stays testable.

**C2. Threshold comparison is integer cross-multiplication**, exactly as
`src/climbvision/quality.py` already does for frame rate (`measured.num * min_den >= min_num *
measured.den`). Thresholds in config are `{num, den}`.

**C3. Coordinates are integers in milli-units:** thousandths of a pixel in pixel spaces,
thousandths of one wall unit in the wall plane, with a single constant `COORDINATE_SCALE = 1000`.
Every point model carries its coordinate space.

**C4. `stabilized_px` is frozen at Stage 3** as the source raster with the container rotation
applied and nothing else. The map between `source_px` and `stabilized_px` is an exact integer
transform for rotations in {0, 90, 180, 270}; a null rotation or one that is not a multiple of 90
is a hard failure `ROTATION_UNSUPPORTED`.

**C5. Every stage emits one append-only run document** modelled exactly on `IngestRun` in
`src/climbvision/schema/provenance.py`, carrying run id, `created_at_utc` under the same pattern,
input document hashes, config version and hash, ontology version, code and Python versions, git
commit and dirty flag, external tool versions, and from Stage 4 onward the model id, checkpoint
hash and score type. Runs live at `<out>/<area>/<key>/runs/<run_id>.json`.

**C6. Nothing is keyed by a decoded frame counter.** Every per-frame record carries
`frame_index_position`, `pts` and the `time_base`. A decoded frame that cannot be resolved to a
`FrameIndex` timestamp is a hard failure, never a best-effort match. Decode order differs from
presentation order on two of the five committed fixtures.

**C7. `unknown` and `abstained` are values, not gaps.** A frame with no result emits a record with
an explicit abstention status and a null payload. Omitting the row is banned, because a missing
row is indistinguishable from "not processed".

**C8. Raw before filtered, in separate documents;** the filtered document references the raw one
by hash.

**C9. Config files are `configs/<area>/v1.json`,** in the same shape as `configs/ingest/v1.json`:
`config_version` and `thresholds.<name> = {value, unit, status, selection}`. `selection` must
state how the number was chosen; a number not yet chosen on data reads
`"Not selected. [PILOT] placeholder; no validation data exists."` A test asserts every threshold
has a non-empty `selection` and that nothing is tagged `[VAL]` while `docs/status.md` records no
selection run.

**C10. New error codes follow the existing SCREAMING_SNAKE convention** and are raised through
`ClimbVisionError(code, message)`. No new exception classes; 25 codes already exist.

### 0.3 The seam checklist

None of this is discoverable from the feature request. Every stage must touch these existing
files, and a stage that skips one will fail a guard it did not know existed.

| File | What the stage must do | Why |
| --- | --- | --- |
| `src/climbvision/schema/versions.py` | Add the schema id and version constants; extend `SCHEMA_IDS` | `test_every_schema_id_resolves_to_a_model` compares `SCHEMA_IDS` against `MODEL_REGISTRY` |
| `src/climbvision/schema/__init__.py` | Import the model, add it to `MODEL_REGISTRY` and to `__all__` | `climbvision validate` dispatches through `MODEL_REGISTRY` on the document's own `schema_id` |
| `tests/unit/test_schema.py` | Add a row to `DOCUMENT_MODELS` with a committed golden fixture under `tests/fixtures/documents/`, and add **every new nested model** to `ALL_MODELS` | `ALL_MODELS` drives the no-float, `extra="forbid"` and `frozen=True` checks. A nested model left out of it is unguarded. |
| `tests/unit/test_scope_guard.py` | Add a `STAGE_N_MODULES` set and change the inventory test to compare the on-disk set against the **union** of the per-stage sets. **Keep the per-stage sets separate: they are the decision record of which stage introduced which module.** Extend `ALLOWED_THIRD_PARTY` only if the brief authorizes a dependency; remove any newly permitted name from `BANNED`; add an assertion that `ALLOWED_THIRD_PARTY` and `BANNED` never intersect. | An import allowlist cannot see a later-stage module that imports nothing banned, so the file inventory itself is pinned |
| `tests/unit/test_scope_guard.py`, dependency pin | Replace `test_the_runtime_dependency_list_is_exactly_pydantic`, which string-matches the literal list, with a **parsed** test (`tomllib`, standard library) asserting the set of distribution names, that **every entry has an upper bound**, and that the optional-group names are exactly as expected, with an explicit distribution-to-import-root map for cases like `opencv-python` to `cv2` | A string match breaks on whitespace and silently passes on a reordered list |
| `src/climbvision/cli.py` and `tests/unit/test_cli.py` | Add the stage's subcommands with exit-code tests (**0** ok, **1** operation failed, **2** usage), plus a test asserting `climbvision validate` picks the new documents up automatically through `MODEL_REGISTRY` | The CLI is the owner's only interface |
| `configs/<area>/v1.json` | The stage's config file, in the C9 shape | Rule 3 |
| `docs/status.md` | The stage row, plus a measured-evidence table shaped like the Stage 1 one | Measured evidence only, never an expectation |
| The seven contract documents | Edit **only** where this brief explicitly authorizes it | `AGENTS.md` Section 12 |
| `docs/adr/<slug>.md` | One file per decision, created **one at a time as the decision is made**, in the format Context / Options considered / Decision / Consequences / Evidence that decided it / Date | A pre-stubbed decision record is indistinguishable from a decided one |
| `scripts/regenerate_fixtures.sh` | Extend it for any new generated fixture, keeping its manual-only banner | A CI regeneration would rewrite the bytes the tests pin |
| `.gitignore` | Add the paths this stage introduces | Path-scoped, never extension-scoped |

### 0.4 Where data lives

| Path | Git status | Reason |
| --- | --- | --- |
| `data/raw/` | ignored already | Real footage. Rule 12. |
| `data/recordings/` | ignored already | Real footage. Rule 12. |
| `data/consent/` | ignored already | Consent records. Rule 12. |
| `data/annotations/` | ignored, **to be added** | Annotation payloads describe real footage frame by frame |
| `data/releases/` | **committed**, with a negation added to `.gitignore` | A frozen test split must be under version control to be frozen. The manifest references annotation payloads **by hash**, so the release is verifiable without the payloads being in git. |
| `artifacts/` | ignored already | Regenerated, never hand-edited |
| `weights/`, `checkpoints/` | ignored already | Rule 12 |

A `.gitignore` negation cannot re-include a file whose **parent directory** is excluded. No rule
may therefore ever ignore `data/` wholesale, or `!data/releases/` becomes inert and the release
silently stops being tracked.

### 0.5 The honest sentence

Every accuracy-shaped number produced from this dataset is a within-participant, within-gym,
single-lighting-condition measurement on one camera placement. It bounds whether the pipeline
works here. It says nothing about a different climber, a different gym or a different camera, and
no report or status entry may imply otherwise.

### 0.6 Report format and stop condition

The implementer's final report is **exactly** these six items, in this order:

1. **The gate table.** One row per gate clause: clause, assertion, measured evidence. Numbers only
   where measured; every other cell reads `pending measurement`.
2. **Files added and changed.** Repository-relative paths, one line each, with what changed.
3. **Config thresholds introduced.** Name, value, unit, status tag.
4. **Open decisions deferred**, each with its decision slug.
5. **What this stage does not prove.**
6. **The command transcript.** Real output, pasted, not paraphrased.

The **reviewer independently re-measures every clause** rather than accepting the implementer's
numbers. That is what caught two real defects at Stage 1 (a fabricated frame-rate delta computed
across a timestamp gap, and a content-addressed manifest that could be silently overwritten out
from under the run record attesting to it).

Then **stop**. Do not start the next stage. Do not mark `docs/status.md` complete until the owner
approves. **If a gate fails**, report the measured gap with its number, propose the smallest next
experiment that would close it, and stop. A failed gate is information; a moved gate is nothing.

### 0.7 Decisions are referenced by slug, never by number

The briefs and the operating manual refer to decisions **by slug, never by number**: a number
reserved in advance is a number that will be wrong. Each decision is recorded as its own file
under `docs/adr/` **at the moment it is made, one at a time.** Decision records are never
pre-stubbed: an empty record is indistinguishable from a decided one, and a directory of
placeholders is a directory of lies.

The full index of open decisions is in `docs/agents/README.md`.

---

## 1. Mission

Turn a user-confirmed set of hold polygons plus a handful of measured wall fiducials into a **wall
set**, **problem versions** and **one planar homography**, with reprojection diagnostics and an
overlay.

Consumes: the `Recording` and `FrameIndex` for the reference frame's timestamp, the Stage 2
polygon annotations, and a hand-written fiducial file.

**Emits no predictions.** No segmentation model, no detector, no inference. The hold map is
user-confirmed by contract (`mvp-contract.md` Sections 1 and 11), so every polygon in every
document this stage writes carries `reviewed_annotation` provenance and originated from a human
tracing it.

The Stage 3 gate in `mvp-contract.md` Section 9 has **already been restated** to match this brief.
**No contract edit is needed here.**

---

## 2. Preconditions

## 2.1 What must be true before this stage opens

| Precondition | Detail |
| --- | --- |
| Stage 1 complete | Deterministic ingest, content-addressed manifests, `climbvision ingest` and `climbvision validate` |
| Stage 2 complete and **approved by the owner** | Commits 2a, 2b and 2c all reviewed and accepted |
| The portrait-orientation fix landed | Stage 2 Task 1, in `src/climbvision/quality.py`. Portrait 1080p footage is no longer flagged as a resolution failure. |
| Footage ingested | The reference frame's recording exists as a `recording.json` plus `frame_index.json` under `artifacts/recordings/<asset_id>/` |
| Hold polygons annotated | Stage 2 `AnnotationDocument` documents with `kind: polygons`, each polygon carrying a **stable human-assigned hold number** and an on-volume flag |

## 2.2 Stage 2 modules this stage depends on

Read them before writing anything; do not reimplement any of them.

| Module | What Stage 3 uses it for |
| --- | --- |
| `src/climbvision/schema/common.py` | `RatioValue`, `Point2D`, `CoordinateSpace`, `TimeInterval` |
| `src/climbvision/schema/ontology.py` | `ProvenanceClass`, `Visibility`, `ONTOLOGY_ID`, `ONTOLOGY_VERSION` |
| `src/climbvision/schema/annotation.py` | `PolygonAnnotation`, the input to the hold map |
| `src/climbvision/schema/metrics.py` | `MetricValue`, `MetricStatus`, `MetricReport` |
| `src/climbvision/geometry/polygons.py` | Shoelace doubled area, exact point-in-polygon, self-intersection check, scanline rasterisation |
| `src/climbvision/evaluation/masks.py` | Mask IoU, for the hold-polygon self-agreement clause |
| `src/climbvision/media/ffmpeg.py` | **The ffmpeg subprocess boundary.** If Stage 2 landed without it, create it here to the same shape as `src/climbvision/media/ffprobe.py`: bare basename, `cwd` set to the file's directory, argv recorded, version recorded, explicit demuxer options, `FFMPEG_NOT_FOUND` when absent. `ffmpeg` is the **second external subprocess boundary** in the codebase after `ffprobe`; `media/frames.py` is its second use site. |
| `src/climbvision/schema/runs.py` | The C5 run-document shape to follow |

## 2.3 What does not exist

No wall set, no calibration, no homography, no overlay, no problem definition. No `wall/` or
`geometry/rotation.py` module. No `configs/wall/v1.json`. No segmenter, and none is required to
reach this gate.

---

## 3. Human inputs required before the agent starts

**The owner never clicks correspondences in a custom GUI.** No point-picking tool is built, and
none is needed. Every input below is either a note, a tape measure reading, a CVAT shape or a
short hand-written JSON file. If a step in this section would require the owner to click points in
software this repository ships, the design is wrong and the agent must stop and say so.

| # | Input | Form | Why it is needed |
| --- | --- | --- | --- |
| 1 | **One clean reference frame per facet** | The owner notes an approximate time, in seconds, and the asset it belongs to. **The agent converts it to an exact timestamp** by resolving the nearest `FrameIndex` entry and reporting the exact `pts` it chose. | The wall set is defined against one image. "Clean" means the climber is not on the wall and no person occludes a hold. |
| 2 | **A tape-measured real distance** | Two identifiable points on the facet, in **millimetres**, plus which two fiducials they are | **Without it the wall plane has no physical scale**, and every millimetre-denominated threshold downstream must abstain. A wall plane with no scale is still geometrically valid; it just cannot answer "how far in millimetres". |
| 3 | **Six to ten CVAT point shapes** | Placed on identifiable, coplanar, well-spread wall features on the reference image. **Not on volumes.** **Not near-collinear.** | These are the fiducials. Fewer than six leaves no redundancy to detect a bad one; more than about twelve makes the exhaustive search slower for no gain. |
| 4 | **A hand-written fiducial file** | JSON, one entry per fiducial: its id and its **wall coordinates in millimetres from any origin the owner likes** | The homography needs both sides of each correspondence. The origin is arbitrary because a homography is defined up to the choice of frame. |
| 5 | **The hold polygons** | Already drawn at Stage 2. Each carries a **stable hold number** and an **on-volume flag**. | The hold map. User-confirmed by contract. |
| 6 | **Hand-written problem definitions** | JSON, one per problem: a list of hold numbers, each with a role and a foot-only flag | Problem identity is user-confirmed by contract (`mvp-contract.md` Section 2). The system never merges or infers problems. |

## 3.1 Fiducial placement guidance, for input 3

Give this to the owner verbatim before they place the points.

| Rule | Reason |
| --- | --- |
| All six to ten points must lie **on the same flat facet** | A homography maps one plane. A point on a different plane is not a correspondence, it is an error with a confident-looking number attached. |
| **Never on a volume** | A volume protrudes. Its parallax grows with depth, so it violates the planarity assumption by a distance that varies with the camera. |
| **Spread them to the corners** of the region the holds occupy | Projective error grows without bound outside the convex hull of the fiducials. Points clustered in the middle leave most of the wall extrapolated. |
| **No three near-collinear** | See trap 4 in Section 13. A near-collinear set solves cleanly and reprojects catastrophically. |
| Pick features that are **identifiable in the image and reachable with a tape measure**: bolt holes, seam corners, panel joints, a permanent marking | The wall coordinates are measured by hand, so the feature must be findable twice, once on the wall and once on the screen. |

The layout policy is the `fiducial-layout-policy` decision; this table is the recommendation the
decision either adopts or overrides.

---

## 4. Deliverables

## 4.1 New modules

All under `src/climbvision/`, all added to a new `STAGE_THREE_MODULES` set kept **separate** from
`STAGE_ONE_MODULES` and `STAGE_TWO_MODULES`.

| Module | Responsibility, one line |
| --- | --- |
| `media/frames.py` | Extract exactly one frame at an exact timestamp, through the ffmpeg subprocess boundary |
| `geometry/rotation.py` | The exact integer map of C4 between `source_px` and `stabilized_px` |
| `geometry/homography.py` | Deterministic exhaustive minimal-sample search and the exact-rational solver |
| `geometry/diagnostics.py` | Reprojection errors, mean squared error, convex hull, hull coverage |
| `wall/__init__.py` | Package marker, empty |
| `wall/build.py` | Assembles a `WallSet` and its `HoldInstance` list from polygon annotations plus a calibration |
| `wall/problems.py` | Validates and emits `ProblemVersion` and `ProblemHold` documents |
| `wall/overlay.py` | Pure-Python deterministic SVG overlay |
| `schema/wall.py` | `Gym`, `Wall`, `WallFacet`, `WallSet`, `HoldInstance`, `ProblemVersion`, `ProblemHold`, `ProblemHoldRole` |
| `schema/calibration.py` | `Calibration`, `Homography`, `FiducialCorrespondence`, and `CalibrationRun` |

`CalibrationRun` lives in `schema/calibration.py`, not in Stage 2's `schema/runs.py`. Stage 3's
models stay in Stage 3's files so the per-stage module sets remain an accurate decision record of
which stage introduced what.

## 4.2 New configuration

`configs/wall/v1.json`. Thresholds, units and status tags are in Section 8.8.

## 4.3 New CLI subcommands

| Command | Does |
| --- | --- |
| `climbvision reference-frame` | Extracts one frame at an exact timestamp and reports the `pts` and `frame_index_position` it used |
| `climbvision calibrate` | Fits the homography from the fiducial file, emits `Calibration` plus `CalibrationRun` |
| `climbvision wall-build` | Emits the `WallSet` and its `HoldInstance` list from the polygon annotations plus the calibration |
| `climbvision problems` | Validates and emits `ProblemVersion` and `ProblemHold` documents |
| `climbvision overlay` | Renders the deterministic SVG diagnostic |

Exit codes follow `src/climbvision/cli.py`: **0** ok, **1** operation failed, **2** usage.

## 4.4 Existing files changed

The Section 0.3 seam checklist, instantiated. Nothing else.

| File | Change |
| --- | --- |
| `src/climbvision/schema/versions.py` | Schema id and version constants for `WallSet`, `HoldInstance`, `ProblemVersion`, `Calibration`, `CalibrationRun`; extend `SCHEMA_IDS` |
| `src/climbvision/schema/__init__.py` | `MODEL_REGISTRY` entries and `__all__` |
| `src/climbvision/schema/ontology.py` | Register `ProblemHoldRole` in the ontology and **bump `ONTOLOGY_VERSION` from 1 to 2** |
| `src/climbvision/cli.py` | Five new subcommands |
| `tests/unit/test_schema.py` | New `DOCUMENT_MODELS` rows; every new nested model into `ALL_MODELS` |
| `tests/unit/test_scope_guard.py` | `STAGE_THREE_MODULES`; the union inventory test; the parsed dependency test still asserting exactly `pydantic` |
| `tests/unit/test_cli.py` | Exit-code tests, and the `validate`-through-`MODEL_REGISTRY` test for the new documents |
| `tests/fixtures/README.md` | Document the new hand-authored wall fixtures |
| `scripts/regenerate_fixtures.sh` | Extend only if a fixture is generated rather than hand-authored; keep the banner |
| `.gitignore` | Add nothing new unless a new output root appears; the Section 0.4 table already covers `artifacts/` |
| `docs/status.md` | The Stage 3 row and the measured-evidence table |
| `docs/adr/` | One file per decision actually made |

**Authorized contract edits: `docs/status.md` only.** `mvp-contract.md` Section 9 already carries
the restated Stage 3 gate, and `evaluation.md` Section 1 already defines every Stage 3 metric
including the `not_applicable` rule for the two mask metrics. If you believe another contract edit
is necessary, **stop and ask**.

### The ontology version bump, and why it is safe

Adding `ProblemHoldRole` changes the ontology, so `ONTOLOGY_VERSION` goes from 1 to 2. This is
safe **only because `ontology_version` is a plain `int` field on every document and never a
`Literal`.** Stage 2 documents keep version 1 and stay valid; nothing is upgraded in place, and
nothing is silently coerced (`data-schema.md` Section 4). Verify this before bumping: if any Stage
2 model pinned `ontology_version` as a `Literal`, fix that first, in its own commit, and say so.

---

## 5. Entities

All eight are **on schedule at Stage 3** per `docs/data-schema.md` Section 1: `Gym`, `Wall`,
`WallFacet`, `WallSet`, `HoldInstance`, `ProblemVersion`, `ProblemHold`, `Calibration`. None is
early and none is late.

Model and field names below are **proposals** except the eight entity names, which are fixed by
`data-schema.md`.

## 5.1 Identity, which encodes the contract

| Id | Derivation | Why this form |
| --- | --- | --- |
| `gym_id`, `wall_id`, `facet_id`, `revision_label` | Owner-supplied slugs, each matching `^[a-z0-9][a-z0-9_-]{0,31}$` | Human-readable, pattern-checkable, no personal data |
| `wall_set_id` | `f"{gym_id}.{wall_id}.{facet_id}.{revision_label}"` | A reset produces a new `revision_label`, therefore a new `wall_set_id` |
| `hold_id` | `f"{wall_set_id}.h{hold_number}"` | **Stable across a polygon correction**, because the polygon is not in the derivation. Correcting a traced outline must not renumber anything. |
| `problem_version_id` | `f"{wall_set_id}.p{problem_slug}"` | **Problem identity is scoped to the `WallSet` revision by construction** (`mvp-contract.md` Section 5, standing rule 2). The id literally cannot be reused across a reset, so the rule holds structurally rather than by discipline. |

A duplicate `hold_number` within a wall set is a hard failure, `HOLD_NUMBER_DUPLICATE`. Two holds
with the same number would collide on `hold_id`, and the collision would be silent.

## 5.2 Field lists

### `schema/wall.py`

| Model | Fields |
| --- | --- |
| `Gym` | `gym_id: str`; `display_name: str`. Nested, not a document. |
| `Wall` | `wall_id: str`; `gym_id: str`; `display_name: str` |
| `WallFacet` | `facet_id: str`; `wall_id: str`; `display_name: str` |
| `WallSet` (document) | `schema_id`; `schema_version`; `wall_set_id: str`; `created_at_utc: str`; `ontology_version: int`; `gym: Gym`; `wall: Wall`; `facet: WallFacet`; `revision_label: str`; `reference_image_sha256: str`; `reference_asset_id: str`; `reference_pts: int`; `reference_frame_index_position: int`; `reference_time_base: Timebase`; `image_width_px: int`; `image_height_px: int`; `coordinate_space: CoordinateSpace` (always `stabilized_px`); `hold_count: int`; `provenance_class: ProvenanceClass` |
| `HoldInstance` (document) | `schema_id`; `schema_version`; `hold_id: str`; `wall_set_id: str`; `hold_number: int`; `polygon_stabilized_px: list[Point2D]`; `polygon_wall_plane: list[Point2D] \| None`; `outside_fiducial_hull: bool`; `centroid_stabilized_px: Point2D`; `doubled_area_stabilized_px: int`; `on_volume: bool`; `provenance_class: ProvenanceClass` |
| `ProblemHoldRole` | Enum: `start`, `intermediate`, `finish` |
| `ProblemHold` | `hold_id: str`; `hold_number: int`; `role: ProblemHoldRole`; `foot_only: bool` |
| `ProblemVersion` (document) | `schema_id`; `schema_version`; `problem_version_id: str`; `wall_set_id: str`; `created_at_utc: str`; `ontology_version: int`; `problem_slug: str`; `grade_note: str \| None`; `holds: list[ProblemHold]`; `provenance_class: ProvenanceClass` |

`polygon_wall_plane` is **null** when the hold lies outside the fiducial hull. Not an
extrapolated polygon, not an empty list: null, with `outside_fiducial_hull: true` beside it, so a
reader can tell "we looked and there was nothing" from "there are zero vertices".

`grade_note` is **explicitly a note and never a prediction.** Route grade prediction is out of
scope permanently (`mvp-contract.md` Section 2: grade is a community judgement, not an
observable). The field carries what the gym's tag said, as a string, and no code may consume it as
a number, rank or feature.

### `schema/calibration.py`

| Model | Fields |
| --- | --- |
| `Homography` | `elements: list[int]` (exactly 9, row-major); `denominator: int`; `normalization: Literal["h33_equals_one"]`; `source_space: CoordinateSpace` (`stabilized_px`); `target_space: CoordinateSpace` (`wall_plane`) |
| `FiducialCorrespondence` | `fiducial_id: str`; `image_point: Point2D` (`stabilized_px`); `wall_point: Point2D` (`wall_plane`) |
| `Calibration` (document) | `schema_id`; `schema_version`; `calibration_id: str`; `wall_set_id: str`; `created_at_utc: str`; `ontology_version: int`; `homography: Homography`; `fiducials: list[FiducialCorrespondence]`; `inlier_fiducial_ids: list[str]`; `max_reprojection_error_milli_wall_units: int`; `rms_reprojection_error_milli_wall_units: int`; `mean_squared_error: RatioValue`; `hull_coverage: RatioValue`; `millimetres_per_wall_unit: RatioValue \| None`; `scale_check_residual_milli_wall_units: int \| None`; `solver_id: str`; `subsets_evaluated: int`; `provenance_class: ProvenanceClass` |
| `CalibrationRun` (document) | The C5 fields: `run_id`; `created_at_utc`; `inputs` and `outputs` as basename/sha256/schema_id triples; `config_version`; `config_sha256`; `ontology_version`; `climbvision_version`; `python_version`; `git_commit`; `git_dirty`; `external_tools`. Plus `camera_motion: Literal["unknown"]` and `camera_motion_reason: str`. |

`millimetres_per_wall_unit` is **null** when no tape measure was supplied. Every downstream
millimetre-denominated threshold must then abstain rather than assume a scale.

`subsets_evaluated` is recorded because it makes the search auditable: with `n` fiducials it must
equal `C(n,4)` minus the subsets rejected for degeneracy, and a reviewer can recompute it.

---

## 6. Decisions already frozen

| Frozen decision | Where |
| --- | --- |
| One approximately planar wall facet; single static camera; no pan, zoom or reframing | `mvp-contract.md` Section 1 |
| Hold map is **user-confirmed** and problem identity is **explicitly user-confirmed** | `mvp-contract.md` Sections 1, 2 and 11 |
| Automatic problem merging is out of scope | `mvp-contract.md` Section 2 |
| Route grade prediction is out of scope | `mvp-contract.md` Section 2 |
| Four coordinate spaces; every geometry value declares exactly one; **wall-plane coordinates are not physical 3D body coordinates** | `mvp-contract.md` Section 4; truth rule 8 |
| A problem ID is scoped to a `WallSet` revision; a reset produces a new `WallSet` | `mvp-contract.md` Section 5 |
| Masks are COCO polygons; RLE deferred because it needs a numerical array dependency | `data-schema.md` Section 6 |
| An overlay is **never the only result**; the structured artifact must exist too | `data-schema.md` Section 6 |
| Absolute filesystem paths never appear in written artifacts | `mvp-contract.md` Section 7 |
| Canonical JSON, no float, explicit `null`, byte-identity is a gate clause | `data-schema.md` Section 7 |
| Reprojection error is reported in **integer milli-wall-units** | `evaluation.md` Section 1 |
| Mask IoU and mask AP are **`not_applicable` until a segmenter is adopted by explicit decision**, which is neither zero nor a failure | `evaluation.md` Section 1; `mvp-contract.md` Section 9 |
| Hold-polygon self-agreement IoU measures one annotator's tracing stability and is **never** reported as inter-annotator agreement | `evaluation.md` Section 1; `annotation-guide.md` Section 6 |
| The Stage 3 gate wording, already restated to match this brief | `mvp-contract.md` Section 9 |
| Conventions C1 through C10 | Section 0.2 of this brief |

---

## 7. Open decisions

| Slug | Blocks | What the owner must decide |
| --- | --- | --- |
| `wall-plane-units-and-scale` | The calibration | What one wall unit **is**. See the option table in Section 8.5. **Recommended: one wall unit equals one millimetre**, which makes `millimetres_per_wall_unit` exactly `1/1`, makes milli-wall-units micrometres, and turns the tape measure into a consistency check rather than a conversion factor with a rounding error in it. |
| `fiducial-layout-policy` | The fiducial placement | How many fiducials, where they go, whether volumes are ever acceptable, and what happens when a facet has too few identifiable features. Section 3.1 is the recommendation this decision adopts or overrides. |
| `hold-segmentation-model` | Nothing at Stage 3 | Whether a segmenter is ever adopted as **assistive preannotation only**, behind a license decision (`model-registry.md` Section 4). Until it is, mask IoU and mask AP are recorded as `not_applicable` with the reason, and **no polygon in any Stage 3 document may originate from a model.** |

The agent decides none of these. Where one is needed and absent, stop and ask.

---

## 8. Approach

## 8.1 Reference frame extraction

`media/frames.py` extracts exactly one frame, through `media/ffmpeg.py`, from the file's own
directory with a bare basename.

```
ffmpeg -hide_banner -loglevel error -nostdin \
       -ignore_editlist 0 -noautorotate \
       -i <basename> \
       -map 0:v:0 -an \
       -vf "select='eq(pts\,<PTS_TICKS>)'<rotation filter>" \
       -fps_mode passthrough \
       -f image2 <out_dir>/frame-%03d.png
```

| Rule | Why |
| --- | --- |
| `-ignore_editlist 0` on the **extraction** call, not only on the probe | An edit list shifts every PTS the demuxer reports. Stage 1 measured the shift on this repository's own CFR fixture at **1024 ticks**. Probing with the flag and extracting without it selects a different frame than the one the frame index names. |
| `-noautorotate` | Without it ffmpeg bakes the rotation in and drops the side data, so the applied transform is unrecorded and the output dimensions silently disagree with C4 |
| `select='eq(pts,N)'` on **integer ticks** | Exact frame selection |
| **No `-ss`, ever** | Seeking before the input is approximate: it lands on the nearest keyframe before the target. Seeking after the input takes seconds, which reintroduces float time. Both are banned. |
| Numbered output pattern plus a file count assertion | **Assert exactly one frame was produced.** Zero files raises `REFERENCE_FRAME_NOT_FOUND`; more than one raises `REFERENCE_FRAME_AMBIGUOUS`. Trusting `-frames:v 1` asserts nothing: it truncates a wrong result into a plausible one. |

Then hash the output with `sha256_file`, and record in the `CalibrationRun`: the argv, the ffmpeg
version, the source asset id, the chosen `pts`, the chosen `frame_index_position`, the
`time_base`, and the output image sha256.

**Assert the extracted image's dimensions equal the C4-transformed coded dimensions** from the
`Recording`'s `VideoStreamInfo`. This is the single check that catches an autorotation mistake, a
wrong `transpose` direction, and a rotation the container declares but the pixels already carry.

## 8.2 The rotation map, C4

`geometry/rotation.py` implements the exact integer map for the four legal rotations, in
**continuous milli-unit coordinates** (not pixel indices, which would need an off-by-one
correction that is easy to get wrong in one direction only). For a source raster of `W` by `H`
milli-units and a clockwise display rotation `R`:

| `R` | Point map | Output dimensions |
| --- | --- | --- |
| 0 | `(x, y) -> (x, y)` | `W` by `H` |
| 90 | `(x, y) -> (H - y, x)` | `H` by `W` |
| 180 | `(x, y) -> (W - x, H - y)` | `W` by `H` |
| 270 | `(x, y) -> (y, W - x)` | `H` by `W` |

Sanity check for 90: the source top-left `(0, 0)` maps to `(H, 0)`, the top-right of the rotated
raster, which is where a clockwise quarter turn puts it. The source bottom-left `(0, H)` maps to
`(0, 0)`.

A rotation that is `null` (`rotation_source` is `display_matrix_unreadable` or `tag_unreadable`,
both of which carry `rotation_degrees: null` per `data-schema.md` Section 9) or that is not a
multiple of 90 raises `ROTATION_UNSUPPORTED`. **Never default an unreadable rotation to zero**;
that is exactly the unknown-to-negative coercion Stage 1 already fixed once.

## 8.3 The homography: a deterministic exhaustive minimal-sample search, not RANSAC

**Why not RANSAC.** With ten to twelve fiducials there are at most a few hundred four-subsets:
`C(10,4) = 210`, `C(12,4) = 495`. Enumeration is therefore **exhaustive, ordered and fully
deterministic**, and it evaluates every candidate rather than a random sample of them. Random
sampling would break byte-identity, would need a seed that is only reproducible until the Python
version changes, and would buy nothing at this scale: it exists to avoid combinatorial explosion
that does not occur here. Use `itertools.combinations`, standard library.

For each 4-subset, in `combinations` order:

1. **Reject degenerate subsets.** For all four triples within the subset, compute the exact
   integer doubled area `|(b - a) x (c - a)|` in **both** the image points and the wall points.
   Reject the subset if any triple is exactly zero (collinear) or below
   `min_fiducial_triangle_doubled_area`. Count rejections; they contribute to `subsets_evaluated`
   being auditable.
2. **Solve the 8-by-8 system by Gaussian elimination over `fractions.Fraction`.** The unknowns are
   `h11..h32` with `h33 = 1`. **No floating point in the solver at all**, not for pivoting, not for
   scaling, not for a tolerance. Pivot on the first non-zero entry in exact arithmetic; a singular
   system means this subset is unusable, so skip it. If **every** subset is rejected or singular,
   raise `HOMOGRAPHY_DEGENERATE`.
3. **Score the candidate over all fiducials, in exact rationals.** For each fiducial, map its image
   point through the candidate: `(u', v', w') = H . (x, y, 1)`. If `w' == 0` the candidate sends a
   fiducial to infinity, so reject the candidate outright. Otherwise `u = u'/w'`, `v = v'/w'`, and
   the squared error is `(u - u_measured)^2 + (v - v_measured)^2` as an exact `Fraction`. The score
   is the sum over **all** fiducials, not over the four in the subset.
4. **Take the minimum**, with a **lexicographic tie-break on the sorted subset index tuple**, so
   two equal-scoring candidates always resolve the same way.

Record `solver_id`, for example `"exhaustive-4subset-exact-rational/v1"`, and `subsets_evaluated`.

**Optional float refinement is out of scope.** If the fit's maximum error exceeds the threshold,
the answer is to **add or re-place fiducials**, not to add an optimiser. A nonlinear refinement
would reintroduce floating point into the one place this stage is exact, would make the result
depend on an iteration count, and would paper over a fiducial that is on a volume or mismeasured,
which is information the owner needs.

## 8.4 Quantisation, and the single most likely correctness defect in this stage

Quantise **once**, at the schema boundary:

1. Normalise so `h33 = 1` by dividing every element by `h33`. If `h33 == 0` exactly, raise
   `HOMOGRAPHY_NORMALIZATION_DEGENERATE`.
2. Multiply every element by `homography_denominator` `[FIXED]` and round half away from zero to
   an integer, using the same rounding rule as `src/climbvision/timebase.py`.
3. Store the nine integers and the denominator.

**Then recompute every reported diagnostic from the quantised matrix, not from the
pre-quantisation rational.** Rebuild `H_q` as `Fraction(element, denominator)` for each element,
reproject every fiducial through `H_q`, and compute the max error, the mean squared error, the RMS
and the inlier list from **those** residuals.

**Say it plainly: this is the single most likely correctness defect in this stage.** The
pre-quantisation rational is right there in the same function, it is more accurate, and using it
produces slightly better-looking numbers. It is also wrong, because the artifact that ships is the
quantised matrix, and a consumer that reprojects with the stored matrix will not reproduce the
stored diagnostics. A calibration whose own diagnostics do not describe itself is worse than one
with a larger honest error, because nothing downstream can detect the discrepancy. Section 10 makes
this a test: **storing a diagnostic computed from the pre-quantisation rational must fail.**

## 8.5 Diagnostics

| Diagnostic | Computation |
| --- | --- |
| Max reprojection error | `math.isqrt(num // den)` of the largest squared residual expressed as a `Fraction`. Documented as an **integer floor** in milli-wall-units. The identity `floor(sqrt(x)) == isqrt(floor(x))` for real `x >= 0` makes this exact rather than an approximation. |
| Mean squared error | An exact `RatioValue`, stored in full. Nothing is lost to the floor. |
| RMS reprojection error | `math.isqrt(mse_num // mse_den)`, documented as an **integer floor** in milli-wall-units |
| Inlier fiducial ids | Those whose reprojection error is at or below `max_reprojection_error_milli_wall_units`, compared by C2 |
| Hull coverage | `RatioValue(holds_whose_centroid_is_inside_the_hull, total_holds)`. The convex hull of the fiducial **image** points, by monotone chain with exact integer cross products. A point exactly on the hull boundary counts as inside; declare and test it. |

**Max, RMS and MSE are computed over all supplied fiducials, not over the inliers only.** Reporting
the max over inliers, where an inlier is defined by being under the max threshold, makes the
threshold self-satisfying: the number would pass by construction and the displaced fiducial would
vanish from the report. The inlier list is reported **beside** the all-fiducial numbers, so a
reviewer sees both.

**Every hold whose centroid falls outside the fiducial hull gets `polygon_wall_plane: null` and
`outside_fiducial_hull: true`, and is counted in the report.** Projective error grows without bound
outside the hull: the mapping is still defined, it is simply unconstrained by any measurement, and
a wall-plane polygon computed there would look exactly like a measured one.

### The scale, `wall-plane-units-and-scale`

| Option | `millimetres_per_wall_unit` | Consequence |
| --- | --- | --- |
| **A: one wall unit is one millimetre** (**recommended**) | Exactly `1/1` | The fiducial file is already in millimetres, so no conversion happens and no rounding is introduced. Milli-wall-units are **micrometres**, so a max reprojection error of `10_000` reads as 10 mm. The tape measure becomes a **consistency check** on the owner's own coordinates rather than a conversion factor. |
| B: one wall unit is the tape-measured reference distance | A quantised `RatioValue` | The distance between two points is generally irrational, so the scale is an approximation with a rounding error that then multiplies into every reported number. |
| C: no scale supplied | `null` | Geometrically valid. Every millimetre-denominated downstream threshold **abstains**, per truth rule 6. |

Under option A, report `scale_check_residual_milli_wall_units`: the signed difference between the
tape-measured distance and the distance implied by the two fiducials' recorded wall coordinates.
**Report it; do not gate on it.** It is a measurement of the owner's tape work, and turning it into
a threshold would invent a number nobody has evidence for.

## 8.6 Camera motion is not measured at this stage

Detecting camera motion requires comparing pixels across frames, which needs a numerical array
dependency this stage does not have and does not want. So:

- Record `camera_motion: "unknown"` in the `CalibrationRun`, with a `camera_motion_reason` string
  saying it was not measured and why.
- **Do not add a member to `QualityFlag`.** `src/climbvision/quality.py::assess` returns one
  `QualityAssessment` per flag, so emitting a fifth flag adds an entry to `Recording.quality`,
  which changes the manifest bytes **for every asset**, which trips `MANIFEST_CONFLICT` in
  `src/climbvision/ingest.py::_refuse_conflicting_manifest` against the run records already
  attesting to the stored bytes. Every previously ingested recording would have to be deleted and
  re-ingested to accommodate a field nobody measured.
- Upgrade it to a real measurement at **Stage 4**, as a **separate document**, once a pixel-level
  dependency is authorized by a brief.

The operating envelope assumes no pan, no zoom and no reframing (`mvp-contract.md` Section 1). This
stage **assumes** that; it does not verify it. Say so in the report.

## 8.7 The overlay

Pure-Python SVG. **No imaging library.** SVG is text, and text is what a byte-stability test can
assert on.

| Element | Rule |
| --- | --- |
| Reference image | Referenced by **relative basename** in the `href`, never an absolute path. `mvp-contract.md` Section 7: a path can contain a person's name. |
| Hold polygons | Drawn with their hold numbers as text labels |
| Fiducials | Crosses at the image points, with each residual drawn as a **line** from the measured point to the reprojected point, so the length of the line is the error |
| Fiducial hull | Dashed |
| Problem membership | Colour-coded by `ProblemHoldRole`; foot-only holds distinguished |
| Attribute ordering | **Deterministic**, sorted, so the bytes are stable and the file diffs cleanly between two calibrations |

The overlay is a **diagnostic view, never the only result** (`data-schema.md` Section 6). The
`WallSet`, `HoldInstance` and `Calibration` documents must exist beside it, and a test asserts
they do.

## 8.8 Threshold table

`configs/wall/v1.json`. Every number carries a status tag. Nothing is `[VAL]`.

| Threshold | Value | Unit | Status | Selection text |
| --- | --- | --- | --- | --- |
| `min_fiducial_count` | Integer placeholder, at least 6 | `count` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` |
| `min_fiducial_triangle_doubled_area` | Integer placeholder | `squared_milli_units_doubled` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` |
| `max_reprojection_error_milli_wall_units` | Integer placeholder | `milli_wall_units` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` |
| `max_rms_reprojection_error_milli_wall_units` | Integer placeholder | `milli_wall_units` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` |
| `min_hull_coverage` | `{num, den}` placeholder | `ratio` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` |
| `min_hold_doubled_area` | Integer placeholder | `squared_milli_units_doubled` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` |
| `homography_denominator` | `1000000` | `denominator` | `[FIXED]` | Definitional, not empirical. Fixes the quantisation grid of the stored matrix. Every reported diagnostic is recomputed from the quantised matrix, so this value affects the recorded numbers and changing it changes what every calibration means. Recorded as an ADR at Stage 3. |

No deterministic gate clause in Section 11 depends on the value of any `[PILOT]` threshold. A
placeholder must not be able to make a gate pass.

## 8.9 New error codes

Raised through the existing `ClimbVisionError(code, message)`; no new exception classes (C10).

`ROTATION_UNSUPPORTED` (if Stage 2 did not already add it), `REFERENCE_FRAME_NOT_FOUND`,
`REFERENCE_FRAME_AMBIGUOUS`, `FIDUCIAL_COUNT_BELOW_MIN`, `FIDUCIAL_SET_DEGENERATE`,
`HOMOGRAPHY_DEGENERATE`, `HOMOGRAPHY_NORMALIZATION_DEGENERATE`, `HOLD_NUMBER_DUPLICATE`,
`PROBLEM_HOLD_UNKNOWN`, `PROBLEM_WITHOUT_START`, `CALIBRATION_CONFLICT`.

`CALIBRATION_CONFLICT` mirrors `MANIFEST_CONFLICT`: refuse to overwrite a stored calibration whose
bytes would change, because the run record attests to the stored bytes by hash. Identical bytes
remain a silent no-op, so a re-fit on identical inputs is idempotent.

---

## 9. Dependencies

## **Zero new dependencies again. This is the second consecutive stage that adds none.**

`pyproject.toml` is unchanged. `ALLOWED_THIRD_PARTY` stays exactly `{"pydantic"}`. The whole
43-name `BANNED` list stays banned, `numpy` and `cv2` included, and this stage is the one where
that would have been easiest to break.

| Thing that looks like it needs a library | What it actually needs |
| --- | --- |
| Exact rational linear algebra | `fractions.Fraction`, standard library |
| Integer square root | `math.isqrt`, standard library |
| Exhaustive subset enumeration | `itertools.combinations`, standard library |
| Convex hull, polygon area, point-in-polygon | Integer cross products, already in `geometry/polygons.py` from Stage 2 |
| The overlay | SVG is text |
| Frame extraction | `ffmpeg` as a subprocess, already the boundary Stage 2 introduced |

`ffmpeg` is an **external tool at the media boundary**, not a Python package. Its version and argv
go into the `CalibrationRun` exactly as `ffprobe`'s go into `IngestRun`. Tests that need it
**skip**, they do not fail (rule 13).

---

## 10. Tests

## 10.1 Homography correctness

| Test | Assertion |
| --- | --- |
| Known integer homography, affine | Build an integer matrix, project four points through it, feed the four correspondences back, and assert the **recovered matrix equals the original up to scale**, checked by integer cross-multiplication (`a_i * b_j == a_j * b_i` for every pair of elements). Not by comparing elements directly: a homography is only defined up to scale, and an element comparison would fail on a correct answer. |
| Known **projective** homography | The same, with a genuinely projective matrix, meaning non-zero `h31` or `h32`. An affine-only test passes for a solver that silently drops the projective terms. |
| Collinear rejection | Four points with three collinear raise, and the message names the offending triple |
| Outlier exclusion | With **six** fiducials, one deliberately displaced, the search selects a subset that **excludes** it, and the displaced fiducial is **absent from `inlier_fiducial_ids`** |
| Quantisation self-consistency | Diagnostics recomputed from the **quantised** matrix equal the stored values exactly. **And the negative case: a calibration whose diagnostics were computed from the pre-quantisation rational must fail this test.** Write the failing variant explicitly so the test is proven to have teeth. |
| Degenerate normalisation | A matrix with `h33 == 0` raises `HOMOGRAPHY_NORMALIZATION_DEGENERATE` |
| Subset count | `subsets_evaluated` equals `C(n,4)` minus the rejected subsets, recomputed independently in the test |

## 10.2 Rotation, holds, problems and the overlay

| Test | Assertion |
| --- | --- |
| Rotation round trip | For each of 0, 90, 180 and 270, applying the map then the inverse returns the original point exactly, and the transformed dimensions match the table in Section 8.2 |
| Rotation rejection | A `null` rotation and a rotation of 45 both raise `ROTATION_UNSUPPORTED` |
| Hold id stability | Correcting a polygon's vertices while leaving `hold_number` unchanged leaves `hold_id` **unchanged** |
| Duplicate hold number | Two polygons with the same `hold_number` in one wall set raise `HOLD_NUMBER_DUPLICATE` |
| Outside the hull | A hold whose centroid lies outside the fiducial hull gets `polygon_wall_plane: null`, `outside_fiducial_hull: true`, and is **counted** in the report rather than silently extrapolated |
| Overlay byte stability | Rendering twice from the same inputs produces byte-identical SVG |
| Overlay contains no absolute path | Grep the rendered bytes for a leading `/` in any `href` and for the string `/Users` |
| Overlay is not the only result | Rendering an overlay without the `WallSet` and `Calibration` documents present on disk fails |
| Unknown problem hold | A problem referencing a hold number not in the wall set raises `PROBLEM_HOLD_UNKNOWN` |
| Problem without a start | A problem with no hold carrying `role: start` raises `PROBLEM_WITHOUT_START` |
| Calibration conflict | Re-fitting with different config and writing over a stored calibration raises `CALIBRATION_CONFLICT`; identical bytes are a silent no-op |
| Frame extraction | **ffmpeg-gated integration test**: extract a frame at a known timestamp from a committed fixture, assert exactly one file is produced, and assert its dimensions equal the C4-transformed coded dimensions. Use `rot90_160x120_1s.mp4`, which carries a real Display Matrix, so the rotation path is exercised on a real fixture and not only in a unit test. |
| Validate picks up new documents | `climbvision validate` accepts one golden fixture per new schema id through `MODEL_REGISTRY` |
| Ontology version | Stage 2 golden documents still validate with `ontology_version: 1` after the bump to 2 |

## 10.3 New fixtures

All hand-authored, under `tests/fixtures/wall/`, documented in `tests/fixtures/README.md` as
**validator inputs, not observations**, exactly as `tests/fixtures/probe_invalid/` is.

| Fixture | Contents |
| --- | --- |
| Synthetic eight-hold wall | Hand-authored polygon JSON in the `AnnotationDocument` `polygons` shape, with hold numbers 1 to 8, one of them flagged `on_volume`, and one deliberately placed outside the fiducial hull |
| Fiducial file with a known exact homography | Six correspondences generated by hand from a chosen integer matrix, so the expected recovered matrix is known before the solver runs |
| Degenerate fiducial set | Four points with three collinear, plus a six-point set with one deliberately displaced |

A gate number comes from real data and **never** from `tests/fixtures/`. Fixtures prove the code
runs; they do not measure calibration quality.

---

## 11. Gate

This is the gate in the restated form already in `mvp-contract.md` Section 9.

## 11.1 Deterministic clauses, not `[PILOT]`

| # | Clause | Assertion |
| --- | --- | --- |
| D1 | Tests and lint | `uv run pytest` all pass, `uv run ruff check .` clean. **No skipped test counts as a pass**; report passed and skipped separately. |
| D2 | Round trip, equality | `model == parse(dump(model))` for every new document model |
| D3 | Round trip, byte identity | `dump(parse(dump(model))) == dump(model)` byte-for-byte for every new document model |
| D4 | Known homography | The known integer homography, affine and projective, is reproduced **exactly** up to scale by integer cross-multiplication |
| D5 | Diagnostics self-consistency | Every reported diagnostic is recomputed from the **quantised** matrix and matches the stored value; the pre-quantisation variant fails the test |
| D6 | Real reprojection error | The real wall's **max reprojection error reported as a number** in milli-wall-units, against a `[PILOT]` target |
| D7 | Hull coverage | Reported as a `RatioValue`, with the count of outside-hull holds and their `polygon_wall_plane: null` |
| D8 | Provenance | **Every `HoldInstance` carries `reviewed_annotation` provenance and no polygon originated from a model.** Assert it as a test over the emitted documents, not as a claim in prose. |
| D9 | Idempotent re-fit | A re-fit on identical inputs produces a **byte-identical** `Calibration` and a **second append-only run record** |

## 11.2 The `[PILOT]` clauses

| Clause | Form |
| --- | --- |
| Reprojection target | Max and RMS reprojection error against `[PILOT]` targets that do not exist yet, so the clause is "measured and reported", not "under X" |
| Hull coverage target | Same |
| Hold-polygon self-agreement IoU | Mask IoU between two blind tracings of the same hold by the same annotator, over a re-traced subset, per wall set. Reported as **self-agreement**, never as inter-annotator agreement (`evaluation.md` Section 1; `annotation-guide.md` Section 6). |

## 11.3 Recorded as `not_applicable`, never blank and never zero

Model **mask IoU** and **mask average precision** are recorded as `MetricStatus.not_applicable`
with the reason string "no segmenter adopted; `hold-segmentation-model` open; the hold map is
user-confirmed by contract". Zero would say the model is bad. Blank would say nobody looked. The
accuracy of a model that does not exist is **undefined**, and `not_applicable` is the only value
that says that.

## 11.4 Honest limitation

With one or two facets, this measures **how consistently one person traces a hold, on one gym's
holds, under one lighting condition.** It supports no claim about a third wall, a different hold
brand, a different colour scheme or a different camera position.

The reprojection error measures how well one plane fits the fiducials **that were measured**. It
says nothing about the parts of the wall outside the fiducial hull, which is why holds out there
get a null wall polygon rather than an extrapolated one.

Camera motion is **assumed absent, not measured** (Section 8.6).

Plus the honest sentence in Section 0.5, verbatim.

---

## 12. Verification commands

```bash
# Environment
uv sync

# Full gate
uv run pytest
uv run ruff check .

# The homography subset, verbosely
uv run pytest tests/unit/test_homography.py -v

# Hermetic run: ffprobe and ffmpeg off PATH. The media-gated tests must SKIP, not fail.
PATH="$(printf '%s' "$PATH" | tr ':' '\n' \
        | grep -v -F "$(dirname "$(command -v ffprobe)")" | paste -sd: -)" \
  uv run pytest

# Extract the reference frame at an exact timestamp
uv run climbvision reference-frame \
  --asset sha256-<64hex> \
  --artifacts artifacts \
  --near-seconds 12 \
  --out artifacts/wall/<wall_set_id>

# Fit the calibration
uv run climbvision calibrate \
  --wall-set <wall_set_id> \
  --reference artifacts/wall/<wall_set_id>/frame-001.png \
  --fiducials ~/climbvision-data/wall/<wall_set_id>.fiducials.json \
  --out artifacts/wall

# Build the wall set and its hold instances
uv run climbvision wall-build \
  --wall-set <wall_set_id> \
  --polygons artifacts/annotations/<asset_id>/pass-a/polygons.json \
  --calibration artifacts/wall/<wall_set_id>/calibration.json \
  --out artifacts/wall

# Emit the problem versions
uv run climbvision problems \
  --wall-set <wall_set_id> \
  --definitions ~/climbvision-data/wall/<wall_set_id>.problems.json \
  --out artifacts/wall

# Render the overlay
uv run climbvision overlay \
  --wall-set artifacts/wall/<wall_set_id>/wall_set.json \
  --calibration artifacts/wall/<wall_set_id>/calibration.json \
  --out artifacts/wall/<wall_set_id>/overlay.svg

# Validate every emitted document through MODEL_REGISTRY
uv run climbvision validate \
  artifacts/wall/<wall_set_id>/wall_set.json \
  artifacts/wall/<wall_set_id>/calibration.json \
  artifacts/wall/<wall_set_id>/problems/*.json

# Idempotence: re-fit and confirm byte-identity plus a second run record
uv run climbvision calibrate --wall-set <wall_set_id> \
  --reference artifacts/wall/<wall_set_id>/frame-001.png \
  --fiducials ~/climbvision-data/wall/<wall_set_id>.fiducials.json \
  --out artifacts/wall
shasum -a 256 artifacts/wall/<wall_set_id>/calibration.json
ls artifacts/wall/<wall_set_id>/runs/

# OPEN THE OVERLAY AND LOOK AT IT
open artifacts/wall/<wall_set_id>/overlay.svg
```

## **The overlay is the human check.**

The last command is not decoration and it is not optional. The owner opens the SVG and confirms
two things with their own eyes:

1. **The polygons sit on the holds.** Not near them, on them.
2. **The fiducial residual lines are short.** A long line is a fiducial that was mismeasured,
   placed on a volume, or matched to the wrong wall coordinate, and it is visible in one second on
   the overlay and invisible in a table of numbers.

That is why it is rendered. `AGENTS.md` Section 9 step 9: if the stage produces visual output,
render a deterministic overlay and **look at it**. A reprojection error of 8 mm and a polygon
sitting two holds to the left are the same number.

---

## 13. Traps

| # | Trap | Consequence if you get it wrong |
| --- | --- | --- |
| 1 | **Auto-rotation on decode.** ffmpeg applies the container rotation by default and drops the side data. | The extracted image silently disagrees with `stabilized_px`, so every hold polygon is transposed relative to every future pose observation. Assert the extracted dimensions equal the C4-transformed coded dimensions. |
| 2 | **`-ignore_editlist 0` is needed on the extraction call, not only on the probe.** | An mp4 edit list shifts every PTS the demuxer reports. Stage 1 measured **1024 ticks** on this repository's own CFR fixture. Probe with the flag and extract without it and you get a different frame than the one the frame index names, with no error anywhere. |
| 3 | **Approximate seeking.** `-ss` before the input lands on the nearest preceding keyframe. | You calibrate against a frame that is not the frame you recorded, and every subsequent number is about a slightly different image. There is no way to detect this after the fact. |
| 4 | **Near-collinear fiducials.** | The 8-by-8 system **solves fine** and the four fitting points reproject **perfectly**. Two metres away the mapping is catastrophically wrong, because a near-degenerate configuration constrains the plane only along one direction. This is why the minimum triangle area is a threshold and not an afterthought, and why the score is computed over all fiducials rather than over the subset. |
| 5 | **Extrapolation beyond the fiducial hull.** | Projective error grows **without bound** outside the hull, and the extrapolated wall-plane polygon looks exactly like a measured one. Null it and flag it. |
| 6 | **Volumes do not lie on the plane.** | Their parallax grows with depth, so a fiducial on a volume biases the whole fit and a hold on a volume has a wall-plane position that is wrong by an amount nobody can bound from one view. Exclude volumes from the diagnostics and flag `on_volume` downstream. |
| 7 | **Quantisation drift.** Reporting diagnostics from the pre-quantisation rational. | The stored matrix and its stored diagnostics describe different things, and nothing downstream can detect it. See Section 8.4. |
| 8 | **Self-intersecting polygons.** CVAT will happily let an annotator draw a bow-tie. | The shoelace area of a self-intersecting polygon is a signed sum that partially cancels, so it returns a plausible smaller number instead of an error. Every IoU, centroid and area computed from it is then quietly wrong. Raise `POLYGON_SELF_INTERSECTING`. |
| 9 | **Algorithmic hold renumbering.** Deriving `hold_id` from position, or from an index into a sorted polygon list. | Correcting one polygon renumbers holds and **invalidates every downstream reference**: every problem definition, every contact annotation targeting a hold, every beta token. Derive `hold_id` from the human-assigned number and nothing else. |
| 10 | **The missing tape measure.** | There is **no physical scale**. Every millimetre-denominated threshold downstream must abstain. This is recoverable only by going back to the wall, so check for it before leaving the gym, not at the keyboard. |
| 11 | **Camera motion assumed rather than measured.** | The envelope forbids pan, zoom and reframing, and this stage cannot verify any of it. A recording with a bumped tripod produces a calibration that is correct for the first frame and wrong for the rest, with no flag anywhere. Record `camera_motion: unknown` honestly and upgrade it at Stage 4. |

---

## 14. Report format and stop condition

Follow Section 0.6 exactly: the gate table, files added and changed, config thresholds introduced,
open decisions deferred with their slugs, what this stage does not prove, and the command
transcript.

Stage-specific additions:

- **Report the overlay as evidence.** State that it was rendered, that it was opened, and what was
  visible: whether the polygons sit on the holds and whether any residual line was conspicuously
  long. This is the one clause where human judgement is the grader, and it must be labelled as
  such (`evaluation.md` Section 3).
- **Report `subsets_evaluated`** and the number of subsets rejected for degeneracy, so a reviewer
  can recompute `C(n,4)` independently.
- **Report the two mask metrics as `not_applicable`** with their reason string, never as blank and
  never as zero.
- **The reviewer re-measures independently**, including recomputing the max reprojection error from
  the stored quantised matrix and the stored fiducials, without running the implementation under
  review.
- **`docs/status.md` is not marked complete** until the owner approves.
- **If a gate clause fails**, report the measured gap with its number, name the failing wall set
  rather than pooling, propose the smallest next experiment (for a reprojection failure that is
  almost always "add or re-place fiducials", not "add an optimiser"), and stop.

Then stop. Do not start Stage 4.

---

## 15. Read-first list

In this order, before writing anything.

| Order | File | Why |
| --- | --- | --- |
| 1 | `AGENTS.md` | Binding operating rules. Sections 2, 3, 5, 6, 9, 10, 11. |
| 2 | `docs/mvp-contract.md` | Sections 1, 2, 4, 5, 7, 9, 10, 11. The envelope, the coordinate spaces, the `WallSet` scoping rule and the restated Stage 3 gate. |
| 3 | `docs/data-schema.md` | Sections 1, 3, 4, 5, 6, 7, 9. Entity table, identity rules, storage formats, and the rotation and edit-list behaviour in Section 9. |
| 4 | `docs/evaluation.md` | Section 1, Stage 3 block, and Sections 3 and 5. |
| 5 | `docs/annotation-guide.md` | Section 6, for the self-agreement rule the IoU clause must honour. |
| 6 | `docs/status.md` | The Stage 1 evidence table shape to imitate. |
| 7 | `docs/agents/briefs/stage-2-annotation-harness.md` | Sections 5 and 8, for the value objects, ontology and geometry primitives this stage consumes. |
| 8 | `configs/ingest/v1.json` | The exact config shape and the exact `selection` wording to imitate. |
| 9 | `src/climbvision/schema/common.py`, `src/climbvision/schema/ontology.py` | The Stage 2 value objects and enums. Do not redefine them. |
| 10 | `src/climbvision/geometry/polygons.py` | Shoelace, point-in-polygon, self-intersection, rasterisation. Do not reimplement them. |
| 11 | `src/climbvision/schema/provenance.py` | `IngestRun`, the model `CalibrationRun` is built from. |
| 12 | `src/climbvision/schema/versions.py`, `src/climbvision/schema/__init__.py` | The two registration seams. |
| 13 | `src/climbvision/schema/recording.py` | `VideoStreamInfo`, especially `coded_width`, `coded_height`, `rotation_degrees` and `rotation_source`, which C4 depends on. |
| 14 | `src/climbvision/media/ffprobe.py` | The subprocess boundary pattern `media/frames.py` must follow. |
| 15 | `src/climbvision/media/normalize.py` | How the frame index is built and sorted, for resolving a timestamp to a `frame_index_position`. |
| 16 | `src/climbvision/ingest.py` | `_refuse_conflicting_manifest`, the model for `CALIBRATION_CONFLICT`, and the reason a new `QualityFlag` member is not an option. |
| 17 | `src/climbvision/quality.py` | The C2 cross-multiplication pattern in `_frame_rate`. |
| 18 | `src/climbvision/timebase.py` | Integer-only conversion and the round-half-away-from-zero rule the quantiser must reuse. |
| 19 | `src/climbvision/cli.py` | Subcommand and exit-code conventions. |
| 20 | `tests/unit/test_scope_guard.py` | The four guards, and the comment above `test_the_stage_one_module_inventory_is_pinned`. |
| 21 | `tests/unit/test_schema.py` | `DOCUMENT_MODELS` and `ALL_MODELS`, and what they enforce. |
| 22 | `tests/fixtures/README.md` | The five video fixtures, especially `rot90_160x120_1s.mp4` and its Display Matrix, and the hand-authored-versus-observed distinction. |
| 23 | `docs/agents/README.md` | The decision index, and the rule that decision records are never pre-stubbed. |
