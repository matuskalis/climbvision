# Stage 7 - repeated-attempt descriptive analytics

Status tags as defined in the preamble of [`mvp-contract.md`](../../mvp-contract.md). This brief
is a complete context package for an agent that starts with no memory of this repository.

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

Expose **only** metrics directly derived from validated primitives:

- the projected hip trajectory;
- move duration;
- contact dwell;
- explicitly defined hesitation observations;
- foot-adjustment counts;
- success and failure grouping;
- transition failure hazard, with uncertainty.

Return `insufficient_data` whenever support is inadequate.

Inputs: Stage 6 attempts, moves and fall events; Stage 5 contact intervals; Stage 4 pose, for the
hip keypoints and joint velocity; and Stage 2 adjudicated outcomes. Definitions of foot
adjustment, hesitation, crux and hip trajectory are in `docs/mvp-contract.md` Section 6 and are
not restated here.

## 2. Preconditions

| # | Precondition | Why |
| --- | --- | --- |
| 1 | The Stage 6 gate is recorded in `docs/status.md` | Every move, attempt and last-stable-configuration this stage aggregates is Stage 6 output |
| 2 | **Adjudicated outcomes exist for every attempt used in the hazard denominator** | `mvp-contract.md` Section 10 requires the transition failure hazard to be derived **from `adjudicated_ground_truth` outcomes**, not from Stage 6's derived candidate |
| 3 | The Stage 6 report's per-attempt `insufficient_data` count is known | It is the floor on how many attempts this stage can aggregate at all |

## 3. Human inputs required before the agent starts

**No new human input**, *provided* the filming advice in the operating manual Section 3.8 was
followed and roughly twenty-five attempts `[PLANNING]` landed on a single problem.

**If that did not happen, say so to the owner now, before writing code.** The consequence is not
subtle: the transition failure hazard needs repeats of the **same problem** by the same climber,
and attempts spread thinly across problems produce nothing for this stage. Most hazards will
return `insufficient_data`, and no amount of code changes that. The smallest experiment that
changes it is **one more filming session concentrated on one already-filmed problem, before that
wall is reset** (`mvp-contract.md` Section 5: problem identity does not survive a `WallSet`
revision). Offer that, then wait.

One decision must be approved before the agent starts.

| | |
| --- | --- |
| Decision | `uncertainty-method-and-support-threshold` |
| Recommended method | A **binomial score interval at 95 percent, without continuity correction** (the Wilson score interval), computed once per hazard and quantised to integer bounds per ten thousand |
| Why not the alternatives | The normal-approximation interval is wrong at small counts and can produce bounds outside `[0, 1]`, which is exactly the regime this dataset lives in. The exact interval requires a beta quantile, which is heavier arithmetic for no gain at these counts. Both remain open; the ADR records which was chosen and why |
| Always stored | The **raw success and trial counts**, so that anyone can recompute the interval under a different method without re-running the pipeline |
| Recommended support threshold | `[PILOT]`, selected on validation data, with a recommended floor of **8 attempts `[PLANNING]`** that the selection record must not go below without stating why |
| What the ADR records | The method by name, the quantile constant as an exact rational, the quantisation denominator, the directed-rounding rule, the support threshold and its selection evidence |

`crux-rule` (Section 7) is the second open decision. It does **not** block the start: the agent
proposes, the owner decides at the report.

## 4. Deliverables

Module paths are **proposals**.

| Path (proposed) | Owns |
| --- | --- |
| `src/climbvision/aggregate/__init__.py` | Package marker and public entry points |
| `src/climbvision/aggregate/hips.py` | The hip midpoint and the hip trajectory document |
| `src/climbvision/aggregate/durations.py` | Move duration and contact dwell aggregates |
| `src/climbvision/aggregate/velocity.py` | Per-joint velocity between consecutive observed samples, with its abstention rule |
| `src/climbvision/aggregate/hesitation.py` | Hesitation observations |
| `src/climbvision/aggregate/adjustments.py` | Foot-adjustment counts and hand re-grab counts |
| `src/climbvision/aggregate/hazard.py` | Transition failure hazard and the uncertainty interval. The interval arithmetic may live here or in its own module; either way its functions must be directly unit-testable against hand arithmetic |
| `src/climbvision/aggregate/report.py` | Assembly of the aggregate documents and the support report |
| `src/climbvision/schema/aggregate.py` | The aggregate document models |
| `src/climbvision/schema/provenance.py` | Extended with the aggregate run document, beside `IngestRun` |
| `configs/aggregate/v1.json` | Every threshold in Section 8.8 |
| `docs/adr/<slug>.md` x2 | `uncertainty-method-and-support-threshold` and `crux-rule`, created one at a time, when decided |

