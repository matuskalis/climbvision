# Stage 2 brief: annotation and evaluation harness

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

Build the machinery that turns human annotation into internal documents, freezes group-aware
splits, tests for leakage, and computes every metric Stages 3 through 7 will report, with **each
metric verified against a hand-calculated fixture**.

This stage consumes the `Recording` and `FrameIndex` documents produced by `climbvision ingest`,
joined on `asset_id` and `frame_index_sha256`. It **produces no predictions and no models.** No
pose, no hold detection, no segmentation, no inference of any kind. Every label in every document
this stage writes was placed by a human or derived deterministically from one that was.

## 1.1 The work splits into three commits, each with its own reviewer pass

| Commit | Scope | Needs footage | Startable |
| --- | --- | --- | --- |
| **2a** | The ontology enums, the shared value objects, the geometry primitives, and the **entire metric library with its hand-calculated fixtures** | No. Hermetic. | Today |
| **2b** | The CVAT task export, the CVAT XML import adapters, the annotation documents, and the correction event | Only for the live smoke test | After the `annotation-tooling-deployment` decision |
| **2c** | Splits, leakage tests, the dataset release, and the agreement measurement | **Yes** | After filming and annotation |

Run the reviewer after each commit. Do not begin 2b before 2a is approved, and do not begin 2c
before 2b is approved. 2a is deliberately first and deliberately hermetic: the metric library is
the part of this stage that everything from Stage 3 onward depends on, and it can be proven
completely correct against arithmetic before a single frame of footage exists.

**Task 1 precedes 2a.** See Section 8.1. It is a four-line change that must land before any real
footage is ingested.

---

## 2. Preconditions

## 2.1 What exists today

| Fact | Value |
| --- | --- |
| Stage 0 | Complete. Seven documents frozen. |
| Stage 1 | Complete, reviewed, gate measured. |
| Test suite | `uv run pytest` reports 423 passed |
| Hermetic suite (`ffprobe` absent, sockets blocked) | 372 passed, 51 skipped |
| Lint | `uv run ruff check .` clean, config in `pyproject.toml` (line length 100; rules `E`, `F`, `I`, `N`, `UP`, `B`, `SIM`; target `py311`) |
| Runtime dependencies | Exactly `pydantic>=2.7,<3` |
| Dev dependencies | `pytest>=8,<9`, `ruff>=0.6,<1.0` |
| Models | Zero |
| CLI subcommands | `climbvision ingest`, `climbvision validate` |
| External tools on this machine | `ffprobe` 8.0 and `ffmpeg` 8.0 (recorded in `tests/fixtures/probe/capture_metadata.json`, platform Darwin-arm64) |
| Source modules | 18, pinned in `STAGE_ONE_MODULES` in `tests/unit/test_scope_guard.py` |
| Document models | `Recording` (schema version 3), `FrameIndex` (2), `IngestRun` (1) |
| Committed video fixtures | 5, synthetic `lavfi` patterns, all below the 1080p envelope, total well under 100 KB |

The five video fixtures and their observed facts are tabulated in `tests/fixtures/README.md`.
Two of them (`cfr_320x240_30fps_1s.mp4`, `vfr_160x120_2s.mp4`) report `decode_order_differs: true`;
`raw_160x120_1s.h264` carries **no PTS at all** and is the absent-timestamp abstention fixture.

## 2.2 What does not exist

No annotations. No split manifests. No dataset releases. No `docs/adr/` directory. No `data/`
directory contents. No `configs/` file other than `configs/ingest/v1.json`. No `geometry/`,
`evaluation/`, `annotation/` or `dataset/` package. No metric implementation of any kind.

## 2.3 What blocks what

- **2a blocks on nothing.** Start it the day this brief is pasted.
- **2b blocks on** the `annotation-tooling-deployment` decision (Section 3.2).
- **2c blocks on** real footage having been shot, ingested with `climbvision ingest`, and
  annotated (Section 3.3), and on the `single-participant-split-policy` decision.
- **All of it blocks on Task 1** (Section 8.1), because a resolution flag computed with the
  current comparison would have to be corrected later, and a corrected manifest collides with
  `MANIFEST_CONFLICT` against the run records already attesting to the stored bytes.

---

## 3. Human inputs required before the agent starts

## 3.1 For commit 2a

**None.** 2a needs no footage, no decision and no owner input. Begin immediately.

## 3.2 For commit 2b: the `annotation-tooling-deployment` decision

The owner picks one and the agent records it as `docs/adr/annotation-tooling-deployment.md`
before writing any adapter code.

| Option | Setup cost | Where the footage goes | Consequence for this repository |
| --- | --- | --- | --- |
| **Self-hosted CVAT via docker compose** (**recommended**) | Roughly 4 GB of container images; Postgres and Redis containers; 30 to 60 minutes of first-time setup `[PLANNING]` | **Never leaves the machine** | One adapter, matching `docs/data-schema.md` Section 8 and `docs/annotation-guide.md` Section 7 |
| **Cloud CVAT** | Zero setup | **Uploads video of the owner's face to a third party.** This is a consent decision under `mvp-contract.md` Section 7, not a convenience choice. | Same adapter, but the privacy boundary moves and the decision record must say so |
| **Label Studio** | About 10 minutes, no Docker `[PLANNING]` | Never leaves the machine | **A different export format means a second adapter.** The contract names CVAT. |

The repository's "no Docker before Stage 8" rule (`AGENTS.md` Section 4) governs **the project's
own dependencies**: what ClimbVision requires to build, test and run. It does not govern what
tools happen to be installed on the annotator's laptop. Running CVAT in Docker on the side adds
nothing to `pyproject.toml`, adds no import, and adds no runtime requirement, so it does not
violate that rule. Say this out loud in the ADR so nobody re-litigates it in three weeks.

## 3.3 For commit 2c: filming, annotation, and the split policy

### Filming and annotation work list

| Item | Quantity | Notes | Estimate `[PLANNING]` |
| --- | --- | --- | --- |
| Attempts filmed | About 50, **with about 25 concentrated on a single problem** `[PLANNING]` | The concentration is what makes a per-transition failure rate measurable later; 50 attempts spread over 50 problems measures nothing twice | 3 to 4 h |
| Clean reference frame per wall facet | 1 each | Note the approximate time only; the agent converts it to an exact timestamp (Stage 3) | 0.25 h |
| Tape-measured distance per facet | 1 each, in **millimetres**, between two identifiable points | Without it the wall plane has no physical scale (Stage 3) | 0.25 h |
| Hold polygons | Every hold on each facet, each with a **stable human-assigned hold number** attribute | Traced once; a re-traced subset later feeds Stage 3's self-agreement IoU | 4 to 6 h |
| Contact tracks | **4 per attempt** (one per limb), with target, hold number, contact label and visibility attributes | Four tracks per attempt is not negotiable: a limb with no contact emits `none`, never a missing track (C7) | 10 to 14 h |
| Attempt spans and outcomes | 1 per attempt | Half-open, per `docs/annotation-guide.md` Sections 3 and 4 | 1 to 2 h |
| Gold keypoint frames | About 200 `[PLANNING]` | Image task, not a video task (Section 8.4) | 4 to 6 h |
| Blind re-annotation | 10 attempts `[PLANNING]`, **at least seven days later**, without sight of the first pass | This is the agreement measurement. Doing it the same evening measures short-term memory. | 2 to 3 h |

**Total: roughly 25 to 40 hours `[PLANNING]`.** That is at the upper edge of "days, not weeks".

### The reduction lever, and what it costs

Dropping to **30 attempts and 120 keypoint frames** saves roughly **twelve hours `[PLANNING]`**
and degrades these specific gates. The owner must see this list before cutting, not after:

| Cut | Gate it degrades |
| --- | --- |
| 50 to 30 attempts | The single-problem concentration falls from about 25 to about 15 attempts, which is the support behind Stage 7's transition failure hazard. Below the `[PILOT]` support threshold the aggregate returns `insufficient_data`, so the Stage 7 gate becomes unmeasurable rather than failing. |
| 50 to 30 attempts | Three-way splits get thin. With group-aware splitting on connected components, a 30-attempt release may produce a test split with too few groups to report a per-slice number, which forces pooled-only reporting and hides exactly the failing slices `docs/evaluation.md` Section 5 requires be reported. |
| 200 to 120 keypoint frames | Stage 4's endpoint PCK, the deciding metric for `pose-backend-selection`, is computed over palm and toe anchors only. Occlusion excludes a large fraction of those points from both numerator and denominator, so the eligible-point count, not the frame count, is the real support. 120 frames may not leave enough eligible endpoint samples to separate two candidate backends. |
| 10 to fewer re-annotated attempts | The Stage 2 `[PILOT]` gate itself. Self-agreement measured on fewer than 10 attempts is a number with no stability. |

### The `single-participant-split-policy` decision

The owner decides, and the agent records, whether this release declares `participant: none` or
`participant: accepted_single_participant` in its leakage block. `mvp-contract.md` Section 8 and
`docs/evaluation.md` Section 2 require one of exactly those two values, and the leakage test
**fails** if the release declares neither. With one climber the honest value is
`accepted_single_participant`, and every number measured on the release then carries the
within-climber caveat of Section 0.5.

### Two further inputs the owner must supply for 2c

- **Split names and proportions.** `configs/dataset/v1.json` cannot be written without them,
  because a threshold with no `value` is `CONFIG_THRESHOLD_MISSING`, not a default. This is an
  open decision in the `docs/agents/README.md` index; do not choose it yourself.
- **The keypoint name list** for the gold set. The canonical keypoint set is a Stage 4 decision in
  the same index. At Stage 2 the names are validated against a list declared in
  `configs/annotation/v1.json` so that a typo is caught, and the closed set is deferred.

Other open decisions in `docs/agents/README.md` also touch this stage. This brief does not
authorize the agent to decide any of them. Where one blocks progress, stop and ask.

---

## 4. Deliverables

## 4.1 New modules

