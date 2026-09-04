# Stage 4 — Climber pose trajectories

Implementation brief. Self-contained context package for an agent starting with zero context.
Read Section 0 first, then Section 15, then the rest.

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

Select **one** pretrained 2D pose backend by an explicit decision, benchmarked on the ClimbVision
gold set rather than on published generic accuracy, and produce per-frame keypoint trajectories
with per-keypoint model scores, storing raw output before any filtering. Explicitly derive palm
and toe **contact anchors** and report endpoint accuracy and track gaps.

Consumes:

| Input | From | Used for |
| --- | --- | --- |
| `Recording` and `FrameIndex` | Stage 1, `recordings/<asset_id>/` | The asset bytes, the presentation-sorted packet table, the time base |
| `Calibration` | Stage 3 | The optional wall-plane projection of each anchor |
| Keypoint gold set | Stage 2 | The ~200 adjudicated frames the backend comparison is measured on |
| Dataset release and split manifests | Stage 2 | Which gold frames are validation and which are the frozen test slice |

Does **not** do: annotation (Stage 2 did it), tracking across identity gaps, contact prediction
(Stage 5), 3D reconstruction (out of scope, `mvp-contract.md` Section 2).

## 2. Preconditions

The agent does not start until every row holds. If a row does not hold, stop and report.

| Precondition | Evidence it holds |
| --- | --- |
| The Stage 3 gate is recorded | A Stage 3 row and measured-evidence table in `docs/status.md` |
| A calibration exists for every wall in the release | One `Calibration` document per `Wall`/`WallFacet` referenced by the release manifest |
| The gold set is adjudicated and split | Roughly 200 `[PLANNING]` frames with `adjudicated_ground_truth` provenance, each assigned to exactly one split by the frozen release |
| The `pck-normalization-scale` decision is closed | A record under `docs/adr/` naming the normalization scale, its coordinate space and its unit |
| The weights directory policy and a checksum-verifying fetch script are agreed | Written down **before any download**, per truth rule 11 |

**No weights may be downloaded before the two model registry entries exist in
`docs/model-registry.md` with all seven fields** (`docs/model-registry.md` Sections 1 and 2). The
registry entry precedes the download; the checksum is filled in from the download and the entry
is then complete.

## 3. Human inputs required before the agent starts

Four items. The owner does not read code; each item below is a decision, not a review.

| # | Input | Why only a human can do it |
| --- | --- | --- |
| 1 | Approve **two** model registry entries, not one | A wholebody pipeline runs a **person detector first**, and that detector is a second model with its own weights, its own license and its own training data. It is the field most often forgotten. Two entries, seven fields each, before any download. |
| 2 | Decide the **checkpoint license** question | The inference code and the checkpoint carry **different licenses**. A wholebody checkpoint trained on a cocktail of datasets inherits the **most restrictive** of their terms even when the code is permissive. This is decisive if the project ever becomes commercial, and it cannot be undone after the model is embedded in a pipeline. |
| 3 | Decide the **canonical keypoint set** (`canonical-keypoint-set`) | It must be **annotatable in a couple of minutes per frame** by a human and **producible by both candidate backends**. A set that only one backend can produce pre-decides `pose-backend-selection`; a set that takes ten minutes a frame makes the gold set unaffordable. |
| 4 | Run the fetch script and eyeball the printed checksums | The download crosses the network and the privacy boundary. The agent writes the script; the human runs it and looks at what it printed. |

**Nothing else.** The gold set was annotated at Stage 2. Stage 4 does not ask for a single new
label.

## 4. Deliverables

### 4.1 New files

Module names are **proposals**; the implementer may rename them, but every rename must be carried
into the scope guard inventory set in the same change.

| Path (proposed) | Kind | Owns |
| --- | --- | --- |
| `src/climbvision/media/decode.py` | module | The **PyAV boundary**. The only place PyAV is imported. Yields decoded frames already joined to their `FrameIndex` position. |
| `src/climbvision/pose/__init__.py` | package | Exports |
| `src/climbvision/pose/keypoints.py` | module | The canonical point set: names, indices, left–right pairs, `keypoint_set_id` |
| `src/climbvision/pose/backend.py` | module | The backend `Protocol`: what an adapter must return and what it must raise |
| `src/climbvision/pose/backends/__init__.py` | package | Adapter registry (a dict, not a plugin system) |
| `src/climbvision/pose/backends/wholebody.py` | module | Adapter for the wholebody candidate, behind optional group `pose-wholebody` |
| `src/climbvision/pose/backends/landmark.py` | module | Adapter for the landmark candidate, behind optional group `pose-landmark` |
| `src/climbvision/pose/anchors.py` | module | Palm and toe anchor derivation, anchor rule ids, wall projection |
| `src/climbvision/pose/pipeline.py` | module | Orchestration and abstention records. No model code, no decode code. |
| `src/climbvision/motion.py` | module | The static-camera check, now that pixel arrays are available |
| `src/climbvision/schema/pose.py` | module | `PoseSeries`, `PoseObservation`, `PosePoint`, `PersonTrack`, `AnchorSeries`, `AnchorObservation`, `PredictionProvenance` |
| `src/climbvision/schema/pose_run.py` | module | `PoseRun`, the Stage 4 run document (C5) |
| `configs/pose/v1.json` | config | Every Stage 4 threshold and fixed identifier (C9) |
| `scripts/fetch_pose_weights.sh` | script | Manual, checksum-verifying fetch. **Never run in CI.** |
| `docs/adr/canonical-keypoint-set.md` | decision | Written first — it is a precondition for the comparison |
| `docs/adr/dense-trajectory-storage-format.md` | decision | Written second, after the size measurement |
| `docs/adr/pose-backend-selection.md` | decision | Written last, after the paired comparison |
| `tests/fixtures/documents/pose_series.valid.json` | fixture | Golden document fixture |
| `tests/fixtures/documents/anchor_series.valid.json` | fixture | Golden document fixture |
| `tests/fixtures/documents/pose_run.valid.json` | fixture | Golden document fixture |

Decision records are created **one at a time, at the moment each is made** (Section 0.7). Do not
pre-stub the three.

### 4.2 Existing files changed — the seam list applied