### Seams to update

Same list as every stage: schema constants and `SCHEMA_IDS`; `MODEL_REGISTRY` and `__all__`;
`DOCUMENT_MODELS` with committed golden fixtures and `ALL_MODELS`; a **new** `STAGE_SEVEN_MODULES`
set beside the existing ones in `tests/unit/test_scope_guard.py`, with `ALLOWED_THIRD_PARTY` and
`BANNED` unchanged and non-intersecting; the dependency pin unchanged; a CLI subcommand with
exit-code tests and a registry-driven `validate` test; `configs/aggregate/v1.json`; the Stage 7
row of `docs/status.md`; contract documents only if a decision authorises it; decision records one
at a time under `docs/adr/`; the manual fixture script left manual; the ignore rules unchanged.

## 5. Entities

**`MetricValue` is a Stage 2 entity** (`docs/data-schema.md` Section 1, and the note in that
section explaining why: Stage 2's own gate is a measured agreement number and `MetricValue` is the
output type of every evaluation from Stage 2 onward). Move durations, contact dwells,
foot-adjustment counts and every other scalar aggregate are emitted **as `MetricValue` records
using Stage 2's model**. Do not define a second metric type here.

Three entities are new at this stage.

### Hip trajectory

| Field | Representation | Notes |
| --- | --- | --- |
| Attempt id | | |
| Coordinate space | Exactly one of `source_px`, `stabilized_px`, `wall_plane` | Required. A geometry value with no declared space is a defect (`mvp-contract.md` Section 4) |
| Samples | Ordered list, one per pose observation | Each sample carries: frame-index position; presentation timestamp in integer microseconds; a **nullable** point in integer milli-units; a visibility label from the closed visibility set; and a status of `observed` or `abstained` |
| Definition | A type that admits **exactly one value**: `midpoint of observed 2D hip joints` | |

The single-valued definition field makes the schema enforce rule 7. A field that can only say what
the thing is cannot be quietly relabelled by a future caller, and it puts the correct phrase in
front of anyone reading the raw JSON.

### Transition hazard

| Field | Representation | Notes |
| --- | --- | --- |
| Problem version id | | |
| From configuration id, to configuration id | Stage 6 configuration ids | An ordered pair |
| Failure count | Integer, **never null** | |
| Attempts at risk | Integer, **never null** | The support. It is why a row is `insufficient_data`, so it is always present |
| Hazard | Exact rational, **nullable** | Failures over attempts at risk, reduced by gcd |
| Interval bounds | Two nullable integers, per ten thousand | Both null whenever the hazard is null |
| Interval method | String naming the method | Never a bare number with no method |
| Status | `measured` or `insufficient_data` | |

### Hesitation observation

| Field | Representation | Notes |
| --- | --- | --- |
| Attempt id | | |
| Configuration id | The stable configuration the observation sits in | |
| Interval | Integer microseconds, half-open | |
| Maximum joint speed | Stored as an exact **squared** rational, see Section 8.4 | With its unit spelled out and the joint identified |
| Definition id | String | The identity of the rule that produced this observation |

Nothing else. No label, no adjective, no interpretation.

### Aggregate run

Modelled exactly on `IngestRun` (C5), pointing at its inputs by hash and at its outputs by hash,
append-only, one per execution.

## 6. Decisions already frozen

