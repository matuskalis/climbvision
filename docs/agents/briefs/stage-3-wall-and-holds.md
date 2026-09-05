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

On the **first measured envelope** (`mvp-contract.md` Sections 1 and 8) the **wall and gym terms
weaken to a board type**: the board is standardized, so a number measured on one board is
**plausibly informative** about another board of the same type. That is an argument from the
envelope and **not a demonstration** - transfer has not been shown, and showing it requires
measuring on a second board. **The single-climber term does not weaken at all**, and neither does
the single lighting condition or the single camera placement.

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

Turn a **versioned board definition** and a handful of **named grid-position fiducials** into a
**wall set**, **problem versions** and **one planar homography**, with reprojection diagnostics, a
grid round-trip check and an overlay.

**The first measured envelope is a standardized LED training board** (a MoonBoard), not a general
gym wall: a flat plywood panel at a fixed overhang, holds bolted at fixed positions on a grid the
**board definition declares** - **11 columns by 18 rows** `[FIXED]` for the board type measured
here, as `grid_columns` and `grid_rows` in `configs/board/<board_id>/v1.json` (Section 8.1) - an
identical hold set and layout on every board of that type worldwide, and LEDs indicating which of
the holds belong to the problem. **The grid is not a contract clause.** The contract still
describes a general wall, has **not** been narrowed, and states no board's geometry; the board is
the envelope in which the MVP is first **measured** (`mvp-contract.md` Section 1, as amended
alongside this brief).

Consumes: the `Recording` and `FrameIndex` for the reference frame's timestamp, the board
definition config, a hand-written fiducial file naming grid positions, and hand-written problem
definitions listing lit holds by grid coordinate.

**Emits no predictions.** No segmentation model, no detector, no inference. Every hold position is
generated from the owner-supplied board definition and projected through a calibration fitted to
fiducials the owner placed by hand. Nothing in any document this stage writes originated from a
model, and every hold record carries the board definition's geometry provenance with it
(Section 5.3).

### What the board removes

Four inputs the previous design was built around are **gone on this envelope, not deferred**:

| Removed | What it was | What replaces it |
| --- | --- | --- |
| Hold polygon tracing | 40 to 80 traced polygons per facet `[PLANNING]`, plus a re-traced subset for a self-agreement measurement | Positions come from the board definition; extent is a configured radius (Section 5.2) |
| Per-hold problem membership | A hand-written list of hold numbers per problem, written against those polygons | Problem identity **is** the set of lit grid coordinates, typed as coordinates (Section 3.2) |
| The separate tape-measured distance | The only source of physical scale | The board definition carries the spacing, with its provenance (Section 8.1) |
| The on-volume flag and the volume-parallax trap | A volume protrudes, so it violates planarity by an amount that varies with the camera | The panel is a flat sheet. There are no volumes on it. |

What remains is smaller and easier: one planar homography, its reprojection diagnostics, and an
overlay.

### What the board adds

Because every hold position is known before the camera is switched on, the system can project every
grid position into the image and back and assert that it round-trips to the **same grid
coordinate**. That is a cheap, deterministic, parameter-free correctness check that a general wall
could never offer, because on a general wall nobody knows where the holds are supposed to be. It is
specified in Section 8.7 and it is gate clause D7 (Section 11.1).

## 1.1 The general-wall path, retained

Nothing here deletes the general wall. On a wall whose hold positions are unknown, the hold map
comes from Stage 2 `AnnotationDocument` documents with `kind: polygons`, each polygon carrying a
stable human-assigned hold number and an on-volume flag; the fiducials are arbitrary coplanar wall
features chosen by the owner, whose wall coordinates are tape-measured in millimetres and
hand-written into the fiducial file; physical scale comes from a tape-measured reference distance
instead of from a board definition; holds on volumes are flagged and kept out of the diagnostics,
because their parallax grows with depth by an amount no single view can bound; hold extent is the
traced polygon; and hold-polygon self-agreement IoU is measurable, because two blind tracings of the
same hold exist (`evaluation.md` Section 1). **None of those inputs exists on the board envelope**,
so each is recorded as `not_applicable` with its reason rather than as zero or as a blank
(Section 11.3). The solver, the quantisation rule, the diagnostics, the hull rule and the overlay
are **identical on both paths**; only the source of the fiducials and of the hold extents differs.

## 1.2 The gate, and the one thing to check before starting

Read the Stage 3 row of `mvp-contract.md` Section 9 first. It is being restated for the board
envelope alongside this brief. If its wording and this brief disagree, that is a defect: **report it
and stop.** Do not resolve it silently and do not edit the contract yourself; the authorized
contract edit for this stage is `docs/status.md` only (Section 4.4).

---

## 2. Preconditions

## 2.1 What must be true before this stage opens

| Precondition | Detail |
| --- | --- |
| Stage 1 complete | Deterministic ingest, content-addressed manifests, `climbvision ingest` and `climbvision validate` |
| Stage 2 complete and **approved by the owner** | Commits 2a, 2b and 2c all reviewed and accepted |
| The portrait-orientation fix landed | Stage 2 Task 1, in `src/climbvision/quality.py`. Portrait 1080p footage is no longer flagged as a resolution failure. |
| Footage ingested | The reference frame's recording exists as a `recording.json` plus `frame_index.json` under `artifacts/recordings/<asset_id>/` |
| **A board definition exists** | One config file for the board type being measured, in the shape of Section 8.1, with **every geometry value carrying its source**. The values are the owner's to supply; this brief specifies the file's shape and the provenance requirement, never the numbers. |
| **Fiducials placed and named** | Point shapes on hold centres in the reference image, each named by its grid coordinate (Section 3, input 3) |
| **Problem definitions written** | One short file per problem, listing its lit holds as grid coordinates with roles (Section 3.2) |

**No hold polygon annotation is required and none is expected.** On this envelope the Stage 2
polygon path is not exercised (Section 1.1).

## 2.2 Stage 2 modules this stage depends on

Read them before writing anything; do not reimplement any of them.

| Module | What Stage 3 uses it for |
| --- | --- |
| `src/climbvision/schema/common.py` | `RatioValue`, `Point2D`, `CoordinateSpace`, `TimeInterval` |
| `src/climbvision/schema/ontology.py` | `ProvenanceClass`, `Visibility`, `ONTOLOGY_ID`, `ONTOLOGY_VERSION` |
| `src/climbvision/schema/annotation.py` | `PolygonAnnotation`, the hold-map input on the **general-wall path only** |
| `src/climbvision/schema/metrics.py` | `MetricValue`, `MetricStatus`, `MetricReport` |
| `src/climbvision/geometry/polygons.py` | Exact integer point-in-polygon, for hull membership. Shoelace doubled area, the self-intersection check and rasterisation are used on the general-wall path only. |
| `src/climbvision/evaluation/masks.py` | Mask IoU. **Not exercised on this envelope.** It exists for the general-wall path and for a future segmenter, and its hand-calculated fixtures remain valid either way. |
| `src/climbvision/media/ffmpeg.py` | **The ffmpeg subprocess boundary.** If Stage 2 landed without it, create it here to the same shape as `src/climbvision/media/ffprobe.py`: bare basename, `cwd` set to the file's directory, argv recorded, version recorded, explicit demuxer options, `FFMPEG_NOT_FOUND` when absent. `ffmpeg` is the **second external subprocess boundary** in the codebase after `ffprobe`; `media/frames.py` is its second use site. |
| `src/climbvision/schema/runs.py` | The C5 run-document shape to follow |

## 2.3 What does not exist

No board definition and no `configs/board/` directory. No wall set, no calibration, no homography,
no overlay, no problem definition. No `wall/` package, no `geometry/rotation.py`, no
`schema/board.py`. No `configs/wall/v1.json`. No segmenter, and none is required to reach this
gate.

---

## 3. Human inputs required before the agent starts

**The owner never clicks correspondences in a custom GUI.** No point-picking tool is built, and
none is needed. Every input below is either a note, a CVAT shape or a short hand-written JSON file.
If a step in this section would require the owner to click points in software this repository
ships, the design is wrong and the agent must stop and say so.

On this envelope the whole owner input is **one reference frame, a handful of clicks and two short
files**. That is the point of a known board: the geometry is already published, so almost nothing
has to be described by hand.

| # | Input | Form | Why it is needed |
| --- | --- | --- | --- |
| 1 | **One clean reference frame of the empty board** | The owner notes an approximate time, in seconds, and the asset it belongs to. **The agent converts it to an exact timestamp** by resolving the nearest `FrameIndex` entry and reporting the exact `pts` it chose. | The wall set is defined against one image. "Clean" means nobody is on the board and no person occludes a hold. One calibration then serves **every problem** on that board until the camera moves or the set is replaced. |
| 2 | **The board definition** | One config file for the board type, in the shape of Section 8.1, with **every geometry value carrying its source** | It supplies the grid, the spacing, the physical scale, the origin corner and the angle. Without it there are no hold positions at all. |
| 3 | **Six named grid-position fiducials** `[PILOT]` | CVAT point shapes on hold centres in the reference image, plus a hand-written JSON file giving each point's **grid coordinate** as two integers | These are the correspondences the homography is fitted to. The wall-plane side is no longer measured by hand: it is computed from the grid coordinate and the board definition. |
| 4 | **Problem definitions** | One short JSON file per problem: the lit holds as grid coordinates, each with a role and a foot-only flag (Section 3.2) | Problem identity is user-confirmed by contract (`mvp-contract.md` Sections 1 and 11). The system never merges or infers problems. |