| File | Change |
| --- | --- |
| `src/climbvision/schema/versions.py` | Add `POSE_SERIES_SCHEMA_ID`, `ANCHOR_SERIES_SCHEMA_ID`, `POSE_RUN_SCHEMA_ID`, their `*_SCHEMA_VERSION = 1` constants, and three entries in `SCHEMA_IDS` |
| `src/climbvision/schema/__init__.py` | Three entries in `MODEL_REGISTRY`, and every new name in `__all__` |
| `tests/unit/test_schema.py` | Three rows in `DOCUMENT_MODELS` with their golden fixtures; **every** nested model added to `ALL_MODELS`, including `PosePoint`, `AnchorObservation`, `PredictionProvenance`, `PersonTrack` and `RatioValue` |
| `tests/unit/test_scope_guard.py` | A **new** set `STAGE_FOUR_MODULES` beside `STAGE_ONE_MODULES`; the inventory test asserts `on_disk == STAGE_ONE_MODULES \| STAGE_FOUR_MODULES`. **Do not extend `STAGE_ONE_MODULES`** — the two sets are the decision record of which stage introduced which module. Add `av` to `ALLOWED_THIRD_PARTY`; introduce `PATH_SCOPED_THIRD_PARTY` (Section 9.2); remove from `BANNED` exactly the roots that move into `PATH_SCOPED_THIRD_PARTY`, so the two never intersect |
| `tests/unit/test_scope_guard.py` | Replace `test_the_runtime_dependency_list_is_exactly_pydantic` with a **parsed** test asserting distribution names, upper bounds and optional-group names, with an explicit distribution → import-root map (`av` → `av`, `numpy` → `numpy`, and one row per backend group) |
| `src/climbvision/cli.py`, `tests/unit/test_cli.py` | Two subcommands (proposed: `pose`, `pose-eval`); exit codes **0** ok, **1** operation failed, **2** usage, exactly as today; plus a test that `validate` accepts the three new documents **through `MODEL_REGISTRY`**, dispatching on `schema_id`, never on filename |
| `pyproject.toml` | `av` and `numpy` added to `dependencies`; two `[dependency-groups]` entries `pose-wholebody` and `pose-landmark`; a `model` marker registered under `[tool.pytest.ini_options]` and **deselected by default** |
| `docs/model-registry.md` | Section 3 currently reads **"Zero models."** It gains its **first two entries**, seven fields each: the pose model and the person detector. Section 4's candidate rows are updated to record which was selected and which was not, with a pointer to the ADR. |
| `docs/status.md` | The Stage 4 row, plus a measured-evidence table shaped exactly like the Stage 1 one |
| `docs/evaluation.md` | **No change.** Stage 4's metric definitions already exist in Section 1. Cite them; do not restate them. |
| `docs/data-schema.md` | **No change.** Section 6 has already been amended to canonical JSON with parallel integer arrays, columnar deferred. Cite it; do not re-amend it. |
| `README.md` | **One row only**, in the list of commands that exist. No claim about a stage that has not shipped. |
| `.gitignore` | **Check, then possibly extend.** `weights/`, `checkpoints/`, `*.pt`, `*.pth`, `*.onnx`, `*.safetensors` are already covered. They do **not** cover the bundle extensions a self-contained landmark package ships. If the selected backend's checkpoint has an extension outside that list, add it, path-scoped, in the same change as the fetch script. |
| `scripts/regenerate_fixtures.sh` | Extend to regenerate the three new document fixtures from a live run, exactly as it already does for the Stage 1 documents. Manual only. |

## 5. Entities

`PersonTrack`, `PoseObservation` and `PredictionProvenance` are all **on schedule at Stage 4**
per `docs/data-schema.md` Section 1. Field identifiers below are **proposals**; the schema
document describes meanings rather than guessing names, and this brief is the place the names are
first proposed.

Every model carries `model_config = ConfigDict(extra="forbid", frozen=True)`. No field is
float-typed. Unknown is an explicit `null`, never an omitted key.

### 5.1 `PoseObservation`

| Field (proposed) | Type | Notes |
| --- | --- | --- |
| `frame_index_position` | `int` | Index into the presentation-sorted `FrameIndex` arrays. **Not** a decoded frame counter (C6). |
| `pts` | `int \| None` | Integer ticks in the stream time base, copied from `FrameIndex.pts`. `null` when the container carried none. |
| `pts_us` | `int \| None` | Integer microseconds via `pts_to_us`. Never `frame_number / fps`. |
| `status` | `Literal["predicted", "abstained"]` | C7: a frame with no result emits a record, not a gap |
| `detection_count` | `int` | Number of person detections on this frame. `0` forces `abstained`. |
| `points` | `list[PosePoint]` | Length equals the canonical keypoint set size, always, in the set's index order |
| `visibility_source` | `Literal["unlabeled"]` | **Always the unlabelled value.** A `Literal` of one member, so the type system forbids anything else. |
| `coordinate_space` | `Literal["stabilized_px"]` | C3 and `mvp-contract.md` Section 4 |

`PosePoint`: `name: str`, `x_milli: int \| None`, `y_milli: int \| None`, `score_milli: int \| None`.
Coordinates are thousandths of a stabilized pixel (C3). Score is in thousandths of whatever the
declared `score_type` is; it is **not** a probability unless the score type says so.

### 5.2 `PoseSeries`

| Field (proposed) | Type | Notes |
| --- | --- | --- |
| `schema_id`, `schema_version` | `Literal` | Registered in `versions.py`, `MODEL_REGISTRY` and `SCHEMA_IDS` |
| `asset_id` | `str` | `sha256-<64 hex>`, constrained by `ASSET_ID_PATTERN` |
| `frame_index_sha256` | `str` | Binds the series to the exact packet table it was joined against |
| `time_base` | `Timebase` | Carried once, on the series — see the note below |
| `track_id` | `str` | The `PersonTrack` this series belongs to |
| `backend_id` | `str` | From config, `[FIXED]` by the ADR |
| `checkpoint_sha256` | `str` | The **pose** checkpoint. The detector's hash lives on `PredictionProvenance`. |
| `score_type` | `str` | Names what `score_milli` is. A raw logit, a calibrated probability and a heatmap peak value are not comparable. |
| `keypoint_set_id` | `str` | From `canonical-keypoint-set` |
| `raw_document_sha256` | `str \| None` | C8: the raw, unfiltered series this one derives from. `null` **only** on the raw document itself. |
| `observations` | `list[PoseObservation]` | One per `FrameIndex` position, none missing |

**A note on C6 and the time base.** C6 requires the frame-index position, the presentation
timestamp and the time base on every per-frame record. The position and the timestamp are on the
observation. The **time base is carried once, on the series**, because it is constant for the
stream and a duplicated copy can silently drift from `FrameIndex.time_base`, while the series
binds `frame_index_sha256` and is the only container through which an observation is ever read.
**If the reviewer rejects this reading, the compliant alternative is to put `time_base` on every
observation at roughly 30 bytes per frame `[PLANNING]`.** Record whichever is chosen, in the
report, as a named decision. Do not leave it implicit.

### 5.3 `PersonTrack`

| Field (proposed) | Type | Notes |
| --- | --- | --- |
| `track_id` | `str` | Deterministic from `(asset_id, run_id)` |
| `asset_id`, `frame_index_sha256` | `str` | Binding |
| `first_frame_index_position`, `last_frame_index_position` | `int` | Coverage |
| `observation_count`, `abstained_count` | `int` | Track-gap statistics derive from these |
| `max_detection_count` | `int` | So multi-person frames are findable as a slice later |
| `selection_rule_id` | `str` | The **declared** rule used when more than one person was detected |
| `provenance_class` | `Literal["prediction"]` | `mvp-contract.md` Section 10 |