| Frozen item | Where | Consequence here |
| --- | --- | --- |
| Hip trajectory is the midpoint of the observed 2D hip joints, never called or used as a centre of mass | `mvp-contract.md` Sections 2, 6, rule 7 | Section 8.1, and the grep test in Section 10 |
| Centre-of-mass claims, 3D biomechanics, force and load inference are out of scope permanently | `mvp-contract.md` Sections 2, 11 | No mass, no force, no 3D anywhere in this stage |
| No composite score of any kind | Rule 2, `mvp-contract.md` Section 2 | Enforced by a grep in the gate |
| Hesitation is **not** a quality judgement; only dwell and low-velocity intervals are recorded | `mvp-contract.md` Section 6 | Section 8.4 |
| Foot adjustment is a count of observed events, not an inference about intent or nerves | `mvp-contract.md` Section 6 | Section 8.5 |
| A crux is a statistically supported failure concentration at the transition level, never the slowest move, never the last hold reached, never from one attempt | `mvp-contract.md` Section 6 | Section 7 |
| The transition failure hazard is derived **from `adjudicated_ground_truth` outcomes** | `mvp-contract.md` Section 10 | Precondition 2, and Section 8.6 |
| Below the support threshold the aggregate returns `insufficient_data`; it does **not** return a value with a wide interval, and it does not return a point estimate with a disclaimer | `evaluation.md` Section 1, Stage 7 | Section 8.6 and trap 5 |
| Every aggregate reports unit, coordinate space where geometric, support and uncertainty | `evaluation.md` Section 1, Stage 7 | Gate clause D7 |
| Time is never computed from a frame counter | `mvp-contract.md` Section 3 | Section 8.2 |
| Conventions C1 to C10 | Section 0 | |

## 7. Open decisions

### `uncertainty-method-and-support-threshold`

Detail in Section 3. It must be recorded before the first hazard is written, because the interval
method is part of the hazard document and a stored bound with no recorded method is unreadable.

### `crux-rule`

| | |
| --- | --- |
| Question | May this stage use the word "crux", and under what rule? |
| Proposal | A transition is labelled a crux only if **both**: its support meets the threshold, **and** its interval's lower bound exceeds the upper bound of the problem's pooled hazard interval |
| Expected behaviour | With roughly ten transitions per problem `[PLANNING]` this will almost never fire. **That is the correct behaviour**, not a bug to be tuned away |
| Multiplicity | The rule needs no multiplicity correction because it is a **stated rule**, not a hypothesis test. It makes no probabilistic claim and reports no p-value |
| Alternative | Emit hazards and **never use the word crux at this stage**. This is a legitimate outcome and costs nothing except a label |
| What the ADR records | Which option, the exact comparison, and the statement that a crux label is a rule outcome and not a significance claim |

## 8. Approach

### 8.1 The hip midpoint

The integer midpoint of the two hip keypoints, in milli-units, with **floor division**, pinned by
a test whose coordinate sum is **odd** (an even sum cannot distinguish floor division from any
other rounding rule). Floor division floors toward negative infinity, which is consistent for
negative coordinates and must stay that way.

If **either** hip keypoint is absent, the sample is `abstained` with a **null** point and its
visibility label preserved. **There is no interpolation.** A smoothed series, if it is ever
wanted, is a **separate document** with `derived` provenance, a named filter and its parameters,
referencing the raw series by hash (C8, rule 4). It is not a field on this one.

### 8.2 Velocity

Computed **only between consecutive observed samples**. The time delta comes from the
**presentation timestamps**, never from a nominal frame rate. If the delta exceeds its threshold,
the velocity **abstains** rather than dividing across the gap.

State the precedent plainly, because it is the reason this paragraph exists: the **first finding
of the Stage 1 review was a fabricated frame-rate delta computed across a timestamp gap**
(`docs/status.md`, Stage 1 row). The identical defect is available here, in a different module,
against a different array. The reviewer will look for it, and the test in Section 10 reproduces
it.

Velocity is an exact rational: displacement in milli-units over the delta in microseconds, scaled
to milli-units per second and reduced by gcd (C1).

### 8.3 No square roots in the schema

Speed is the magnitude of a displacement vector, which is a square root, and a square root is not
a rational. Two consequences, both mandatory:

1. **Threshold comparison uses squared quantities**: compare the squared speed against the squared
   threshold by integer cross-multiplication (C2). No square root is taken at all.
2. **What is stored is what was computed**: the maximum **squared** speed as an exact rational,
   with its unit spelled out, plus the joint and the sample pair that produced it. A rounded speed
   is a derived value that invites comparison against differently-rounded values, and byte-identity
   dies with it.