All paths are under `src/climbvision/`. Every one of them must be added to a new
`STAGE_TWO_MODULES` set in `tests/unit/test_scope_guard.py`, kept **separate** from
`STAGE_ONE_MODULES`.

| Module | Commit | Responsibility, one line |
| --- | --- | --- |
| `schema/ontology.py` | 2a | The limb, contact target, contact label, visibility, outcome and provenance-class enums, plus `ONTOLOGY_ID` and `ONTOLOGY_VERSION` |
| `schema/common.py` | 2a | `RatioValue`, `TimeInterval`, `Point2D`, `CoordinateSpace` |
| `schema/metrics.py` | 2a | `MetricValue`, `MetricStatus`, and the `MetricReport` document |
| `geometry/__init__.py` | 2a | Package marker, empty |
| `geometry/polygons.py` | 2a | Shoelace doubled area, exact integer point-in-polygon, self-intersection check, scanline rasterisation |
| `evaluation/__init__.py` | 2a | Package marker, empty |
| `evaluation/intervals.py` | 2a | Temporal IoU, interval sweep, false-contact time |
| `evaluation/matching.py` | 2a | Greedy one-to-one event matching, F1, boundary-error distribution |
| `evaluation/masks.py` | 2a | Mask IoU by rasterisation, mask average precision over the sweep |
| `evaluation/keypoints.py` | 2a | PCK and endpoint PCK with exclusion accounting |
| `evaluation/sequences.py` | 2a | Normalised sequence edit distance |
| `evaluation/risk_coverage.py` | 2a | Risk-coverage curve over a measured ordering key |
| `evaluation/agreement.py` | 2a | Per-frame label agreement, interval-level agreement, per-pass unknown rate |
| `evaluation/report.py` | 2a | Assembles `MetricValue` lists into a `MetricReport` |
| `schema/annotation.py` | 2b | `AnnotationDocument` and the four annotation sibling models |
| `schema/participant.py` | 2b | `Participant`, `ConsentRecord` |
| `schema/correction.py` | 2b | `CorrectionEvent` |
| `schema/runs.py` | 2b | `HarnessRun`, the Stage 2 append-only run document (C5) |
| `media/ffmpeg.py` | 2b | **The ffmpeg subprocess boundary.** The second external media boundary after `media/ffprobe.py`. Nothing else in the codebase may invoke ffmpeg. |
| `annotation/__init__.py` | 2b | Package marker, empty |
| `annotation/task_export.py` | 2b | Builds the CVAT task media and the frame map |
| `annotation/cvat_video.py` | 2b | Reader and writer for the CVAT-for-video track dialect |
| `annotation/cvat_images.py` | 2b | Reader and writer for the CVAT-for-images shape dialect |
| `annotation/importer.py` | 2b | Resolves a CVAT export plus a frame map into internal documents |
| `annotation/adjudicate.py` | 2b | Merges two passes into adjudicated ground truth, retaining both |
| `schema/dataset.py` | 2c | `DatasetRelease` and its nested models |
| `dataset/__init__.py` | 2c | Package marker, empty |
| `dataset/split.py` | 2c | The deterministic group-aware split algorithm |
| `dataset/leakage.py` | 2c | The three leakage checks and the participant-clause check |
| `dataset/release.py` | 2c | Freezes and verifies a release |

## 4.2 New configuration

| File | Commit | Contents |
| --- | --- | --- |
| `configs/evaluation/v1.json` | 2a | `temporal_iou_reporting_levels`, `mask_ap_iou_sweep`, `pck_alpha`, `min_metric_support` |
| `configs/annotation/v1.json` | 2b | `max_unknown_annotation_fraction`, `self_agreement_interval_f1_target`, `self_agreement_label_target`, and the declared `keypoint_names` list (a declaration, not a threshold) |
| `configs/dataset/v1.json` | 2c | The split ratios |

Exact values, units and status tags are in Section 8.10.

## 4.3 New CLI subcommands

| Command | Commit | Does |
| --- | --- | --- |
| `climbvision task-export` | 2b | Builds the CVAT task media and frame map for one asset |
| `climbvision annotation-import` | 2b | CVAT export plus frame map to internal documents |
| `climbvision release` | 2c | Splits, checks leakage, freezes a `DatasetRelease` |
| `climbvision leakage` | 2c | Re-runs the leakage checks against an existing release manifest |
| `climbvision evaluate` | 2c | Computes a `MetricReport` from two document sets |

Exit codes follow `src/climbvision/cli.py`: **0** ok, **1** operation failed, **2** usage.

## 4.4 New scripts and fixtures

| Path | Purpose |
| --- | --- |
| `scripts/build_reannotation_task.sh` | Manual-only. Selects the ten attempts for the blind second pass deterministically and calls `climbvision task-export` for each. Carries a manual-only banner in the style of `scripts/regenerate_fixtures.sh`. |
| `tests/fixtures/cvat/` | Hand-authored CVAT XML validator inputs, documented as inputs and **not** as observations, exactly as `tests/fixtures/probe_invalid/` is |
| `tests/fixtures/documents/` | One golden document per new schema id, plus one per `AnnotationDocument` kind |

## 4.5 Existing files changed

This is the Section 0.3 seam checklist instantiated for Stage 2. Nothing else in the seven
contract documents may be edited.

| File | Change |
| --- | --- |
| `src/climbvision/quality.py` | Task 1, the portrait-orientation fix (Section 8.1) |
| `src/climbvision/errors.py` | No change. New codes are string literals raised through the existing `ClimbVisionError`; there is no code registry to update. |
| `src/climbvision/schema/versions.py` | Seven new schema id and version constants; extend `SCHEMA_IDS` |
| `src/climbvision/schema/__init__.py` | Seven new `MODEL_REGISTRY` entries; extend `__all__` |
| `src/climbvision/cli.py` | Five new subcommands |
| `tests/unit/test_schema.py` | New `DOCUMENT_MODELS` rows; every new nested model added to `ALL_MODELS` |
| `tests/unit/test_scope_guard.py` | `STAGE_TWO_MODULES`; union-based inventory test; the allowlist/banned disjointness assertion; the parsed dependency test |
| `tests/unit/test_cli.py` | Exit-code tests for the five subcommands; the `validate`-through-`MODEL_REGISTRY` test |
| `tests/unit/test_quality.py` | Task 1 regression tests |
| `tests/fixtures/README.md` | Document the new CVAT fixtures and their hand-authored status |
| `scripts/regenerate_fixtures.sh` | Extend for any newly generated fixture; keep the banner |
| `.gitignore` | Add `data/annotations/`; add the `!data/releases/` negation with its reason |
| `docs/status.md` | The Stage 2 row, the measured-evidence table, and **removal of the known-defect row** once Task 1 lands |
| `docs/adr/` | One file per decision actually made |

**Authorized contract edits: `docs/status.md` only.** `docs/mvp-contract.md`,
`docs/data-schema.md`, `docs/evaluation.md`, `docs/annotation-guide.md`,
`docs/model-registry.md` and `README.md` are **not** edited at Stage 2. The two amendments this
stage depends on are already in place: `mvp-contract.md` Section 9 and `annotation-guide.md`
Section 6 already state the self-agreement rule, and `data-schema.md` Section 1 already lists
`MetricValue` at Stage 2. If you believe another contract edit is necessary, **stop and ask**.

---

## 5. Entities

## 5.1 Which entities this stage puts in code

From `docs/data-schema.md` Section 1, every row marked "Stage introduced: 2":

| Entity | Status |
| --- | --- |
| `DatasetRelease` | On schedule at Stage 2 |
| `ConsentRecord` | On schedule at Stage 2. **Model only.** Instances live outside the repository (rule 12); the committed golden fixture is synthetic and pseudonymous. |
| `Participant` | On schedule at Stage 2. It is the split grouping key, which is why the model is needed here and the user-facing control is not until Stage 8. |
| `CorrectionEvent` | On schedule at Stage 2, because adjudication records corrections append-only |
| `MetricValue` | On schedule at Stage 2. Its "Stage introduced" column has just been amended from 7 to 2, because Stage 2's own gate is a measured agreement number and `MetricValue` is the output type of every evaluation from here on. |

Plus the four **annotation siblings**, which this brief introduces: `ContactAnnotation`,
`AttemptAnnotation`, `KeypointAnnotation`, `PolygonAnnotation`.

## 5.2 Why the annotation siblings are distinct entities

They are **not** early versions of `ContactEvent` and `Attempt`. Collapsing them would violate
truth rule 5.

| Reason | Detail |
| --- | --- |
| Different provenance | An annotation carries `reviewed_annotation` or `adjudicated_ground_truth`. `ContactEvent` and `Attempt` carry `derived`, computed from pose and contact inference. A reviewed annotation that happens to agree with a later derivation is still a reviewed annotation. |
| Different stage, on schedule | `ContactEvent` arrives at Stage 5 and `Attempt` at Stage 6 (`data-schema.md` Section 1). Neither is late; they are simply different things. |
| Different failure modes | An annotation can be `boundary_uncertain` because the annotator could not place a frame. A derived contact event cannot: it fails by abstaining. The fields are not the same fields. |
| Comparability requires separation | The Stage 5 gate compares derived `ContactEvent`s **against** adjudicated `ContactAnnotation`s. If they were one type, the comparison would be a type comparing to itself and the provenance of the reference would be unrecoverable. |

## 5.3 Field lists

Integers and rationals only. No float-typed field anywhere, including inside a `dict` value type
(`tests/unit/test_schema.py::test_no_field_is_typed_as_a_float` walks the annotation, not the
value). Every geometry value declares exactly one coordinate space. Every interval is half-open.
Unknown is an explicit `null`, never an omitted key.

All model names below are **proposals** except `DatasetRelease`, `ConsentRecord`, `Participant`,
`CorrectionEvent` and `MetricValue`, which are fixed by `docs/data-schema.md` Section 1.

### Value objects, `schema/common.py`