The envelope allows exactly one climber (`mvp-contract.md` Section 1), so there is **no
association algorithm at Stage 4** and the track id is constant per asset per run. A track that
needs re-identification across a gap is a later stage's work and must not be invented here.

### 5.4 `AnchorObservation` and `AnchorSeries`

| Field (proposed) | Type | Notes |
| --- | --- | --- |
| `frame_index_position` | `int` | C6 |
| `pts`, `pts_us` | `int \| None` | C6 |
| `limb` | `Literal["left_hand", "right_hand", "left_foot", "right_foot"]` | Closed set |
| `point` | `Point \| None` | `stabilized_px`, milli-units. `null` when abstained. |
| `anchor_rule_id` | `str` | Which named rule produced it |
| `source_keypoint_names` | `list[str]` | Recorded **even when abstained**, so the reason is auditable |
| `status` | `Literal["derived", "abstained"]` | `derived`, not `predicted`: the anchor is a deterministic function of a prediction |
| `wall_point` | `Point \| None` | `wall_plane`, milli-wall-units. `null` outside the fiducial hull or when the anchor abstained. |

`AnchorSeries` binds `asset_id`, `frame_index_sha256`, `track_id`, `pose_series_sha256`,
`calibration_sha256 \| None`, `config_version`, `config_sha256`, and the observations.

### 5.5 `PredictionProvenance`

| Field (proposed) | Type | Notes |
| --- | --- | --- |
| `model_id`, `model_version` | `str` | The exact release or commit, not a branch name |
| `checkpoint_sha256` | `str` | Verified at load, per run |
| `detector_model_id`, `detector_checkpoint_sha256` | `str \| None` | The **second model.** `null` only for a backend that genuinely runs no detector, and the ADR must say so. |
| `code_license`, `checkpoint_license` | `str` | Two fields, because they are two different licenses |
| `score_type` | `str` | Declared, not assumed |
| `execution_provider` | `str` | Pinned; recorded because determinism depends on it |
| `preprocessing_id` | `str` | Names the exact resize, pad and colour-order pipeline applied outside the adapter |
| `coordinate_space` | `Literal["stabilized_px"]` | Per `mvp-contract.md` Section 4 |
| `upstream_document_sha256` | `dict[str, str]` | The chain back to pixels: recording, frame index, calibration |

### 5.6 The rule that keeps the exclusion accounting honest

**Visibility on a prediction is always `unlabeled`; the model's score is a separate field with a
declared score type, and a score is never thresholded into an occlusion claim.**

`occluded` and `out_of_frame` are statements about the world; `unlabeled` is a statement about the
dataset (`mvp-contract.md` Section 6, `docs/annotation-guide.md` Section 2). Converting a low
score into `occluded` turns a model artefact into a claim about the world, and it corrupts the
exclusion accounting in `docs/evaluation.md` Section 1, where occluded and out-of-frame keypoints
are excluded from **both** the numerator and the denominator and their count is reported. If the
model can nominate exclusions, the model decides its own denominator.

A **low score does drive abstention**: below the score floor, the anchor abstains. That is a
statement about the dataset ("we declined"), not about the world ("it was hidden"), and it is
recorded as `abstained`, never as `occluded`.

## 6. Decisions already frozen

Do not reopen any of these. Cite them; do not restate them.

| Frozen | Where |
| --- | --- |
| Half-open intervals `[start_us, end_us)`; integer microseconds; time is never `frame_number / fps` | `mvp-contract.md` Section 3 |
| Four coordinate spaces; every geometry value declares exactly one | `mvp-contract.md` Section 4 |
| The visibility value set, and that `occluded` ≠ `unlabeled` ≠ `none` | `mvp-contract.md` Section 5, `annotation-guide.md` Section 2 |
| Hip trajectory is the midpoint of two observed 2D hip keypoints, **never** center of mass | `mvp-contract.md` Section 6, truth rule 7 |
| 3D biomechanics and center-of-mass claims are out of scope, permanently, for the MVP | `mvp-contract.md` Sections 2 and 11 |
| Endpoint PCK for palm and toe anchors is the deciding metric; the pooled number is not | `evaluation.md` Section 1, `model-registry.md` Section 4 |
| Occluded and out-of-frame keypoints are excluded from numerator **and** denominator, with their count reported | `evaluation.md` Section 1 |
| The backend is chosen by an ADR on the **ClimbVision gold set**, not by published generic AP | `model-registry.md` Section 4 |
| Seven registry fields before any download; weights never committed; checkpoint checksum verified **per run** | `model-registry.md` Sections 1 and 2, `AGENTS.md` Section 7 |
| No pretrained model is ground truth. Its output is a `prediction`. | `model-registry.md` Section 2 |
| Dense trajectories are canonical JSON with parallel integer arrays; Parquet/Arrow deferred | `data-schema.md` Section 6 |
| No float-typed field anywhere; canonical serialization; explicit `null` | `data-schema.md` Section 7 |
| A document of the wrong schema version fails loudly at the boundary; never coerced | `data-schema.md` Section 4 |
| The normalization scale for endpoint accuracy | `docs/adr/pck-normalization-scale.md`, closed as a precondition |

Frozen by this brief, into `configs/pose/v1.json`, `[FIXED]` by the `pose-backend-selection`
decision: `backend_id`, `pose_checkpoint_sha256`, `detector_checkpoint_sha256`,
`execution_provider`, `keypoint_set_id`, `palm_anchor_rule_id`, `toe_anchor_rule_id`,
`preprocessing_id`. These are identifiers rather than tunable numbers; they carry `[FIXED]`
because changing one requires the ADR to change, which is exactly what `[FIXED]` means.

## 7. Open decisions

Three decisions close at Stage 4, by slug: `pose-backend-selection`, `canonical-keypoint-set`,
`dense-trajectory-storage-format`.

### 7.1 `canonical-keypoint-set`

Decided by the owner (Section 3, item 3), recorded by the agent. Constraints the record must
satisfy:

- **Annotatable in a couple of minutes per frame** `[PLANNING]`. The gold set is roughly 200 frames; at ten minutes a frame it does not get built.
- **Producible by both candidate backends**, otherwise the keypoint set silently decides `pose-backend-selection`.
- Must contain the joints the palm and toe anchor rules need on **both** backends (Section 8.4).
- Must contain the two hip joints, because `mvp-contract.md` Section 6 defines hip trajectory as their midpoint.
- Left–right pairs are declared explicitly and are **subject-relative**, not image-relative.

### 7.2 `pose-backend-selection`

Both candidates are already listed **by name** in `docs/model-registry.md` Section 4. This brief
describes them by property, so that the ADR — not the brief — makes the selection.

