# Stage 5 — Limb-hold contact intervals

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

Predict per-limb **contact intervals** with an **interpretable geometry-and-time baseline, before
any learned model.** The MVP predicts the **left hand and the right hand only**; feet are
**deferred, not deleted**, by the `hands-first-scope` decision (Section 7.4). Targets are `hold`,
`volume`, `wall_region`, `none` and `unknown`, for the two hands.

Evaluate **event F1 at three temporal-overlap levels**, **boundary errors**, **false-contact
time**, **hands and feet as separate slices** — the hand slices measured, the **foot slices
`not_applicable` with the reason recorded** (Section 8.8) — and a **risk-coverage curve**.

Consumes:

| Input | From | Used for |
| --- | --- | --- |
| Anchor observations (**palm**, with wall-plane points) | Stage 4 | The per-frame hand positions the geometry runs on. Toe anchors are produced by Stage 4 and **consumed by no code path here** (Section 7.4) |
| Hold polygons and `Calibration` | Stage 3 | The wall-plane geometry the anchors are tested against |
| Adjudicated contact annotations and release splits | Stage 2 | Ground truth, and which attempts are validation and which are the frozen test split |

Does **not** do: **foot contacts** (Section 7.4), intentional-versus-incidental labelling (a human
decision by contract), move segmentation or beta sequences (Stage 6), aggregates (Stage 7), or any
learned model. There is no model at Stage 5, by design: an interpretable baseline first establishes
what geometry alone can do, so a later learned model has something to beat that is not zero.

### 1.1 The measured envelope