| Model | Fields |
| --- | --- |
| `RatioValue` | `num: int`; `den: int`. Validator: `den >= 1`, and `math.gcd(abs(num), den) == 1` so the pair is always reduced. Two equal ratios therefore serialize to the same bytes. |
| `CoordinateSpace` | Enum: `source_px`, `stabilized_px`, `wall_plane`, `body_local_3d`. Values and order verbatim from `mvp-contract.md` Section 4. |
| `Point2D` | `x_milli: int`; `y_milli: int`; `space: CoordinateSpace`. C3. |
| `TimeInterval` | `start_us: int`; `end_us: int`; `start_pts: int \| None`; `end_pts: int \| None`; `time_base: Timebase`; `start_observed: bool`; `end_observed: bool`. Half-open `[start_us, end_us)`. Validator: `end_us >= start_us`. A zero-length interval is empty and legal. `start_observed: false` means the contact or attempt began before the recording did; the boundary is **not** clamped silently (`annotation-guide.md` Section 3). |

`Timebase` already exists in `src/climbvision/schema/recording.py`. Import it; do not redefine it.

### Ontology, `schema/ontology.py`

| Enum | Members, in this exact order |
| --- | --- |
| `Limb` | `left_hand`, `right_hand`, `left_foot`, `right_foot` |
| `ContactTarget` | `hold`, `volume`, `wall_region`, `none`, `unknown` |
| `ContactLabel` | `intentional_use`, `incidental_touch`, `unknown` |
| `Visibility` | `visible`, `occluded`, `out_of_frame`, `unlabeled` |
| `Outcome` | `send`, `fall`, `controlled_drop`, `aborted`, `unknown` |
| `ProvenanceClass` | `prediction`, `preannotation`, `reviewed_annotation`, `adjudicated_ground_truth`, `derived` |

`ContactTarget`, `ContactLabel`, `Visibility` and `Outcome` are copied verbatim from
`mvp-contract.md` Section 5, in the contract's order. `ProvenanceClass` is verbatim from Section
10. `Limb` is new at Stage 2 and closed. `ONTOLOGY_ID = "climbvision.ontology"` and
`ONTOLOGY_VERSION = 1`.

**`ontology_version` is a plain `int` field on every document, never a `Literal`.** A later stage
will bump it, and a `Literal` would force every already-written document to be rewritten, which is
exactly the silent coercion `data-schema.md` Section 4 forbids.

### Annotation, `schema/annotation.py`

`AnnotationDocument` is **one** document model with a `kind` discriminator, rather than four
document models. Reason: four models would quadruple the seam surface (four schema ids, four
registry entries, four `DOCUMENT_MODELS` rows) to express one idea. The discriminator keeps each
document single-purpose and validated.

| Model | Fields |
| --- | --- |
| `AnnotationDocument` | `schema_id`; `schema_version`; `annotation_id: str`; `created_at_utc: str` (same pattern as `IngestRun.created_at_utc`); `ontology_version: int`; `provenance_class: ProvenanceClass`; `pass_id: str`; `annotator_id: str` (pseudonymous); `asset_id: str \| None` (null for a polygon document, which is bound to a reference image rather than a recording); `reference_image_sha256: str \| None`; `source_cvat_sha256: str \| None`; `frame_map_sha256: str \| None`; `kind: Literal["contacts","attempts","keypoints","polygons"]`; `contacts: list[ContactAnnotationInterval]`; `attempts: list[AttemptAnnotation]`; `keypoints: list[KeypointAnnotation]`; `polygons: list[PolygonAnnotation]`. Model validator: exactly the list named by `kind` may be non-empty, else `ANNOTATION_KIND_MISMATCH`. |
| `ContactAnnotationInterval` (the concrete model for the `ContactAnnotation` entity; one annotation is exactly one interval and the name says so) | `limb: Limb`; `target_kind: ContactTarget`; `target_ref: str \| None` (a hold id when `target_kind == hold`, else null); `contact_label: ContactLabel`; `visibility: Visibility`; `interval: TimeInterval`; `source_track_id: str \| None`; `boundary_uncertain: bool` |
| `AttemptAnnotation` | `attempt_index: int`; `interval: TimeInterval`; `outcome: Outcome`; `problem_version_id: str \| None` (null until Stage 3 exists); `boundary_uncertain: bool` |
| `KeypointAnnotation` | `keypoint_name: str`; `point: Point2D \| None` (null when the point is not locatable); `visibility: Visibility`; `frame_index_position: int`; `pts: int`; `time_base: Timebase`. C6 and C7: a gold frame with no decision emits a row with `visibility: unlabeled` and `point: null`, never no row. |
| `PolygonAnnotation` | `polygon_id: str`; `hold_number: int \| None`; `vertices: list[Point2D]` (space `stabilized_px`); `on_volume: bool`; `visibility: Visibility` |

### Participant and consent, `schema/participant.py`

| Model | Fields |
| --- | --- |
| `Participant` | `schema_id`; `schema_version`; `participant_id: str` (opaque pseudonym, pattern `^p[0-9a-z_-]{1,31}$`, never derived from a name, an email or a path); `consent_record_id: str \| None`; `created_at_utc: str` |
| `ConsentRecord` | `schema_id`; `schema_version`; `consent_record_id: str`; `participant_id: str`; `created_at_utc: str`; `scope: str`; `retention_until_utc: str \| None`; `withdrawn_at_utc: str \| None`. **No path field of any kind**, and no name, contact detail or free-text identifier. The retention semantics are an open decision in the `docs/agents/README.md` index; the model records the date and nothing more. |

### Correction, `schema/correction.py`

| Model | Fields |
| --- | --- |
| `CorrectionEvent` | `schema_id`; `schema_version`; `correction_id: str`; `created_at_utc: str`; `actor_id: str` (pseudonymous); `target_schema_id: str`; `target_document_sha256: str` (pattern `SHA256_HEX_PATTERN`); `field_path: str` (a JSON pointer); `previous_value_json: str`; `new_value_json: str`; `reason: str`; `provenance_class: ProvenanceClass` |

Values are carried as JSON **strings**, not as typed unions, so a correction to any field of any
document is representable without the correction model knowing that document's schema. The target
is referenced by hash and **is never mutated** (`annotation-guide.md` Section 6).

### Metrics, `schema/metrics.py`

| Model | Fields |
| --- | --- |
| `MetricStatus` | Enum: `measured`, `insufficient_data`, `not_applicable`, `abstained` |
| `MetricValue` | `metric_id: str`; `value: RatioValue \| None`; `unit: str`; `numerator: int \| None`; `denominator: int \| None`; `support: int`; `status: MetricStatus`; `slice: dict[str, str]`; `threshold_ref: str \| None`; `coordinate_space: CoordinateSpace \| None`; `excluded_count: int` |
| `MetricReport` | `schema_id`; `schema_version`; `report_id: str`; `created_at_utc: str`; `release_id: str`; `split_name: str`; `ontology_version: int`; `reference_document_sha256: list[str]`; `candidate_document_sha256: list[str]`; `metrics: list[MetricValue]` |

`value` is null whenever `status` is not `measured`. `numerator` and `denominator` are the raw
integer counts behind `value`, kept separately so a reader can pool or re-slice without the
rational hiding the support. `slice` names the slice a value was computed over, for example
`{"limb": "left_hand", "tiou": "3/10"}`; a pooled value carries an empty dict.

### Dataset, `schema/dataset.py`

| Model | Fields |
| --- | --- |
| `DatasetRelease` | `schema_id`; `schema_version`; `release_id: str`; `created_at_utc: str`; `ontology_version: int`; `split_algorithm_id: str`; `split_ratios: dict[str, RatioValue]`; `group_keys: list[str]`; `members: list[ReleaseMember]`; `annotation_files: list[AnnotationFileRef]`; `leakage: LeakageDeclaration`; `gold_frame_procedure_id: str`; `gold_frames: list[GoldFrameRef]` |
| `ReleaseMember` | `asset_id: str`; `participant_id: str`; `problem_version_id: str \| None`; `wall_set_id: str \| None`; `split_name: str`; `group_key: str` |
| `AnnotationFileRef` | `basename: str`; `sha256: str`; `schema_id: str`. **Basename only.** An absolute path can contain a person's name (`mvp-contract.md` Section 7). |
| `LeakageDeclaration` | `participant: Literal["none","accepted_single_participant"]`; `problem: Literal["none"]`; `asset: Literal["none"]` |
| `GoldFrameRef` | `asset_id: str`; `frame_index_position: int`; `pts: int`; `time_base: Timebase`. C6. |

### Run document, `schema/runs.py`

| Model | Fields |
| --- | --- |
| `HarnessRun` | `schema_id`; `schema_version`; `run_id: str`; `created_at_utc: str`; `command: Literal["task-export","annotation-import","release","leakage","evaluate"]`; `inputs: list[DocumentRef]`; `outputs: list[DocumentRef]`; `config_version: str`; `config_sha256: str`; `ontology_version: int`; `climbvision_version: str`; `python_version: str`; `git_commit: str \| None`; `git_dirty: bool \| None`; `external_tools: list[ExternalToolRef]` |
| `DocumentRef` | `basename: str`; `sha256: str`; `schema_id: str \| None` (null for a non-document input such as a CVAT XML export) |
| `ExternalToolRef` | `name: str`; `version: str`; `argv: list[str]`. Empty list for a pure command. |

`build_ingest_run` in `src/climbvision/provenance.py` already implements the git-state probe with
the correct abstention behaviour (an unavailable repository yields `null`, never a fabricated
clean flag). **Reuse it, do not reimplement it.** Factor the git probe into a shared helper if
needed, but do not change `build_ingest_run`'s output.

## 5.4 Artifact layout

Following the Stage 1 pattern and C5:

```
<out>/annotations/<asset_id>/<pass_id>/<kind>.json
<out>/annotations/<asset_id>/runs/<run_id>.json
<out>/annotations/<asset_id>/runs/<run_id>.cvat.raw.xml
<out>/releases/<release_id>/release.json
<out>/releases/<release_id>/runs/<run_id>.json
<out>/metrics/<release_id>/<report_id>.json
<out>/metrics/<release_id>/runs/<run_id>.json
```