| Axis | Candidate A: wholebody model behind a small ONNX-runtime wrapper library | Candidate B: self-contained landmark model |
| --- | --- | --- |
| Code license | Permissive, to be confirmed and recorded | Permissive, to be confirmed and recorded |
| Checkpoint license | **Different from the code license.** Trained on a cocktail of datasets; inherits the most restrictive of their terms. Decisive for any commercial use. | To be confirmed and recorded separately from the code license |
| Keypoint coverage | 133 points `[PLANNING]`, including 21 per hand and 3 per foot — a real hand and foot skeleton | 33 body landmarks `[PLANNING]`, **no hand skeleton** |
| Separate detector needed | **Yes.** A person detector runs first. That detector is a second model with its own weights, license and training data. | No |
| Apple Silicon | Runs; the hardware execution provider is available but is **not bit-reproducible across operating-system updates** | Official Apple-Silicon wheels |
| CPU | **Deterministic on the CPU execution provider.** Pin the CPU provider and record it in provenance. | Runs |
| Install footprint | Wrapper plus runtime, plus two checkpoints `[PLANNING]` | Single package plus one bundle `[PLANNING]` |
| Determinism | Deterministic on the pinned CPU provider; **the hardware provider is not** | To be measured by the two-run byte-identity test |
| Disqualifying property | — | Emits a **metric 3D output**. It is attractive and it is **banned**: 3D is out of scope (`mvp-contract.md` Sections 2 and 11). A grep test enforces this. |

**Deciding evidence.** Paired endpoint accuracy on the **same** gold frames, compared with a
**paired test on the per-keypoint agreement and disagreement counts** — the count of frames where
A hits and B misses against the count where B hits and A misses. **Never two independently pooled
numbers.** Two pooled proportions with overlapping intervals say nothing; the paired counts are
what the gold set can actually support, because both backends see identical frames.

**The honest outcome is very likely "not separable."** A true gap below roughly three percentage
points `[PLANNING]` is not resolvable on a gold set this size (Section 11.3). When the paired test
does not separate them, the ADR **says so**, and the tiebreak is stated and recorded in this
order:

1. **License** — the checkpoint license, not the code license.
2. **Footprint** — install size and the number of checkpoints to fetch and verify.
3. **Determinism** — byte-identical output across two runs on a pinned execution provider.

A tiebreak recorded as a tiebreak is honest. A tiebreak dressed up as an accuracy win is not.

### 7.3 `dense-trajectory-storage-format`

`docs/data-schema.md` Section 6 has already been amended: **canonical JSON with parallel integer
arrays following the `FrameIndex` pattern, columnar format deferred.** The ADR records the sizing
that justifies it:

| Quantity | Value | Tag |
| --- | --- | --- |
| Pose series per attempt | On the order of one megabyte | `[PLANNING]` |
| Whole dataset | A few tens of megabytes | `[PLANNING]` |
| Version-controlled | **None of it.** `artifacts/` is git-ignored. | — |
| A float-native columnar dependency | Roughly 40 MB | `[PLANNING]`, from `data-schema.md` Section 6 |

Adding a large float-native dependency to solve a problem that does not exist is exactly the
speculative abstraction `AGENTS.md` Section 4 forbids. A columnar format is also float-native,
which collides with the no-float rule and would need its own decision about how integers survive
the round trip.

**The one sub-decision left open**, and the evidence that closes it: within canonical JSON, does
each observation carry `points` as a list of named point objects, or as three index-aligned
integer arrays (`x`, `y`, `score`) with the names living once in the keypoint set? Measure both
on **one real attempt** and record the two byte sizes in the ADR. With 133 keypoints at 30 fps,
the repeated name strings are the dominant term; if the measured difference is under a factor of
two, keep the named-object form for readability and say so.

## 8. Approach

### 8.1 Decode, and the join to the frame index

One pass. The decode module is the **only** place PyAV is imported.

- Pass the **same edit-list setting the ingest boundary passes** (`-ignore_editlist 0`, `data-schema.md` Section 9). Measurement on this repository's own CFR fixture showed the flag shifts every PTS by 1024 ticks. If the decoder and the prober disagree, every timestamp is offset by a constant and the join fails on the first frame.
- For every decoded frame, take its **presentation timestamp** and look it up in `FrameIndex.pts`. **Never enumerate decoded frames and use the loop counter as an index.** `decode_order_differs` is `true` on two of the five committed fixtures.
- A decoded timestamp **not present** in the frame index is a **hard failure** with a named error code (C6). Not a nearest match, not a tolerance window.
- A frame-index position **never visited** by the decoder is recorded as an `abstained` observation, **not dropped** (C7). The observation count therefore equals `FrameIndex.packet_count`, exactly, on every asset.

### 8.2 The backend adapter contract

The protocol in `pose/backend.py` is small and total:

- **Returns** the raw arrays as the backend produced them, plus the declared `score_type`, plus the detection count.
- **Raises** `ClimbVisionError` with a named SCREAMING_SNAKE code (C10) if the checkpoint is missing, the import fails, the checkpoint hash does not match, or the output shape is unexpected.
- **Never** returns zeros. **Never** returns a stub. **Never** falls back to a second backend, a cached result, or a synthetic prediction.

That is truth rule 14, and it gets its own test (Section 10.4). A fake prediction is
indistinguishable from a real one downstream, which is why the failure has to be loud.

Assert the **keypoint count against the pinned checkpoint at load.** The wrapper library returns
different counts depending on which model class is instantiated, and the index map in
`keypoints.py` is only valid for the pinned checkpoint. A wrong count is a hard failure, not a
truncation.

Hand the backend the **colour order it documents.** The ONNX wrapper follows the OpenCV
convention; the landmark package does not. Feeding the wrong order produces keypoints that look
plausible and are wrong, which is strictly worse than a crash.

### 8.3 Detection policy

The envelope allows exactly one climber (`mvp-contract.md` Section 1), but the detector does not
know that.

| Detections on a frame | Behaviour |
| --- | --- |
| 0 | `status = abstained`, `points` all-null, `detection_count = 0`. A record, not a gap. |
| 1 | Normal path |
| more than 1 | Apply a **declared** rule — largest bounding box, with a deterministic tie-break on box coordinates — and **record `detection_count`** so multi-person frames can be excluded as a slice later |

**Never silently pick.** The rule id goes in the config as `[FIXED]`, and the count goes on every
observation, because "how often did more than one person appear" is a question the gate has to be
able to answer.

### 8.4 Anchor derivation

Explicit, named, and stored with its rule id. One row per anchor, one column per backend:

| Anchor | Rule (proposed id) | Candidate A source keypoints | Candidate B source keypoints |
| --- | --- | --- | --- |
| Palm, left | `palm_centroid_v1` | Left wrist plus two named left-hand landmarks from the hand block | Left wrist plus the two named hand landmarks the 33-point set provides |
| Palm, right | `palm_centroid_v1` | Right wrist plus two named right-hand landmarks | Right wrist plus the two named hand landmarks |
| Toe, left | `toe_centroid_v1` | The named left-foot landmarks | The named left-foot landmarks |
| Toe, right | `toe_centroid_v1` | The named right-foot landmarks | The named right-foot landmarks |