### 8.4 Hesitation observations

A hesitation observation is a **stable segment** whose duration is at least the hesitation dwell
threshold and whose **maximum tracked-joint speed over the whole segment** stays below the speed
threshold. It is emitted as an observation with its definition id.

**No adjective appears anywhere in the output.** Not in a field name, not in a value, not in a
template. The system never asserts that the climber was uncertain, scared, tired or reading the
route (`mvp-contract.md` Section 6).

### 8.5 Foot adjustments, and the partition with moves

A foot adjustment is an occurrence within an attempt where a foot releases and re-attaches such
that the **stable configuration before and after is identical**. That is exactly the case Stage 6
excludes from moves. The two definitions are complementary **by construction**:

| Bracketing stable configurations | Stage 6 | Stage 7 |
| --- | --- | --- |
| Identical | not a move | one foot adjustment (foot) or one hand re-grab (hand) |
| Different | inside exactly one move | not an adjustment |

A test asserts that every release-and-re-attach occurrence is counted **exactly once**, as one or
the other, never both and never neither.

The contract defines the **foot** case only (`mvp-contract.md` Section 6). A hand release and
re-attach with an identical bracketing configuration is a **hand re-grab**, counted under its own
definition id and **never folded into the foot-adjustment count**. If the owner would rather not
have that second count at all, dropping it is a smaller change than merging it, and merging it is
a silent redefinition of a contract term.

### 8.6 The transition failure hazard

For an ordered pair of configurations within one problem version:

| Quantity | Definition |
| --- | --- |
| Attempts at risk | The attempts that **reached** the from-configuration |
| Failures | Those among them whose **adjudicated** outcome was `fall` **and** whose last stable configuration was that from-configuration |
| Hazard | Failures over attempts at risk, as an exact rational reduced by gcd |

If the attempts at risk fall below the support threshold, the status is `insufficient_data`, the
hazard is `null`, **and the interval bounds are null too**. No number is printed. The failure
count and the attempts-at-risk count remain populated: they are the observed support and the
reason the row is insufficient, and nulling them would leave a row that says nothing at all.

The interval is computed once from the two integer counts, using directed rounding so that
quantisation can only **widen** the interval, never narrow it: the square root is taken with the
integer square root of a scaled integer (never a floating-point square root), rounded up for the
half-width; the lower bound is then floored and the upper bound ceiled at the per-ten-thousand
scale. The scale used for the integer square root is a `[FIXED]` constant chosen so that its
truncation error is orders of magnitude below one per-ten-thousand unit.

### 8.7 Propagation

Any aggregate whose inputs include an attempt with `insufficient_data`, or an attempt whose
unknown fraction exceeds its threshold, **inherits `insufficient_data`**. A mean over moves whose
contacts were unknown is not a mean (rule 15).

### 8.8 Thresholds

All in `configs/aggregate/v1.json`, in the shape of `configs/ingest/v1.json`, each with value,
unit, status and a selection string. A `[PILOT]` entry carries a placeholder value and the
selection string `"Not selected. [PILOT] placeholder; no validation data exists."`

| Threshold (proposed name) | Unit | Status | Controls |
| --- | --- | --- | --- |
| `min_support_attempts` | count | `[PILOT]`, recommended floor 8 `[PLANNING]` | Hazard abstention |
| `hesitation_dwell_us` | microseconds | `[PILOT]` | Hesitation observation |
| `hesitation_max_speed_squared` | milli-units squared per second squared | `[PILOT]` | Hesitation observation |
| `max_velocity_gap_us` | microseconds | `[PILOT]` | Velocity abstention |
| `max_unknown_input_fraction` | rational, unitless | `[PILOT]` | Aggregate abstention |
| `interval_method` | string | `[FIXED]` on adoption of the decision | Which interval |
| `interval_quantile_constant` | rational | `[FIXED]` on adoption | The 95 percent normal quantile as an exact rational |
| `interval_quantisation_denominator` | count | `[FIXED]` on adoption, proposed 10 000 | Bound granularity |
| `integer_sqrt_scale` | count | `[FIXED]` on adoption | Integer square-root precision |

## 9. Dependencies