The raw CVAT export is preserved verbatim beside the run that consumed it, **run-scoped** so a
second import cannot overwrite the first run's preserved bytes. That is C8 and it is the same
mistake Stage 1 already fixed once for raw ffprobe output (`data-schema.md` Section 2).

The frozen release additionally lives at `data/releases/<release_id>/release.json` and is
**committed**.

---

## 6. Decisions already frozen

Do not re-open any of these. Cite them; do not restate their content in code comments.

| Frozen decision | Where |
| --- | --- |
| Intervals are half-open `[start_us, end_us)`; a zero-length interval is empty | `mvp-contract.md` Section 3 |
| Time is never `frame_number / nominal_fps`; original integer PTS and the container `time_base` are preserved | `mvp-contract.md` Section 3 |
| Four closed ontology sets, with `unknown` always available | `mvp-contract.md` Section 5 |
| Occluded, unobserved or unknown data is never converted into a negative label | `mvp-contract.md` Section 5, standing rule 1 |
| A problem ID is scoped to a `WallSet` revision | `mvp-contract.md` Section 5, standing rule 2 |
| `intentional_use` vs `incidental_touch` is a **human** judgement with an explicit `unknown` escape, never a model output trusted unreviewed | `mvp-contract.md` Section 6; `annotation-guide.md` Section 1 |
| Five provenance classes, never collapsed | `mvp-contract.md` Section 10 |
| Splits are group-aware on participant **and** problem simultaneously | `mvp-contract.md` Section 8 |
| A single-participant release must explicitly declare `accepted_single_participant`, and the leakage test fails if it declares neither that nor `none` | `mvp-contract.md` Section 8; `evaluation.md` Section 2 |
| The test set is frozen and evaluated once; never tune on it | `mvp-contract.md` Section 8 |
| Leakage is tested by named tests, not assumed | `evaluation.md` Section 2 |
| With one annotator the measure is blind intra-annotator test-retest, reported as `self_agreement`, **never** as inter-annotator agreement | `mvp-contract.md` Section 9; `annotation-guide.md` Section 6 |
| Adjudication never silently overwrites; both passes are retained; `unknown` is a valid adjudication | `annotation-guide.md` Section 6 |
| CVAT is an import/export adapter, not the domain model; no CVAT concept leaks inward and no internal concept is dropped | `data-schema.md` Section 8; `annotation-guide.md` Section 7 |
| Masks are stored as COCO polygons; RLE is deferred because it needs a numerical array dependency | `data-schema.md` Section 6 |
| Canonical JSON, sorted keys, compact separators, binary-mode write, trailing newline, no float, explicit `null` | `data-schema.md` Section 7 |
| Temporal IoU is reported at `0.1`, `0.3` and `0.5` `[FIXED]` as a reporting convention | `evaluation.md` Section 1 |
| Occluded and out-of-frame keypoints are excluded from PCK's numerator **and** denominator, and the count is reported | `evaluation.md` Section 1 |
| Normalised sequence edit distance is reported separately for limb-aware and limb-agnostic forms and never pooled | `evaluation.md` Section 1 |
| Mask IoU and mask AP are `not_applicable` until a segmenter is adopted by explicit decision | `evaluation.md` Section 1 |
| Below the support threshold an aggregate returns `insufficient_data`, not a value with a disclaimer | `evaluation.md` Section 1 |
| Capability and regression checks are reported separately; regressions are held to a stricter bar | `evaluation.md` Section 3 |
| `MetricValue` is a Stage 2 entity | `data-schema.md` Section 1 |
| Conventions C1 through C10 | Section 0.2 of this brief |

---

## 7. Open decisions

| Slug | Blocks | What the owner must decide |
| --- | --- | --- |
| `annotation-tooling-deployment` | 2b | Which CVAT deployment, per the table in Section 3.2 |
| `annotation-storage-and-release-commit-policy` | 2c | Confirms the Section 0.4 table: annotation payloads under `data/annotations/` are ignored, the release manifest under `data/releases/` is committed, and the release references payloads by hash. The decision exists because the alternative (committing payloads) is defensible and must be refused deliberately rather than by omission. |
| `single-participant-split-policy` | 2c | `participant: none` or `participant: accepted_single_participant` in the release's leakage block |
| `agreement-measurement-design` | 2c | Which ten attempts are re-annotated, how blindness is enforced, the minimum gap (this brief assumes at least seven days), and whether a kappa is computed at all and under which marginal assumption |
| `pck-normalization-scale` | Nothing at Stage 2 | The normalisation scale procedure is a Stage 4 decision. At Stage 2 the PCK function takes the scale as an explicit per-sample argument in milli-units, so the metric is implementable and testable now. Until the decision is recorded, any PCK computed on real data reports `abstained`, not a number. |
| `hold-segmentation-model` | Nothing at Stage 2 | No segmenter is adopted. Mask IoU and mask AP are implemented and fixture-tested, and on real data they emit `not_applicable` with the reason. `not_applicable` is neither zero nor a failure: the accuracy of a model that does not exist is undefined, not bad. |

The agent decides none of these. Where one is needed and absent, stop and ask.

---

## 8. Approach

## 8.1 Task 1, before anything else: fix the portrait-orientation defect

`src/climbvision/quality.py::_resolution` currently reads:

```python
elif width >= min_width and height >= min_height:
```

with `min_width = 1920` `[FIXED]` and `min_height = 1080` `[FIXED]`. A portrait 1080x1920 file
whose rotation is **baked into the pixels** therefore reports a resolution `fail`, even though it
is genuinely 1080p. `configs/ingest/v1.json` documents the intent explicitly: the `min_height`
entry's `selection` reads "Paired with min_width so a 1080p recording in either orientation is
judged against the same envelope." The `and` prevents exactly that.

**The fix.** Compare the **larger** dimension against `min_width` and the **smaller** against
`min_height`. The `width is None or height is None` branch and the `UNKNOWN` status are unchanged.

**Why it is byte-safe.** All five committed fixtures are 320x240 or smaller, so all five already
report `fail` and continue to. Neither the `measurement` keys (`width`, `height`) nor the
`threshold` keys (`min_width`, `min_height`) change, and neither does the emitted `status`. Every
golden document under `tests/fixtures/documents/` stays byte-identical, and
`tests/integration/test_ingest.py` continues to pass without regenerating anything.

**Why it must land first.** Once real portrait footage is ingested with the current comparison, the
stored `recording.json` records `resolution_below_min: fail`. Fixing the comparison afterwards
changes the manifest bytes for the same video bytes, and
`src/climbvision/ingest.py::_refuse_conflicting_manifest` then raises `MANIFEST_CONFLICT`, because
earlier run records attest to the stored bytes by hash. The workaround currently recorded in
`docs/status.md` ("film in landscape") is removed by this fix, and that row of the known-defects
table is deleted in the same change.

**Tests to add** in `tests/unit/test_quality.py`: a 1920x1080 landscape input reports `ok`; a
1080x1920 portrait input reports `ok`; a 1920x1079 input reports `fail`; a 1079x1920 input reports
`fail`; a 1920x1920 input reports `ok`; a `None` width still reports `unknown`. Assert the
`measurement` dict still carries the raw `width` and `height` in source order, unswapped, because
the flag records what the container declared, not a normalised view of it.

## 8.2 Ontology, value objects and geometry primitives (2a)

Write `schema/ontology.py` and `schema/common.py` exactly as specified in Section 5.3.

**One high-value test.** Parse `docs/mvp-contract.md` Section 5 for the four ontology tables and
assert that each enum's member values, **in order**, equal the contract's rows. This is a
deterministic grader that makes ontology drift a test failure rather than a discovery three stages
later. Parse the markdown tables with `re`; do not add a markdown dependency.

`geometry/polygons.py` exposes four functions, all exact integer arithmetic:

| Function | Definition |
| --- | --- |
| Doubled signed area | Shoelace: `sum(x_i * y_{i+1} - x_{i+1} * y_i)` over the closed ring. Doubled so it is always an integer. Sign gives orientation; do not normalise it away, because orientation is information. |
| Point in polygon | Exact integer even-odd ray cast. Boundary handling is declared and tested, not left to chance: a point exactly on an edge counts as **inside**. |
| Self-intersection | All non-adjacent edge pairs, tested by exact integer orientation (`cross`) with the collinear-overlap case handled explicitly. Raise `POLYGON_SELF_INTERSECTING`. A polygon with fewer than three distinct vertices raises `POLYGON_DEGENERATE`. |
| Scanline rasterisation | Even-odd rule, **pixel-centre sampling**, in doubled integers. For pixel `(px, py)` at reference resolution, the sample point is `(2000*px + 1000, 2000*py + 1000)` in doubled milli-units, with every polygon vertex doubled. Nothing rounds anywhere, and the convention stays exact even if `COORDINATE_SCALE` were ever an odd multiple. |

## 8.3 The CVAT task export (2b), which is the load-bearing piece

A command takes an asset id and an optional span and produces two things: the media CVAT will
decode, and a **frame map** from CVAT frame index to source timestamp and frame-index position.

### Building the media

Invoke ffmpeg through `media/ffmpeg.py`, from the source file's own directory with a bare
basename, exactly as `media/ffprobe.py::_run` already does, so the argv recorded in the run
document contains no absolute path.

```
ffmpeg -hide_banner -loglevel error -nostdin \
       -ignore_editlist 0 -noautorotate \
       -i <basename> \
       -map 0:v:0 -an \
       -vf "<span filter><rotation filter>" \
       -fps_mode passthrough \
       -c:v libx264 -pix_fmt yuv420p -g 1 -x264-params keyint=1:scenecut=0 \
       <derived basename>
```