The exact source keypoint names come from `canonical-keypoint-set` and are written into
`configs/pose/v1.json` and into `AnchorObservation.source_keypoint_names` on **every** record.

The centroid is an integer floor-division centroid over the source points (Section 10.1 pins the
convention with hand-calculated values).

**If any source keypoint is absent, or its score is below the score floor, the anchor is
`abstained` with a null point.** Never a partial centroid over whatever happened to be present: a
two-point centroid and a three-point centroid are different quantities, and a record that silently
switches between them is a measurement of nothing. The `source_keypoint_names` list still records
all the rule's sources, so the reason is auditable.

### 8.5 Wall projection

Apply the Stage 3 homography to each anchor. Null the result **outside the fiducial hull** — an
extrapolated homography is not a measurement. Store **both** the `stabilized_px` value and the
`wall_plane` value; **neither replaces the other**, because the pixel value is the observation and
the wall value is a derivation through a calibration that has its own error.

Wall-plane coordinates are not physical 3D body coordinates (truth rule 8).

### 8.6 The static-camera check

The envelope requires no pan, no zoom, no reframing (`mvp-contract.md` Section 1). Stage 1 could
not check this: it never decoded a pixel. Stage 4 can, because a numerical array library is now
present.

- Take a **fixed border region** of the frame — the outer band, away from where the climber is.
- Compute the **mean absolute difference** between the reference frame and a sample of frames, as an integer in milli-units of pixel intensity.
- Emit a **separate camera-motion document** with an `ok` / `fail` / `unknown` three-valued status, mirroring `QualityStatus`.

**It is not a member of the recording's quality flags.** Adding a flag to `QualityAssessment`
would change `recording.json` bytes that earlier `IngestRun` records already attest to by hash,
which is the `MANIFEST_CONFLICT` failure Stage 1 exists to prevent. The camera-motion document
points at the recording by hash, the way `IngestRun` already does.

### 8.7 Raw before filtered

Write the raw series first, hash it, then write any filtered series referencing the raw by hash
(C8, truth rule 4). At Stage 4 the filtered document may be identical in content to the raw one —
that is fine and it must still be two documents, because Stage 5 and Stage 6 will add smoothing
and the seam has to exist before it is needed, not after someone has already smoothed in place.

### 8.8 Every threshold, named

Into `configs/pose/v1.json` (C9). Each entry carries `value`, `unit`, `status` and `selection`.
A missing `value` is `CONFIG_THRESHOLD_MISSING`, never a default.

| Name (proposed) | Unit | Tag |
| --- | --- | --- |
| `backend_id` | identifier | `[FIXED]` |
| `pose_checkpoint_sha256` | sha256_hex | `[FIXED]` |
| `detector_checkpoint_sha256` | sha256_hex | `[FIXED]` |
| `execution_provider` | identifier | `[FIXED]` |
| `keypoint_set_id` | identifier | `[FIXED]` |
| `preprocessing_id` | identifier | `[FIXED]` |
| `palm_anchor_rule_id`, `toe_anchor_rule_id` | identifier | `[FIXED]` |
| `multi_detection_rule_id` | identifier | `[FIXED]` |
| `min_keypoint_score_milli` | thousandths of the declared score type | `[PILOT]` |
| `max_track_gap_frames` | count | `[PILOT]` |
| `endpoint_accuracy_threshold_ratio` | `{num, den}` fraction of the normalization scale | `[PILOT]` |
| `max_camera_motion_mad_milli` | thousandths of a pixel intensity level | `[PILOT]` |

Every `[PILOT]` entry's `selection` string reads
`"Not selected. [PILOT] placeholder; no validation data exists."` until a selection run is
recorded in `docs/status.md`.

## 9. Dependencies

### 9.1 The table

| Package | Why | License | Apple Silicon / CPU | Approximate footprint |
| --- | --- | --- | --- | --- |
| `av` (PyAV) | The decode boundary. `AGENTS.md` Section 4 already names FFmpeg/`ffprobe` or PyAV as the **only** permitted media boundary. | Package: permissive. **Its bundled media libraries carry their own licence terms**, which vary by build (LGPL and GPL builds both exist) and **must be recorded** in the run document beside the library version. | Wheels for both | Tens of MB `[PLANNING]` |
| `numpy` | Frame arrays out of the decoder, the backend input tensor, and the border-region mean absolute difference in the static-camera check | Permissive | Wheels for both | Tens of MB `[PLANNING]` |
| Wholebody wrapper + ONNX runtime | Optional group `pose-wholebody` | To be recorded per `model-registry.md` Section 1 | CPU provider deterministic; hardware provider **not bit-reproducible** | Hundreds of MB with checkpoints `[PLANNING]` |
| Self-contained landmark package | Optional group `pose-landmark` | To be recorded per `model-registry.md` Section 1 | Official Apple-Silicon wheels | Hundreds of MB with the bundle `[PLANNING]` |

`numpy` is currently in `BANNED`. Moving it out is an **authorized pin edit** under this brief
(`AGENTS.md` Section 6: "a stage brief that authorizes a new dependency says so explicitly").

**Everything else stays banned**, and the reviewer checks that the banned list did not shrink by
more than the four roots above: deep-learning frameworks, scientific-computing and dataframe
libraries, plotting, web frameworks, and network clients.

### 9.2 The path-scoped mechanism

A blanket unban would let a backend import leak into `schema/` or `ingest.py`. Introduce
`PATH_SCOPED_THIRD_PARTY` (proposed): a map from import root to the set of repository-relative
path prefixes under which that root may be imported.

| Import root | Permitted only under |
| --- | --- |
| `av` | `climbvision/media/` |
| `numpy` | `climbvision/media/`, `climbvision/motion.py`, `climbvision/pose/` |
| The wholebody wrapper and ONNX runtime roots | `climbvision/pose/backends/` |
| The landmark package root | `climbvision/pose/backends/` |

The scope guard then asserts, as three separate named tests:

1. Every import root under `src/` is stdlib, first-party, in `ALLOWED_THIRD_PARTY`, or in `PATH_SCOPED_THIRD_PARTY` **and** the importing file sits under one of that root's permitted prefixes.
2. `ALLOWED_THIRD_PARTY & BANNED == set()` **and** `set(PATH_SCOPED_THIRD_PARTY) & BANNED == set()`. The allowlist and the banned list never intersect.
3. Every root in `PATH_SCOPED_THIRD_PARTY` is actually imported by at least one file, so a stale permission cannot silently widen the surface.

Clause 1 is what replaces the protection lost by removing those roots from `BANNED`. It must be
tested in **both** directions: permitted inside, refused outside.

### 9.3 The default test run stays hermetic