Six is a `[PILOT]` starting point, not a measured minimum. Fewer than six leaves no redundancy to
detect a misnamed fiducial; beyond about twelve `[PILOT]` the exhaustive search gets slower for no
gain. The count lives in config as `min_fiducial_count` (Section 8.10) and the layout is the
`fiducial-layout-policy` decision.

## 3.1 Fiducial placement guidance, for input 3

Give this to the owner verbatim before they place the points.

| Rule | Reason |
| --- | --- |
| Click the point that **is** the grid position, not the visual centre of the hold | A grid position is a mounting point on the panel. An asymmetric hold's visual centre can sit most of a hold's width away from it, and that offset is the same size as the errors this stage exists to measure. The board definition declares which physical point a grid position denotes (`grid_position_reference`, Section 5.3). Click that point on every fiducial, or the fit inherits a systematic bias nobody can see afterwards. |
| **Four corner positions plus two interior ones** is the recommended set | The corner positions bound the panel, so every other grid position falls inside the fiducial hull and nothing is extrapolated. The two interior points are the redundancy that turns a misnamed corner into a visible residual instead of a perfect-looking fit. |
| Include positions at both the **top and the bottom** of the panel | The camera looks steeply up at an overhanging board, so the top of the panel is compressed into far fewer pixels per grid pitch than the bottom (trap 2). Fiducials only along the bottom constrain the fit only where it was already easy. |
| **No three near-collinear** | See trap 5 in Section 13. Six positions taken from one row or one column are a collinear set: they solve cleanly and reproject catastrophically. Four corners plus two interior positions satisfies this by construction. |
| **Name the grid coordinate, and get the origin corner right** | A consistently mirrored or transposed naming fits with **zero reprojection error** and puts every hold in the wrong place. No number this stage computes can catch it. See trap 1, and Section 8.9. |

The layout policy is the `fiducial-layout-policy` decision; this table is the recommendation the
decision either adopts or overrides.

## 3.2 Problem definitions, for input 4

A problem on this board **is** its set of lit holds. The owner types them:

| Field | Form |
| --- | --- |
| `problem_slug` | An owner-chosen slug matching `^[a-z0-9][a-z0-9_-]{0,31}$` |
| `holds` | The lit holds, each a grid coordinate plus a role of `start`, `intermediate` or `finish`, plus a foot-only flag |
| `grade_note` | Optional. **A note, never a prediction** (Section 5.3). |

That is roughly **eight to fifteen coordinates per problem** `[PLANNING]`, and it takes well under a
minute of typing.

**There is no official public data source for these problems.** No published dataset and no
supported public API exists. Community-maintained wrappers exist and are partly broken, and reading
the commercial application's own database is a **terms-of-service question rather than a technical
one**. This brief does not authorize it, and the agent must not attempt it. Manual entry is
therefore the MVP path; an import adapter is a later addition behind the
`lit-hold-entry-and-import` decision, which must settle the licensing question **before** any code
reads a third-party source.

The entry format is validated rather than trusted: a coordinate outside the grid raises
`PROBLEM_HOLD_OUT_OF_GRID`; a coordinate the board definition does not list as occupied raises
`PROBLEM_HOLD_UNKNOWN`; a problem with no `start` hold raises `PROBLEM_WITHOUT_START`; a problem
with no `finish` hold raises `PROBLEM_WITHOUT_FINISH`; and a coordinate listed twice raises
`PROBLEM_HOLD_DUPLICATE`.

---

## 4. Deliverables

## 4.1 New modules

All under `src/climbvision/`, all added to a new `STAGE_THREE_MODULES` set kept **separate** from
`STAGE_ONE_MODULES` and `STAGE_TWO_MODULES`.

| Module | Responsibility, one line |
| --- | --- |
| `media/frames.py` | Extract exactly one frame at an exact timestamp, through the ffmpeg subprocess boundary |
| `geometry/rotation.py` | The exact integer map of C4 between `source_px` and `stabilized_px` |
| `geometry/homography.py` | Deterministic exhaustive minimal-sample search, the exact-rational solver, and the exact rational inverse |
| `geometry/diagnostics.py` | Reprojection errors, mean squared error, convex hull, hull coverage, the grid round trip |
| `wall/__init__.py` | Package marker, empty |
| `wall/board.py` | Loads and validates the board definition, generates the grid positions and their exact wall-plane centres, and applies the hold extent model |
| `wall/build.py` | Assembles a `WallSet` and its `HoldInstance` list from the board definition plus a calibration |
| `wall/problems.py` | Validates lit-hold grid coordinates and emits `ProblemVersion` and `ProblemHold` documents |
| `wall/overlay.py` | Pure-Python deterministic SVG overlay |
| `schema/board.py` | `BoardDefinition`, `GridPosition`, `BoardGeometrySource` |
| `schema/wall.py` | `Gym`, `Wall`, `WallFacet`, `WallSet`, `HoldInstance`, `HoldExtentModel`, `ProblemVersion`, `ProblemHold`, `ProblemHoldRole` |
| `schema/calibration.py` | `Calibration`, `Homography`, `FiducialCorrespondence`, and `CalibrationRun` |

`CalibrationRun` lives in `schema/calibration.py`, not in Stage 2's `schema/runs.py`. Stage 3's
models stay in Stage 3's files so the per-stage module sets remain an accurate decision record of
which stage introduced what.

## 4.2 New configuration

| File | Contents |
| --- | --- |
| `configs/wall/v1.json` | The stage's thresholds, in the C9 shape. Names, units and status tags are in Section 8.10. |
| `configs/board/<board_id>/v1.json` | **One file per board type**, in the C9 shape, holding **declarations rather than thresholds**: the grid, the spacing, the origin corner, the angle and the geometry provenance. Its shape is Section 8.1; its field list is Section 5.3. A second board type is a second directory, never an edit to the first. |

A board definition entry keeps all four C9 keys and adds one, `source`, a closed enum naming where
the value came from. The reason C9 requires `selection` is the reason this file needs both: a number
whose origin is not written down is a number nobody can check. An empty `selection` or a missing
`source` is a hard failure, not a default (Section 8.1).

## 4.3 New CLI subcommands

| Command | Does |
| --- | --- |
| `climbvision reference-frame` | Extracts one frame at an exact timestamp and reports the `pts` and `frame_index_position` it used |
| `climbvision calibrate` | Fits the homography from the fiducial file and the board definition, runs the grid round trip, emits `Calibration` plus `CalibrationRun` |
| `climbvision wall-build` | Emits the `WallSet` and its `HoldInstance` list from the board definition plus the calibration |
| `climbvision problems` | Validates lit-hold grid coordinates and emits `ProblemVersion` and `ProblemHold` documents |
| `climbvision overlay` | Renders the deterministic SVG diagnostic |

Exit codes follow `src/climbvision/cli.py`: **0** ok, **1** operation failed, **2** usage.

## 4.4 Existing files changed

The Section 0.3 seam checklist, instantiated. Nothing else.

| File | Change |
| --- | --- |
| `src/climbvision/schema/versions.py` | Schema id and version constants for `WallSet`, `HoldInstance`, `ProblemVersion`, `Calibration`, `CalibrationRun`; extend `SCHEMA_IDS`. **`BoardDefinition` gets none**: it is a nested model, not a document (Section 5.3). |
| `src/climbvision/schema/__init__.py` | `MODEL_REGISTRY` entries and `__all__` |
| `src/climbvision/schema/ontology.py` | Register `ProblemHoldRole` in the ontology and **bump `ONTOLOGY_VERSION` from 1 to 2** |
| `src/climbvision/cli.py` | Five new subcommands |
| `tests/unit/test_schema.py` | New `DOCUMENT_MODELS` rows; every new nested model into `ALL_MODELS`, `BoardDefinition` and `GridPosition` included |
| `tests/unit/test_scope_guard.py` | `STAGE_THREE_MODULES`; the union inventory test; the parsed dependency test still asserting exactly `pydantic` |
| `tests/unit/test_cli.py` | Exit-code tests, and the `validate`-through-`MODEL_REGISTRY` test for the new documents |
| `tests/fixtures/README.md` | Document the new hand-authored board and wall fixtures, **including that the fixture board geometry is invented for testing and measures nothing** (Section 10.4) |
| `scripts/regenerate_fixtures.sh` | Extend only if a fixture is generated rather than hand-authored; keep the banner |
| `.gitignore` | Add nothing new unless a new output root appears; the Section 0.4 table already covers `artifacts/` |
| `docs/status.md` | The Stage 3 row and the measured-evidence table |
| `docs/adr/` | One file per decision actually made |

**Authorized contract edits: `docs/status.md` only.** The contract amendment that introduces the
board envelope is being made alongside this brief, not by the implementing agent: `mvp-contract.md`
Section 1 and Section 9, `data-schema.md` Section 1 (which gains `BoardDefinition` at Stage 3) and
`evaluation.md` Section 1 are edited there. Two things to check rather than fix:

- If `mvp-contract.md` Section 9's Stage 3 row and Section 11 of this brief disagree, **stop and
  ask** (Section 1.2).
- `mvp-contract.md` Section 10 maps the hold map to `preannotation -> reviewed_annotation`. On this
  envelope no preannotation and no tracing happens: hold records are `derived` from an
  owner-supplied definition (Section 5.3). If the amended Section 10 does not cover that, **stop and
  ask**; do not pick a provenance class to make a test pass.

### The ontology version bump, and why it is safe

Adding `ProblemHoldRole` changes the ontology, so `ONTOLOGY_VERSION` goes from 1 to 2. This is
safe **only because `ontology_version` is a plain `int` field on every document and never a
`Literal`.** Stage 2 documents keep version 1 and stay valid; nothing is upgraded in place, and
nothing is silently coerced (`data-schema.md` Section 4). Verify this before bumping: if any Stage
2 model pinned `ontology_version` as a `Literal`, fix that first, in its own commit, and say so.

---

## 5. Entities

The eight wall entities are **on schedule at Stage 3** per `docs/data-schema.md` Section 1: `Gym`,
`Wall`, `WallFacet`, `WallSet`, `HoldInstance`, `ProblemVersion`, `ProblemHold`, `Calibration`.
None is early and none is late.

**`BoardDefinition` is a ninth**, added to `docs/data-schema.md` Section 1 as a documented entity
introduced at Stage 3 by the amendment that accompanies this brief. Read that row before writing
the model; if it is not there, **stop and ask** rather than inventing an entity the schema document
does not know about.

Model and field names below are **proposals** except the nine entity names, which are fixed by
`data-schema.md`.

## 5.1 Identity, which encodes the contract

| Id | Derivation | Why this form |
| --- | --- | --- |
| `gym_id`, `wall_id`, `facet_id`, `revision_label` | Owner-supplied slugs, each matching `^[a-z0-9][a-z0-9_-]{0,31}$` | Human-readable, pattern-checkable, no personal data |
| `wall_set_id` | `f"{gym_id}.{wall_id}.{facet_id}.{revision_label}"` | A reset produces a new `revision_label`, therefore a new `wall_set_id`. On a standardized board a "reset" is the installation of a different set version, which is a different `board_version`, which is a different `revision_label`. |
| `hold_id`, board envelope | `f"{wall_set_id}.c{column:02d}r{row:02d}"` | The grid coordinate **is** the identity. It is assigned by the board's manufacturer rather than by an annotator, it cannot drift when anything is corrected, and it sorts in grid order. Trap 8 (algorithmic renumbering) is structurally impossible here. |
| `hold_id`, general-wall path | `f"{wall_set_id}.h{hold_number}"` | Unchanged: **stable across a polygon correction**, because the polygon is not in the derivation. Correcting a traced outline must not renumber anything. |
| `problem_version_id` | `f"{wall_set_id}.p{problem_slug}"` | **Problem identity is scoped to the `WallSet` revision by construction** (`mvp-contract.md` Section 5, standing rule 2). The id literally cannot be reused across a reset, so the rule holds structurally rather than by discipline. |

On the board envelope the hold list is generated from the board definition's occupied positions, so
a duplicate is impossible by construction. On the general-wall path a duplicate `hold_number` within
a wall set remains a hard failure, `HOLD_NUMBER_DUPLICATE`: two holds with the same number would
collide on `hold_id`, and the collision would be silent.

## 5.2 Hold extent, the `hold-extent-model` decision

Contact detection needs to know not only **where** a hold is but **how big** it is. Two options,
both real:

| Option | Annotation cost | What it gets wrong | Reuse |
| --- | --- | --- | --- |
| **A: a circle of a configured radius around the grid centre** (**recommended for the MVP**) | **Zero.** Nothing is traced, ever. | Every hold becomes one disc. A long pinch, a large jug and a small crimp are all discs of the same radius, so the extent is wrong by roughly the spread of the hold set. | The radius is a single `[PILOT]` threshold in wall units (Section 8.10), identical on every board of the type |
| B: trace the standardized hold shapes once | 40 to 80 polygons `[PLANNING]`, **once ever** | Nothing structural; it is the real outline, up to tracing stability | Because the hold set and layout are identical worldwide, the tracing is done **once for the board type** and reused on every board of that type forever, not once per board and not once per gym |

**Recommend A for the MVP; record B as the documented upgrade path**, not as a rejected option: its
cost is paid once globally rather than per wall, which is exactly the property that makes it worth
doing later. The choice is the `hold-extent-model` decision, and `HoldExtentModel` is recorded on
every `WallSet` and every `HoldInstance`, so no consumer ever has to guess which one produced a
record. The decision must be recorded **before Stage 5 opens**, because contact detection consumes
the extent; it does not block Stage 3 closing.

## 5.3 Field lists

### `schema/board.py`