| Flag | Why it is there |
| --- | --- |
| `-ignore_editlist 0` | mp4 edit lists shift the PTS the demuxer reports. Stage 1 measured the shift on this repository's own CFR fixture at 1024 ticks. The export must see the same timestamps the frame index recorded, or the map is off by an edit list. |
| `-noautorotate` | Without it ffmpeg silently bakes the container rotation in and drops the side data, so the applied transform becomes unrecorded and unverifiable |
| `-map 0:v:0 -an` | Video stream 0 only. Dropping audio is deliberate: the annotator does not need bystander conversation, and audio presence is already a recorded fact in the manifest. |
| rotation filter | C4, applied **explicitly** so it is in the argv |
| `-fps_mode passthrough` | **No frame-rate conversion.** Any conversion changes the frame count and destroys the one-to-one map. |
| `-g 1 -x264-params keyint=1:scenecut=0` | All keyframes, so CVAT's seek lands on the frame it says it landed on |

The rotation filter chain for container rotation `R` (the clockwise rotation a player applies for
display) is `transpose=1` for 90, `transpose=1,transpose=1` for 180, `transpose=2` for 270, and no
filter for 0. **Pin this mapping with a test** against the committed `rot90_160x120_1s.mp4`
fixture, asserting the derived file's coded dimensions equal the C4-transformed source
dimensions. Do not trust the mapping because it looks right; the fixture exists precisely to
decide it. Any other rotation, or a null rotation, raises `ROTATION_UNSUPPORTED`.

The optional span is applied with `select='between(pts,<start_ticks>,<end_ticks>)'` on the
**integer PTS in stream ticks**, never with `-ss` or `-to`. `-ss` before the input seeks to the
nearest keyframe, which is approximate, and both options take seconds, which reintroduces float
time.

### Building the frame map

1. Probe the derived file with the existing `probe_packets`.
2. Sort its packets by PTS, exactly as `build_frame_index` does. Decode order differs from
   presentation order on two of the five committed fixtures, so this is not theoretical.
3. Sort the source `FrameIndex` entries by PTS (they already are) and take the slice covered by
   the span.
4. **Assert the two counts are equal.** If they differ, raise `FRAME_MAP_COUNT_MISMATCH` with both
   counts in the message. Do not trim, pad, or align by nearest timestamp.
5. Zip by position. CVAT numbers frames `0..N-1` in presentation order, so CVAT frame `i` is
   derived-file presentation position `i` is source frame-index position `i + offset`.
6. Emit one row per CVAT frame: `{cvat_frame, frame_index_position, pts, time_base}`.

The derived file's own PTS values are recorded but **never assumed equal** to the source's: the
muxer may rebase the first frame to zero, and the map is by position after an exact count
assertion, which is a total resolution rather than a best-effort match (C6).

Record in the `HarnessRun`: the ffmpeg argv, the ffmpeg version, the source file sha256 and the
derived file sha256, exactly as `IngestRun` records the ffprobe argv, version and raw-output
hashes.

## 8.4 Gold keypoints and hold polygons do not use a video task at all

For the 200 gold keypoint frames and for the hold polygons, extract the selected frames as **PNGs
named by their timestamp** and use a CVAT **image** task. The frame-number problem then disappears
by construction: the file name carries the timestamp, so the map is the name.

Name pattern: `<asset_id_short>_pts<PTS>_us<US>.png`, where `asset_id_short` is the first 12 hex
characters of the asset id. This is a content hash, not a path and not a person, so it is safe in
a filename. The importer parses the `name` attribute of each `<image>` element and resolves it
against the `FrameIndex`; a name that does not resolve to an existing `FrameIndex` entry raises
`FRAME_TIMESTAMP_UNRESOLVED`.

### Gold frame selection is deterministic and recorded

Never "the annotator picked some frames".

1. Candidates are all frame-index positions inside an annotated attempt.
2. Partition candidates into **stable-configuration frames** and **move frames** using the
   attempt's contact annotations: a frame whose set of (limb, target) pairs is unchanged from the
   previous frame is stable, otherwise it is in a move.
3. Within each partition, order candidates ascending by
   `sha256(f"{release_id}\x1f{asset_id}\x1f{attempt_index}\x1f{frame_index_position}")`.
4. Take the first `k/2` from each partition, **rejecting any candidate adjacent in
   `frame_index_position` to one already taken.** Consecutive frames are near-duplicates and
   inflate apparent support without adding information.
5. Store `gold_frame_procedure_id` and the resulting `gold_frames` list in the `DatasetRelease`.

## 8.5 The CVAT import adapters

Parse with `xml.etree.ElementTree` from the standard library.

**Before parsing**, scan the leading bytes of the file for `<!DOCTYPE` and raise
`CVAT_DOCTYPE_FORBIDDEN` if present. A document-type declaration is where entity-expansion attacks
live, and an annotation export has no legitimate use for one. Rejecting before parsing, not after,
is the point.

**Coordinates.** CVAT writes coordinates as decimal strings such as `"1234.56"`. Parse them with
`decimal.Decimal` (standard library, exact for decimal strings), multiply by `COORDINATE_SCALE`,
quantise with round-half-away-from-zero, and convert to `int`. **Never** `float(s) * 1000`: that
is a float in the ingest path of a no-float schema, and the error it introduces is invisible until
a byte-identity test fails on a different machine.

**Track semantics, CVAT for video.**

| CVAT construct | Internal meaning | Failure if wrong |
| --- | --- | --- |
| `outside="1"` on a shape at frame `f` | The **half-open end**: `end_us` is the timestamp of frame `f`, and frame `f` is **not** part of the interval | Off by one frame on every interval, in the same direction, which silently biases every boundary error and every temporal IoU |
| `occluded="1"` | Visibility `occluded`. **Never** a released contact, never `target_kind: none` | Converts an unobserved state into a negative label, which standing rule 1 forbids |
| `keyframe="0"` | An interpolated shape. The export must be requested keyframe-only; the importer raises `CVAT_INTERPOLATED_SHAPE` if it sees one | Track interpolation fills **every** frame, so importing interpolated shapes turns four annotated keyframes into thousands of fabricated observations |
| A track with no terminating `outside` shape | Raise `CVAT_TRACK_UNTERMINATED` unless the annotator explicitly marked the end unobserved | An unterminated track silently becomes an interval running to the end of the recording |
| `<attribute name="x"></attribute>` | Empty string. Raise `CVAT_ATTRIBUTE_EMPTY` | An empty string silently becoming `unknown` is a fabricated abstention: it looks like the annotator decided they could not tell, when in fact nobody looked |
| An attribute value outside its ontology set | Raise `CVAT_ATTRIBUTE_UNKNOWN_VALUE` | A value outside its set is a defect, not a new category (`AGENTS.md` Section 3) |

**The writer.** Each of `cvat_video.py` and `cvat_images.py` exposes both a reader and a writer for
its dialect. The writer exists so the round trip in `annotation-guide.md` Section 7 is testable:
internal document to CVAT XML to internal document must be byte-identical under
`dumps_canonical`. It is not a production export path and is not exposed on the CLI.

**Adjudication.** `annotation/adjudicate.py` takes two passes and emits a third document with
provenance `adjudicated_ground_truth`. Both input documents are retained on disk and referenced by
hash in the output's `HarnessRun`. Where the two passes disagree and the evidence does not decide
it, the adjudicated value is `unknown`; adjudication does not mean picking a winner
(`annotation-guide.md` Section 6).

## 8.6 The metric definitions

Each is stated precisely enough to implement without a judgement call. Every one returns a
`MetricValue`; none returns a bare number.

| Metric | Exact definition | Degenerate input |
| --- | --- | --- |
| **Temporal IoU** | Intersection over union of two half-open intervals, both in integer microseconds. `intersection = max(0, min(a_end,b_end) - max(a_start,b_start))`; `union = (a_end-a_start) + (b_end-b_start) - intersection`. Result is `RatioValue(intersection, union)` reduced by `gcd`. | `union == 0` yields `status: not_applicable`, `value: null`. Two empty intervals are not "perfectly matched". |
| **Event matching** | Restricted to the **same limb**. Two variants, **target-aware** (the target ref must also match) and **target-agnostic**, computed and reported **separately and never pooled**. Candidate pairs are sorted by descending temporal IoU with a deterministic tie-break on `(gt_start_us, gt_end_us, pred_start_us, pred_end_us)`; matching is **greedy one-to-one**; a pair is kept if its tIoU is **at or above** the threshold, compared by C2 cross-multiplication. | An abstained prediction is counted as a **false negative at full coverage** and is **also reported separately** as an abstention count, so the two readings never have to be reconstructed from each other. |
| **F1** | `RatioValue(2*tp, 2*tp + fp + fn)`, reduced. **Never** the harmonic mean of two floats. | `2*tp + fp + fn == 0` yields `insufficient_data`. |
| **Boundary error** | For every matched pair, two **signed integer microsecond** values: `pred_start - gt_start` and `pred_end - gt_end`. Reported as a **distribution**: nearest-rank integer quantiles plus minimum and maximum. **Never a mean alone**; a mean of a bimodal boundary error is a number describing no observation. | Nearest rank is fixed: for `n` sorted values and percentile `q`, `rank = ceil(q*n/100)`, 1-based. No interpolation, so the reported quantile is always an observed value. |
| **False-contact time** | Per limb. Total predicted contact duration with no adjudicated contact, computed by an **interval sweep over the union** of the predicted intervals. | Overlapping predicted intervals must not be double-counted; see the fixture in Section 10.2, which is chosen specifically to fail a naive per-interval implementation. |
| **Mask IoU** | Scanline rasterisation at the **reference resolution**, even-odd rule, pixel-centre sampling in doubled integers (Section 8.2). `RatioValue(intersection_pixels, union_pixels)`. | Empty union yields `not_applicable`. |
| **Mask AP** | Mean over the configured IoU threshold sweep of the per-threshold average precision, computed from a precision-recall curve ordered by a **measured** model score whose `score_type` is recorded. Reported **per wall set and pooled**: a model that works on one gym's hold colours and fails on another's is invisible in a pooled number. | No segmenter exists, so on real data this emits `not_applicable` with the reason. There is no score to order by, and inventing one is rule 1. |
| **PCK** | A hit when `distance <= alpha * normalization_scale`, written as an exact integer comparison on **squared** quantities: `d2 * alpha_den^2 <= alpha_num^2 * scale^2`, where `d2 = dx^2 + dy^2` in milli-units. **No square root anywhere.** The boundary is **inclusive**. Keypoints labelled `occluded`, `out_of_frame` or `unlabeled` are excluded from **both** numerator and denominator, and `excluded_count` reports how many. | **Endpoint PCK** is the identical computation restricted to the palm and toe anchors, reported separately. It is the one that matters: contact detection depends on the ends of the limbs, and torso and hip joints are easier and inflate a pooled PCK. |
| **Normalised sequence edit distance** | Levenshtein with unit insert, delete and substitute costs over **token strings**, normalised by the **reference** length: `RatioValue(distance, len(reference))`. Reported separately for the limb-aware and limb-agnostic forms. | An empty reference yields `insufficient_data`, never a division. **The value can exceed one**, and that is correct, not a bug to clamp: a prediction longer than the reference can require more edits than the reference has tokens. |
| **Risk-coverage** | Predictions sorted by a **measured ordering key** whose `score_type` is recorded, never by an invented confidence. At each retention fraction, `coverage = RatioValue(retained, total)` and `risk = RatioValue(errors_among_retained, retained)`. At full coverage, abstentions count as errors. | With no ordering key the curve is `abstained`, not a straight line. |
| **Agreement** | Three numbers, always reported together: per-frame label agreement (`RatioValue(frames_agreeing, frames_compared)`); interval-level agreement as event F1 at **each** configured tIoU threshold; and **each pass's own unknown rate**. | Reported as `self_agreement` when there is one annotator. **Do not compute a kappa** without stating the marginal assumption: most frames are "no contact", so a chance-corrected statistic on this distribution is dominated by the marginal and will read as either impressively high or catastrophically low depending on an assumption nobody wrote down. If a kappa is wanted, it is part of the `agreement-measurement-design` decision. |