Register a `model` marker in `[tool.pytest.ini_options]` and **deselect it by default**
(`addopts = "-q -m 'not model'"`). The default run must import **no backend** and download
**nothing** (truth rule 13). Sockets are already blocked by the autouse `block_network` fixture in
`tests/conftest.py`.

**`AGENTS.md` Section 9 says no skipped test counts as a pass.** A marker deselection is not a
skip — the test never enters the session. Both facts must be reported: the default run's
pass count, **and** the separate `-m model` run's pass count with the hardware and checkpoint
hashes it ran against. A deselected test whose result is never reported is a test that does not
exist.

## 10. Tests

Hand-calculated fixtures with exact expected values. Numbers inside a fixture are **arithmetic,
not thresholds**, and are untagged. **A gate number never comes from `tests/fixtures/`**
(`AGENTS.md` Section 11): fixtures prove the code runs; they do not measure accuracy.

### 10.1 Anchor centroid, floor-division convention pinned

Three named source points, `stabilized_px`, milli-units:

| Source point | `x_milli` | `y_milli` |
| --- | --- | --- |
| `p1` (wrist) | `1000` | `-1000` |
| `p2` (hand landmark 1) | `1200` | `-1010` |
| `p3` (hand landmark 2) | `1105` | `-992` |

Sums: `x = 3305`, `y = -3002`. Expected anchor:

```
x = 3305 // 3 = 1101      (3 * 1101 = 3303, remainder 2)
y = -3002 // 3 = -1001    (3 * -1001 = -3003 <= -3002 < -3000)
```

The test asserts exactly `(1101, -1001)` and therefore pins two conventions at once:

- **Floor, not round.** Rounding `x` gives `1102`.
- **Floor toward negative infinity, not truncation toward zero.** Truncating `y` gives `-1000`.

A negative stabilized-pixel coordinate is not a mistake in the fixture: a keypoint can be
predicted outside the image bounds, and the sign convention has to be pinned for exactly that case.

### 10.2 The same case with one source below the score floor

Identical points, but `p3.score_milli = 120` against a fixture score floor of `300`. Expected:

| Field | Expected |
| --- | --- |
| `status` | `abstained` |
| `point` | `null` |
| `source_keypoint_names` | all three names, unchanged |

The **wrong but tempting** answer the test must reject is the two-point centroid over `p1` and
`p2`: `(2200 // 2, -2010 // 2) = (1100, -1005)`. The test asserts the result is `null`, and
asserts it is not `(1100, -1005)`, so a partial centroid cannot pass by coincidence.

### 10.3 A frame with zero detections yields a record, not a gap

Decode a committed fixture, force `detection_count = 0` on one frame through the adapter seam, and
assert:

- `len(series.observations) == frame_index.packet_count` — exactly, no gaps (C7).
- The affected observation has `status = "abstained"`, all-null coordinates, all-null scores.
- No observation is missing and no observation is duplicated.

### 10.4 The rule-14 test

With the checkpoint file absent:

- Calling the adapter **raises** `ClimbVisionError` with the named code.
- The adapter **returns nothing under any input** — parametrize over an empty array, a wrong-dtype array, a wrong-shape array and a valid-shaped array, and assert `pytest.raises` in every case.
- Assert the raised code is the checkpoint-missing code specifically, not a generic one, so a future refactor that swallows and re-raises is caught.

This is the single most important test in the stage. A silent fallback is the failure mode that
produces a plausible-looking dataset of fabricated keypoints.

### 10.5 The pinned index map

- Loading with a keypoint count different from the pinned one **raises**. Parametrize over one-less and one-more.
- **Left–right pairs are subject-relative.** Mirror a synthetic keypoint array horizontally and assert that applying the declared pair map swaps left and right. A pair map that is image-relative passes a naive test and silently swaps the climber's hands.

### 10.6 Endpoint accuracy over a hand-authored three-frame gold set

Three frames, four anchors each, twelve endpoint samples. Adjudicated visibility and predicted
outcome per cell:

| Frame | Left hand | Right hand | Left foot | Right foot |
| --- | --- | --- | --- | --- |
| 1 | visible, hit | visible, hit | visible, hit | visible, **miss** |
| 2 | visible, hit | visible, **miss** | **occluded — excluded** | visible, hit |
| 3 | visible, hit | visible, hit | visible, hit | **out_of_frame — excluded** |

Counts computed by hand:

| Quantity | Value |
| --- | --- |
| Total endpoint samples | `12` |
| Excluded (occluded or out-of-frame) | `2` |
| Evaluated | `10` |
| Hits | `8` |
| Pooled endpoint accuracy | `RatioValue{num: 4, den: 5}` (8/10, reduced by gcd) |
| Hands slice | `6` evaluated, `5` hits → `RatioValue{num: 5, den: 6}` |
| Feet slice | `4` evaluated, `3` hits → `RatioValue{num: 3, den: 4}` |

The slices sum back to the pool: `6 + 4 = 10` evaluated and `5 + 3 = 8` hits. Assert that too —
a slicing bug that drops a sample is otherwise invisible.

**The hit predicate, in exact integers (C2).** With normalization scale `S` in milli-units and
threshold ratio `t/u`, a keypoint is a hit iff

```
(dx*dx + dy*dy) * u*u  <=  t*t * S*S
```

Boundary fixture, with `S = 100000` and `t/u = 1/20` as **fixture constants, not config values**:

| `dx` | `dy` | Left side | Right side | Expected |
| --- | --- | --- | --- | --- |
| `3000` | `4000` | `25000000 * 400 = 10000000000` | `1 * 10000000000` | **hit** — the boundary is inclusive |
| `3000` | `4001` | `25008001 * 400 = 10003200400` | `1 * 10000000000` | **miss** |

The `<=` is pinned by the first row. No square root is taken anywhere.

### 10.7 Grep test: no occlusion label from a score comparison

A deterministic grader over `src/climbvision/pose/` and `src/climbvision/motion.py`: assert that
the string tokens for the `occluded` and `out_of_frame` visibility values do not appear at all.
The only visibility value the pose package may name is the unlabelled one. This fails loudly the
moment someone writes `if score < floor: visibility = occluded`.

### 10.8 Grep test: no reference to the banned 3D output

Assert that no file under `src/` references the landmark candidate's metric-3D attribute names, or
the `body_local_3d` coordinate space. 3D is out of scope (`mvp-contract.md` Sections 2 and 11) and
the landmark candidate offers it in the same call as the 2D output, so it is one attribute access
away at all times.

### 10.9 Integration: decode a committed fixture and join

Using `tests/fixtures/video/cfr_320x240_30fps_1s.mp4` and
`tests/fixtures/video/vfr_160x120_2s.mp4`, both of which have `decode_order_differs = true`:

- Every decoded presentation timestamp is present in `FrameIndex.pts`.
- The set of visited frame-index positions equals `range(packet_count)` — **complete**, no holes.
- Re-running the decode produces the same visit order.