**Add nothing.** The interval needs one square root on two scalars, computed once and quantised;
that is the standard-library integer square root over a scaled integer, not a numerical library.
There is **no statistics library and no dataframe library** at this stage: `BANNED` in
`tests/unit/test_scope_guard.py` already lists `scipy`, `pandas` and `sklearn`, and it stays that
way, while `numpy` stays path-scoped to the modules Stage 4 authorized and is not imported here.
This stage adds no dependency beyond those Stage 4 authorized.

## 10. Tests

Every expected value below is **hand-calculated**. Numbers in this section are arithmetic and
fixture facts, not thresholds, and are untagged by the convention in `AGENTS.md` Section 8.

| # | Test | Expected |
| --- | --- | --- |
| T1 | Hip midpoint. Left hip at `(1 234 567, 2 345 678)`, right hip at `(1 234 568, 2 345 679)`, milli-units | `(1 234 567, 2 345 678)`. Both sums are odd, so this pins **floor division** and would fail under round-half-away |
| T2 | One hip absent | Sample status `abstained`, point `null`, visibility preserved. **No single-hip fallback**, no interpolation |
| T3 | Naming, which is rule 7 as a test | A grep over `src/`, `tests/` and the emitted documents for centre-of-mass vocabulary (`center_of_mass`, `centre_of_mass`, `com`, `centroid`, `mass`) returns nothing except, if present, an explicit refusal comment |
| T4 | **The Stage 1 regression, reproduced.** Two samples separated by more than `max_velocity_gap_us` | Velocity `abstained`. **Not** a number divided across the gap. A second case with a delta below the threshold returns the exact rational |
| T5 | Hazard, measured. 2 failures in 8 attempts at risk, quantile constant `1.96`, quantisation denominator `10 000` | Hazard `1/4` exactly. Interval bounds `714` and `5908` per ten thousand under floor-lower/ceil-upper quantisation, that is `7.14` to `59.08` percent. The rounding rule is pinned by this test, not left to the implementation |
| T6 | The same input under a support threshold of `10` | Status `insufficient_data`; hazard, both bounds **and** the metric value all `null`; failure count `2` and attempts at risk `8` **still present** |
| T7 | Serialisation of an insufficient-data metric | Emits `null` for value, numerator, denominator and both bounds. A number that should not be read must not be printed |
| T8 | The move/adjustment partition | Every release-and-re-attach occurrence in a hand-authored attempt is counted **exactly once**, as a move or as an adjustment, never both and never neither. Reuse the Stage 6 decisive fixture, whose same-target case gives zero moves and whose different-target case gives one |
| T9 | Hesitation record shape | Carries only interval, speed, configuration, attempt and definition id. A grep for judgement vocabulary (`hesitant`, `uncertain`, `scared`, `tired`, `nervous`, `struggled`, `confident`) over `src/` and the emitted documents returns nothing |
| T10 | Propagation | An aggregate over an attempt marked `insufficient_data` returns `insufficient_data`, not a partial mean |
| T11 | The denominator | Attempts that never reached the from-configuration are **excluded** from attempts at risk. A fixture with three attempts, two of which reached the configuration, gives an attempts-at-risk of `2`, not `3` |
| T12 | Provenance of the outcome | The hazard reads the **adjudicated** outcome. A fixture whose derived candidate and adjudicated label disagree gives the adjudicated answer, and a test asserts the derived candidate is not read on that path |
| T13 | Round-trip | `model == parse(dump(model))` and byte-identical re-serialization for every new document |
| T14 | Registry | `climbvision validate` resolves each new document by its own `schema_id` |

The suite stays hermetic: `block_network` in `tests/conftest.py` stays in force, and no new
external tool is introduced.

## 11. Gate

**This stage's gate is mostly deterministic.** `mvp-contract.md` Section 9 states it as a
**support threshold to be chosen and honoured**, not as an accuracy. Do not invent an accuracy
target for Stage 7; there is none, and a number that looks like one would be a fabrication.

### Deterministic clauses