## 8.7 The split algorithm

**Deterministic, with no random number generator anywhere.** Not a seeded RNG: no RNG. A seeded
shuffle is reproducible only for as long as nobody changes the Python version.

1. **Group key.** Build a bipartite graph whose nodes are problems and sessions (assets), with an
   edge joining a problem to every session in which it was attempted. Take **connected
   components**. A problem and every session containing it therefore always land in the same
   split, which is what makes the problem clause of `mvp-contract.md` Section 8 hold rather than
   usually hold. The recorded `group_key` is the component id, derived as
   `"g" + sha256(sorted component member ids joined by \x1f)[:16]`.
2. **Bucketing.** For each group, compute `sha256(f"{release_id}\x1f{group_key}")`, take the first
   16 hex digits as an integer, and assign to a split by cumulative ratio bounds using integer
   arithmetic only.
3. **Balancing.** A deterministic pass that moves **whole groups**: sort groups by
   `(-member_count, group_key)` and greedily assign each to the split furthest below its target
   member count, ties broken by the declared split order. Whole groups only; a balancing pass that
   splits a group is a leakage bug wearing a helpful hat.
4. **Record `split_algorithm_id`**, for example `"connected-components-hash-bucket-balance/v1"`.
   Changing the algorithm changes the id, so two releases built by different algorithms are never
   silently comparable.

## 8.8 Leakage and freezing

`dataset/leakage.py` implements four checks, all deterministic and none `[PILOT]`:

| Check | Assertion |
| --- | --- |
| Asset | No asset SHA-256 appears in more than one split |
| Problem | No problem id appears in more than one split |
| Participant | No participant id appears in more than one split, **unless** the release declares `participant: accepted_single_participant` |
| Declaration | The leakage block declares one of exactly `none` or `accepted_single_participant` for the participant key. Declaring neither **fails**, per `mvp-contract.md` Section 8. |

Freezing writes the release **once**, through `dumps_canonical`, and records its sha256 in
`docs/status.md`. A test asserts the committed manifest under `data/releases/` still hashes to the
recorded value, so an accidental re-split becomes a test failure rather than a quiet change of
what "the test set" means. Rewriting an existing release id raises `RELEASE_FROZEN`; new data
means a **new release id**, never a re-split.

## 8.9 Threshold table

Every number carries a status tag. Nothing is `[VAL]`; no validation data exists.

| Threshold | File | Value | Unit | Status | Selection text |
| --- | --- | --- | --- | --- | --- |
| `temporal_iou_reporting_levels` | `configs/evaluation/v1.json` | `[{"num":1,"den":10},{"num":3,"den":10},{"num":5,"den":10}]` | `ratio` | `[FIXED]` | Taken verbatim from `docs/evaluation.md` Section 1, which fixes the reporting levels at 0.1, 0.3 and 0.5. Reporting convention, not a tuned value. |
| `mask_ap_iou_sweep` | `configs/evaluation/v1.json` | Ten rationals, `50/100` to `95/100` in steps of `5/100` | `ratio` | `[FIXED]` | Reporting convention, not empirical. Fixed so AP numbers are comparable across runs; changing the sweep changes what every AP number means. Recorded as an ADR at Stage 2. |
| `pck_alpha` | `configs/evaluation/v1.json` | `{"num":1,"den":10}` | `ratio_of_normalization_scale` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` |
| `min_metric_support` | `configs/evaluation/v1.json` | Integer placeholder | `count` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` |
| `max_unknown_annotation_fraction` | `configs/annotation/v1.json` | `{num, den}` placeholder | `ratio` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` |
| `self_agreement_interval_f1_target` | `configs/annotation/v1.json` | `{num, den}` placeholder | `ratio` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` |
| `self_agreement_label_target` | `configs/annotation/v1.json` | `{num, den}` placeholder | `ratio` | `[PILOT]` | `Not selected. [PILOT] placeholder; no validation data exists.` |
| `split_ratio_<name>` | `configs/dataset/v1.json` | One `{num, den}` per split | `ratio` | `[FIXED]` once the owner chooses them | Cites the decision that fixed them. **Cannot be written before the owner supplies them** (Section 3.3). |

No gate clause in Section 11 depends on the value of any `[PILOT]` threshold. That is deliberate:
a placeholder must not be able to make a gate pass.

---

## 9. Dependencies

## **Zero new dependencies. Say this loudly, because it is a design result and not an oversight.**

`pyproject.toml` is unchanged. `ALLOWED_THIRD_PARTY` stays exactly `{"pydantic"}`. The whole
43-name `BANNED` list stays banned, including `numpy`, `cv2`, `torch`, `onnxruntime`, `mediapipe`,
`sklearn` and `requests`.

| Thing that looks like it needs a library | What it actually needs |
| --- | --- |
| CVAT XML | `xml.etree.ElementTree`, standard library |
| Decimal coordinate parsing | `decimal`, standard library |
| Rasterisation | Integer scanline arithmetic |
| Edit distance | Two integer rows |
| Convex hull, polygon area, point-in-polygon | Integer cross products |
| Ratios | `math.gcd` |
| TOML parsing in the dependency-pin test | `tomllib`, standard library since 3.11 |
| Hashing | `hashlib`, already used by `src/climbvision/hashing.py` |

**One new external tool at the boundary: `ffmpeg`.** Already installed (version 8.0 on this
machine). It is not a Python package, it is used only by the task export and the reference-frame
extraction, it lives behind `media/ffmpeg.py`, and its version and argv are recorded in the run
document **exactly as `ffprobe`'s already are**. Register it in `docs/model-registry.md` Section
3? **No**: that table is authorized for edit only where a brief says so, and Stage 2 does not edit
contract documents. Record the ffmpeg version in the `HarnessRun` and in the Stage 2 measured
evidence table in `docs/status.md`.

If `ffmpeg` is absent, raise `FFMPEG_NOT_FOUND` with an install hint, exactly as
`media/ffprobe.py::executable` raises `FFPROBE_NOT_FOUND`. Tests that need it **skip**, they do not
fail (rule 13).

---

## 10. Tests

## 10.1 The rule about metric fixtures

**A metric fixture without a hand-computed expectation is worthless.** It asserts that the
implementation agrees with itself. Every expected value below was computed by hand and is written
as an **exact integer pair**. Do not compute an expected value by running the implementation.

## 10.2 The hand-calculated fixtures, with their exact expected values