These fixtures are **160×120 and 320×240, far below the 1080p envelope.** They prove the join and
nothing else. They must never appear in a gate accuracy number.

### 10.10 Model-marked smoke test, deselected by default

Marked `model`. Asserts output **shape** against the pinned keypoint count, and **determinism**:
two runs on the same input, on the pinned execution provider, produce byte-identical
`dumps_canonical` output. Reported separately, with the checkpoint hashes and the hardware it ran
on.

## 11. Gate

### 11.1 Deterministic clauses — all must pass

| # | Clause |
| --- | --- |
| D1 | `uv run pytest` passes and `uv run ruff check .` is clean |
| D2 | Round-trip byte-identity for all new documents: `model == parse(dump(model))` **and** `dump(parse(dump(model))) == dump(model)` (`evaluation.md` Section 4.2) |
| D3 | Every decoded frame joins to a frame-index timestamp; the observation count **equals** `FrameIndex.packet_count`; no gaps |
| D4 | Raw keypoints are stored in a separate document, referenced by hash, **before** any filtering (C8) |
| D5 | **Both** models have complete seven-field registry entries in `docs/model-registry.md` |
| D6 | Both checkpoints are **verified by hash at load**, and a deliberately wrong checksum **refuses to run** — demonstrated, not asserted in prose |
| D7 | The adapter **raises** rather than fabricating when the checkpoint is absent (truth rule 14) |
| D8 | The default test run requires **no network** and downloads **nothing** |
| D9 | Two runs of the same backend on the same input produce **byte-identical** output |

### 11.2 `[PILOT]` clauses — measured and reported, not thresholded

| # | Clause | Reported as |
| --- | --- | --- |
| P1 | Pooled accuracy on the frozen test slice | An exact rational, with its interval, with the excluded occluded and out-of-frame **count reported alongside** |
| P2 | **Endpoint** accuracy on the frozen test slice | The same, and this is the one that matters (`evaluation.md` Section 1) |
| P3 | Track gaps: fraction of frames abstained | Exact rational, **separately for hands and for feet** |
| P4 | Track gaps: longest abstention run | Integer frame count and integer microseconds, **separately for hands and for feet** |

Pooled and endpoint numbers are **never** merged, and hands and feet are **never** pooled. Torso
and hip joints are easier and inflate a pooled number; contact detection depends on the ends of
the limbs.

### 11.3 The honest limitation, with the arithmetic shown

This is a `[PLANNING]` calculation about **what the dataset can support**. It is not a result and
it is not a prediction of the outcome.

| Step | Value | Tag |
| --- | --- | --- |
| Frozen test slice | roughly 40 frames | `[PLANNING]` |
| Anchors per frame | 4 | — |
| Endpoint samples | `40 × 4 = 160` | `[PLANNING]` |
| Remaining after occlusion and out-of-frame exclusion | perhaps 110 | `[PLANNING]` |
| 95% normal-approximation half-width at `p ≈ 0.85`: `1.96 × sqrt(0.85 × 0.15 / 110)` | `≈ 0.067`, i.e. **±6.7 percentage points** | `[PLANNING]` |
| The same at `p = 0.5`, the worst case | `1.96 × sqrt(0.25 / 110) ≈ 0.093`, i.e. **±9.3 percentage points** | `[PLANNING]` |

**What that buys.** Enough to detect a backend that is **badly wrong**. Not enough to certify one
that is **nearly right**. Not enough to separate two backends whose true gap is under about three
percentage points `[PLANNING]`.

**Two further honesty clauses, both of which make the interval above optimistic:**

- The 160 samples are **not independent**. They come from clustered frames within a small number
  of attempts, so the effective sample size is smaller than 110 and the true interval is wider
  than the normal approximation says.
- The paired comparison (Section 7.2) recovers some power, because both backends see identical
  frames and the disagreement counts are what is tested. It does **not** make the gold set bigger.

**Report the interval next to every number.** A proportion without its interval, on a sample this
size, is a claim the data does not support.

### 11.4 What this stage does not prove

- Nothing about a different climber, gym, camera placement or lighting condition (Section 0.5).
- Nothing about contact. Anchor proximity is not contact, and this stage never says it is.
- Nothing about 3D position, limb length, reach or center of mass.
- Nothing about the model's behaviour on the hardware execution provider, which is deliberately
  not pinned and not measured.

## 12. Verification commands

Repository-relative. Placeholders in angle brackets.

```
uv sync
uv run pytest
uv run ruff check .

uv sync --group pose-wholebody          # or --group pose-landmark, whichever the ADR selected
scripts/fetch_pose_weights.sh           # manual only; prints and verifies both checksums

uv run climbvision pose <video> --out artifacts
uv run climbvision validate \
  artifacts/recordings/<asset_id>/pose_series.raw.json \
  artifacts/recordings/<asset_id>/pose_series.json \
  artifacts/recordings/<asset_id>/anchor_series.json \
  artifacts/recordings/<asset_id>/camera_motion.json \
  artifacts/recordings/<asset_id>/runs/<run_id>.pose.json

uv run climbvision pose-eval --release <release_id> --split validation
uv run climbvision pose-eval --release <release_id> --split validation --backend <other_backend_id>

uv run pytest -m model                  # explicitly; deselected by default
```

Plus the offline check from `AGENTS.md` Section 9: run the suite in an environment where
`ffprobe` is **not** on `PATH` and no backend group is installed. The `ffprobe`- and
model-dependent tests skip or deselect; the unit suite still passes. Report both counts.

Byte-identity check for D9, run twice and compared:

```
uv run climbvision pose <video> --out artifacts_a
uv run climbvision pose <video> --out artifacts_b
diff artifacts_a/recordings/<asset_id>/pose_series.raw.json \
     artifacts_b/recordings/<asset_id>/pose_series.raw.json
```

## 13. Traps

Fourteen. Each has already cost someone a day somewhere.