| # | Clause | Assertion | Evidence |
| --- | --- | --- | --- |
| D1 | Tests and lint | `uv run pytest` all pass; `uv run ruff check .` clean | pending measurement |
| D2 | Round-trip | Byte-identical re-serialization for every new document | pending measurement |
| D3 | Abstention below support | `insufficient_data` returned below the support threshold, with **every numeric field null** | pending measurement |
| D4 | Propagation | `insufficient_data` propagates through every dependent aggregate | pending measurement |
| D5 | Naming | The hip trajectory is never called or used as a centre of mass, enforced by a grep test | pending measurement |
| D6 | Velocity | Never computed across a timestamp gap | pending measurement |
| D7 | Metric completeness | Every metric carries its unit, its coordinate space where geometric, its support and its uncertainty | pending measurement |
| D8 | Partition | Moves and foot adjustments partition the release-and-re-attach events exactly | pending measurement |
| D9 | Denominator | Hazard denominators are **attempts at risk**, not all attempts | pending measurement |
| D10 | No composite score | No composite score exists anywhere, enforced by a grep | pending measurement |

### `[PILOT]` clauses

| # | Clause | Reported as |
| --- | --- | --- |
| P1 | The **support threshold itself**, selected on validation data | The number, with its selection reasoning recorded in `docs/status.md` |
| P2 | The hesitation dwell and speed thresholds | The numbers, with their selection reasoning |

### Honest limitation

Read this before writing code, and repeat it in the report.

With about fifty attempts `[PLANNING]`, of which about twenty-five `[PLANNING]` are concentrated
on one problem, the remainder leaves roughly four to six problems `[PLANNING]` with enough repeats
to define any transition at all. **Most transitions will have between three and eight attempts at
risk `[PLANNING]` and will return `insufficient_data`.**

The following is a `[PLANNING]` calculation about what this dataset can support. It is not a
result and nothing has been measured. At **eight** attempts at risk with **two** failures, the 95
percent binomial score interval runs from about **7 percent to about 59 percent** `[PLANNING]`,
that is from "rare" to "more often than not". A hazard whose interval spans that range does not
distinguish a hard move from an easy one.

If the owner did concentrate about twenty-five attempts `[PLANNING]` on one problem, that problem
may yield one or two transitions `[PLANNING]` with enough support for a hazard that is merely
**wide** rather than useless. **No crux claim should be expected from this dataset.**

**Report the count of transitions that returned `insufficient_data` as a headline number in the
gate table, not as a footnote.** It is the single most informative number this stage produces.

## 12. Verification commands

```bash
uv sync
uv run pytest
uv run ruff check .

# Aggregate for one problem
uv run climbvision aggregate --problem <problem_version_id> --out artifacts

# Aggregate a single named metric, so one number can be traced end to end
uv run climbvision aggregate --problem <problem_version_id> --metric <metric_name> --out artifacts

# The support report: how many aggregates returned insufficient_data, and which
uv run climbvision aggregate --problem <problem_version_id> --report support --out artifacts

# Validate every emitted document through the registry
uv run climbvision validate artifacts/<...>/*.json

# Hermetic check: the unit suite must still pass with ffprobe absent from PATH
```

| Command | Proves |
| --- | --- |
| `pytest`, `ruff` | D1 |
| `aggregate` for a problem | D3, D4, D7, D8, D9 |
| `aggregate` for one metric | That a single metric's unit, support and uncertainty travel with it |
| the support report | The headline `insufficient_data` count |
| `validate` | D2 and the registry seam |

## 13. Traps

| # | Trap | Why it happens | What to do |
| --- | --- | --- | --- |
| 1 | The hip midpoint drifting into centre-of-mass language | "Centre" is the natural English word for a midpoint, and every neighbouring field is biomechanical | The single-valued definition field, plus the grep test T3. Rule 7 |
| 2 | Silent interpolation | A gap makes the trajectory look broken, and filling it makes the plot look right | The trajectory becomes smooth and the velocity becomes fiction, with no way to tell afterwards. Abstain, and put any smoothing in a separate document with a named filter |
| 3 | Velocity across a gap | The two samples are adjacent **in the list**, so subtracting them looks correct | They are not adjacent in time. Abstain above the gap threshold. This is the reproduced Stage 1 defect, T4 |
| 4 | The wrong denominator | All attempts is the easy denominator to reach for | It understates every hazard on late transitions, because attempts that never got there dilute it. T11 |
| 5 | Returning a wide interval instead of `insufficient_data` | A wide interval feels more informative than nothing | `evaluation.md` Section 1 explicitly forbids it: below the support threshold the aggregate returns `insufficient_data`, not a value with a wide interval and not a point estimate with a disclaimer |
| 6 | Multiplicity | With ten to twenty transitions per problem `[PLANNING]`, one will look elevated by chance | The crux rule is a stated rule, not a test, and it reports no p-value. Never present the highest hazard as a finding |
| 7 | Move and adjustment double counting | The same release-and-re-attach is visible to both modules | The partition in Section 8.5, asserted by T8 |
| 8 | Hesitation presented as a judgement | A dwell observation is one adjective away from a story | Any output word beyond dwell, interval, speed and observation is a contract violation. T9 |
| 9 | Using the derived rather than the adjudicated outcome | Stage 6's candidate is right there in the attempt document | It makes the failure rate a function of the deriver's bugs. `mvp-contract.md` Section 10 requires `adjudicated_ground_truth`. T12 |