| # | Fixture | Input | Expected, exactly |
| --- | --- | --- | --- |
| 1 | Temporal IoU, overlapping | `A = [1_000_000, 2_000_000)`, `B = [1_500_000, 2_500_000)` | intersection `500_000`, union `1_500_000`, IoU `1/3`. **Matches at threshold `3/10`** (`1*10 = 10 >= 3*3 = 9`) and **fails at `5/10`** (`10 >= 15` is false). |
| 2 | Temporal IoU, touching half-open | `A = [0, 1_000_000)`, `B = [1_000_000, 2_000_000)` | intersection `0`, union `2_000_000`, IoU `0/1`, status `measured`. Touching is **exactly zero overlap**, not a near-match. |
| 3 | Temporal IoU, one microsecond | `A = [0, 1_000_001)`, `B = [1_000_000, 2_000_000)` | intersection `1`, union `2_000_000`, IoU `1/2_000_000`. Non-zero. |
| 4 | Temporal IoU, empty union | `A = [5, 5)`, `B = [5, 5)` | status `not_applicable`, value `null` |
| 5 | Event matching and F1 | Same limb. Ground truth `G1 = [1_000_000, 2_000_000)`, `G2 = [3_000_000, 4_000_000)`. Predictions `P1 = [950_000, 2_050_000)`, `P2 = [3_000_000, 3_200_000)`, `P3 = [6_000_000, 7_000_000)`. Threshold `5/10`. | `P1`/`G1` tIoU `= 1_000_000/1_100_000 = 10/11`, matched. `P2`/`G2` tIoU `= 200_000/1_000_000 = 1/5`, **below threshold**, unmatched. `P3` no overlap. Therefore **tp = 1, fp = 2, fn = 1**, and **F1 = 2*1/(2*1+2+1) = 2/5**. |
| 6 | Boundary error | The matched pair from fixture 5 | start error `950_000 - 1_000_000 = -50_000`; end error `2_050_000 - 2_000_000 = +50_000`. Sorted `[-50_000, +50_000]`; min `-50_000`, max `+50_000`; nearest-rank p50 = index `ceil(0.5*2) = 1` = `-50_000`; p90 = index `ceil(0.9*2) = 2` = `+50_000`. |
| 7 | False-contact time | Predicted `[0, 400)` and `[300, 700)`; adjudicated `[0, 200)` | Union of predictions `[0, 700)`; minus adjudicated `[0, 200)` gives `[200, 700)` = **`500` microseconds**. A naive per-interval implementation returns `200 + 400 = 600` and this fixture exists to fail it. |
| 8 | Mask IoU | Two 10-by-10 pixel squares, **offset by 5 along x only**: `A = [0,10) x [0,10)`, `B = [5,15) x [0,10)`, vertices in milli-units | 100 pixels each, intersection `50`, union `150`, IoU `50/150 = 1/3` |
| 9 | Concave polygon area | Vertices `(0,0) (4000,0) (4000,2000) (2000,2000) (2000,4000) (0,4000)` in milli-units | Shoelace doubled area `24_000_000` milli-units squared, that is an L-shape of area 12 square pixels. The rasteriser must cover **exactly 12 pixels**, which cross-checks the analytic area against the sampling convention. |
| 10 | Self-intersecting polygon | Bow-tie `(0,0) (4000,0) (0,4000) (4000,4000)` | Raises `POLYGON_SELF_INTERSECTING` |
| 11 | PCK | 5 keypoints; normalisation scale `200_000` milli-px; alpha `1/10`, so the threshold is `20_000` milli-px. Displacements: K1 `(0,0)`; K2 `(20_000,0)`; K3 `(0,3_000)`; K4 `(20_001,0)`; K5 adjudicated visibility `occluded`. | K5 excluded from **both** numerator and denominator. K2 is the **inclusive boundary** case: `400_000_000 * 100 = 40_000_000_000 <= 1 * 40_000_000_000`, a hit. K4 is the **one-unit-beyond** case: `20_001^2 * 100 = 40_004_000_100 > 40_000_000_000`, a miss. Result **`3/4`**, `excluded_count = 1`, `support = 4`. |
| 12 | Sequence edit distance | Reference `[attach(left_hand,H1), attach(right_hand,H2), release(left_hand,H1)]`; prediction `[attach(left_hand,H1), attach(right_hand,H3)]` | One substitution plus one deletion, distance `2`, reference length `3`, **`2/3`** |
| 13 | Edit distance above one | Reference `[a]`; prediction `[a, b, c]` | distance `2`, reference length `1`, value `2/1`. **Asserted as greater than one and not clamped.** |
| 14 | Edit distance, empty reference | Reference `[]` | status `insufficient_data`, value `null` |
| 15 | Risk-coverage | 5 predictions; errors on P2 and P4; abstentions on P4 and P5 | Retained `{P1,P2,P3}`, so **coverage `3/5`**; errors among retained `{P2}`, so **risk `1/3`**. At full coverage, coverage `5/5` and risk `2/5`. |
| 16 | Agreement | Two passes over 10 compared frames, agreeing on 8; pass A `unknown` on 1 frame, pass B `unknown` on 2 | per-frame agreement `8/10 = 4/5`; pass A unknown rate `1/10`; pass B unknown rate `2/10 = 1/5`. Reported as `self_agreement`. |

## 10.3 Adapter and pipeline tests

| Test | Assertion |
| --- | --- |
| CVAT `outside` mapping | A track whose shape at frame `f` carries `outside="1"` produces `end_us` equal to frame `f`'s timestamp, and frame `f` is **not** in the interval |
| CVAT occlusion | `occluded="1"` maps to `Visibility.occluded` and **never** to `target_kind: none` or to a released contact |
| Empty attribute | `<attribute name="contact_label"></attribute>` raises `CVAT_ATTRIBUTE_EMPTY` and does **not** become `unknown` |
| DOCTYPE | An XML file containing `<!DOCTYPE` raises `CVAT_DOCTYPE_FORBIDDEN` **before** any parse is attempted |
| Interpolated shape | `keyframe="0"` raises `CVAT_INTERPOLATED_SHAPE` |
| Decimal coordinates | `"1234.567"` becomes `1234567` milli-units exactly; `"1234.5675"` rounds half away from zero to `1235` (assert against `decimal`, not against a float) |
| Frame-count mismatch | A derived file with one packet fewer than the source span raises `FRAME_MAP_COUNT_MISMATCH`, reporting both counts |
| Round trip | Internal `AnnotationDocument` to CVAT XML to internal document is **byte-identical** under `dumps_canonical` |
| Split determinism | The same inputs produce a byte-identical `DatasetRelease` |
| Split permutation invariance | Shuffling the input member order produces a **byte-identical** release |
| Leakage, asset | An asset in two splits fails |
| Leakage, problem | A problem in two splits fails |
| Leakage, participant | A participant in two splits fails **unless** the release declares `accepted_single_participant` |
| Leakage, declaration | A release declaring neither `none` nor `accepted_single_participant` for the participant key **fails** |
| Frozen release | The committed manifest under `data/releases/` still hashes to the value recorded in `docs/status.md` |
| Re-freeze refusal | Writing an existing release id raises `RELEASE_FROZEN` |
| Adjudication | Both input passes remain on disk unchanged and are referenced by hash in the run |
| Correction immutability | Applying a `CorrectionEvent` leaves the target document's bytes unchanged |
| Ontology drift | Each enum equals the corresponding table in `docs/mvp-contract.md` Section 5, in order |
| C7 abstention rows | A gold frame with no annotator decision emits a row with `visibility: unlabeled` and `point: null`; the row is never omitted |
| Task export round trip | ffmpeg-gated integration test: export a task from a committed fixture, rebuild the frame map, and assert every CVAT frame resolves to the expected `FrameIndex` position and `pts` |
| Validate picks up new documents | `climbvision validate` accepts one golden fixture per new schema id, dispatching through `MODEL_REGISTRY` on the document's own `schema_id` |
| CLI exit codes | 0 on success, 1 on a `ClimbVisionError`, 2 on a usage error, for each of the five subcommands |
| Portrait fix | The six cases in Section 8.1 |
| Golden byte-identity after Task 1 | All five committed fixtures still produce byte-identical `recording.json` |

## 10.4 Fixture policy

New CVAT fixtures go under `tests/fixtures/cvat/` and are documented in
`tests/fixtures/README.md` as **hand-authored validator inputs, not observations**, exactly as the
malformed probe fixtures in `tests/fixtures/probe_invalid/` are. `scripts/regenerate_fixtures.sh`
does **not** touch them, and its closing message must say so, as it already does for
`probe_invalid/`.

A gate number comes from real annotated data and **never** from `tests/fixtures/`. Fixtures prove
the code runs; they do not measure accuracy.

---

## 11. Gate

## 11.1 Deterministic clauses, measurable without footage

All must pass. None is `[PILOT]`.

| # | Clause | Assertion |
| --- | --- | --- |
| D1 | Tests and lint | `uv run pytest` all pass and `uv run ruff check .` clean. **No skipped test counts as a pass**; report passed and skipped counts separately. |
| D2 | Round trip, equality | `model == parse(dump(model))` for every new document model |
| D3 | Round trip, byte identity | `dump(parse(dump(model))) == dump(model)` **byte-for-byte** for every new document model. Not redundant with D2: D2 alone passes when serialization is lossy in a way that normalizes back. |
| D4 | Metric fixtures | Every metric in `docs/evaluation.md` Section 1 has a hand-calculated fixture whose expected value is written as an exact integer pair and is reproduced exactly |
| D5 | No float, integer thresholds | No float-typed field on any new model (`ALL_MODELS` walker), no float in any emitted document (value walker), and every threshold comparison is integer cross-multiplication |
| D6 | CVAT round trip | Export then import preserves the internal record byte-for-byte |
| D7 | Frame map | The frame map is exact, or the import hard-fails. A count mismatch raises; it never aligns by nearest timestamp. |
| D8 | Leakage | The four leakage checks pass and are deterministic, not `[PILOT]` |
| D9 | Frozen release | The committed release manifest hashes to the value recorded in `docs/status.md` |
| D10 | Task 1 byte-safety | All five committed fixtures produce byte-identical golden documents after the portrait fix |

## 11.2 The `[PILOT]` clause

Annotation agreement on the contact ontology, measured on the blind second pass and reported as
**`self_agreement`**:

| Reported number | Form |
| --- | --- |
| Interval agreement | Event F1 at tIoU `3/10` and `5/10`, per limb and pooled |
| Label agreement | Per-frame label agreement per limb |
| Unknown rate | Each pass's own unknown rate, reported separately, never averaged |

The **target** is `[PILOT]`: it will be set on validation data and does not exist yet. The clause
is therefore "measured and reported", not "above X". Reporting a number and calling it a pass
against a target that does not exist would be the fabrication the whole project is built to
prevent.

## 11.3 Honest limitation, stated in the report and in `docs/status.md`

With one annotator this measures **intra-annotator test-retest consistency, not inter-annotator
agreement.** `mvp-contract.md` Section 9 and `annotation-guide.md` Section 6 have already been
amended to say so. Self-agreement measures the stability of one person's interpretation and is an
**upper bound on what a second annotator would achieve**; it says nothing about whether the
ontology is shareable.

The metric fixtures prove the **metrics are correctly implemented**. They prove **nothing about
pipeline accuracy**, because no pipeline exists yet: there is no pose model, no contact model and
no prediction of any kind at Stage 2.

Plus the honest sentence in Section 0.5, verbatim.

---

## 12. Verification commands

Runnable without reading any code. Repository-relative paths throughout.