The MVP is measured on a **standardized LED training board**: a flat panel hung at a fixed angle,
holds bolted at fixed positions on a grid the **board definition declares** - an **11-column by
18-row** grid `[FIXED]` for the board type measured here
(`docs/agents/briefs/stage-3-wall-and-holds.md` Section 8.1) - the same panel and the same hold
positions in every installation worldwide, with a per-hold LED marking which holds belong to the
problem (`mvp-contract.md` Section 1, which fixes the envelope and states no board's geometry).
This is the commercially standardized board class; a Kilter- or Moonboard-style panel is the
familiar instance of it. **The contract stays
general.** The board is the **first measured envelope**, not a narrowing of what the contract may
describe, and every number this stage produces is a number about this board.

Three properties of that envelope are load-bearing for this brief:

| Property of the envelope | Consequence for Stage 5 |
| --- | --- |
| The problem's holds are lit, typically **8 to 15** of them `[PLANNING]`, out of the grid's fixed positions | The candidate set is small, sparse and enumerable, not a dense spray wall. Section 8.10 |
| The panel is steeply overhung and the camera shoots upward from beneath it | The climber's body occludes its own limbs far more than on a vertical wall, and the anchors this stage consumes degrade accordingly. Section 8.11 |
| Hold positions are identical between installations | A radius selected on this board is selected against a fixed geometry rather than against one gym's setting. It still says nothing about a different board angle, a different camera placement or a different climber (Section 0.5) |

## 2. Preconditions

The agent does not start until every row holds. If a row does not hold, stop and report.

| Precondition | Evidence it holds |
| --- | --- |
| The Stage 4 gate is recorded, **including palm endpoint accuracy with its interval** | A Stage 4 row and measured-evidence table in `docs/status.md`. Endpoint accuracy without its interval is not evidence; the anchors this stage runs on are only as good as that number, and its interval is what says how much to trust the contact numbers. **The palm number is the one that gates this stage**, because the MVP consumes palm anchors only (Section 7.4). A toe endpoint number, where Stage 4 measured one, is recorded and not consumed, and the two are never pooled into one endpoint figure. |
| A calibration exists **whose hull coverage is reported** | The Stage 3 calibration document plus the reported fiducial hull coverage. The hull is what the inside/outside slice is computed against; without it the slice cannot be built. |
| Adjudicated contact annotations exist for **all released attempts** | `adjudicated_ground_truth` provenance on every contact interval in the release, not a subset |
| The millimetres-per-wall-unit scale is known, **or** every millimetre-denominated threshold explicitly abstains | The `wall-plane-units-and-scale` decision under `docs/adr/`. **Note:** every Stage 5 threshold is denominated in **milli-wall-units**, not millimetres, so the thresholds themselves are selectable without the scale. The scale is needed only to *report* a radius in physical units, and any such report reads `unknown` until the scale is closed. |

## 3. Human inputs required before the agent starts

**None new.** All annotation was done at Stage 2. Stage 5 does not ask for a single new label, a
single new trace, or a single new frame of video.

The owner approves one decision, and one further decision is **already approved** and needs only
its record written:

| Slug | What the owner approves |
| --- | --- |
| `contact-threshold-selection-protocol` | Thresholds are swept on **validation only**; the chosen values are written into `configs/contacts/v1.json` with the sweep recorded in each threshold's `selection` string; and the **frozen test set is touched exactly once, at the end.** |
| `hands-first-scope` | **Already approved.** The MVP predicts hand contacts only. The agent does not reopen it, does not widen it, and does not narrow it further: it writes the record (Section 7.4), implements the two-hand scope, and reports the foot slices as `not_applicable`. |

The threshold protocol is the whole of the owner's ongoing involvement, and it is the one thing an
agent cannot be trusted to enforce on itself, because a sweep that quietly includes the test split
produces a better-looking number and leaves no trace in the code.

## 4. Deliverables

### 4.1 New files

Module names are **proposals**; any rename must be carried into the scope guard inventory set in
the same change.

| Path (proposed) | Kind | Owns |
| --- | --- | --- |
| `src/climbvision/contacts/__init__.py` | package | Exports |
| `src/climbvision/contacts/proximity.py` | module | Exact integer point-to-polygon signed distance in the wall plane |
| `src/climbvision/contacts/hysteresis.py` | module | The two-radius state machine, per limb and hold |
| `src/climbvision/contacts/postprocess.py` | module | Gap merging, minimum-duration filtering, occlusion bridging |
| `src/climbvision/contacts/baseline.py` | module | Orchestration, abstention rules, margin computation |
| `src/climbvision/contacts/evaluation.py` | module | Assembles and slices the metrics |
| `src/climbvision/schema/contacts.py` | module | `ContactSeries`, `ContactEvent` |
| `src/climbvision/schema/contact_run.py` | module | `ContactRun`, the Stage 5 run document (C5) |
| `configs/contacts/v1.json` | config | Every Stage 5 threshold (C9) |
| `docs/adr/hands-first-scope.md` | decision | Written first — it determines **which limbs exist** for every other decision in the stage |
| `docs/adr/contact-membership-space.md` | decision | Written second — it determines what the geometry module computes in |
| `docs/adr/contact-target-scope.md` | decision | Written third — it determines what the baseline is allowed to emit |
| `docs/adr/contact-threshold-selection-protocol.md` | decision | Written fourth, **before the first sweep runs** |
| `tests/fixtures/documents/contact_series.valid.json` | fixture | Golden document fixture |
| `tests/fixtures/documents/contact_run.valid.json` | fixture | Golden document fixture |

Decision records are created **one at a time, at the moment each is made** (Section 0.7).

### 4.2 Existing files changed — the seam list applied

| File | Change |
| --- | --- |
| `src/climbvision/schema/versions.py` | Add `CONTACT_SERIES_SCHEMA_ID`, `CONTACT_RUN_SCHEMA_ID`, their `*_SCHEMA_VERSION = 1` constants, and two entries in `SCHEMA_IDS` |
| `src/climbvision/schema/__init__.py` | Two entries in `MODEL_REGISTRY`, and every new name in `__all__` |
| `tests/unit/test_schema.py` | Two rows in `DOCUMENT_MODELS` with their golden fixtures; `ContactEvent` and every other nested model added to `ALL_MODELS` |
| `tests/unit/test_scope_guard.py` | A **new** set `STAGE_FIVE_MODULES` beside `STAGE_ONE_MODULES` and `STAGE_FOUR_MODULES`; the inventory test asserts the union. **Do not extend an earlier stage's set.** Plus a **negative** test: no file under `climbvision/contacts/` imports anything outside the standard library and `climbvision` — no `numpy`, no `av`, no backend root |
| `tests/unit/test_scope_guard.py` | The parsed dependency test asserts Stage 5 added **no** distribution and **no** optional group |
| `src/climbvision/cli.py`, `tests/unit/test_cli.py` | Subcommands (proposed: `contacts`, `contacts-eval`, `contacts-sweep`); exit codes **0** ok, **1** operation failed, **2** usage, exactly as today; plus a test that `validate` accepts the two new documents **through `MODEL_REGISTRY`**, dispatching on `schema_id`, never on filename |
| `docs/evaluation.md` | **No change.** Section 1 "Stage 5 — contact intervals" already defines temporal IoU, event F1, boundary error, false-contact time and risk-coverage, and fixes the three tIoU reporting levels. Cite it; do not restate it. Reporting an unattempted slice as `not_applicable` needs no new metric definition either: Section 1 already sets that precedent for the mask metrics before a segmenter is adopted. |
| `docs/mvp-contract.md`, `docs/data-schema.md`, `docs/annotation-guide.md` | **No change by this stage.** The ontology, the half-open convention and the occlusion rule are all already there, and the **board envelope is recorded in the contract by its own amendment**, not by Stage 5. If the contract's envelope and Section 1.1 of this brief disagree on a fact, that is a defect: report it, do not resolve it silently (Section 0). |
| `docs/status.md` | The Stage 5 row, plus a measured-evidence table shaped exactly like the Stage 1 one |
| `README.md` | **The command rows only.** No claim about a stage that has not shipped. |
| `.gitignore` | **No change expected.** `artifacts/` already covers the emitted documents and the sweep outputs. Confirm rather than assume. |
| `scripts/regenerate_fixtures.sh` | Extend to regenerate the two new document fixtures from a live run. Manual only. |

## 5. Entities

`ContactEvent` arrives at Stage 5 **on schedule** per `docs/data-schema.md` Section 1. `MoveEvent`,
`BetaSequence` and `FallEvent` remain **documented-only**: no stub, no placeholder class, no empty
file. The repository does not contain a model for an entity whose real structure is not yet known.

Field identifiers below are **proposals**. Every model carries
`model_config = ConfigDict(extra="forbid", frozen=True)`. No field is float-typed.

### 5.1 `ContactEvent`

| Field (proposed) | Type | Notes |
| --- | --- | --- |
| `event_id` | `str` | Deterministic from `(asset_id, limb, start_us, target_ref)`, so re-runs produce the same ids |
| `asset_id` | `str` | `sha256-<64 hex>`, constrained by `ASSET_ID_PATTERN` |
| `limb` | `Literal["left_hand", "right_hand", "left_foot", "right_foot"]` | Closed set. **Stays four-valued.** Feet are deferred, not deleted (Section 7.4), and narrowing the type would delete the vocabulary a later stage restores. The MVP **attempts** only the two hands, and that is recorded in `ContactSeries.attempted_limbs`, not in this type. |
| `target_kind` | `Literal["hold", "volume", "wall_region", "none", "unknown"]` | The contact-target ontology, `mvp-contract.md` Section 5. A value outside the set is a defect, not a new category. |
| `target_ref` | `str \| None` | The `HoldInstance` id, **scoped to its `WallSet` revision**. `null` for `none`, `unknown` and any abstained event. |
| `contact_label` | `Literal["unknown"]` | **Fixed to `unknown`.** A `Literal` of one member, so the type system forbids anything else. |
| `start_us`, `end_us` | `int` | **Half-open** `[start_us, end_us)`. Integer microseconds. A zero-length interval is empty and must not be emitted. |
| `start_unobserved`, `end_unobserved` | `bool` | Per `annotation-guide.md` Section 3: a boundary that falls outside the recording is marked, never silently clamped |
| `status` | `Literal["predicted", "abstained"]` | C7 |
| `margin_milli_wall_units` | `int \| None` | The geometric slack that produced the decision. `null` when abstained. |
| `score_type` | `str` | Names what the margin is. Proposed value: `geometric_margin_milli_wall_units`. |
| `provenance_class` | `Literal["prediction"]` | `mvp-contract.md` Section 10 |
| `inside_fiducial_hull` | `bool` | Whether the anchor lay inside the calibration's fiducial hull for the whole interval. Drives the hull slice. |

### 5.2 `ContactSeries`

| Field (proposed) | Type | Notes |
| --- | --- | --- |
| `schema_id`, `schema_version` | `Literal` | Registered in `versions.py`, `MODEL_REGISTRY` and `SCHEMA_IDS` |
| `asset_id` | `str` | Binding |
| `frame_index_sha256` | `str` | The exact packet table the intervals were built against |
| `wall_set_id` | `str` | Problem identity is scoped to a `WallSet` revision |
| `calibration_sha256` | `str` | The exact homography used |
| `pose_series_sha256` | `str` | Really the **anchor** series hash from Stage 4; name it for what it points at |
| `raw_document_sha256` | `str \| None` | C8. `null` **only** on the raw document itself. |
| `config_version`, `config_sha256` | `str` | Two runs with different config are different runs |
| `postprocess_order` | `str` | The recorded order, `[FIXED]`. See Section 8.6. |
| `attempted_limbs` | `list[Literal[...]]` | The limbs this run **attempted to predict**, sorted in the declared order of the `limb` literal — left hand, right hand, left foot, right foot — so that the ordering is stated once and byte-identity is testable. For the MVP: exactly `left_hand` and `right_hand`. A limb absent from this list was **not attempted**; a limb present in it but with no event over some span was attempted and produced a result. Without this field, "no foot events" and "feet all off the wall" are the same bytes. |
| `events` | `list[ContactEvent]` | |

### 5.3 The rule that keeps this stage inside the contract

**The contact label is always `unknown` at this stage.**

The baseline **never** predicts `intentional_use` versus `incidental_touch`. Load is not
observable from a single camera (`mvp-contract.md` Sections 2 and 6), and the contract makes that
distinction a **human annotation decision with an explicit `unknown` escape**
(`annotation-guide.md` Section 1). Visual proximity is never automatically intentional use
(truth rule 9).

A `Literal["unknown"]` is used rather than a validator, so the type system forbids the other two
values and a future contributor cannot widen it by accident.

### 5.4 The rule that keeps the deferred limbs honest

**A limb the system did not attempt is `unknown`. It is never `none`.**

`none` means "the limb is demonstrably not in contact" (`mvp-contract.md` Section 5). That is a
**determinate claim about the world**, and the MVP has no evidence for it about a foot, because it
never looked. Turning "we did not attempt it" into "it was not touching anything" is the exact
coercion standing rule 1 forbids — `unknown` is not `false`, missing propagates as missing — and
it is the single most likely way this stage's scope cut would become a lie in the data.

Concretely, and each clause is separately testable:

| Rule | Enforcement |
| --- | --- |
| No event for a limb outside `attempted_limbs` may carry `target_kind = "none"` | Section 10.11, gate clause D10 |
| Nor `target_kind = "hold"`, `"volume"` or `"wall_region"`: a determinate **positive** claim about an unattempted limb is the same defect in the other direction | Section 10.11, gate clause D10 |
| Any event emitted for an unattempted limb carries `target_kind = "unknown"`, `target_ref = null`, `status = "abstained"` | Section 10.11 |
| The **absence** of foot events is not left to inference: `attempted_limbs` states it (Section 5.2) | Section 10.11, C7 |

The stage may emit no foot events at all, which is the simplest compliant behaviour. What it may
**not** do is emit a foot event that asserts a determinate contact state, or leave a reader to
infer "not in contact" from silence.

## 6. Decisions already frozen

Do not reopen any of these. Cite them; do not restate them.

| Frozen | Where |
| --- | --- |
| Intervals are **half-open** `[start_us, end_us)`; a zero-length interval is empty | `mvp-contract.md` Section 3, `annotation-guide.md` Section 3 |
| `start_us` is the first frame in which contact is established; `end_us` is the first frame in which it is no longer present, and is **not** part of the interval | `annotation-guide.md` Section 3 |
| Two consecutive contacts of the same limb **share a boundary value**: no gap, no overlap | `annotation-guide.md` Section 3 |
| **Occlusion does not end a contact.** It is a visibility label on an observation, not a termination. | `annotation-guide.md` Section 3 |
| `occluded` is not `none`; `unknown` is not `false`; missing propagates as missing | `mvp-contract.md` Section 5, standing rule 1 |
| The five contact-target values and the three contact-label values are **closed sets** | `mvp-contract.md` Section 5 |
| `intentional_use` versus `incidental_touch` is a **human** decision | `mvp-contract.md` Section 6, `annotation-guide.md` Section 1 |
| A problem ID is **scoped to a `WallSet` revision** | `mvp-contract.md` Section 5, standing rule 2 |
| Wall-plane coordinates are **not** physical 3D body coordinates | `mvp-contract.md` Section 4, truth rule 8 |
| tIoU is **reported at `0.1`, `0.3` and `0.5` `[FIXED]`** — a reporting convention, not a target | `evaluation.md` Section 1 |
| Boundary error is in **integer microseconds** and reported as a **distribution, not a mean alone** | `evaluation.md` Section 1 |
| Risk-coverage exists because **abstention is a first-class output** | `evaluation.md` Section 1 |
| The test set is frozen and evaluated **once**; selection of any kind happens on validation only | `mvp-contract.md` Section 8, `evaluation.md` Section 2 |
| Confidence never increases downstream: an upstream `abstained` cannot become a confident downstream result | `mvp-contract.md` Section 10, truth rule 15 |
| No float-typed field anywhere; canonical serialization; explicit `null` | `data-schema.md` Section 7 |
| **No new dependency at Stage 5.** | This brief, Section 9 |

## 7. Open decisions

Four decisions close at Stage 5, by slug: `hands-first-scope`,
`contact-threshold-selection-protocol`, `contact-membership-space`, `contact-target-scope`.

### 7.1 `contact-threshold-selection-protocol`

Approved by the owner (Section 3). The record states:

- Thresholds are swept on the **validation split only**.
- The chosen values are written into `configs/contacts/v1.json`, and each threshold's `selection` string records **the sweep**: the grid searched, the metric optimized, the split, and the release id.
- The **frozen test split is evaluated exactly once, at the end**, through the mechanism fixed by the Stage 2 `test-set-evaluation-policy` decision.
- **Stage 5 does not invent a second mechanism for this.** If the Stage 2 decision left the enforcement mechanism open, stop and ask, rather than building a competing one.

### 7.2 `contact-membership-space`

**Test membership in the wall plane, not in pixels.**

| | Wall plane | Pixels |
| --- | --- | --- |
| A dilation radius means | A **uniform physical distance** everywhere on the facet | A different physical distance at the top of the frame than at the bottom, because of perspective |
| A threshold is | Selectable once, for the wall | Re-selectable per camera placement, silently |
| Error source | **Calibration error now enters every contact decision** | Only anchor error |

The cost is real and is the reason the **inside-hull slice exists**: calibration error grows with
distance from the fiducial hull, and it lands directly on the attach radius. Reporting every
metric inside versus outside the hull is what makes that error visible instead of averaged away.

### 7.3 `contact-target-scope`

**Recommendation: `volume` and `wall_region` targets are NOT predicted at this stage.**

- The baseline **abstains** on both. It never emits `target_kind = "volume"` and never emits `target_kind = "wall_region"`.
- They remain **annotation-only** targets: Stage 2 annotators label them, and the ontology keeps them.
- Their annotated time is **counted against the baseline** as false-contact time or missed detection, **not quietly excluded from the denominator.**

That last clause is the whole point of the decision. Excluding a target the system cannot predict
makes the metric measure a narrower problem than the one the product has, and the narrowing is
invisible in the number. Counting it as a loss reports a **known, quantified gap** instead.

### 7.4 `hands-first-scope`

**Approved by the owner (Section 3). The MVP predicts hand contacts only. Feet are deferred.**

This is a **scope decision, taken on the merits of the measurement**, and the record must say so
rather than assert it. Two substantive reasons, neither of which is annotation cost:

| Reason | What it means on this envelope |
| --- | --- |
| **Foot visibility is worst exactly here.** Foot visibility was already the weakest measurement in the pipeline. On a steeply overhung panel the climber hangs beneath the wall, so the body occludes its own feet far more than on a vertical wall, and the camera shoots steeply upward into that occlusion. The envelope makes the weakest input weaker. | The toe anchors from Stage 4 would be abstained or badly placed over a large fraction of every attempt, and a contact interval built on them would be measuring the anchor, not the contact. |
| **The foot target is poorly defined here.** Footwork on these boards is genuinely unconstrained: climbers smear on bare plywood between the holds, and many problems place no constraint on the feet at all. | The **ground truth itself is weak**, not merely the prediction. There is no stable answer for an annotator to give on a smear that belongs to no hold, so a foot event scored against it would be scoring disagreement about the question. |

**Deferring a target whose ground truth is weak is an honest scope decision. Measuring it anyway
would produce a number nobody should read** — an accuracy figure whose denominator is a label the
annotation guide cannot pin down. That is the reasoning the record carries.

What the decision does **not** do:

- It does not remove `left_foot` or `right_foot` from the limb vocabulary (Section 5.1).
- It does not remove the hands-versus-feet slice (Section 8.8).
- It does not remove the per-foot threshold overrides (Section 8.9).
- It does not license `none` for a foot. See Section 5.4, which is the rule this decision is most likely to be violated through.

| What the record states |
| --- |
| The MVP-attempted limb set: `left_hand`, `right_hand` |
| The two reasons above, as reasons about **measurement**, not about effort |
| That the foot machinery — vocabulary, slices, threshold overrides — is **retained**, and why |
| That every foot slice is reported `not_applicable` with the reason, and never as zero, absent or failed |
| That restoring feet requires: a re-measured foot visibility rate on this envelope, an annotation rule for smears on bare board surface, and its own selection run for the foot radii |

## 8. Approach

### 8.1 Per frame, per attempted limb

Runs for the **left hand and the right hand**. It does not run for a foot, and there is no code
path that produces a determinate foot result (Sections 5.4 and 7.4).

Take the Stage 4 palm anchor, projected into the wall plane. Then:

| Anchor state | Behaviour |
| --- | --- |
| Observed, inside the hull | Run the geometry (Section 8.2) |
| Observed, outside the hull | Run the geometry, and set `inside_fiducial_hull = false` on any resulting event |
| **Abstained** | Hold the limb's state through the gap if the **whole gap** is shorter than the occlusion-bridge threshold. Beyond it, the limb's state becomes **`unknown`**. |

**An abstained anchor never becomes `none`.** `occluded` is not `none`
(`mvp-contract.md` Section 5, standing rule 1). This is the most likely domain bug in the stage.

**Why the whole gap, not a prefix.** If the gap exceeds the bridge, the contact interval ends at
the timestamp of the **first abstained frame**, and an abstained `unknown` event covers the whole
gap. Splitting the gap into a "held" prefix and an "unknown" suffix would place a boundary
**inside unobserved data**, inventing a measured-looking timestamp where nothing was observed.
That is a rule-6 violation dressed up as precision.

### 8.2 Exact integer point-to-polygon geometry

For each hold **on the problem** — on this envelope, its lit holds (Section 8.10) — compute the
anchor's relationship to the polygon.

**Insideness, by even-odd ray cast on integers.** For each edge `(x1,y1) → (x2,y2)` and point
`(px,py)`:

```
if (y1 > py) != (y2 > py):
    d   = y2 - y1                      # non-zero, guaranteed by the test above
    lhs = (px - x1) * d
    rhs = (py - y1) * (x2 - x1)
    crossing = (lhs < rhs) if d > 0 else (lhs > rhs)
```

No division, no float. The float form `x1 + (py-y1)*(x2-x1)/(y2-y1)` is what this replaces.

**The boundary case is handled before the loop, not by it.** A ray cast is ambiguous for a point
exactly on an edge or on a vertex. Test boundary membership explicitly first. **Declared
convention: a point on the boundary is inside.**

**Squared distance to the boundary.** For segment `A=(x1,y1)`, `B=(x2,y2)` and point `P`:

```
abx, aby = x2-x1, y2-y1
apx, apy = px-x1, py-y1
t_num = apx*abx + apy*aby
t_den = abx*abx + aby*aby
if t_den == 0:      d2 = RatioValue(apx*apx + apy*apy, 1)      # degenerate edge
elif t_num <= 0:    d2 = RatioValue(apx*apx + apy*apy, 1)      # nearest is A
elif t_num >= t_den: d2 = RatioValue((px-x2)**2 + (py-y2)**2, 1)  # nearest is B
else:
    cross = apx*aby - apy*abx
    d2 = RatioValue(cross*cross, t_den)                        # perpendicular foot
```

**The perpendicular squared distance is a rational, not an integer.** `cross*cross / t_den` does
not generally divide evenly. Flooring it here would break exactness at exactly the boundary the
hysteresis cares about, so it is carried as a `RatioValue` (C1) and every comparison is done by
cross-multiplication (C2):

```
d2 <= r2        <=>   d2.num * r2.den  <=  r2.num * d2.den
```

**Squaring destroys the sign.** The "signed distance" of the mission statement is carried as a
**pair**: an `inside` boolean plus a non-negative squared distance to the boundary. There is no
negative squared distance. For membership and hysteresis, **an inside point has effective squared
distance zero**, because any inside point is trivially within any radius.

**No square roots anywhere in a decision path.** The only square root in the stage is
`math.isqrt` — stdlib, exact for integers — used for two **reported** or **compared** integer
quantities (Sections 8.4 and 8.7), never for a radius comparison.

### 8.3 Hysteresis

A `(limb, hold)` pair has a state machine with two radii:

| Transition | Condition |
| --- | --- |
| far → near | Squared distance is **within the squared attach radius**, and has been so for at least the **minimum attach duration** |
| near → far | Squared distance **exceeds the squared release radius**, and has done so for at least the **minimum release duration** |

**The release radius is strictly larger than the attach radius**, asserted at config load with a
named error code. One radius alone produces dozens of one-frame intervals when an anchor jitters
on the boundary — see the regression test in Section 10.3, which produces four intervals with one
radius and one interval with two on the same input.

### 8.4 Ambiguity abstention

If **two holds are simultaneously within the attach radius** and **the difference of their
distances is below the target-margin threshold**, emit an event with `target_kind = "unknown"`,
`target_ref = null` and `status = "abstained"`.

**This is the insufficient-evidence rule (truth rule 6), not a tie-break.** A tie-break picks a
winner; this declines. On a dense wall, two small holds a few centimetres apart are inside any
usable radius of each other, and the margin abstention is the only thing that stops the system
confidently naming the wrong one.

**On the board envelope this rule fires less often**, because the lit candidates sit on a fixed
grid and are sparser than the neighbours on a spray wall (Section 8.10). That is a property of the
equipment, not a property of the method, and the report must say so: a low ambiguity-abstention
rate measured here is **not** evidence that the abstention rule could be dropped elsewhere. Keep
the rule, keep the threshold, and report the rate.

The distance comparison is done on integers: define `dist_floor(h) = isqrt(d2.num // d2.den)`,
an exact deterministic integer function, and test
`abs(dist_floor(h1) - dist_floor(h2)) < min_target_margin_milli_wall_units`.

**The flooring bound, stated honestly:** each `dist_floor` is short of the true distance by less
than one milli-wall-unit, so the difference is off by at most two. The margin threshold must
therefore never be set to a value where two milli-wall-units matter, and its `selection` string
must say so.

### 8.5 When `none` may be emitted

**`none` is emitted only when the anchor is farther than the `definite_none_margin` from every
hold on the wall.**

Between "clearly on a hold" and "clearly off everything", the answer is **`unknown`**. There are
therefore three zones, not two:

| Zone | Value |
| --- | --- |
| Within the attach radius of exactly one of the problem's holds, by more than the target margin | That hold |
| Within the attach radius of two or more of the problem's holds, inside the target margin | `unknown`, abstained |
| Beyond the attach radius but within the definite-none margin of some hold | `unknown` |
| Within the definite-none margin of a hold that is **present on the panel but not on this problem** | `unknown` — **never `none`** (Section 8.10) |
| Beyond the definite-none margin of **every** hold present on the panel | `none` |

### 8.6 Raw first, then post-processing, in a recorded order

1. Write the **unfiltered interval set** and hash it (C8, truth rule 4).
2. **Then** apply **gap merging**.
3. **Then** apply the **minimum-duration filter**.

The order is `merge, then filter`. It is recorded in `ContactSeries.postprocess_order` and in the
run document, and it is `[FIXED]`. Section 10.5 gives a crafted input on which the two orders give
different answers — one interval versus zero — so the pin is tested, not asserted.

### 8.7 The margin

For every **emitted** event, record the **margin**: the distance slack that produced the decision,
as `isqrt` of the difference between the squared attach radius and the observed squared distance,
in integer milli-wall-units.

- It is a **measured geometric quantity, not an invented confidence** (truth rule 1). It is declared as such through `score_type`.
- It is the **ordering key for the risk-coverage curve**.
- Flooring can put two events at the same integer margin, so the risk-coverage ordering **breaks ties deterministically by `event_id`**, otherwise the curve is not reproducible.
- It is **never** presented as a probability, and no calibration is applied to make it look like one.

### 8.8 Evaluation

Reuse the Stage 2 evaluation library. Do not build a second one — a parallel metric implementation
that drifts from the first is worse than no second implementation.

Report, **never pooled together**:

| Metric | Reported as |
| --- | --- |
| Event F1, **target-aware** | At each of tIoU `0.1`, `0.3`, `0.5` `[FIXED]` |
| Event F1, **target-agnostic** | At each of the same three levels |
| Boundary error | Integer **quantiles**, plus minimum and maximum. Nearest-rank, **no interpolation** — interpolation produces floats. |
| False-contact time | Integer microseconds, **per attempted limb** |

And **every** metric sliced three ways:

1. **Hands versus feet.** The **hand** slice is measured and reported. The **foot** slice reads
   **`not_applicable`, with the reason recorded** — `"Feet are not attempted in the MVP; see the
   hands-first-scope decision."` It is not absent, not zero and not a failure. `not_applicable` is
   the same treatment `evaluation.md` Section 1 already gives the mask metrics before a segmenter
   is adopted: the accuracy of something that was never attempted is **undefined, not bad**.
2. **Inside versus outside the fiducial hull.**
3. **Holds on volumes versus holds on the wall.** The board is a **flat panel**, so `volume`
   targets are not expected to occur on this envelope at all. An **empty** slice also reads
   `not_applicable` with its reason, never `0`, because a zero here would be read as a measurement.

**Keep the slicing machinery in full.** Two reasons, and the second is the one that matters. It is
needed unchanged when feet return, so deleting it now buys nothing and costs a re-measurement
later. And **reporting a slice as explicitly not attempted is itself the honest output**: a report
that simply has no foot row is indistinguishable from a report whose foot row was quietly dropped
because it looked bad.

**At full coverage, abstained predictions count as false negatives.** State this explicitly in the
report. The alternative — dropping them from the denominator — makes abstention look free, makes
precision look excellent, and destroys the entire point of the risk-coverage curve, which exists
to show what abstention actually costs.

### 8.9 Every threshold, named

Into `configs/contacts/v1.json` (C9). Each entry carries `value`, `unit`, `status` and
`selection`. A missing `value` is `CONFIG_THRESHOLD_MISSING`, never a default. **All `[PILOT]`.**

| Name (proposed) | Unit |
| --- | --- |
| `attach_radius_milli_wall_units` | milli-wall-units |
| `release_radius_milli_wall_units` | milli-wall-units |
| `min_attach_duration_us` | microseconds |
| `min_release_duration_us` | microseconds |
| `min_contact_duration_us` | microseconds |
| `max_merge_gap_us` | microseconds |
| `max_occlusion_bridge_us` | microseconds |
| `min_target_margin_milli_wall_units` | milli-wall-units |
| `definite_none_margin_milli_wall_units` | milli-wall-units |
| `attach_radius_milli_wall_units.hand` / `.foot` | milli-wall-units |
| `release_radius_milli_wall_units.hand` / `.foot` | milli-wall-units |

**Per-hand and per-foot overrides exist for every radius from the start**, because feet and hands
almost certainly need different values (Section 13, trap 10) and retrofitting the seam later means
re-running every measurement.

**The foot overrides stay in the config, and stay unselected.** They are the seam that lets feet
return without a config migration. Their `selection` strings read
`"Not selected. Feet are not attempted in the MVP; see the hands-first-scope decision. No
validation data exists."` — which is a different statement from "not swept yet", and the
difference is exactly what a later reader needs. The **hand** overrides are the ones the sweep
selects.

**There is no fallback.** An override with no `value` is `CONFIG_THRESHOLD_MISSING`, not "use the
base value". If hand and foot radii are meant to be equal, both entries carry the same number and
both `selection` strings say why. A silent fallback hides the fact that the two were never
separately selected.

Every other `selection` string reads
`"Not selected. [PILOT] placeholder; no validation data exists."` until the sweep is run and
recorded in `docs/status.md`.

### 8.10 What the board makes easier

**The contact-target vocabulary collapses to a small closed set.** On this envelope a hand is on
one of the **problem's lit holds**, on the **board surface** between them, on **nothing**, or the
observation does not say — that is, `hold` restricted to the lit set, `wall_region`, `none`,
`unknown`. `volume` does not occur on a flat panel. The candidate hold set for a problem is
**typically 8 to 15 holds** `[PLANNING]`, enumerated by which LEDs are lit, rather than every hold
on a wall.

This does **not** widen what the baseline emits. `wall_region` remains abstained by
`contact-target-scope` (Section 7.3), and its annotated time is still counted against the
baseline as a known, quantified gap rather than excluded.

Two consequences follow, and both belong in the report:

| Consequence | Why it follows | What to report |
| --- | --- | --- |
| **Ambiguity abstention fires less often.** Candidates sit on a fixed grid and are sparse; two lit holds are rarely inside each other's attach radius, unlike two adjacent holds on a dense spray wall | Geometry of the equipment, not quality of the method | The measured ambiguity-abstention rate, **stated as a property of this envelope**. A low rate here is not evidence about a spray wall (Section 8.4) |
| **"The system named a hold that is not on this problem" is a free correctness check.** The lit set is known before any annotation exists, so every emitted `target_ref` can be tested for membership in it | The problem definition already enumerates its holds; no human labels a single frame for this check | The count of emitted events whose `target_ref` is **outside** the problem's lit hold set. It is a **deterministic** clause (D9), not a `[PILOT]` one, and its correct value is **zero** |

The off-problem check is cheap and it is not a substitute for the F1: naming a **wrong lit hold**
passes it. It bounds one specific failure mode — the geometry reaching a hold that the problem
does not contain — at zero annotation cost, which is why it is worth a gate clause of its own.

**The restriction carries one obligation with it.** On this envelope every grid position holds a
physical hold, lit or not, so a hand on an **unlit** hold is genuinely in contact with something.
Restricting the **target** vocabulary to the lit set must not be allowed to turn that into `none`,
which asserts "demonstrably not in contact" (`mvp-contract.md` Section 5) about a hand that is
demonstrably on a hold. The unlit holds therefore participate in the `definite_none_margin` test
of Section 8.5 as **`none`-suppressors only**: proximity to one yields `unknown`, and an unlit
hold is **never** emitted as a `target_ref`. Their positions come from the panel's fixed grid, so
this too costs no annotation.

### 8.11 What the board makes harder

**Self-occlusion is worse here than on a vertical wall.** The panel is steeply overhung, the
climber hangs beneath it, and the camera shoots upward from below, so the body occludes its own
limbs for longer and more often. That degrades the Stage 4 anchors this stage consumes, and it
lands on two places in the design:

| Expectation | Consequence |
| --- | --- |
| The **abstention rate is higher** than it would be on a vertical wall | More time is spent in the abstained-anchor row of Section 8.1, and the risk-coverage curve is the report's most informative artifact rather than a formality |
| The **occlusion-bridge threshold matters more** | `max_occlusion_bridge_us` decides how much of that occluded time is held through and how much becomes `unknown`. On this envelope it is a load-bearing threshold, not a tidy-up |

**Both statements are directions, not numbers.** No expected abstention rate is stated here,
because none has been measured, and a plausible-looking figure in a brief is indistinguishable
from a result once someone quotes it. The requirement is that both are **measured and reported**:

- the abstention rate **per hand**, with the share attributable to occlusion bridging separated
  from the share attributable to ambiguity (Section 8.4) — gate clause P5;
- the sensitivity of the abstention rate to `max_occlusion_bridge_us` across the sweep grid, on
  **validation only**, so the threshold's `selection` string records what it was trading.

If the measured abstention rate makes the contact numbers unusable, that is a **result about this
envelope** and it is reported as one. It is not a reason to shorten the bridge until the number
improves, which would move an occlusion into an `unknown` and then into a shorter interval without
observing anything new.

## 9. Dependencies

**Add nothing.**

Point-in-polygon, point-to-segment distance, hysteresis and interval algebra are **integer
arithmetic on data already in memory**. `math.gcd` (for `RatioValue` reduction) and `math.isqrt`
(for the two integer square roots in Sections 8.4 and 8.7) are standard library.

Everything banned at Stage 4 stays banned. **No learned model. No machine-learning library.** The
mission is an interpretable baseline *before* any learned model, and a learned model added here
would make the baseline unmeasurable.

The scope guard gets a **negative test** for this: no file under `climbvision/contacts/` imports
anything outside the standard library and `climbvision`. Not `numpy`, not `av`, not a pose backend
root. That test is cheap and it is the thing that catches "I just needed an array here".

## 10. Tests

Hand-calculated with exact values. Numbers inside a fixture are **arithmetic, not thresholds**,
and are untagged. **A gate number never comes from `tests/fixtures/`** (`AGENTS.md` Section 11).

### 10.1 The square hold

A square hold with corners at the origin and one thousand milli-units on each side:
`(0,0)`, `(1000,0)`, `(1000,1000)`, `(0,1000)`.

| Anchor | Expected | Why |
| --- | --- | --- |
| `(500, 500)` | `inside = true`, effective squared distance `0` | The centre |
| `(1300, 500)` | `inside = false`, squared distance `90000` | Nearest edge is `x = 1000`; the anchor is **300 milli-units outside**; `300² = 90000` |
| `(1000, 500)` | `inside = true`, effective squared distance `0` | **Exactly on an edge. Convention: the boundary is inside.** |
| `(1000, 1000)` | `inside = true` | Exactly on a vertex; same convention, and the case a ray cast gets wrong |

The `(1300, 500)` value is produced by the perpendicular branch and is exact:
`cross = 300*1000 - 500*0 = 300000`, `t_den = 1000000`, `d² = 300000² / 1000000 = 90000`.

**Radius comparisons on that value:**

| Squared radius | Comparison | Result |
| --- | --- | --- |
| `40000` (radius 200) | `90000 > 40000` | **not near** |
| `160000` (radius 400) | `90000 < 160000` | **near** |

### 10.2 Insideness has no negative squared distance

Assert that the geometry module returns an `(inside, squared_distance)` pair and that the squared
distance is **never negative** for any input, over a parametrized sweep of inside, outside,
on-edge and on-vertex anchors. A negative squared distance means someone tried to encode the sign
into the magnitude, which cannot survive squaring.

### 10.3 The flapping regression test

Eight frames at 33333 µs spacing, `pts_us = 0, 33333, 66666, 99999, 133332, 166665, 199998,
233331`, each carrying its own packet duration of 33333 µs. Anchor distance to a single hold, in
milli-wall-units:

```
190, 210, 190, 210, 190, 210, 190, 210
```

Both minimum durations set to `0` µs in the fixture config, so the test isolates the radii.

| Configuration | Expected |
| --- | --- |
| **One radius**, 200 (squared 40000) | **Four** intervals: `[0, 33333)`, `[66666, 99999)`, `[133332, 166665)`, `[199998, 233331)` |
| **Two radii**, attach 200 / release 400 (squared 40000 / 160000) | **One** interval: `[0, 266664)`, with `end_unobserved = true` |

With one radius, `190² = 36100 ≤ 40000` is near and `210² = 44100 > 40000` is far, so the state
alternates every frame. With two radii, the limb enters near at the first frame and never leaves,
because `44100` never exceeds `160000`.

The open interval's end is `pts_us` of the last frame plus **that frame's own packet duration**
from `FrameIndex`, never a nominal frame time (`mvp-contract.md` Section 3), and it is marked
`end_unobserved` rather than clamped (`annotation-guide.md` Section 3).

### 10.4 Occlusion bridging: held, unknown, never `none`

Ten frames at 33333 µs spacing, `pts_us = 0 … 299997`. Occlusion bridge threshold `100000` µs.

**Case A — short gap.** Near at `f0,f1,f2`; **abstained** at `f3,f4`; near at `f5 … f9`.
Gap span `[99999, 166665)` = `66666` µs `< 100000` → **held**.

| Expected |
| --- |
| One contact interval `[0, 333330)`, `end_unobserved = true`. **No `unknown` event. No `none` event.** |

**Case B — long gap.** Near at `f0,f1,f2`; **abstained** at `f3,f4,f5,f6`; near at `f7,f8,f9`.
Gap span `[99999, 233331)` = `133332` µs `> 100000` → **not held**.

| Expected |
| --- |
| Contact interval `[0, 99999)` |
| Abstained `unknown` event `[99999, 233331)` |
| Contact interval `[233331, 333330)`, `end_unobserved = true` |
| **No `none` event anywhere in either case.** Assert this directly, not by inspection. |

### 10.5 Two holds inside the margin

Hold A: square `(0,0)`–`(1000,1000)`. Hold B: square `(1600,0)`–`(2600,1000)`. Attach radius 400
(squared 160000). `min_target_margin = 50` milli-wall-units.

| Anchor | Distance to A | Distance to B | Difference | Expected |
| --- | --- | --- | --- | --- |
| `(1300, 500)` | `300` | `300` | `0` | `target_kind = "unknown"`, `target_ref = null`, `status = "abstained"` |
| `(1250, 500)` | `250` | `350` | `100` | `target_ref = A`, `status = "predicted"`, margin recorded |

The first row is the important one: a naive nearest-hold-with-tie-break returns hold A confidently.
The test asserts it returns `unknown` and asserts `target_ref is None`.

### 10.6 Merge-then-filter versus filter-then-merge

Crafted input: two fragments for one `(limb, hold)` pair, `[0, 20000)` and `[25000, 45000)`.
Config: `max_merge_gap_us = 10000`, `min_contact_duration_us = 30000`.

| Order | Working | Result |
| --- | --- | --- |
| **Merge, then filter** (implemented) | Gap `5000 ≤ 10000` → merge to `[0, 45000)`; duration `45000 ≥ 30000` → keep | **One** interval `[0, 45000)` |
| Filter, then merge | `20000 < 30000` → drop; `20000 < 30000` → drop; nothing left to merge | **Zero** intervals |

The test asserts the implemented order gives one interval, and a second test asserts
`ContactSeries.postprocess_order` records it, so the pin and the behaviour cannot drift apart.

### 10.7 Raw before filtered

Assert that the raw interval document exists on disk, that its hash is recorded, and that the
filtered document's `raw_document_sha256` equals that hash. Assert the raw document's own
`raw_document_sha256` is `null`. Assert that the raw document is written **before** the filtered
one, by checking the run document's ordering of input hashes.

### 10.8 Grep test: the intentional/incidental label is never assigned

A deterministic grader over `src/climbvision/`: the string tokens `intentional_use` and
`incidental_touch` appear **nowhere** outside the ontology definitions that the contract requires.
Any assignment of either value from Stage 5 code fails the build.

### 10.9 End-to-end metric test, reusing the Stage 2 worked examples

Hand-authored predictions and ground truth for one limb and one hold:

| | Interval |
| --- | --- |
| Prediction `P1` | `[0, 100000)` |
| Prediction `P2` | `[200000, 260000)` |
| Ground truth `G1` | `[10000, 110000)` |
| Ground truth `G2` | `[200000, 400000)` |

Temporal IoU, computed by hand:

| Pair | Intersection | Union | tIoU |
| --- | --- | --- | --- |
| `P1`,`G1` | `[10000,100000)` = `90000` | `[0,110000)` = `110000` | `RatioValue{num: 9, den: 11}` |
| `P2`,`G2` | `[200000,260000)` = `60000` | `[200000,400000)` = `200000` | `RatioValue{num: 3, den: 10}` — **exactly 0.3** |

Event F1, with the match convention **`tIoU ≥ level`** pinned by the second row:

| Level | TP | FP | FN | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- | --- |
| `0.1` | `2` | `0` | `0` | `1/1` | `1/1` | `RatioValue{num: 1, den: 1}` |
| `0.3` | `2` | `0` | `0` | `1/1` | `1/1` | `RatioValue{num: 1, den: 1}` |
| `0.5` | `1` | `1` | `1` | `1/2` | `1/2` | `RatioValue{num: 1, den: 2}` |

Boundary errors, signed as `predicted − adjudicated`, integer microseconds, over the matched pairs
at level `0.1`: `-10000`, `-10000`, `0`, `-140000`. Sorted:
`[-140000, -10000, -10000, 0]`. Nearest-rank quantiles, **no interpolation**:

| Statistic | Value |
| --- | --- |
| minimum | `-140000` |
| p25 (rank 1) | `-140000` |
| p50 (rank 2) | `-10000` |
| p75 (rank 3) | `-10000` |
| maximum | `0` |

False-contact time: predicted contact with no adjudicated contact is `[0, 10000)`, so
**`10000` µs**. `P2` lies entirely inside `G2` and contributes zero.

### 10.10 Abstention counts as a false negative at full coverage

Add a ground-truth contact `G3 = [500000, 600000)` over which the baseline emitted an **abstained**
event. Assert that at full coverage:

- the recall denominator **includes** `G3`;
- `G3` is counted as a **false negative**, not omitted;
- the risk-coverage curve at coverage `1` reproduces exactly the full-coverage F1 computed above.

If dropping the abstention changes the number, the test fails. This is the clause that keeps
abstention from being free.

### 10.11 An unattempted limb never serializes a determinate value

The input fixture is deliberately hostile: it carries **observed toe anchors** for both feet, in
the wall plane, one of them **inside the attach radius of a hold**. Nothing in the data stops the
geometry from running on them; only the scope decision does.

| Assertion |
| --- |
| `attempted_limbs` is exactly `["left_hand", "right_hand"]`, in the declared limb order (Section 5.2) |
| Over **every** event in **both** the raw and the filtered document, no event whose `limb` is `left_foot` or `right_foot` has `target_kind == "none"` |
| Nor `"hold"`, `"volume"` or `"wall_region"`. A determinate **positive** claim about an unattempted limb is the same defect facing the other way |
| Any foot event that exists at all has `target_kind == "unknown"`, `target_ref is None`, `status == "abstained"` |
| A hand-authored `ContactSeries` fixture containing a foot event with `target_kind = "none"` **fails validation**, through a model validator on `ContactSeries` that asserts the invariant across `attempted_limbs` and `events`, surfacing as `DOCUMENT_INVALID` from `climbvision validate`. No new error code |
| The assertion runs against the **parsed round-trip** of the canonical bytes, not against the in-memory model alone: the rule is about what serializes |

Both documents are checked, not just the filtered one. A coercion that appears only in the raw
interval set is still a coercion, and the raw document is the one truth rule 4 exists to preserve.

### 10.12 The named hold is always on the problem

The problem's lit hold set is `{H1, H2, H3}`. The panel also carries `H9` at a neighbouring grid
position, **not lit**, whose polygon lies within the attach radius of the anchor.

| Anchor | Expected |
| --- | --- |
| Inside `H1`'s polygon | `target_ref = H1`, `status = "predicted"` |
| Inside `H9`'s polygon, and beyond the definite-none margin of `H1`, `H2` and `H3` | `target_kind = "unknown"`. **Not `H9`** — it is not on the problem. **Not `none`** — the hand is on a hold (Sections 8.5, 8.10) |
| Beyond the definite-none margin of every hold on the panel, lit or unlit | `none` |

Plus a set-level assertion over a real asset for gate clause D9: every emitted `target_ref` is a
member of the problem's lit hold set, scoped to its `WallSet` revision. The expected count of
violations is **zero**, and the count is reported whether or not it is zero.

## 11. Gate

### 11.1 Deterministic clauses — all must pass

| # | Clause |
| --- | --- |
| D1 | `uv run pytest` passes and `uv run ruff check .` is clean |
| D2 | Round-trip byte-identity for all new documents: `model == parse(dump(model))` **and** `dump(parse(dump(model))) == dump(model)` (`evaluation.md` Section 4.2) |
| D3 | Raw intervals preserved in a separate document and referenced by hash from the filtered one (C8) |
| D4 | `contact_label == "unknown"` on **every** emitted event, without exception |
| D5 | Occlusion **never** produces `none` — demonstrated on the Section 10.4 fixture and asserted over the full emitted set on a real asset |
| D6 | Every threshold lives in versioned config with a **unit** and a **selection** string, and **no threshold is hardcoded** — enforced by a grep test over `src/climbvision/contacts/` for bare integer literals in comparison positions |
| D7 | Re-running on identical inputs produces **byte-identical** documents |
| D8 | Metrics reported **per slice**, with **no pooled-only number** anywhere in the report, and the **foot slices present and reading `not_applicable` with their reason** — absent is a failure, `0` is a failure |
| D9 | **No emitted `target_ref` lies outside the problem's lit hold set**, scoped to its `WallSet` revision — asserted on the Section 10.12 fixture and over the full emitted set on a real asset. Expected count zero, reported either way |
| D10 | **An unattempted limb never carries a determinate target.** No foot event with `target_kind` in `{none, hold, volume, wall_region}` in the raw or the filtered document, and a fixture that contains one fails validation (Section 10.11) |

### 11.2 `[PILOT]` clauses — measured and reported, not thresholded

| # | Clause | Reported as |
| --- | --- | --- |
| P1 | Event F1 at tIoU `0.1`, `0.3`, `0.5`, in **both** the target-aware and target-agnostic variants, on the **frozen test split** | Six exact rationals, each with its interval |
| P2 | Boundary-error distribution | Integer quantiles **plus minimum and maximum**, in microseconds |
| P3 | False-contact time | Integer microseconds, **per attempted limb** — left hand and right hand, separately |
| P4 | Risk-coverage curve over the **geometric margin** | Coverage and error rate as pairs of exact rationals, ordered by margin with ties broken by `event_id` |
| P5 | **Abstention rate, per hand**, with the share attributable to **occlusion bridging** separated from the share attributable to **ambiguity** (Sections 8.4, 8.11) | Exact rationals. **No expected value is stated anywhere in this brief**; the direction — higher than a vertical wall would give — is an expectation to be checked against the measurement, never a substitute for it |

Each of P1 through P5 is additionally reported for the three slices of Section 8.8. The **hand**
slice carries numbers; the **foot** slice reads `not_applicable` with its reason; the volume slice
reads `not_applicable` if it is empty on this envelope.

### 11.3 The honest limitation, with the arithmetic shown

This is a `[PLANNING]` calculation about **what the dataset can support**. It is not a result.

| Step | Value | Tag |
| --- | --- | --- |
| Attempts in the release | roughly 50 | `[PLANNING]` |
| Adjudicated contact intervals, **all four limbs** | on the order of 2000 to 3000 | `[PLANNING]` |
| The **hands-only** subset of those, as an illustrative assumption of one half | roughly 1250 | `[PLANNING]` |
| 95% normal-approximation half-width on 1250 intervals at `p ≈ 0.85`: `1.96 × sqrt(0.85 × 0.15 / 1250)` | `≈ 0.020`, i.e. **±2.0 percentage points** | `[PLANNING]` |
| The same at `p = 0.5`, the worst case: `1.96 × sqrt(0.25 / 1250)` | `≈ 0.028`, i.e. **±2.8 percentage points** | `[PLANNING]` |
| `(hand, lit hold)` cells per problem version: 2 hands by 8 to 15 lit holds | 16 to 30 | `[PLANNING]` |

**The one-half assumption is an assumption, not a measurement.** Nobody has counted how the
adjudicated intervals split between hands and feet on this envelope. Substitute the measured hand
count as soon as Stage 2 reports it, and recompute; until then every half-width above is
illustrative, and the direction of the error is known — a smaller hand subset widens it.

**What that buys, and what it does not.**

- A **pooled** event F1 over hands to roughly ±2 to ±3 percentage points `[PLANNING]`.
- **Per-hold performance is unmeasurable.** How many intervals reach any one `(hand, lit hold)` cell depends entirely on how many attempts landed on that problem version, which is the same concentration precondition Stage 7 needs. Spread thinly across problems, no cell is measurable at all.
- **The independence assumption is wrong**, and it flatters the number. Intervals within one attempt are correlated. For anything that varies at the attempt level, the effective unit is the **attempt**, not the interval: at 50 attempts and `p ≈ 0.85` the half-width is `1.96 × sqrt(0.85 × 0.15 / 50) ≈ 0.099`, i.e. **±9.9 percentage points** `[PLANNING]`. That figure does not improve by dropping feet — the attempt count is unchanged. Report both, and say which unit each number used.
- **Feet are not attempted** (Section 7.4), so the foot slices carry **no support at all** — not low support, none. `not_applicable` is the only honest entry, and when feet return they need their own annotation, their own visibility measurement on this envelope and their own power calculation before any foot number means anything.
- Every number is **within-participant, within-gym and on one board** (Section 0.5, Section 1.1).
- **`volume` and `wall_region` targets are unpredicted by design** (Section 7.3). Their annotated time is reported as a **known, quantified gap**, in microseconds, not excluded. On a flat panel `volume` is expected to be empty, which is `not_applicable`, not zero.

### 11.4 What this stage does not prove

- Nothing about **intentional use**. Load is not observable, and the baseline never claims it.
- **Nothing about feet.** Not that foot contacts are hard, not that they are easy, not that they are rare: the MVP does not look at them (Section 7.4). A foot slice reading `not_applicable` is a statement about scope, not a result.
- Nothing about a different climber, gym, camera placement or lighting condition.
- **Nothing about a wall that is not this board.** A radius, a margin and a bridge threshold selected on a fixed grid under a fixed overhang are selected against that geometry. A spray wall changes the candidate density, and a vertical wall changes the occlusion (Sections 8.10, 8.11).
- Nothing about performance outside the fiducial hull beyond what the hull slice measures.
- Nothing about `volume` or `wall_region` targets, which the baseline abstains on entirely.
- Nothing about what a **learned** model could do. The baseline sets a floor, not a ceiling.

## 12. Verification commands

Repository-relative. Placeholders in angle brackets.

```
uv sync
uv run pytest
uv run ruff check .

uv run climbvision contacts <asset_id> \
  --wall-set <wall_set_id> \
  --problem <problem_version_id> \
  --out artifacts

uv run climbvision validate \
  artifacts/recordings/<asset_id>/contact_series.raw.json \
  artifacts/recordings/<asset_id>/contact_series.json \
  artifacts/recordings/<asset_id>/runs/<run_id>.contacts.json

uv run climbvision contacts-eval  --release <release_id> --split validation
uv run climbvision contacts-sweep --release <release_id> --split validation --out artifacts/sweeps
```

Then, and only then, **exactly once, at the end**, through the mechanism fixed by the Stage 2
`test-set-evaluation-policy` decision:

```
uv run climbvision contacts-eval --release <release_id> --split test
```

Byte-identity check for D7, run twice and compared:

```
uv run climbvision contacts <asset_id> --wall-set <wall_set_id> --problem <problem_version_id> --out artifacts_a
uv run climbvision contacts <asset_id> --wall-set <wall_set_id> --problem <problem_version_id> --out artifacts_b
diff artifacts_a/recordings/<asset_id>/contact_series.raw.json \
     artifacts_b/recordings/<asset_id>/contact_series.raw.json
diff artifacts_a/recordings/<asset_id>/contact_series.json \
     artifacts_b/recordings/<asset_id>/contact_series.json
```

Plus the offline check from `AGENTS.md` Section 9. Stage 5 adds no dependency and touches no
model, so the **entire** Stage 5 test suite must pass with `ffprobe` absent, no backend installed
and sockets blocked. Report the count.

## 13. Traps

Sixteen. Each one has a specific, named consequence.

| # | Trap | Consequence if missed |
| --- | --- | --- |
| 1 | **The half-open off-by-one.** `[start_us, end_us)`; `end_us` is the timestamp of the first frame **without** contact and is not part of the interval. It recurs here because **interval construction is new code**, even though Stage 2 already fixtured the convention. | Every interval is one frame long in the wrong direction. Two consecutive contacts either overlap by one frame or leave a one-frame hole, and the boundary-error distribution acquires a constant offset that looks like a real bias. |
| 2 | **Hysteresis flapping with one radius.** | It produces a **beautiful number at the loosest overlap level and a catastrophic one at the strictest.** Dozens of one-frame intervals each overlap the ground truth slightly, so tIoU `0.1` looks fine and tIoU `0.5` collapses. Reading only the loosest level hides it completely. |
| 3 | **Filtering before merging.** | It **deletes the fragments that would have merged into a valid interval** (Section 10.6: one interval becomes zero). The system then reports a missed contact where the geometry was actually right. |
| 4 | **Occlusion ending the contact.** This is the **most likely domain bug in the stage** and it is explicitly banned by `annotation-guide.md` Section 3. | Every contact is chopped at every self-occlusion. Event F1 collapses at the strict overlap levels, the boundary-error distribution becomes bimodal, and the cause looks like a geometry problem. |
| 5 | **Abstention accounting.** Dropping abstained predictions from the denominator. | **Precision looks excellent** and the **risk-coverage curve becomes meaningless**, because the whole curve measures what abstention costs. A system that abstains on everything scores perfectly. |
| 6 | **Calibration error propagating.** A pixel-level error becomes a wall-plane error that **grows with distance from the fiducial hull** and lands directly on the attach radius. | Contacts far from the fiducials get systematically wrong radii. This is exactly what the inside/outside-hull slice diagnoses, which is why that slice is not optional. |
| 7 | **Adjacent holds.** Two small holds a few centimetres apart on a dense wall are inside any usable radius of each other. | Without the margin abstention (Section 8.4), the system **confidently names the wrong hold**, and the target-agnostic F1 stays high while the target-aware F1 quietly drops. |
| 8 | **Proximity is not use.** A hand hovering over a hold for a whole move is not a contact, and the baseline cannot tell the difference. | This is exactly why the baseline **never labels intentional use** (truth rule 9, `annotation-guide.md` Section 1). Any attempt to infer it from dwell time is a load claim from monocular RGB. |
| 9 | **An unattempted foot coerced to a determinate value.** The single most likely way this stage's scope cut becomes a lie in the data: "we did not attempt it" serializing as "it was not touching anything". It arrives disguised as tidiness — a default, an empty target, a `None` that dumps as `"none"`. | A reader, a Stage 6 configuration and a Stage 7 count all take `none` as a **claim about the world**. The system asserts a foot was off the wall in frames where no code ever looked at that foot. Sections 5.4, 10.11, clause D10. |
| 10 | **Feet are not small hands**, and the seam must survive their absence. Toe anchors are less visible and more often occluded, and on this envelope worst of all (Section 8.11). | Deleting the per-foot threshold overrides while feet are deferred means retrofitting the seam later and **re-running every measurement** to select the foot radii against a config shape that changed. Keep them, unselected, with the reason in the `selection` string (Section 8.9). |
| 11 | **Dropping the foot slices instead of reporting them `not_applicable`.** | A report with no foot row is indistinguishable from a report whose foot row was removed because it looked bad. `not_applicable` **with the reason** is the output; absent and `0` are both defects, and `0` is the worse of the two because it reads as a measurement (Section 8.8, clause D8). |
| 12 | **Reading the board's sparser candidates as an improvement in the method.** Ambiguity abstention fires less often here than it would on a spray wall. | It is a property of the **equipment**: lit holds sit on a fixed grid, far apart. Quoting the low rate as evidence that the abstention rule is unnecessary generalizes a fact about the panel into a claim about the algorithm, and the first dense wall it meets confidently names the wrong hold (Sections 8.4, 8.10). |
| 13 | **`none` on an unlit hold.** The candidate set is restricted to the problem's lit holds, and the naive consequence is that a hand on any other hold is "far from every candidate", therefore `none`. | The system asserts "demonstrably not in contact" about a hand that is visibly on a hold. Unlit holds are `none`-suppressors and never targets: the answer there is `unknown` (Sections 8.5, 8.10, test 10.12). |
| 14 | **Tuning on test.** | The sweep runs on **validation**; the frozen split is evaluated **once** (`mvp-contract.md` Section 8, `evaluation.md` Section 2). A number tuned on test is not a measurement, and the release cannot be un-contaminated afterwards. |
| 15 | **Squaring destroys the sign.** Trying to carry a signed distance through a squared comparison. | Inside points come out looking far away. Carry `(inside, squared_distance)` as a pair; an inside point has effective squared distance zero. |
| 16 | **Flooring the perpendicular distance.** `cross² / t_den` is a **rational**, not an integer. | Flooring it to fit an `int` breaks exactness at exactly the radius boundary the hysteresis is testing, so the "exact integer arithmetic" claim becomes false precisely where it matters. Carry the `RatioValue` and cross-multiply (C1, C2). |

## 14. Report format and stop condition

As Section 0.6, with these stage-specific requirements:

- The gate table has **one row per clause** from Sections 11.1 and 11.2 — ten deterministic, five `[PILOT]` — using the clause ids `D1`–`D10` and `P1`–`P5`. A clause whose data does not exist reads **`pending measurement`**.
- **No pooled-only number appears anywhere.** Every `[PILOT]` number is accompanied by its hands/feet, inside/outside-hull, and volume/wall slices. A pooled number without its slices is a rejected report, not an incomplete one.
- **The foot slices appear in every table, reading `not_applicable` with the reason.** A report that omits them, or that prints `0`, is rejected on that ground alone (Section 8.8).
- The **abstention rate per hand** is reported, split into its occlusion-bridging and ambiguity shares, together with a sentence saying whether it came out higher or lower than the vertical-wall expectation in Section 8.11 — and no expectation is reported as though it were the measurement.
- The **count of emitted `target_ref`s outside the problem's lit hold set** is reported, whether or not it is zero (clause D9).
- Both interval widths from Section 11.3 are reported — the interval-as-unit one and the attempt-as-unit one — with the unit named beside each, and the **measured hand share of the adjudicated intervals** substituted for the one-half assumption if Stage 2 has reported it.
- The **annotated time on `volume` and `wall_region` targets** is reported, in integer microseconds, as a known quantified gap.
- The **sweep** is reported: the grid searched, the metric optimized, the split, the release id, and the chosen values, matching the `selection` strings written into `configs/contacts/v1.json` byte for byte.
- The report states, in one sentence, that the frozen test split was evaluated **once**, and names the command and the timestamp.

The reviewer independently re-measures every clause rather than accepting the implementer's
numbers: re-runs the commands, re-computes the F1 from the emitted documents against the
adjudicated annotations, re-derives the risk-coverage curve, independently checks that no `none`
event exists over an occluded span, and independently checks the emitted documents for **any
determinate target on a limb outside `attempted_limbs`** and for **any `target_ref` outside the
problem's lit hold set**. Those last two are set-level greps over the artifacts, not a reading of
the implementer's table.

Then **stop** and wait for the owner's decision. Do not open Stage 6.

## 15. Read-first list

In this order, before writing anything.

| File | Read for |
| --- | --- |
| `AGENTS.md` | The binding rules. Sections 2, 3, 4, 5, 6, 9 and 11 in full. |
| `docs/mvp-contract.md` | Sections 2 (force and load out of scope), 3 (half-open intervals), 4 (coordinate spaces), 5 (the contact-target and contact-label ontologies, and the two standing rules), 6 (attempt, intentional use, occlusion), 8 (split policy), 9 (the Stage 5 gate row), 10 (provenance classes, confidence never increases downstream) |
| `docs/evaluation.md` | Section 1 "Stage 5 — contact intervals" — temporal IoU, event F1, boundary error, false-contact time, risk-coverage, and the three `[FIXED]` tIoU levels. Section 2 (split and leakage). Section 3 (capability versus regression). Section 4.2 (round-trip). Section 5 (when a gate fails). |
| `docs/annotation-guide.md` | Section 0 (answer `unknown` rather than guessing), **Section 3 (bounding a contact interval — the half-open rule, shared boundaries, unobserved boundaries, and the ban on occlusion ending a contact)**, Section 1 (intentional versus incidental), Section 6 (adjudication) |
| `docs/data-schema.md` | Sections 1 (`ContactEvent` is due at Stage 5; `MoveEvent`, `BetaSequence`, `FallEvent` are not), 3 (identity rules, problem ID scoped to `WallSet`), 4 (versioning), 5 (provenance), 7 (serialization, no floats) |
| `docs/status.md` | The ledger shape, the Stage 1 measured-evidence table you are copying, and the Stage 4 endpoint accuracy with its interval |
| `docs/agents/briefs/stage-4-pose.md` | What an anchor observation actually contains, when it abstains, and what the wall projection nulls |
| `docs/agents/briefs/stage-3-wall-and-holds.md` | The hold polygon representation, the homography, and what "fiducial hull coverage" means |
| `docs/agents/briefs/stage-2-annotation-harness.md` | The evaluation library you are reusing, its worked metric examples, the release manifest, and the `test-set-evaluation-policy` mechanism |
| `src/climbvision/quality.py` | The integer cross-multiplication pattern (C2) and the config-threshold accessor that raises `CONFIG_THRESHOLD_MISSING` |
| `src/climbvision/timebase.py` | `pts_to_us`, `us_to_pts` — integer arithmetic only, rounding half away from zero |
| `src/climbvision/serialization.py` | `dumps_canonical` is the **only** `json.dumps` in the codebase |
| `src/climbvision/schema/provenance.py` | `IngestRun`, the model C5 says to copy exactly |
| `src/climbvision/schema/versions.py`, `src/climbvision/schema/__init__.py` | The three registration points |
| `src/climbvision/cli.py` | Subcommand shape, exit codes, and `schema_id`-based dispatch |
| `tests/unit/test_scope_guard.py` | The guards you are about to extend, and the comment explaining why the inventory set is pinned |
| `tests/unit/test_schema.py` | `DOCUMENT_MODELS`, `ALL_MODELS`, and the float-annotation walker |
| `tests/conftest.py` | `block_network` and the fixture paths |
| `configs/ingest/v1.json` | The exact config shape C9 says to copy, including the `selection` string convention |