## 14. Report format and stop condition

Follow Section 0. In addition, this stage's report must contain:

- the **count of transitions that returned `insufficient_data`**, in the gate table;
- for every hazard that was measured: the failure count, the attempts-at-risk count, the exact rational, both integer bounds and the interval method, in one row;
- the selected support threshold with its selection evidence, and an explicit statement that the number was selected on validation data and never on the frozen test split;
- whether the crux rule fired, and if it did not, the statement that not firing is the expected and correct outcome at this sample size;
- what this stage does not prove: it proves no accuracy, it estimates nothing about any other climber, gym or camera placement, and a wide interval is not a finding;
- the honest sentence from Section 0, attached to every accuracy-shaped number.

Then stop and wait for the owner's decision. Stage 8 has its own precondition, and it is a hard
blocker.

## 15. Read-first list

| File | Read for |
| --- | --- |
| `AGENTS.md` | All of it. Sections 2, 3, 5, 6, 9 and 11 are binding |
| `docs/mvp-contract.md` | Sections 2 (out of scope: centre of mass, force, composite scores), 4 (coordinate spaces), **6 (foot adjustment, hesitation, crux, hip trajectory)**, 9 (the Stage 7 gate is a support threshold), 10 (the hazard comes from adjudicated outcomes; confidence never increases) |
| `docs/data-schema.md` | Sections 1 (`MetricValue` is a Stage 2 entity), 5 (provenance), 6 (storage formats), 7 (serialization, no floats, explicit nulls) |
| `docs/evaluation.md` | **Section 1, Stage 7**, which forbids returning a wide interval in place of `insufficient_data`; Section 2 (splits); Section 3 (deterministic graders first); Section 5 |
| `docs/annotation-guide.md` | Section 5 (outcomes) and Section 6 (adjudication), because the hazard depends on both |
| `docs/status.md` | The Stage 1 row: the fabricated frame-rate delta computed across a timestamp gap. That is trap 3 |
| `docs/agents/00-operating-manual.md` | Sections 2.1 items 23 to 30, 3.8 (how many attempts and of what), 5.7 (hesitations are derived here, not annotated), 11.2 (expect a lot of `insufficient_data`) |
| `docs/agents/briefs/stage-6-attempts-moves-beta.md` | The move definition, the configuration id, and the same-configuration rule this stage's adjustment count is the complement of |
| `src/climbvision/schema/versions.py`, `schema/__init__.py`, `schema/provenance.py` | The registration seam and the run-document shape |
| `src/climbvision/quality.py` | Integer cross-multiplication against a config threshold, and `CONFIG_THRESHOLD_MISSING` |
| `src/climbvision/timebase.py` | `pts_to_us`, `us_to_pts`, and integer-only rounding half away from zero |
| `src/climbvision/serialization.py`, `errors.py`, `hashing.py` | `dumps_canonical`, `loads_json`, `ClimbVisionError`, `sha256_file` |
| `tests/unit/test_scope_guard.py`, `tests/unit/test_schema.py`, `tests/conftest.py` | The module inventory pins, `ALLOWED_THIRD_PARTY`, `BANNED`, `DOCUMENT_MODELS`, `ALL_MODELS`, `block_network` |
| `configs/ingest/v1.json` | The config shape and the `selection` string convention |