| # | Trap | Consequence if missed |
| --- | --- | --- |
| 1 | **Decode-order timestamps.** Enumerating decoded frames and using the loop counter as an index into the presentation-sorted frame index. | The **whole trajectory misaligns** by the reorder distance. Two of the five committed fixtures reorder. The result looks like a plausible trajectory of the wrong frames. |
| 2 | **Edit lists.** The decoder and the prober must pass the same `-ignore_editlist` setting. | Every timestamp is offset by a **constant** — 1024 ticks, measured on this repository's CFR fixture — and the join fails on the first frame. If someone then adds a tolerance, it fails silently instead. |
| 3 | **Colour order.** The ONNX wrapper follows the OpenCV convention; the landmark package does not. | Keypoints that **look plausible and are wrong.** Strictly worse than a crash, because nothing alerts you. |
| 4 | **Wholebody index ordering.** The two hand blocks are **adjacent** in the 133-point layout, and left/right are **subject-relative**. | An off-by-one-block error gives you the **wrong hand** for every frame. A mirrored preprocessing step silently swaps left and right, and the endpoint accuracy stays high because both hands are usually near each other. |
| 5 | **The wrapper returns different keypoint counts per model class.** | The index map is valid only for the pinned checkpoint. A different class silently reinterprets every index. Assert the count at load. |
| 6 | **The forgotten second model.** The person detector is a separate model with separate weights, license and training data. | Truth rule 11 is violated the moment the pipeline runs, and the licence question is answered wrongly because only one licence was ever read. |
| 7 | **Normalised landmark coordinates.** The landmark candidate returns coordinates relative to the **input image**, after whatever letterbox or resize the adapter applied. | Unless the transform is inverted **exactly**, every keypoint is offset by the padding. The offset is constant, so it looks like a calibration problem and gets "fixed" in the wrong module. |
| 8 | **The banned metric 3D output.** It arrives in the same call as the 2D output and it is genuinely attractive. | It is out of scope permanently (`mvp-contract.md` Sections 2 and 11). Once it is in a document, some downstream stage will use it and the contract is broken retroactively. |
| 9 | **Score is not visibility.** | Thresholding a score into `occluded` converts a model artefact into a claim about the world and lets the model choose its own evaluation denominator. |
| 10 | **The non-reproducible hardware execution provider.** It is faster and it is the default on Apple Silicon. | It is **not bit-reproducible across operating-system updates.** D9 passes today and fails after an OS upgrade, with no code change to blame. Pin the CPU provider and record it in provenance. |
| 11 | **Preprocessing inside the adapter.** Two imaging libraries resize with different interpolation kernels. | If the resize lives inside the adapter, the recorded `preprocessing_id` is a **lie**, and the two backends are compared on differently-resized pixels. Move the resize outside and give it its own id. |
| 12 | **A missing frame is never a zero keypoint.** | Emitting the origin puts a point in the **corner of the image**, which Stage 5 will later find is nearest to whatever hold sits in that corner and report as a contact. Abstain with a null (C7). |
| 13 | **The committed fixtures are below the envelope.** 160×120 and 320×240 against a 1080p `[FIXED]` envelope. | They prove the join and the plumbing. A gate accuracy number computed on them is meaningless and forbidden (`AGENTS.md` Section 11). |
| 14 | **Editing the wrong pin.** Adding Stage 4 modules to `STAGE_ONE_MODULES` to make the guard pass. | The per-stage sets **are** the decision record of which stage introduced which module. Merging them destroys it. Add a new set; never edit a pin to make your own change pass (`AGENTS.md` Section 6). |

## 14. Report format and stop condition

As Section 0.6, with these stage-specific requirements:

- The gate table has **one row per clause** from Sections 11.1 and 11.2 — nine deterministic, four `[PILOT]` — using the clause ids `D1`–`D9` and `P1`–`P4`. A clause whose data does not exist reads **`pending measurement`**, and the report says so rather than substituting synthetic data.
- Every `[PILOT]` number is reported **with its interval** (Section 11.3) and with the excluded occluded and out-of-frame count beside it.
- The default run's pass count **and** the `-m model` run's pass count are both reported, with the checkpoint hashes and the hardware.
- The two model registry entries are reproduced in the report, all seven fields each, so the reviewer can check them without opening another file.
- The `pose-backend-selection` record states whether the paired test **separated** the candidates. If it did not, the record says **"not separable"** and names the tiebreak actually used.
- The `time_base`-placement decision from Section 5.2 is named explicitly, whichever way it went.

The reviewer independently re-measures every clause rather than accepting the implementer's
numbers: re-runs the commands, re-computes the accuracy from the emitted documents, and
independently verifies that the adapter raises with the checkpoint absent.

Then **stop** and wait for the owner's decision. Do not open Stage 5.

## 15. Read-first list

In this order, before writing anything.

| File | Read for |
| --- | --- |
| `AGENTS.md` | The binding rules. Sections 2, 3, 4, 5, 6, 7, 9 and 11 in full. |
| `docs/mvp-contract.md` | Sections 1 (envelope), 2 (out of scope, the 3D ban), 4 (coordinate spaces), 5 (visibility ontology), 6 (hip trajectory), 7 (privacy), 9 (the Stage 4 gate row), 10 (provenance classes) |
| `docs/data-schema.md` | Sections 1 (which entities are due at Stage 4), 4 (versioning), 5 (provenance fields), 6 (dense trajectory storage), 7 (serialization), 9 (the ingest media protocol, especially decode order and edit lists) |
| `docs/evaluation.md` | Section 1 "Stage 4 — pose" (PCK, endpoint PCK, the exclusion rule), Section 2 (split and leakage policy), Section 3 (how results are checked), Section 4.2 (the round-trip clause) |
| `docs/model-registry.md` | Sections 1 (the seven fields), 2 (policy, no silent fallback), 3 (currently "Zero models"), 4 (the candidates by name and the conditions attached to them) |
| `docs/status.md` | The ledger shape and the Stage 1 measured-evidence table you are copying |
| `docs/annotation-guide.md` | Section 2 (`occluded` vs `out_of_frame` vs `unlabeled`) |
| `docs/agents/briefs/stage-2-annotation-harness.md`, `stage-3-wall-and-holds.md` | What the gold set, the release manifest and the calibration actually look like |
| `src/climbvision/quality.py` | The integer cross-multiplication pattern (C2) and the config-threshold accessor that raises `CONFIG_THRESHOLD_MISSING` |
| `src/climbvision/serialization.py` | `dumps_canonical` is the **only** `json.dumps` in the codebase |
| `src/climbvision/timebase.py` | `parse_rational`, `pts_to_us`, `us_to_pts` — integer arithmetic only |
| `src/climbvision/media/ffprobe.py`, `src/climbvision/media/normalize.py` | The existing media boundary, and why `normalize.py` is pure |
| `src/climbvision/schema/provenance.py` | `IngestRun`, the model C5 says to copy exactly |
| `src/climbvision/schema/frame_index.py` | The parallel-integer-array pattern the pose series follows |
| `src/climbvision/schema/versions.py`, `src/climbvision/schema/__init__.py` | The three registration points |
| `src/climbvision/cli.py` | Subcommand shape, exit codes, and `schema_id`-based dispatch |
| `tests/unit/test_scope_guard.py` | The four guards you are about to extend. Read the comment on `test_the_stage_one_module_inventory_is_pinned` before touching the set. |
| `tests/unit/test_schema.py` | `DOCUMENT_MODELS`, `ALL_MODELS`, and the float-annotation walker |
| `tests/conftest.py` | `block_network`, `has_ffprobe`, the fixture paths |
| `configs/ingest/v1.json` | The exact config shape C9 says to copy |
| `scripts/regenerate_fixtures.sh` | Why it is manual-only, and how document fixtures are regenerated from a live run |
| `.gitignore` | Path-scoped, not extension-scoped, and why |