```bash
# Environment
uv sync

# Full gate
uv run pytest
uv run ruff check .

# The hand-calculated metric subset, verbosely, so each expected value is visible
uv run pytest tests/unit/test_metrics_hand_calculated.py -v

# Hermetic run: ffprobe and ffmpeg off PATH. The media-gated tests must SKIP, not fail.
PATH="$(printf '%s' "$PATH" | tr ':' '\n' \
        | grep -v -F "$(dirname "$(command -v ffprobe)")" | paste -sd: -)" \
  uv run pytest

# 2b: build a CVAT task and its frame map for one ingested asset
uv run climbvision task-export \
  --asset sha256-<64hex> \
  --artifacts artifacts \
  --out artifacts/cvat_tasks

# 2b: import a CVAT export against that frame map
uv run climbvision annotation-import \
  --cvat artifacts/cvat_tasks/<task>/annotations.xml \
  --frame-map artifacts/cvat_tasks/<task>/frame_map.json \
  --pass pass-a \
  --out artifacts

# 2c: split, check leakage and freeze a release
uv run climbvision release \
  --annotations artifacts/annotations \
  --release-id rel-<yyyy-mm-dd> \
  --out data/releases

# 2c: re-run the leakage checks against the frozen manifest
uv run climbvision leakage data/releases/rel-<yyyy-mm-dd>/release.json

# 2c: the agreement measurement, pass A against pass B
uv run climbvision evaluate \
  --release data/releases/rel-<yyyy-mm-dd>/release.json \
  --reference artifacts/annotations/<asset_id>/pass-a \
  --candidate artifacts/annotations/<asset_id>/pass-b \
  --out artifacts/metrics

# Validate every emitted document through MODEL_REGISTRY
uv run climbvision validate \
  artifacts/annotations/<asset_id>/pass-a/contacts.json \
  artifacts/annotations/<asset_id>/pass-a/attempts.json \
  data/releases/rel-<yyyy-mm-dd>/release.json \
  artifacts/metrics/rel-<yyyy-mm-dd>/<report_id>.json

# The frozen-release hash, to be compared against docs/status.md by eye
shasum -a 256 data/releases/rel-<yyyy-mm-dd>/release.json
```

Expected exit codes: 0 for every command above on success; 1 for an operation failure; 2 for a
usage error. Stage 1 measured 423 passed for the full suite and 372 passed / 51 skipped hermetic;
report the new counts as measured, never as expected.

---

## 13. Traps

Each with the consequence spelled out, because the consequence is what makes an agent take it
seriously.

| # | Trap | Consequence if you get it wrong |
| --- | --- | --- |
| 1 | **CVAT frame numbers are not frame-index positions.** CVAT numbers what it decoded, from a file you built, in presentation order. | Every timestamp in every annotation is wrong by a constant, and nothing in the pipeline can detect it, because a plausible timestamp is indistinguishable from a correct one. |
| 2 | **The `outside` flag is the half-open end.** | Every interval shifts by one frame in the same direction. Temporal IoU degrades slightly, and **every boundary error is silently biased**, so the Stage 5 boundary distribution measures your adapter, not the model. |
| 3 | **Track interpolation on export fills every frame.** | Four annotated keyframes become thousands of fabricated observations that look exactly like human annotations. Choose keyframe-only on export and **assert it** on import. |
| 4 | **CVAT occlusion is not a released contact.** | Converts "hidden" into "not touching", which is the unknown-to-negative coercion standing rule 1 exists to forbid, and it does so in the ground truth, so every downstream number inherits it. |
| 5 | **Empty attribute strings are not `unknown`.** | A fabricated abstention. It looks like the annotator judged the evidence insufficient, when in fact nobody looked. |
| 6 | **XML entity expansion.** | A DOCTYPE in an annotation export can expand into gigabytes or read local files. Reject before parsing; an annotation export has no legitimate DOCTYPE. |
| 7 | **Touching half-open intervals.** `[0,1_000_000)` and `[1_000_000,2_000_000)` overlap by **zero**; `[0,1_000_001)` and `[1_000_000,2_000_000)` overlap by **one microsecond**. | Using `<=` where `<` belongs makes touching intervals overlap, which merges every consecutive pair of contacts of the same limb into one, destroying the move structure Stage 6 depends on. |
| 8 | **Float thresholds.** `0.1 + 0.2 != 0.3` in binary floating point. | A tIoU exactly at `0.3` compares as below `0.3` on some inputs and not others. The comparison becomes machine-dependent and byte-identity dies. Use C2 cross-multiplication everywhere, including in tests. |
| 9 | **Group leakage with one climber.** Every asset shares one participant, so the participant clause is unsatisfiable by construction. | Silently dropping the clause is a leakage bug. Declare `accepted_single_participant` explicitly, and carry the within-climber caveat on every number. |
| 10 | **Problem identity across a gym reset.** Holds get reset; the same wall with a new set is a new `WallSet`, and problem identities do not survive it (`mvp-contract.md` Section 5). | Treating a post-reset problem as the same problem puts the same "problem" in two splits with different pixels, which is leakage that no leakage test can see because the ids genuinely differ. |
| 11 | **Frozen means frozen.** | Re-splitting after new data arrives silently changes what "the test set" means, and every previously reported number becomes a number about a different dataset. New data means a **new release id**. |
| 12 | **The rasterisation convention changes IoU by several percent on small holds.** Pixel-centre versus pixel-corner versus any-coverage sampling give materially different answers when a hold is 15 pixels across. | Two implementations of "mask IoU" that disagree by 3 percent will be compared as if they measured the same thing. Fix the convention, write it down, and test it with fixture 9, where the analytic area and the pixel count must agree. |
| 13 | **PCK exclusion accounting cuts both ways.** Excluding occluded points from the denominator raises the score; forgetting to exclude them from the numerator raises it further and invisibly. | Report `excluded_count` alongside every PCK value. A PCK of `3/4` over 4 eligible points from 200 annotated is a different claim from `3/4` over 190. |
| 14 | **Computing a kappa casually.** Most frames are "no contact". | A chance-corrected statistic over that marginal reads as either near-perfect or near-zero depending on an assumption nobody stated. Do not compute one without stating the marginal assumption, and make it part of `agreement-measurement-design`. |
| 15 | **`float(s) * 1000` on a CVAT coordinate.** | Introduces a float into the ingest path of a no-float schema. It will round differently on a different machine and break byte-identity for reasons that take a day to find. Use `decimal.Decimal`. |
| 16 | **`-ss` for span selection.** | Before the input it seeks to the nearest keyframe, which is approximate; after the input it takes seconds, which is float time. Both are banned. Use `select='between(pts,...)'` on integer ticks. |

---

## 14. Report format and stop condition

Follow Section 0.6 exactly: the gate table, files added and changed, config thresholds introduced,
open decisions deferred with their slugs, what this stage does not prove, and the command
transcript.

Stage-specific additions:

- **Report three times, once per commit.** 2a, 2b and 2c each get their own report and their own
  reviewer pass. The 2a report contains D1 through D5 and D10 measured, and every other clause as
  `pending measurement`.
- **The reviewer re-measures independently.** For 2a that means recomputing each hand-calculated
  expectation from the fixture table in Section 10.2 by hand, not by running the code under
  review.
- **`docs/status.md` is not marked complete** until the owner approves 2c.
- **If a gate clause fails**, report the measured gap with its number, name the failing slice by
  participant, problem and wall set rather than hiding it in a pooled average, propose the
  smallest next experiment, and stop.

Then stop. Do not start Stage 3.

---

## 15. Read-first list

In this order, before writing anything.

| Order | File | Why |
| --- | --- | --- |
| 1 | `AGENTS.md` | Binding operating rules. Sections 2, 3, 5, 6, 9, 10, 11. |
| 2 | `docs/mvp-contract.md` | Sections 3, 4, 5, 6, 7, 8, 9, 10. The ontology and the split policy are here and are frozen. |
| 3 | `docs/data-schema.md` | Sections 1, 4, 5, 6, 7, 8. Entity table, provenance, serialization, and why CVAT is an adapter. |
| 4 | `docs/evaluation.md` | Sections 1, 2, 3, 4. Every metric this stage implements is defined here. |
| 5 | `docs/annotation-guide.md` | All of it. It is the human decision rule the adapter must not contradict. |
| 6 | `docs/status.md` | The Stage 1 evidence table shape, and the known-defect row Task 1 removes. |
| 7 | `configs/ingest/v1.json` | The exact config shape and the exact `selection` wording to imitate. |
| 8 | `src/climbvision/schema/provenance.py` | `IngestRun`, the model `HarnessRun` is built from. |
| 9 | `src/climbvision/schema/versions.py`, `src/climbvision/schema/__init__.py` | The two registration seams. |
| 10 | `src/climbvision/serialization.py`, `src/climbvision/hashing.py`, `src/climbvision/timebase.py` | `dumps_canonical` is the only `json.dumps` in the codebase. Integer arithmetic only in timestamp conversion. |
| 11 | `src/climbvision/quality.py` | Task 1 lives here, and `_frame_rate` is the cross-multiplication pattern C2 refers to. |
| 12 | `src/climbvision/media/ffprobe.py` | The subprocess boundary pattern `media/ffmpeg.py` must copy: bare basename, `cwd` set to the file's directory, argv recorded, version recorded, explicit demuxer options. |
| 13 | `src/climbvision/media/normalize.py` | `build_frame_index` and the pts-sorting behaviour the frame map depends on. |
| 14 | `src/climbvision/ingest.py` | Orchestration shape, and `_refuse_conflicting_manifest`, which is why Task 1 must land first. |
| 15 | `src/climbvision/cli.py` | Subcommand and exit-code conventions. |
| 16 | `tests/unit/test_scope_guard.py` | The four guards. Read the comment above `test_the_stage_one_module_inventory_is_pinned`. |
| 17 | `tests/unit/test_schema.py` | `DOCUMENT_MODELS` and `ALL_MODELS`, and what they enforce. |
| 18 | `tests/conftest.py` | `block_network`, the fixture paths, and `VIDEO_FIXTURES`. |
| 19 | `tests/fixtures/README.md` | The five video fixtures and their observed facts; the hand-authored-versus-observed distinction the CVAT fixtures must copy. |
| 20 | `scripts/regenerate_fixtures.sh` | The manual-only banner and the rationale for it. |
| 21 | `docs/agents/README.md` | The decision index, and the rule that decision records are never pre-stubbed. |