| Model | Fields |
| --- | --- |
| `GridPosition` | `column: int`; `row: int`. Zero-based, counted from `origin_corner`. Nested, not a document. |
| `BoardGeometrySource` | Enum: `manufacturer_specification`, `owner_measurement`, `fixture` |
| `GeometryProvenanceEntry` | `field: str` (the declaration it describes); `source: BoardGeometrySource`; `reference: str` (the config entry's `selection` text verbatim: the publication and its date, or the instrument and the date it was used); `recorded_at_utc: str` |
| `BoardDefinition` | `board_id: str` (slug); `board_version: str`; `grid_columns: int`; `grid_rows: int`; `origin_corner: Literal["bottom_left","bottom_right","top_left","top_right"]`; `column_spacing_mm: RatioValue`; `row_spacing_mm: RatioValue`; `grid_position_reference: str`; `overhang_degrees_from_vertical: int`; `occupied_positions: list[GridPosition]`; `geometry_provenance: list[GeometryProvenanceEntry]`. Nested, **not a document**. |

**`BoardDefinition` is nested in the `WallSet` in full**, not referenced by id. Three reasons: a
reader of one `WallSet` then has the grid, the spacing, the angle and the provenance without a
second file; the geometry that produced every hold ships with the holds, so a later edit to the
config cannot silently redescribe an existing wall set; and it needs no new schema id, no
`MODEL_REGISTRY` entry and no golden document of its own. It is added to `ALL_MODELS` so the
no-float, `extra="forbid"` and `frozen=True` guards apply to it like everything else.

A model validator asserts there is **exactly one `GeometryProvenanceEntry` per declared geometry
field** and that no `reference` is empty. That is what makes gate clause D6 checkable rather than
aspirational. Per-field provenance is deliberate: the spacing may come from a published
specification while the angle came off the owner's inclinometer, and a single file-level source
string would flatten that into one claim that is half true.

`occupied_positions` lists **every position that carries a mounted hold, explicitly**. Nothing is
inferred from `grid_columns * grid_rows`, because whether every grid position on the board being
measured carries a hold is a property of that board, not of arithmetic. Do not assume full
occupancy; the list is part of `board-geometry-source` and the owner supplies it.

`overhang_degrees_from_vertical` is an **integer** (`AGENTS.md` Section 3: angles are integer
degrees). Stage 3 **records it and does not consume it**: a planar homography does not need the
angle. It is declared because two boards at different angles are different measurement envelopes,
and because the inclination is what makes the Stage 4 and Stage 5 traps what they are (traps 2 and
3). It is not a route into 3D: wall-plane coordinates are not physical 3D body coordinates (truth
rule 8).

### `schema/wall.py`

| Model | Fields |
| --- | --- |
| `Gym` | `gym_id: str`; `display_name: str`. Nested, not a document. |
| `Wall` | `wall_id: str`; `gym_id: str`; `display_name: str` |
| `WallFacet` | `facet_id: str`; `wall_id: str`; `display_name: str` |
| `HoldExtentModel` | Enum: `circle_radius`, `polygon` |
| `WallSet` (document) | `schema_id`; `schema_version`; `wall_set_id: str`; `created_at_utc: str`; `ontology_version: int`; `gym: Gym`; `wall: Wall`; `facet: WallFacet`; `revision_label: str`; `board: BoardDefinition \| None` (null on the general-wall path); `board_definition_sha256: str \| None`; `hold_extent_model: HoldExtentModel`; `reference_image_sha256: str`; `reference_asset_id: str`; `reference_pts: int`; `reference_frame_index_position: int`; `reference_time_base: Timebase`; `image_width_px: int`; `image_height_px: int`; `coordinate_space: CoordinateSpace` (always `stabilized_px`); `hold_count: int`; `provenance_class: ProvenanceClass` |
| `HoldInstance` (document) | `schema_id`; `schema_version`; `hold_id: str`; `wall_set_id: str`; `grid_position: GridPosition \| None`; `hold_number: int \| None`; `centre_wall_plane: Point2D`; `centre_stabilized_px: Point2D \| None`; `extent_model: HoldExtentModel`; `radius_milli_wall_units: int \| None`; `polygon_stabilized_px: list[Point2D] \| None`; `polygon_wall_plane: list[Point2D] \| None`; `outside_fiducial_hull: bool`; `outside_image_bounds: bool`; `provenance_class: ProvenanceClass` |
| `ProblemHoldRole` | Enum: `start`, `intermediate`, `finish` |
| `ProblemHold` | `hold_id: str`; `grid_position: GridPosition \| None`; `hold_number: int \| None`; `role: ProblemHoldRole`; `foot_only: bool` |
| `ProblemVersion` (document) | `schema_id`; `schema_version`; `problem_version_id: str`; `wall_set_id: str`; `created_at_utc: str`; `ontology_version: int`; `problem_slug: str`; `grade_note: str \| None`; `holds: list[ProblemHold]`; `provenance_class: ProvenanceClass` |

`grid_position` and `hold_number` are **both nullable and exactly one of them is set**: the grid
coordinate on the board envelope, the human-assigned number on the general-wall path. A model
validator enforces the exclusivity, so a record can never be silently identified two ways.

Under `extent_model: circle_radius` the two polygon fields are **null** and
`radius_milli_wall_units` carries the configured radius. Under `extent_model: polygon` the reverse
holds. Null, not an empty list: an empty list says "there are zero vertices", null says "we looked
and there was nothing" (C7).

On this envelope the known quantity is the **wall-plane** centre and the computed one is the
**image** centre, which is the reverse of the general-wall path. So it is `centre_stabilized_px`
that is **null** when the position falls outside the fiducial hull, with `outside_fiducial_hull:
true` beside it: out there the image position is unconstrained by any measurement and would look
exactly like a measured one (Section 8.6). `outside_image_bounds` is true when the projected centre
falls outside the raster; the envelope requires the full problem to be visible (`mvp-contract.md`
Section 1), so a non-zero count is a **framing violation, not a calibration failure**, and the
report must name it as one.

**Provenance on this envelope is `derived`, not `reviewed_annotation`.** A hold record here is
arithmetic over a human-authored board definition and a human-placed set of fiducials; nobody
looked at that specific hold outline, and claiming `reviewed_annotation` would say they did (truth
rule 5). The human confirmation is recorded once, where a human actually made it: the board
definition is nested in the `WallSet` with its per-field provenance, and its sha256 is recorded
beside it. On the general-wall path, where a person traced each polygon, `reviewed_annotation`
remains correct. See Section 4.4 for the one contract row to check before writing this.

`grade_note` is **explicitly a note and never a prediction.** Route grade prediction is out of
scope permanently (`mvp-contract.md` Section 2: grade is a community judgement, not an
observable). The field carries what the problem's published tag said, as a string, and no code may
consume it as a number, rank or feature.

### `schema/calibration.py`

| Model | Fields |
| --- | --- |
| `Homography` | `elements: list[int]` (exactly 9, row-major); `denominator: int`; `normalization: Literal["h33_equals_one"]`; `source_space: CoordinateSpace` (`stabilized_px`); `target_space: CoordinateSpace` (`wall_plane`) |
| `FiducialCorrespondence` | `fiducial_id: str`; `image_point: Point2D` (`stabilized_px`); `wall_point: Point2D` (`wall_plane`); `grid_position: GridPosition \| None` (null on the general-wall path) |
| `Calibration` (document) | `schema_id`; `schema_version`; `calibration_id: str`; `wall_set_id: str`; `created_at_utc: str`; `ontology_version: int`; `board_definition_sha256: str \| None`; `homography: Homography`; `fiducials: list[FiducialCorrespondence]`; `inlier_fiducial_ids: list[str]`; `max_reprojection_error_milli_wall_units: int`; `rms_reprojection_error_milli_wall_units: int`; `mean_squared_error: RatioValue`; `hull_coverage: RatioValue`; `millimetres_per_wall_unit: RatioValue \| None`; `scale_check_residual_milli_wall_units: int \| None`; `grid_positions_checked: int`; `grid_round_trip_failures: list[GridPosition]`; `max_grid_round_trip_error_milli_wall_units: int \| None`; `min_grid_pitch_milli_wall_units: int \| None`; `positions_outside_image_bounds: int`; `solver_id: str`; `subsets_evaluated: int`; `provenance_class: ProvenanceClass` |
| `CalibrationRun` (document) | The C5 fields: `run_id`; `created_at_utc`; `inputs` and `outputs` as basename/sha256/schema_id triples; `config_version`; `config_sha256`; `ontology_version`; `climbvision_version`; `python_version`; `git_commit`; `git_dirty`; `external_tools`. Plus `camera_motion: Literal["unknown"]` and `camera_motion_reason: str`. |

`FiducialCorrespondence` records **both** the grid position and the wall point it produced, so the
derivation from the board definition is auditable rather than trusted.

`board_definition_sha256` is recorded on the `Calibration` and on the `WallSet`, and `wall-build`
**refuses to combine a calibration and a board definition whose hashes disagree**
(`BOARD_DEFINITION_MISMATCH`). A calibration fitted against one spacing and holds generated from
another is wrong everywhere and looks fine, which is exactly the class of failure this repository
already hashes its way out of.

`millimetres_per_wall_unit` is **never null on the board envelope**: the board definition supplies
the scale. It is null only on the general-wall path when no tape measure was supplied, and every
downstream millimetre-denominated threshold must then abstain rather than assume a scale.
`scale_check_residual_milli_wall_units` is null here, because there is no separate tape-measured
distance to check against.

The four grid fields are null or zero on the general-wall path, where there is no grid to round-trip
through. `grid_round_trip_failures` is **empty on a pass**, and it is a list rather than a count
because a reviewer needs to know *which* positions failed: failures concentrated in the top rows are
foreshortening (trap 2), failures scattered anywhere are a bad fit.

`subsets_evaluated` is recorded because it makes the search auditable: with `n` fiducials it must
equal `C(n,4)` minus the subsets rejected for degeneracy, and a reviewer can recompute it.

---

## 6. Decisions already frozen

| Frozen decision | Where |
| --- | --- |
| One approximately planar wall facet; single static camera; no pan, zoom or reframing | `mvp-contract.md` Section 1 |
| **The MVP is measured on a standardized LED training board**, which is one such facet. The contract stays general; the board is the first measured envelope, not a narrowing. | `mvp-contract.md` Section 1, as amended alongside this brief |
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
| Hold-polygon self-agreement IoU measures one annotator's tracing stability and is **never** reported as inter-annotator agreement. It is defined for the **general-wall path**; on the board envelope no polygon is traced, so it is `not_applicable` (Section 11.3). | `evaluation.md` Section 1; `annotation-guide.md` Section 6 |
| Conventions C1 through C10 | Section 0.2 of this brief |

---

## 7. Open decisions

| Slug | Blocks | What the owner must decide |
| --- | --- | --- |
| `board-geometry-source` | The board definition, therefore everything | Where each declared geometry value comes from: the manufacturer's published specification, **cited by publication and date**, or the owner's own measurement, **cited by instrument and date**. Also the origin corner, what physical point a grid position denotes, and which positions carry a mounted hold. **The agent invents none of these numbers.** This brief fixes the shape of the file and the requirement that every value carries its source; the values are the owner's. |
| `hold-extent-model` | Stage 5, not Stage 3 | A configured radius around each grid centre, or a one-time tracing of the standardized hold shapes. See the option table in Section 5.2. **Recommended for the MVP: the circle**, with the polygon recorded as the documented upgrade path. |
| `lit-hold-entry-and-import` | Nothing at Stage 3 | Whether an import adapter for problem definitions is ever built, and from what source. Manual entry is the MVP path (Section 3.2). No official public data source exists, and the licensing question is settled **before** any code reads a third-party source, not after. |
| `wall-plane-units-and-scale` | The calibration | What one wall unit **is**. See the option table in Section 8.1. **Recommended: one wall unit equals one millimetre**, which makes `millimetres_per_wall_unit` exactly `1/1` and milli-wall-units micrometres. On the board envelope the physical scale comes from the board definition's spacing rather than from a tape measure, so the recommendation is unchanged and only its source moved. |
| `fiducial-layout-policy` | The fiducial placement | How many fiducials and which grid positions they are. Section 3.1 is the recommendation this decision adopts or overrides. On the board envelope the "is it on a volume" question disappears; the question that replaces it is how far up the panel the fiducials must reach before the top of the board is actually constrained. |
| `hold-segmentation-model` | Nothing at Stage 3 | Whether a segmenter is ever adopted as **assistive preannotation only**, behind a license decision (`model-registry.md` Section 4). Until it is, mask IoU and mask AP are recorded as `not_applicable` with the reason, and **no hold position, extent or polygon in any Stage 3 document may originate from a model.** |

The agent decides none of these. Where one is needed and absent, stop and ask.

---

## 8. Approach

## 8.1 The board definition, the grid and the scale

### The file

`configs/board/<board_id>/v1.json`, one file per board type, in the C9 shape: a `config_version`
plus one entry per declared value carrying `{value, unit, status, selection, source}`. The first
four keys are C9's, unchanged, so the existing guard that every entry has a non-empty `selection`
and a valid `status` covers this file for free. `selection` carries the provenance in words: the
publication and its date, or the instrument and the date it was used. `source` is the one added key
and carries the same fact as a closed enum, so code can act on it. An entry with an empty
`selection`, or with no `source`, is a hard failure, `BOARD_GEOMETRY_SOURCE_MISSING`, never a
default.

| Declaration | Unit | Notes |
| --- | --- | --- |
| `board_id`, `board_version` | identifier | Names, not thresholds, therefore untagged |
| `grid_columns`, `grid_rows` | `count` | `[FIXED]` for a board type. A different grid is a different board type and therefore a different file. |
| `column_spacing_mm`, `row_spacing_mm` | `millimetres`, as `{num, den}` (C1) | `[FIXED]` per board type. Two values, not one: **do not assume the pitch is equal along both axes.** |
| `origin_corner` | declaration | Which physical corner is grid `(0, 0)`. Column and row indices increase away from it. |
| `grid_position_reference` | declaration | What physical point on the board a grid position denotes, in words. The fiducial clicks must land on that point (Section 3.1). |
| `overhang_degrees_from_vertical` | `degrees` | `[FIXED]` per board. Recorded, not consumed (Section 5.3). |
| `occupied_positions` | declaration | Every position carrying a mounted hold, listed explicitly. Never inferred from `grid_columns * grid_rows`. |

**Do not invent a single one of these numbers.** Not the spacing, not the panel size, not the hold
count per set. That the grid is 11 columns by 18 rows `[FIXED]` is a **declaration in this file**
(`grid_columns` and `grid_rows` above), a structural property of the board type rather than a
contract clause, and may be stated; every physical dimension is the owner's to supply through
`board-geometry-source`, carrying either the manufacturer's published specification cited by
publication and date, or the owner's own tape measure cited by instrument and date. Whichever was
used is recorded in the file, per value. An agent that fills one in from memory has fabricated the
measurement envelope, and every number the stage reports afterwards is about a board that does not
exist.

### From grid coordinate to wall-plane point

For position `(c, r)` the wall-plane centre is `(c * column_spacing, r * row_spacing)` in the units
`wall-plane-units-and-scale` fixes, computed as exact `Fraction`s and **quantised once**, at the
schema boundary, by the round-half-away-from-zero rule of `src/climbvision/timebase.py`. Every
downstream computation, the round trip included, uses the **quantised** centres. That is the same
discipline Section 8.5 imposes on the homography, for the same reason: the artifact that ships must
describe itself.

### The scale, `wall-plane-units-and-scale`

| Option | `millimetres_per_wall_unit` | Consequence |
| --- | --- | --- |
| **A: one wall unit is one millimetre** (**recommended**) | Exactly `1/1` | The board definition's spacing is already in millimetres, so the only quantisation is the one above. Milli-wall-units are **micrometres**, so a max reprojection error of `10_000` reads as 10 mm. |
| B: one wall unit is one grid pitch | The spacing, as a `RatioValue` | Tempting, because grid centres become exact integers with no quantisation at all. **Rejected unless the two spacings are equal:** with different column and row pitches the plane is anisotropic, a "distance in wall units" is then not a physical distance in any direction, and every reported reprojection error becomes uninterpretable. |
| C: one wall unit is a tape-measured reference distance | A quantised `RatioValue` | The general-wall fallback. The distance between two measured points is generally irrational, so the scale is an approximation whose rounding error multiplies into every reported number. |
| D: no scale supplied | `null` | **Cannot arise on this envelope**, because the board definition always carries the spacing. It remains legal on the general-wall path, where every millimetre-denominated downstream threshold then **abstains**, per truth rule 6. |

`scale_check_residual_milli_wall_units` is **null here.** It existed to check the owner's tape work
against their own coordinates, and there is no tape measurement on this path to check. Where the
geometry provenance is `owner_measurement`, what checks it is the reprojection residual at the
fiducials and the grid round trip, and both are reported.

## 8.2 Reference frame extraction

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

## 8.3 The rotation map, C4

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

## 8.4 The homography: a deterministic exhaustive minimal-sample search, not RANSAC

**This design is unchanged by the board.** Only the source of the fiducials moved, from features the
owner chose and tape-measured to grid positions the owner named. The solver, the degeneracy
rejection, the exact arithmetic, the scoring rule and the tie-break stay exactly as written here.

**Why not RANSAC.** With six to twelve fiducials there are at most a few hundred four-subsets:
`C(6,4) = 15`, `C(12,4) = 495`. Enumeration is therefore **exhaustive, ordered and fully
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
depend on an iteration count, and would paper over a fiducial that was clicked off its grid
position or named with the wrong coordinate, which is information the owner needs.

## 8.5 Quantisation, and the single most likely correctness defect in this stage

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

## 8.6 Diagnostics

| Diagnostic | Computation |
| --- | --- |
| Max reprojection error | `math.isqrt(num // den)` of the largest squared residual expressed as a `Fraction`. Documented as an **integer floor** in milli-wall-units. The identity `floor(sqrt(x)) == isqrt(floor(x))` for real `x >= 0` makes this exact rather than an approximation. |
| Mean squared error | An exact `RatioValue`, stored in full. Nothing is lost to the floor. |
| RMS reprojection error | `math.isqrt(mse_num // mse_den)`, documented as an **integer floor** in milli-wall-units |
| Inlier fiducial ids | Those whose reprojection error is at or below `max_reprojection_error_milli_wall_units`, compared by C2 |
| Hull coverage | `RatioValue(holds_whose_projected_centre_is_inside_the_hull, total_holds)`. The convex hull of the fiducial **image** points, by monotone chain with exact integer cross products. A point exactly on the hull boundary counts as inside; declare and test it. |

**Max, RMS and MSE are computed over all supplied fiducials, not over the inliers only.** Reporting
the max over inliers, where an inlier is defined by being under the max threshold, makes the
threshold self-satisfying: the number would pass by construction and the displaced fiducial would
vanish from the report. The inlier list is reported **beside** the all-fiducial numbers, so a
reviewer sees both.

**Report every fiducial's residual individually, beside its grid coordinate.** A pooled max and RMS
are not enough on an overhanging board: the camera looks steeply up, the top of the panel is
compressed into far fewer pixels per grid pitch than the bottom, and **the residual should be
expected to grow with height** (trap 2). A single pooled number hides that gradient completely,
whereas six residuals tagged with their rows show it at a glance. This is a **reporting
requirement, not a threshold**: no number here says how large the gradient may be, because nobody
has measured one.

**Every hold whose projected centre falls outside the fiducial hull gets `centre_stabilized_px:
null` and `outside_fiducial_hull: true`, and is counted in the report.** Projective error grows
without bound outside the hull: the mapping is still defined, it is simply unconstrained by any
measurement, and an image position computed out there would look exactly like a measured one. With
the recommended layout of four corner positions this set is **empty by construction**, because a
homography maps the interior of the corner quadrilateral to the interior of its image, so a
non-empty set means the corners were not used or a fiducial was misnamed. That makes hull coverage
a signal on this envelope rather than a routine ratio.

## 8.7 The grid round trip, which only a known board makes possible

Every grid position is known, so the calibration can be asked a question a general wall cannot
answer: **does the mapping still resolve individual holds?**

For each of the `grid_columns * grid_rows` positions:

1. Take its exact wall-plane centre from the board definition, **quantised** (Section 8.1).
2. Map it into `stabilized_px` through the **exact rational inverse of the stored quantised
   homography**. The inverse is the integer adjugate over the determinant, all in `Fraction`: no
   float, no new dependency. A determinant of exactly zero raises `HOMOGRAPHY_NOT_INVERTIBLE`.
3. **Quantise that image point to integer milli-pixels** (C3). This step is the whole point: it is
   the same quantisation every stored image coordinate undergoes, so the round trip measures what a
   consumer of the artifact would actually experience.
4. Map the quantised image point back through the stored quantised homography.
5. Assert the **nearest grid position** to the result is the position you started from.

All positions must pass. A failure raises `GRID_ROUND_TRIP_FAILED` naming the offending positions,
and the failing positions are stored on the `Calibration` rather than only logged.

| Property | Why it matters |
| --- | --- |
| **Parameter-free** | "Nearest grid position" needs no threshold, so the clause is deterministic and cannot be made to pass by choosing a `[PILOT]` placeholder (Section 8.10) |
| **Cheap** | A few hundred exact rational multiplications, once per calibration |
| **It measures resolution, not just consistency** | A failure means two neighbouring holds are no longer distinguishable at the achieved precision, which is a real statement about whether the calibration can support contact detection at all |
| **It is not a substitute for the overlay** | A consistently mirrored or transposed grid naming round-trips **perfectly** and is still wrong everywhere (trap 1) |

Report `max_grid_round_trip_error_milli_wall_units` beside `min_grid_pitch_milli_wall_units`, so
the margin is visible as two numbers rather than asserted as a pass. Report
`positions_outside_image_bounds` separately: the envelope requires the full problem visible
(`mvp-contract.md` Section 1), so a non-zero count is a **framing violation**, and calling it a
calibration failure would point the owner at the wrong fix.

## 8.8 Camera motion is not measured at this stage

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

## 8.9 The overlay

Pure-Python SVG. **No imaging library.** SVG is text, and text is what a byte-stability test can
assert on.

| Element | Rule |
| --- | --- |
| Reference image | Referenced by **relative basename** in the `href`, never an absolute path. `mvp-contract.md` Section 7: a path can contain a person's name. |
| The projected grid | Every grid position drawn at its projected centre, with its extent (a circle under `circle_radius`, the polygon under `polygon`) and its grid coordinate as a text label |
| The origin corner | Marked, and labelled with the corner the board definition declares. This is the only place a mirrored or transposed naming becomes visible (trap 1). |
| Fiducials | Crosses at the clicked image points, with each residual drawn as a **line** from the clicked point to the reprojected point, so the length of the line is the error |
| Fiducial hull | Dashed |
| Problem membership | Colour-coded by `ProblemHoldRole`; foot-only holds distinguished; positions not in the problem drawn faintly, so "lit" and "unlit" are distinguishable at a glance |
| Attribute ordering | **Deterministic**, sorted, so the bytes are stable and the file diffs cleanly between two calibrations |

The overlay is a **diagnostic view, never the only result** (`data-schema.md` Section 6). The
`WallSet`, `HoldInstance` and `Calibration` documents must exist beside it, and a test asserts
they do.

## 8.10 Threshold table

`configs/wall/v1.json`. Every number carries a status tag. Nothing is `[VAL]`. The board's own
geometry is **not** here: it lives in `configs/board/<board_id>/v1.json` as declarations with
sources (Section 8.1), because it is a property of the equipment and not a decision this project
gets to make.

| Threshold | Value | Unit | Status | Selection text |
| --- | --- | --- | --- | --- |
| `min_fiducial_count` | Integer placeholder, at least 6 | `count` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` |
| `min_fiducial_triangle_doubled_area` | Integer placeholder | `squared_milli_units_doubled` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` |
| `max_reprojection_error_milli_wall_units` | Integer placeholder | `milli_wall_units` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` |
| `max_rms_reprojection_error_milli_wall_units` | Integer placeholder | `milli_wall_units` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` |
| `min_hull_coverage` | `{num, den}` placeholder | `ratio` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` |
| `hold_radius_milli_wall_units` | Integer placeholder | `milli_wall_units` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` The whole cost of `hold-extent-model` option A is this one number (Section 5.2). |
| `min_hold_doubled_area` | Integer placeholder | `squared_milli_units_doubled` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` **General-wall path and `hold-extent-model` option B only**; unused while hold extent is a circle. |
| `homography_denominator` | `1000000` | `denominator` | `[FIXED]` | Definitional, not empirical. Fixes the quantisation grid of the stored matrix. Every reported diagnostic is recomputed from the quantised matrix, so this value affects the recorded numbers and changing it changes what every calibration means. Recorded as an ADR at Stage 3. |

No deterministic gate clause in Section 11 depends on the value of any `[PILOT]` threshold. A
placeholder must not be able to make a gate pass. The grid round trip (Section 8.7) is
parameter-free precisely so that it cannot be.

## 8.11 New error codes

Raised through the existing `ClimbVisionError(code, message)`; no new exception classes (C10).

`ROTATION_UNSUPPORTED` (if Stage 2 did not already add it), `REFERENCE_FRAME_NOT_FOUND`,
`REFERENCE_FRAME_AMBIGUOUS`, `BOARD_DEFINITION_INVALID`, `BOARD_GEOMETRY_SOURCE_MISSING`,
`BOARD_DEFINITION_MISMATCH`, `FIDUCIAL_COUNT_BELOW_MIN`, `FIDUCIAL_SET_DEGENERATE`,
`FIDUCIAL_GRID_POSITION_UNKNOWN`, `FIDUCIAL_GRID_POSITION_DUPLICATE`, `HOMOGRAPHY_DEGENERATE`,
`HOMOGRAPHY_NORMALIZATION_DEGENERATE`, `HOMOGRAPHY_NOT_INVERTIBLE`, `GRID_ROUND_TRIP_FAILED`,
`HOLD_NUMBER_DUPLICATE`, `PROBLEM_HOLD_UNKNOWN`, `PROBLEM_HOLD_OUT_OF_GRID`,
`PROBLEM_HOLD_DUPLICATE`, `PROBLEM_WITHOUT_START`, `PROBLEM_WITHOUT_FINISH`,
`CALIBRATION_CONFLICT`.

`FIDUCIAL_GRID_POSITION_UNKNOWN` is raised when a fiducial names a position the board definition
does not list as occupied. It is a separate code from `PROBLEM_HOLD_UNKNOWN` because the two mean
different things to the owner: one says a click was named wrongly, the other says a problem was
typed wrongly, and a shared code would send them to the wrong file.

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
| Inverting the homography for the grid round trip | The integer **adjugate over the determinant**, in `Fraction`. A 3-by-3 inverse is nine 2-by-2 determinants; it is not a reason to import a numerical library. |
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
| Exact inverse | `H` composed with its exact rational inverse is the identity **exactly**, in `Fraction`, for both the affine and the projective fixture matrix; a singular matrix raises `HOMOGRAPHY_NOT_INVERTIBLE` |

## 10.2 The board, the grid and the round trip

| Test | Assertion |
| --- | --- |
| Board definition provenance | A definition with an empty `selection`, or with no `source`, on any declared geometry value raises `BOARD_GEOMETRY_SOURCE_MISSING`; a definition missing a provenance entry for a declared value raises `BOARD_DEFINITION_INVALID`. Write both negative cases. |
| Grid centres | For a hand-authored fixture board, the generated wall-plane centres equal a table of expected values **computed by hand** from the spacing, including at least one position where the quantisation actually rounds |
| Grid round trip | Every position on the fixture board round-trips to its own grid coordinate (Section 8.7), and `max_grid_round_trip_error_milli_wall_units` is reported beside `min_grid_pitch_milli_wall_units` |
| Grid round trip, negative | A deliberately coarse `homography_denominator`, or a fixture camera far enough away, makes at least one position round-trip to a **neighbouring** coordinate and raises `GRID_ROUND_TRIP_FAILED` naming it. Without this the clause is untested and could pass vacuously. |
| **The mirrored grid fits perfectly** | Relabel the fixture fiducials under a consistent left-right mirror and assert the solver returns a fit whose max reprojection error is **zero** and whose grid round trip **passes**. This test does not assert a defence; it **pins the absence of one**, so nobody later reports "the numbers were clean" as evidence the naming was right (trap 1). |
| Fiducial names a vacant position | A fiducial naming a position the board definition does not list as occupied raises `FIDUCIAL_GRID_POSITION_UNKNOWN`; the same position named twice raises `FIDUCIAL_GRID_POSITION_DUPLICATE` |
| Board mismatch | Building a wall set from a calibration whose `board_definition_sha256` differs from the supplied definition raises `BOARD_DEFINITION_MISMATCH` |
| Hold identity | `hold_id` is derived from the grid coordinate alone, so changing the radius, the extent model or any diagnostic leaves every `hold_id` **unchanged** |
| Extent exclusivity | Under `circle_radius` both polygon fields are null and the radius is set; under `polygon` the reverse. A record with both, or neither, fails validation. |
| Outside the hull | A position whose projected centre lies outside the fiducial hull gets `centre_stabilized_px: null`, `outside_fiducial_hull: true`, and is **counted** in the report rather than silently extrapolated |
| Outside the image | A position projecting outside the raster is counted in `positions_outside_image_bounds` and is **not** counted as a calibration failure |

## 10.3 Rotation, problems and the overlay

| Test | Assertion |
| --- | --- |
| Rotation round trip | For each of 0, 90, 180 and 270, applying the map then the inverse returns the original point exactly, and the transformed dimensions match the table in Section 8.3 |
| Rotation rejection | A `null` rotation and a rotation of 45 both raise `ROTATION_UNSUPPORTED` |
| Overlay byte stability | Rendering twice from the same inputs produces byte-identical SVG |
| Overlay contains no absolute path | Grep the rendered bytes for a leading `/` in any `href` and for the string `/Users` |
| Overlay is not the only result | Rendering an overlay without the `WallSet` and `Calibration` documents present on disk fails |
| Overlay shows the origin | The rendered bytes contain the declared `origin_corner` as a label, because it is the only human-readable guard against trap 1 |
| Problem holds | A lit coordinate outside the grid raises `PROBLEM_HOLD_OUT_OF_GRID`; one the definition does not list as occupied raises `PROBLEM_HOLD_UNKNOWN`; a repeated coordinate raises `PROBLEM_HOLD_DUPLICATE` |
| Problem roles | No `start` raises `PROBLEM_WITHOUT_START`; no `finish` raises `PROBLEM_WITHOUT_FINISH` |
| Problem scoping | Two `ProblemVersion` documents with the same `problem_slug` on two `WallSet` revisions get **different** `problem_version_id`s, so problem identity cannot survive a reset |
| Calibration conflict | Re-fitting with different config and writing over a stored calibration raises `CALIBRATION_CONFLICT`; identical bytes are a silent no-op |
| Frame extraction | **ffmpeg-gated integration test**: extract a frame at a known timestamp from a committed fixture, assert exactly one file is produced, and assert its dimensions equal the C4-transformed coded dimensions. Use `rot90_160x120_1s.mp4`, which carries a real Display Matrix, so the rotation path is exercised on a real fixture and not only in a unit test. |
| Validate picks up new documents | `climbvision validate` accepts one golden fixture per new schema id through `MODEL_REGISTRY` |
| Ontology version | Stage 2 golden documents still validate with `ontology_version: 1` after the bump to 2 |

## 10.4 New fixtures

All hand-authored, under `tests/fixtures/wall/`, documented in `tests/fixtures/README.md` as
**validator inputs, not observations**, exactly as `tests/fixtures/probe_invalid/` is.

| Fixture | Contents |
| --- | --- |
| A small fixture board definition | A grid small enough to check by hand, with an invented spacing, an origin corner, a full provenance block and **`source: fixture` on every value**. It is not a description of any real board. |
| Fiducial file with a known exact homography | Six correspondences generated by hand from a chosen integer matrix, so the expected recovered matrix is known before the solver runs |
| Mirrored fiducial file | The same six image points with a consistently mirrored grid naming, for the trap-1 test |
| Degenerate fiducial set | Four points with three collinear, plus a six-point set with one deliberately displaced |
| A sparse-occupancy board definition | A definition whose `occupied_positions` is deliberately **not** the full grid, so nothing in the code can quietly assume `grid_columns * grid_rows` |

**`source: fixture` exists so an invented geometry can never be mistaken for a measured one.** Every
`WallSet` carries its board definition and its provenance, so a reader can always see which it was.
A gate number comes from real data and **never** from `tests/fixtures/`: a number computed against a
fixture geometry is not a gate number. Fixtures prove the code runs; they do not measure calibration
quality.

---

## 11. Gate

This is the gate in the form being restated in `mvp-contract.md` Section 9 for the board envelope.
Check the two against each other before starting (Section 1.2).

## 11.1 Deterministic clauses, not `[PILOT]`

| # | Clause | Assertion |
| --- | --- | --- |
| D1 | Tests and lint | `uv run pytest` all pass, `uv run ruff check .` clean. **No skipped test counts as a pass**; report passed and skipped separately. |
| D2 | Round trip, equality | `model == parse(dump(model))` for every new document model |
| D3 | Round trip, byte identity | `dump(parse(dump(model))) == dump(model)` byte-for-byte for every new document model |
| D4 | Known homography | The known integer homography, affine and projective, is reproduced **exactly** up to scale by integer cross-multiplication |
| D5 | Diagnostics self-consistency | Every reported diagnostic is recomputed from the **quantised** matrix and matches the stored value; the pre-quantisation variant fails the test |
| D6 | Board geometry provenance | **Every declared geometry value in the board definition carries a non-empty `selection` and a valid `source`**, and the definition nested in the emitted `WallSet` matches the config that was read, by sha256. Empty provenance fails, exactly as C9 requires a non-empty `selection`. |
| D7 | Grid round trip | **Every grid position projects into the image and back to its own grid coordinate** (Section 8.7). Parameter-free, so no `[PILOT]` placeholder can make it pass. Report the count checked, the max round-trip error and the minimum grid pitch. |
| D8 | Real reprojection error | The real board's **max and RMS reprojection error reported as numbers** in milli-wall-units, with **every fiducial's individual residual beside its grid coordinate**, against `[PILOT]` targets |
| D9 | Hull coverage | Reported as a `RatioValue`, with the count of outside-hull positions and their `centre_stabilized_px: null`, and separately the count of positions outside the image raster |
| D10 | Provenance and origin | **Every `HoldInstance` carries `derived` provenance, names the board definition it came from, and nothing in any emitted document originated from a model.** Assert it as a test over the emitted documents, not as a claim in prose. |
| D11 | Idempotent re-fit | A re-fit on identical inputs produces a **byte-identical** `Calibration` and a **second append-only run record** |

## 11.2 The `[PILOT]` clauses

| Clause | Form |
| --- | --- |
| Reprojection target | Max and RMS reprojection error against `[PILOT]` targets that do not exist yet, so the clause is "measured and reported", not "under X" |
| Hull coverage target | Same |

There is **no annotation-agreement clause at this gate on this envelope.** Nothing is traced, so
there is nothing for a second pass to disagree with. That is a real reduction in what the stage
proves, not a saving: see Section 11.4.

## 11.3 Recorded as `not_applicable`, never blank and never zero

| Metric | Reason string |
| --- | --- |
| Model **mask IoU** and **mask average precision** | "no segmenter adopted; `hold-segmentation-model` open; the hold map is user-confirmed by contract" |
| **Hold-polygon self-agreement IoU** | "no polygon tracing on the board envelope; hold extent is generated from the board definition under `hold-extent-model`" |

Zero would say the thing was measured and was bad. Blank would say nobody looked. The value of a
measurement whose input does not exist is **undefined**, and `not_applicable` is the only value that
says so. All three metrics stay defined in `evaluation.md` Section 1 and stay implemented, because
the general-wall path still needs them (Section 1.1).

## 11.4 Honest limitation

This measures **one camera placement, on one board, in one gym, under one lighting condition.** It
supports no claim about a different camera position, a different room or a different board.

**The board makes the geometry easier and the honesty harder.** Because no human traces anything,
this stage no longer measures any human's consistency at all: the hold positions are as good as the
board definition, and **the board definition is checked by the overlay and by the grid round trip,
not by a second observer.** A wrong spacing, a wrong origin corner or a transposed grid naming
produces a calibration with excellent numbers and every hold in the wrong place (trap 1).

The reprojection error measures how well one plane fits the fiducials **that were clicked**. It says
nothing about the parts of the panel outside the fiducial hull, which is why positions out there get
a null image centre rather than an extrapolated one. On a steep overhang it should be expected to
grow with height (trap 2), which is why the per-fiducial residuals are reported and not only the
pooled maximum.

Camera motion is **assumed absent, not measured** (Section 8.8).

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

# Fit the calibration and run the grid round trip
uv run climbvision calibrate \
  --wall-set <wall_set_id> \
  --board configs/board/<board_id>/v1.json \
  --reference artifacts/wall/<wall_set_id>/frame-001.png \
  --fiducials ~/climbvision-data/wall/<wall_set_id>.fiducials.json \
  --out artifacts/wall

# Build the wall set and its hold instances from the board definition
uv run climbvision wall-build \
  --wall-set <wall_set_id> \
  --board configs/board/<board_id>/v1.json \
  --calibration artifacts/wall/<wall_set_id>/calibration.json \
  --out artifacts/wall

# Emit the problem versions from the lit-hold grid coordinates
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
  --board configs/board/<board_id>/v1.json \
  --reference artifacts/wall/<wall_set_id>/frame-001.png \
  --fiducials ~/climbvision-data/wall/<wall_set_id>.fiducials.json \
  --out artifacts/wall
shasum -a 256 artifacts/wall/<wall_set_id>/calibration.json
ls artifacts/wall/<wall_set_id>/runs/

# OPEN THE OVERLAY AND LOOK AT IT
open artifacts/wall/<wall_set_id>/overlay.svg
```

## **The overlay is the human check, and on this envelope it is the only one.**

The last command is not decoration and it is not optional. The owner opens the SVG and confirms
three things with their own eyes:

1. **The projected grid sits on the holds.** Not near them, on them.
2. **The origin corner label is on the corner it names**, and the grid coordinates increase in the
   directions the board definition declares. A mirrored or transposed naming fits with zero error
   and passes the round trip (trap 1). This look is the only thing that catches it.
3. **The fiducial residual lines are short**, and the long ones, if any, are at the top rather than
   scattered. A long line is a fiducial clicked off its grid position or named with the wrong
   coordinate; a residual gradient rising up the panel is foreshortening (trap 2). Both are visible
   in one second on the overlay and invisible in a table of numbers.

That is why it is rendered. `AGENTS.md` Section 9 step 9: if the stage produces visual output,
render a deterministic overlay and **look at it**. A reprojection error of 8 mm and a grid mirrored
about its centre line are the same number.

---

## 13. Traps

Traps 1 through 4 are specific to the board envelope. The rest carry over unchanged.

| # | Trap | Consequence if you get it wrong |
| --- | --- | --- |
| 1 | **A mirrored or transposed grid naming.** The owner clicks six correct hold centres and names them from the wrong origin corner, or with columns and rows swapped. | The relabelling is itself a projective map of the grid, so the solver returns an **exact** fit: max reprojection error zero, hull coverage full, grid round trip passing. Every hold is then in the wrong place and **no number this stage computes can detect it**. The declared `origin_corner`, drawn and labelled on the overlay, is the only guard. Section 10.2 pins this with a test that asserts the perfect fit, so nobody later cites clean numbers as evidence of correct naming. |
| 2 | **Foreshortening on a steep overhang.** A board of this class is a steep overhang, on the order of 40 degrees from vertical `[PLANNING]`, and the camera shoots steeply upward at it. | The top of the panel occupies far fewer pixels per grid pitch than the bottom, so the **reprojection error will not be uniform across the panel and should be expected to grow with height.** A pooled maximum hides the gradient entirely. Report each fiducial's residual beside its grid row (Section 8.6), and place fiducials at the top as well as the bottom (Section 3.1). The grid round trip has its smallest margin at the top, which is where it fails first. |
| 3 | **The climber hangs underneath the panel.** On a steep overhang the body is between the camera and the holds it is using, so **the holds in use are exactly the holds that are occluded.** | Not fatal here, because calibration is done on an empty board. It is fatal to assume away later: Stage 4's endpoint pose and Stage 5's contact intervals will both be measured against limbs that are frequently hidden, at a far higher rate than on a vertical wall. Record the expectation now, and never let `occluded` become `none` (`mvp-contract.md` Section 5, standing rule 1). |
| 4 | **Clicking the hold instead of the grid position.** A fiducial placed on an asymmetric hold's visual centre rather than on the point the board definition calls a grid position. | The whole fit inherits a systematic offset of roughly a hold's radius, in a direction that varies with the hold. It looks like ordinary residual noise, and it is not recoverable from the artifact afterwards. Declare `grid_position_reference` in the board definition and click that point every time (Section 3.1). |
| 5 | **Near-collinear fiducials.** | The 8-by-8 system **solves fine** and the four fitting points reproject **perfectly**. Two metres away the mapping is catastrophically wrong, because a near-degenerate configuration constrains the plane only along one direction. This is why the minimum triangle area is a threshold and not an afterthought, and why the score is computed over all fiducials rather than over the subset. Six positions taken from one row of the grid are exactly this. |
| 6 | **Extrapolation beyond the fiducial hull.** | Projective error grows **without bound** outside the hull, and an extrapolated image position looks exactly like a computed one. Null it and flag it. Using the four corner positions as fiducials makes the outside-hull set empty by construction. |
| 7 | **Quantisation drift.** Reporting diagnostics from the pre-quantisation rational. | The stored matrix and its stored diagnostics describe different things, and nothing downstream can detect it. See Section 8.5. |
| 8 | **Algorithmic hold renumbering.** Deriving `hold_id` from a position in a list, a sort order or an index, rather than from the grid coordinate. | It **invalidates every downstream reference**: every problem definition, every contact annotation targeting a hold, every beta token. On this envelope the grid coordinate is the identity and nothing else may enter the derivation; on the general-wall path the human-assigned number plays the same role. |
| 9 | **Auto-rotation on decode.** ffmpeg applies the container rotation by default and drops the side data. | The extracted image silently disagrees with `stabilized_px`, so every hold position is transposed relative to every future pose observation. Assert the extracted dimensions equal the C4-transformed coded dimensions. |
| 10 | **`-ignore_editlist 0` is needed on the extraction call, not only on the probe.** | An mp4 edit list shifts every PTS the demuxer reports. Stage 1 measured **1024 ticks** on this repository's own CFR fixture. Probe with the flag and extract without it and you get a different frame than the one the frame index names, with no error anywhere. |
| 11 | **Approximate seeking.** `-ss` before the input lands on the nearest preceding keyframe. | You calibrate against a frame that is not the frame you recorded, and every subsequent number is about a slightly different image. There is no way to detect this after the fact. |
| 12 | **Camera motion assumed rather than measured.** | The envelope forbids pan, zoom and reframing, and this stage cannot verify any of it. A recording with a bumped tripod produces a calibration that is correct for the first frame and wrong for the rest, with no flag anywhere. Record `camera_motion: unknown` honestly and upgrade it at Stage 4. |
| 13 | **Inventing the board geometry.** Filling in a spacing, a panel size or a hold count from memory because it "is standard". | Every number the stage reports is then about a board that does not exist, and the arithmetic is self-consistent, so nothing downstream can detect it. `board-geometry-source` exists for exactly this; a declared value with no source raises `BOARD_GEOMETRY_SOURCE_MISSING`, and a fixture geometry carries `source: fixture` so it can never be mistaken for a measured one. |
| 14 | **Self-intersecting polygons.** CVAT will happily let an annotator draw a bow-tie. **General-wall path and `hold-extent-model` option B only.** | The shoelace area of a self-intersecting polygon is a signed sum that partially cancels, so it returns a plausible smaller number instead of an error. Every IoU, centroid and area computed from it is then quietly wrong. Raise `POLYGON_SELF_INTERSECTING`. |

---

## 14. Report format and stop condition

Follow Section 0.6 exactly: the gate table, files added and changed, config thresholds introduced,
open decisions deferred with their slugs, what this stage does not prove, and the command
transcript.

Stage-specific additions:

- **Report the board definition's provenance verbatim**, one line per declared value: what the
  value is, where it came from, and the date. This is the input every other number depends on, and
  it is the one an agent could most easily have invented (trap 13).
- **Report the overlay as evidence.** State that it was rendered, that it was opened, and what was
  visible: whether the projected grid sits on the holds, whether the origin corner label is on the
  corner it names, and whether any residual line was conspicuously long. This is the one clause
  where human judgement is the grader, and it must be labelled as such (`evaluation.md` Section 3).
- **Report the grid round trip** as three numbers: positions checked, maximum round-trip error, and
  the minimum grid pitch it is measured against. A pass with no margin reported is not a pass worth
  reading.
- **Report every fiducial's residual with its grid coordinate**, not only the pooled max and RMS, so
  the height gradient is visible (trap 2).
- **Report `subsets_evaluated`** and the number of subsets rejected for degeneracy, so a reviewer
  can recompute `C(n,4)` independently.
- **Report the three `not_applicable` metrics** with their reason strings (Section 11.3), never as
  blank and never as zero.
- **The reviewer re-measures independently**, including recomputing the max reprojection error from
  the stored quantised matrix and the stored fiducials, and re-running the grid round trip from the
  stored matrix and the stored board definition, without running the implementation under review.
- **`docs/status.md` is not marked complete** until the owner approves.
- **If a gate clause fails**, report the measured gap with its number, name the failing wall set
  rather than pooling, propose the smallest next experiment (for a reprojection failure that is
  almost always "add or re-place fiducials", not "add an optimiser"; for a round-trip failure
  concentrated at the top of the panel it is "move or raise the camera", not "loosen the check"),
  and stop.

Then stop. Do not start Stage 4.

---

## 15. Read-first list

In this order, before writing anything.

| Order | File | Why |
| --- | --- | --- |
| 1 | `AGENTS.md` | Binding operating rules. Sections 2, 3, 5, 6, 9, 10, 11. |
| 2 | `docs/mvp-contract.md` | Sections 1, 2, 4, 5, 7, 9, 10, 11. The envelope including the board amendment, the coordinate spaces, the `WallSet` scoping rule, the restated Stage 3 gate, and the Section 10 provenance row Section 4.4 says to check. |
| 3 | `docs/data-schema.md` | Sections 1, 3, 4, 5, 6, 7, 9. The entity table including the `BoardDefinition` row, identity rules, storage formats, and the rotation and edit-list behaviour in Section 9. |
| 4 | `docs/evaluation.md` | Section 1, Stage 3 block, and Sections 3 and 5. |
| 5 | `docs/annotation-guide.md` | Section 6, for the self-agreement rule, which this envelope records as `not_applicable` rather than measures. |
| 6 | `docs/status.md` | The Stage 1 evidence table shape to imitate. |
| 7 | The owner's board definition, `configs/board/<board_id>/v1.json`, and the `board-geometry-source` decision record under `docs/adr/` if it has been made | The geometry every other number depends on, and its provenance. **If either is missing, stop and ask.** Do not supply a number yourself. |
| 8 | `docs/agents/briefs/stage-2-annotation-harness.md` | Sections 5 and 8, for the value objects, ontology and geometry primitives this stage consumes. |
| 9 | `configs/ingest/v1.json` | The exact config shape and the exact `selection` wording to imitate. |
| 10 | `src/climbvision/schema/common.py`, `src/climbvision/schema/ontology.py` | The Stage 2 value objects and enums. Do not redefine them. |
| 11 | `src/climbvision/geometry/polygons.py` | Point-in-polygon for hull membership; shoelace, self-intersection and rasterisation for the general-wall path. Do not reimplement them. |
| 12 | `src/climbvision/schema/provenance.py` | `IngestRun`, the model `CalibrationRun` is built from. |
| 13 | `src/climbvision/schema/versions.py`, `src/climbvision/schema/__init__.py` | The two registration seams. |
| 14 | `src/climbvision/schema/recording.py` | `VideoStreamInfo`, especially `coded_width`, `coded_height`, `rotation_degrees` and `rotation_source`, which C4 depends on. |
| 15 | `src/climbvision/media/ffprobe.py` | The subprocess boundary pattern `media/frames.py` must follow. |
| 16 | `src/climbvision/media/normalize.py` | How the frame index is built and sorted, for resolving a timestamp to a `frame_index_position`. |
| 17 | `src/climbvision/ingest.py` | `_refuse_conflicting_manifest`, the model for `CALIBRATION_CONFLICT`, and the reason a new `QualityFlag` member is not an option. |
| 18 | `src/climbvision/quality.py` | The C2 cross-multiplication pattern in `_frame_rate`. |
| 19 | `src/climbvision/timebase.py` | Integer-only conversion and the round-half-away-from-zero rule the quantiser must reuse, for the matrix and for the grid centres. |
| 20 | `src/climbvision/cli.py` | Subcommand and exit-code conventions. |
| 21 | `tests/unit/test_scope_guard.py` | The four guards, and the comment above `test_the_stage_one_module_inventory_is_pinned`. |
| 22 | `tests/unit/test_schema.py` | `DOCUMENT_MODELS` and `ALL_MODELS`, and what they enforce. |
| 23 | `tests/fixtures/README.md` | The five video fixtures, especially `rot90_160x120_1s.mp4` and its Display Matrix, and the hand-authored-versus-observed distinction. |
| 24 | `docs/agents/README.md` | The decision index, and the rule that decision records are never pre-stubbed. **The three slugs this brief introduces are not in that index yet**: `board-geometry-source`, `hold-extent-model` and `lit-hold-entry-and-import`. Report the gap; do not silently add them. |
