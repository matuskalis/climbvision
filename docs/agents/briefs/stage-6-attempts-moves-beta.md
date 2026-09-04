# Stage 6 - attempts, moves, beta and falls

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

Derive, deterministically and from contact transitions alone:

- multiple attempts per recording;
- stable contact-state graphs;
- moves;
- beta token sequences in both the limb-aware and the limb-agnostic form;
- outcomes, as candidates only;
- the last stable contact configuration before an unrecovered loss of contact;
- a comparison of two attempts by contact-event alignment.

There is **no video action model** at this stage and **no generated text** anywhere in it.

Inputs: the Stage 5 contact series; the Stage 3 problem definitions (`ProblemVersion`,
`ProblemHold` with its role); and the Stage 2 adjudicated attempt annotations, which supply the
outcomes. Definitions of attempt, move, beta sequence and fall location are in
`docs/mvp-contract.md` Section 6 and are not restated here.

## 2. Preconditions

Tick every row before starting. An unticked precondition is the reason gates get measured on
nothing (`docs/agents/00-operating-manual.md` Section 7.1).

| # | Precondition | Why | Where it is recorded |
| --- | --- | --- | --- |
| 1 | The Stage 5 gate is recorded in `docs/status.md` **with its slices**, hands and feet separately | Every token in this stage is a Stage 5 contact event. A pooled Stage 5 number hides a foot-contact failure that will dominate the foot tokens here | `docs/status.md`, Stage 5 row |
| 2 | Adjudicated attempt spans and outcomes exist for every recording to be derived | The derived outcome is a candidate only; the annotated outcome is the one every downstream consumer uses | Stage 2 output, item 23 of the operating manual |
| 3 | The **contact `unknown` rate is measured**, per limb slice | It determines how much of this stage can run at all. If it is high, most attempts exceed the unknown-token threshold and this stage returns `insufficient_data` by design, not by defect | Stage 5 report |
| 4 | For the `[PILOT]` half of the gate only: the hand-written beta on about ten attempts `[PLANNING]`, written from the video without sight of any derived output | Without it the gate is circular: beta derived from adjudicated contacts, scored against beta derived by the same rule | Operating manual Section 5.3 and item 28, Section 14 |

Rows 1 to 3 gate the code. Row 4 gates only the measured `[PILOT]` clauses: the stage may reach
**code-complete** without it, and must then report the `[PILOT]` clauses as `pending measurement`
rather than substituting anything (operating manual Section 1).

## 3. Human inputs required before the agent starts

**No new human input is created by this stage.** Everything it consumes was already scheduled by
the annotation plan. One decision must be approved before the agent writes code.

| Item | Detail |
| --- | --- |
| Decision to approve | `outcome-derivation-boundary` |
| Question | May a `fall` ever be distinguished from a `controlled_drop` **by derivation**? |
| Recommendation | **No.** The two are indistinguishable from contact geometry alone: both are "all limbs leave the wall and stay off it". The distinction is a judgement about control (`annotation-guide.md` Section 5), which is why the annotation guide lets a human answer `unknown` for exactly this case |
| Consequence of the recommendation | The stage emits a **candidate** outcome in a coarser vocabulary than the contract ontology, reports its agreement with the human label, and never replaces it |
| Why it matters | `mvp-contract.md` Section 6 already forbids claiming the **cause** of a fall. This decision keeps the **type** of a fall equally honest: a deriver that prints `fall` has made a claim about control that no contact interval supports |

Everything else the owner must produce for this stage (attempt spans, outcomes, hand-written beta)
is already in the annotation plan. If it does not exist yet, that is precondition 2 or 4 failing,
not a new request.

## 4. Deliverables

All module paths below are **proposals**. If the reviewer or the owner prefers different names,
use theirs and keep one home per concern; do not create a second module that does the same work.

| Path (proposed) | Owns |
| --- | --- |
| `src/climbvision/sequence/__init__.py` | Package marker and the public entry points |
| `src/climbvision/sequence/states.py` | Interval boundaries to a piecewise-constant configuration timeline; the configuration value object; the stability test |
| `src/climbvision/sequence/moves.py` | Move derivation from the stable-segment sequence |
| `src/climbvision/sequence/attempts.py` | Attempt segmentation, the candidate outcome, the agreement field, the last stable configuration |
| `src/climbvision/sequence/beta.py` | The token grammar, the total order, both forms |
| `src/climbvision/sequence/compare.py` | Contact-event alignment and the normalised edit distance |
| `src/climbvision/sequence/derive.py` | Orchestration only, modelled on `ingest.py` |
| `src/climbvision/schema/sequence.py` | The sequence document models |
| `src/climbvision/schema/provenance.py` | Extended with the derivation run document, beside `IngestRun` |
| `src/climbvision/provenance.py` | Extended with a derivation-run builder beside `build_ingest_run`, reusing the existing `git` boundary rather than opening a second one |
| `configs/sequence/v1.json` | Every threshold in Section 8.10 |
| `docs/adr/<slug>.md` x2 | `outcome-derivation-boundary` and `beta-token-grammar`, created one at a time, when decided |

**No new dependency. No action-recognition model.** Not now and not later at this stage: the
roadmap is explicit that moves are derived from contact transitions **before** any video action
model is even considered (`README.md` roadmap, Stage 6).

### Seams to update

| Seam | Concretely |
| --- | --- |
| Schema constants | New `*_SCHEMA_ID` and `*_SCHEMA_VERSION` per document, added to `SCHEMA_IDS` in `src/climbvision/schema/versions.py` |
| Registry and exports | `MODEL_REGISTRY` and `__all__` in `src/climbvision/schema/__init__.py` |
| Schema tests | A row per document in `DOCUMENT_MODELS` with a committed golden fixture under `tests/fixtures/documents/`; every nested model added to `ALL_MODELS` |
| Scope guard | A **new** `STAGE_SIX_MODULES` set beside the existing `STAGE_ONE_MODULES`, kept separate as a decision record. `ALLOWED_THIRD_PARTY` and `BANNED` unchanged, and they must not intersect |
| Dependency pin | Unchanged: this stage adds no dependency beyond those Stage 4 authorized |
| CLI | Proposed subcommands `derive` and `compare`, with exit-code tests, plus a test that `validate` resolves the new documents through `MODEL_REGISTRY` and not by filename |
| Config | `configs/sequence/v1.json` in the shape of `configs/ingest/v1.json` |
| Status ledger | The Stage 6 row rewritten with a measured-evidence table; `pending measurement` wherever nothing was measured |
| Contract documents | Edit **only** if the token grammar decision changes a definition. Section 6 of the contract is frozen; an edit there needs its own decision record |
| Fixture script | `scripts/regenerate_fixtures.sh` stays manual-only; new fixtures for this stage are hand-authored JSON, not regenerated media |
| Ignore rules | Unchanged |

## 5. Entities

`Attempt`, `MoveEvent`, `BetaSequence` and `FallEvent` are all scheduled for Stage 6 in
`docs/data-schema.md` Section 1 and all carry provenance class `derived`
(`mvp-contract.md` Section 10). Field identifiers below are **proposals**; where this brief is
unsure of a name it describes the meaning instead, as `docs/data-schema.md` requires.

### Contact configuration (value object, not a document)

| Field | Representation | Notes |
| --- | --- | --- |
| Configuration id | `sha256-<64 hex>`, following `ASSET_ID_PATTERN` in `hashing.py` | Canonical hash of the sorted limb-to-target mapping, computed over `dumps_canonical` bytes so identity and serialization cannot drift |
| Assignments | Sorted list of (limb, target reference) pairs | The limb order is the fixed order in Section 8.8. Target values come from the closed contact-target set in `mvp-contract.md` Section 5 |
| Determinacy flag | Boolean | `false` if any limb's target is `unknown` |

**Two indeterminate configurations are never equal**, even if their unknowns coincide. Equality is
exposed as an explicit predicate that returns `false` whenever either side is indeterminate, and
the configuration id of an indeterminate configuration is salted with the identity of the segment
that produced it, so that **id equality and configuration equality always agree**. If they
disagree, downstream grouping by id silently re-merges what equality kept apart. That is rule 15
expressed in code: unknown must not compare equal to unknown.

### Attempt

| Field | Representation | Notes |
| --- | --- | --- |
| Attempt id | Opaque string id | Stable under re-derivation of identical inputs |
| Asset id | `sha256-<64 hex>` | The recording |
| Problem version id | Opaque id | Scoped to a `WallSet` revision (`mvp-contract.md` Section 5) |
| Attempt index | Integer, zero-based | Ordered by start timestamp within the recording |
| Interval | `start_us`, `end_us`, integer microseconds, half-open | Plus `start_observed` and `end_observed` booleans |
| Derived outcome candidate | Closed set, see Section 8.6 | Never a member of the contract outcome set |
| Annotated outcome | Contract outcome set, nullable | Copied from the Stage 2 adjudicated record, never recomputed |
| Agreement | `agree`, `disagree`, `not_compared` | Definition in Section 8.6 |
| Provenance class | Literal `derived` | |
| Unknown time | Integer microseconds | Total time inside the attempt during which any limb's target was `unknown` |

### Move event

| Field | Representation | Notes |
| --- | --- | --- |
| Move id | Opaque string id | |
| Attempt id | | |
| Move index | Integer, zero-based | |
| Interval | Integer microseconds, half-open | End of the previous stable segment to start of the next differing stable segment |
| From configuration id, to configuration id | Configuration ids | Both determinate by construction |
| Changed limbs | Sorted list | The limbs whose target differs between the two configurations |
| Status | `derived` or `insufficient_data` | |

### Beta sequence

| Field | Representation | Notes |
| --- | --- | --- |
| Attempt id | | |
| Form | `limb_aware` or `limb_agnostic` | Two documents per attempt, never one document with two payloads |
| Tokens | Ordered list of token objects, each carrying kind, limb (null in the limb-agnostic form), target reference and `time_us` | The time is carried **on** the token, not in a parallel array, so the two cannot drift out of alignment |
| Unknown token count | Integer | Tokens whose target reference is `unknown` |
| Status | `derived` or `insufficient_data` | |
| Token total order id | String | The identity of the ordering rule that produced this sequence |

### Fall event

| Field | Representation | Notes |
| --- | --- | --- |
| Fall event id | Opaque string id | |
| Attempt id | | |
| Last stable configuration id | Configuration id | |
| Last stable configuration end time | Integer microseconds | |
| Loss time | Integer microseconds | |
| Cause | A type that admits **exactly one value**, `not_claimed` | |

The cause field is a single-valued literal so that the **schema itself** enforces rule 10. A
convention can be forgotten in a code review; a type cannot hold a value it does not have.
Nothing else belongs on this document.

### Attempt comparison

| Field | Representation | Notes |
| --- | --- | --- |
| Comparison id, reference attempt id, hypothesis attempt id | | |
| Problem version id | | Both attempts must share it |
| Form | `limb_aware` or `limb_agnostic` | Required, never defaulted |
| Alignment | Ordered list of operations: match, substitute, insert, delete, each with its reference and hypothesis indices | The alignment is the result; the distance is a summary of it |
| Edit distance | Integer | Unit integer costs |
| Normalised distance | Exact rational, nullable | Distance over reference length, reduced by gcd |
| Status | `measured` or `insufficient_data` | |

### Derivation run

Modelled exactly on `IngestRun` (C5): run id, creation time, input hashes for every consumed
document, config version and config hash, ontology version, `climbvision` and Python versions,
git commit and dirty flag, and the tool versions in force. Append-only, one per execution, and it
points at its outputs by hash rather than the reverse.

## 6. Decisions already frozen

Do not reopen these. If one of them appears to block the work, stop and report the conflict.

| Frozen item | Where | Consequence here |
| --- | --- | --- |
| Intervals are half-open `[start_us, end_us)`; a zero-length interval is empty | `mvp-contract.md` Section 3 | Segment boundaries touch without overlapping; a segment of zero length does not exist |
| Time is never `frame_number / nominal_fps` | `mvp-contract.md` Section 3 | Every timestamp here comes from a recorded presentation timestamp |
| Four closed ontology sets | `mvp-contract.md` Section 5 | A derived value outside its set is a defect, not a new category |
| A move is a transition between two **stable** configurations; micro-fluctuations that do not change the configuration are not moves | `mvp-contract.md` Section 6 | Section 8.4 is a restatement of this rule, not an invention |
| Fall location is the last stable configuration and a timestamp; the cause is never claimed | `mvp-contract.md` Section 6 | The fall event carries five fields and no sixth |
| Both beta forms are maintained and comparison states which form it used | `mvp-contract.md` Section 6, `evaluation.md` Section 1 | The two are never pooled into one number |
| `unknown` is a legitimate outcome; a recording that cuts before the top is `unknown`, not `fall` | `mvp-contract.md` Section 6, `annotation-guide.md` Section 5 | Section 8.5's third end condition |
| Attempt, move, beta and fall are all provenance class `derived` | `mvp-contract.md` Section 10 | One class per artifact, never collapsed |
| Confidence never increases downstream | `mvp-contract.md` Section 10 | Section 8.9 |
| No generated coaching text, ever | `mvp-contract.md` Sections 2 and 11 | No string in any output is composed at runtime |
| The Stage 6 gate metric is the normalised sequence edit distance, reported separately per form | `evaluation.md` Section 1 | Section 11 |
| Conventions C1 to C10 | Section 0 | Ratios are rationals; comparisons are cross-multiplications; configs are versioned |

## 7. Open decisions

### `outcome-derivation-boundary`

| | |
| --- | --- |
| Question | May the deriver distinguish `fall` from `controlled_drop`? |
| Option A **(recommended)** | It may not. The deriver emits a candidate in its own coarser closed set and reports agreement against the human label |
| Option B | It may, using some proxy for control such as descent speed or limb ordering. This is a claim about intent from geometry, and there is no validated label for it |
| Consequence of A | The derived candidate set is `send_candidate`, `loss_of_contact_candidate`, `unknown`. It is **not** the contract outcome set, and the ADR must say so explicitly, because a second closed set is exactly the kind of thing that gets mistaken for an ontology extension |
| What the ADR records | The candidate set; the compatibility mapping in Section 8.6; the statement that the annotated label wins in every downstream use; and the fact that `unknown` candidates are counted, not silently dropped |

### `beta-token-grammar`

| | |
| --- | --- |
| Question | What is a token, and what is the total order over tokens? |
| Proposal | Two kinds, `attach` and `release`. A limb-aware token carries kind, limb and target reference. A limb-agnostic token carries kind and target reference. Target references are drawn from the contact-target set: a hold instance, a volume, a wall region, or `unknown`. `none` never appears as a token target, because the absence of contact is what a release token already encodes |
| Total order **(the load-bearing half)** | Time ascending; then release before attach; then a fixed limb order; then target reference lexicographically by its canonical string |
| Why the order must be stated | Without a total order, two events at the same timestamp order arbitrarily, the token sequence differs between runs on identical input, and the edit distance becomes nondeterministic. A nondeterministic gate number is not a measurement |
| Status of the order id | `[FIXED]` once this decision is recorded; a change to the ordering rule is a new order id and invalidates every stored comparison |
| What the ADR records | The token shape, the target vocabulary, the four ordering keys in order, the fixed limb order, and the order id string |

## 8. Approach

### 8.1 Inputs and their provenance

Read the Stage 5 contact intervals (`reviewed_annotation` or `adjudicated_ground_truth` where
they exist, `prediction` where they do not), the Stage 3 problem definition with each hold's role,
and the Stage 2 adjudicated attempt spans and outcomes. Every input is referenced by hash in the
derivation run. Provenance classes are never mixed inside one derived document: if a derivation
consumed predicted contacts, that fact is recorded, and it is not silently upgraded by the fact
that the output is `derived`.

### 8.2 Breakpoints and the configuration timeline

Take **every interval boundary** inside the attempt as a breakpoint. Between two consecutive
breakpoints the limb-to-target mapping is constant by construction, so each segment gets exactly
one configuration. The result is a piecewise-constant timeline whose segment durations sum to the
attempt duration; assert that sum, because it is the cheapest possible check that no boundary was
dropped.

### 8.3 The stability test

A segment is stable when **all three** hold:

1. its duration is at least the minimum stable dwell;
2. the number of limbs in contact is at least the minimum supporting limbs;
3. its configuration is determinate.

Test 3 runs first in effect: an indeterminate configuration can never be stable, whatever its
duration, because a stable segment is an endpoint of a move and a move between unknowns is a
phantom.

### 8.4 Moves - the crux of Stages 6 and 7

A move is the span from the **end of one stable segment** to the **start of the next stable
segment whose configuration differs**. Unstable segments in between are absorbed into the move.

**If the next stable configuration equals the previous one, that is not a move.** It is a foot
adjustment or a hand re-grab, and it is counted at Stage 7 (`mvp-contract.md` Section 6, foot
adjustment).

Getting this wrong is the crux of Stages 6 and 7. Counting a same-configuration cycle as a move
inflates every move count, shortens every move duration distribution, injects a spurious token
pair into both beta forms, and creates a self-transition in Stage 7's hazard table that can never
be a real failure transition. It has its own decisive test, T1 and T2 in Section 10, and that
test is the first thing the reviewer should re-run.

### 8.5 Attempt segmentation

| Boundary | Rule | Result |
| --- | --- | --- |
| Start | The first time at which **all** the problem's `start`-role holds are held continuously for the minimum start dwell | Attempt start, `start_observed = true` |
| Start, degenerate | The recording begins with the climber already on the wall | `start_observed = false`; the interval start is the first observed contact timestamp, marked unobserved, **never presented as a measured start** (`annotation-guide.md` Section 4) |
| End, first of the three below | | |
| - send | All `finish`-role holds held continuously for the minimum finish dwell | `send_candidate` |
| - loss of contact | All limbs release within the fall release window, followed by at least the minimum off-wall time with zero contacts | `loss_of_contact_candidate`, which the decision in Section 7 refuses to split |
| - recording end | The recording ends before either of the above | `unknown` |

The gap between two attempts belongs to **no attempt** (`mvp-contract.md` Section 6). Assert it:
no derived record may carry a timestamp inside an inter-attempt gap.

### 8.6 The candidate outcome and the agreement field

The derived outcome is a **candidate**. The annotated outcome comes from Stage 2. The agreement is
reported. **The annotated label wins in every downstream use**, including Stage 7's hazard.

| Candidate | Annotated `send` | Annotated `fall` | Annotated `controlled_drop` | Annotated `aborted` | Annotated `unknown` | No annotation |
| --- | --- | --- | --- | --- | --- | --- |
| `send_candidate` | agree | disagree | disagree | disagree | not_compared | not_compared |
| `loss_of_contact_candidate` | disagree | agree | agree | disagree | not_compared | not_compared |
| `unknown` | not_compared | not_compared | not_compared | not_compared | not_compared | not_compared |

An annotated `unknown` is `not_compared`, not `agree`: the human said the recording does not
decide it, and scoring a candidate against that would be scoring it against nothing. The
`not_compared` count is reported **beside** the agreement rate, because an agreement rate computed
over four comparable attempts out of fifty is a different claim from one computed over fifty.

### 8.7 The fall event

Records the last stable configuration, that configuration's end time, and the loss timestamp.
Nothing else. No hold, no body position, no cause, no adjective.

### 8.8 Beta tokenisation

Emit the limb-aware sequence first, in the total order from Section 7. Derive the limb-agnostic
sequence as the **order-preserving projection** of the limb-aware sequence with the limb key
dropped. Never sort it independently: two independently sorted sequences can disagree about
relative order on the same input, and then the two forms describe different climbs.

The fixed limb order is a stated constant, proposed as left hand, right hand, left foot, right
foot, and its identity is part of the order id.

### 8.9 Comparison by contact-event alignment

Standard global sequence alignment with unit integer costs for substitution, insertion and
deletion. Emit the alignment, the integer edit distance, and the distance normalised by the
**reference** length as an exact rational (C1).

| Condition | Behaviour |
| --- | --- |
| The two attempts are on different problem versions | Hard failure, `PROBLEM_VERSION_MISMATCH`. A distance across problems is a meaningless number that looks like a result |
| The two sequences are in different forms | Hard failure, `BETA_FORM_MISMATCH` |
| Either sequence's unknown token fraction exceeds its threshold | Status `insufficient_data`, normalised distance `null`. Not a number |
| The reference sequence is empty | Status `insufficient_data`, normalised distance `null`, integer distance still reported. Never a division by zero, and never a silently omitted document (C7) |
| The hypothesis is longer than the reference | The normalised distance exceeds one. **Do not clamp it.** A clamp turns a large disagreement into exactly the same number as a merely bad one |

### 8.10 Unknown propagation

If an attempt's unknown token fraction exceeds its threshold, every derived aggregate for that
attempt returns `insufficient_data` rather than a number. Unknown contacts propagate into moves,
tokens and comparisons; nothing downstream is more confident than the contacts it came from
(rule 15).

### 8.11 Thresholds

Every one of these lives in `configs/sequence/v1.json` in the shape of `configs/ingest/v1.json`,
with value, unit, status and a selection string. A threshold with no `value` is a hard failure
(`CONFIG_THRESHOLD_MISSING`), so a `[PILOT]` entry carries a placeholder value **and** the
selection string `"Not selected. [PILOT] placeholder; no validation data exists."` A placeholder
is never reported as selected, and a selection run is recorded in `docs/status.md` when it
happens.

| Threshold (proposed name) | Unit | Status | Controls |
| --- | --- | --- | --- |
| `min_stable_dwell_us` | microseconds | `[PILOT]` | Segment stability |
| `min_supporting_limbs` | count | `[PILOT]` | Segment stability |
| `min_start_dwell_us` | microseconds | `[PILOT]` | Attempt start |
| `min_finish_dwell_us` | microseconds | `[PILOT]` | Send candidate |
| `fall_release_window_us` | microseconds | `[PILOT]` | Loss-of-contact candidate |
| `min_off_wall_us` | microseconds | `[PILOT]` | Loss-of-contact candidate |
| `max_unknown_token_fraction` | rational, unitless | `[PILOT]` | Comparison and aggregate abstention |
| `token_total_order_id` | string | `[FIXED]` on adoption of `beta-token-grammar` | Token ordering identity |

## 9. Dependencies

**Add nothing.** Interval sweeps and dynamic programming are pure Python: sorting boundaries,
folding a timeline and filling an alignment matrix need no array library. The runtime dependency
list stays exactly `pydantic`, and the parsed dependency-pin test stays as it is.

**No action-recognition model appears at this stage, ever.** Moves are derived from contact
transitions, and any video action model is a later question that this stage does not open.
`BANNED` in `tests/unit/test_scope_guard.py` stays as it is, and `ALLOWED_THIRD_PARTY` stays
`{"pydantic"}`.

## 10. Tests

Every expected value below is **hand-calculated**, per `AGENTS.md` Section 9 item 6. Numbers in
this section are arithmetic and fixture facts, not thresholds, and are untagged by the convention
in `AGENTS.md` Section 8.

The shared fixture, hand-authored, one attempt of 10 000 000 microseconds, with
`min_stable_dwell_us = 1 000 000` and `min_supporting_limbs = 3`:

| Limb | Intervals |
| --- | --- |
| left hand | H1 over `[0, 10 000 000)` |
| right hand | H2 over `[0, 10 000 000)` |
| left foot | H3 over `[0, 10 000 000)` |
| right foot | H4 over `[0, 4 000 000)`, no contact over `[4 000 000, 4 500 000)`, then a re-attachment over `[4 500 000, 10 000 000)` |

Breakpoints are `0, 4 000 000, 4 500 000, 10 000 000`: three segments of `4 000 000`, `500 000`
and `5 500 000` microseconds, summing to `10 000 000`. Segment 2 has three limbs in contact, which
meets the minimum, but its duration is below the dwell threshold, so it is unstable.

| # | Test | Expected |
| --- | --- | --- |
| **T1** | **The decisive test.** The right foot re-attaches to **H4**, so segment 3's configuration equals segment 1's | **Zero moves.** One same-configuration cycle, counted at Stage 7, not here |
| **T2** | **The decisive test, mirrored.** The right foot re-attaches to **H5** instead | **One move**, interval `[4 000 000, 4 500 000)`, duration `500 000` microseconds, changed limbs exactly `[right foot]` |
| T3 | Breakpoints and segments from the hand-authored interval set | Three segments; durations `4 000 000`, `500 000`, `5 500 000`; sum equals the attempt duration |
| T4 | A segment in which the left foot's target is `unknown` | Never stable, at any duration. Two such segments do **not** compare equal, and their configuration ids differ |
| T5 | Two attempts in one recording with a rest between | Two attempt records; the gap belongs to neither; no derived record carries a timestamp inside the gap |
| T6 | A recording starting mid-attempt | `start_observed = false`; the first frame is not used as the start |
| T7 | A recording cutting before the top | Candidate `unknown`. **Never** a loss-of-contact candidate |
| T8 | The derived candidate vocabulary | The candidate field's type admits neither `fall` nor `controlled_drop`; a schema test asserts the closed set, and the deriver has no code path that separates them |
| T9 | Two events at an identical timestamp: the left hand releases H2 and the right hand attaches H6 at `5 000 000` | Order is `release(left_hand, H2)` then `attach(right_hand, H6)`, deterministically |
| T10 | Input permutation | Shuffling the order of the input intervals does not change the token sequence, the move list or any id |
| T11 | Both forms | Two documents per attempt. Comparing a limb-aware sequence against a limb-agnostic one raises `BETA_FORM_MISMATCH`. A grep over `src/` for pooled-form vocabulary (`pooled`, `combined`, `overall`, `both_forms`) returns nothing |
| T12 | Edit distance. Reference `attach(H1), attach(H2), attach(H3)`; hypothesis `attach(H1), attach(H9), attach(H3), attach(H4)` | **One substitution plus one insertion, distance 2**, normalised to the exact rational **2/3** |
| T13 | Normalised distance above one. Reference of two tokens, hypothesis of five | Distance 3, normalised 3/2, **not clamped to 1** |
| T14 | Cross-problem comparison | Raises `PROBLEM_VERSION_MISMATCH` |
| T15 | An attempt over the unknown token fraction | `insufficient_data` for every derived aggregate, with null values, rather than a number |
| T16 | The cause field | Admits exactly one value, `not_claimed`; any other value fails validation. A grep over `src/` and the emitted documents for cause-like vocabulary (`cause`, `because`, `caused_by`, `reason`, `due_to`, `slipped`) returns only the single literal |
| T17 | No prose | A grep over `src/` for text-generation vocabulary and for sentence-shaped literals returns nothing, and a schema test asserts that every string field in the sequence documents is an id, a hash, or a member of a closed set |
| T18 | Round-trip | `model == parse(dump(model))` and `dump(parse(dump(model))) == dump(model)` byte-for-byte, for every new document (`evaluation.md` Section 4.2) |
| T19 | Registry | `climbvision validate` resolves each new document by its own `schema_id`, and an unknown id still raises `SCHEMA_ID_UNKNOWN` |

The suite must remain hermetic: no network (the autouse `block_network` fixture in
`tests/conftest.py` stays in force) and no new external tool.

## 11. Gate

The Stage 6 gate in `mvp-contract.md` Section 9 is a `[PILOT]` target: normalised sequence edit
distance against adjudicated beta, to be set on validation data. The deterministic clauses below
are this brief's own, and they are not accuracy-shaped.

### Deterministic clauses

| # | Clause | Assertion | Evidence |
| --- | --- | --- | --- |
| D1 | Tests and lint | `uv run pytest` all pass, no skips counted as passes; `uv run ruff check .` clean | pending measurement |
| D2 | Round-trip | Byte-identical re-serialization for every new document | pending measurement |
| D3 | Multiple attempts | More than one attempt derived from one recording, with the inter-attempt gap belonging to neither | pending measurement |
| D4 | Same-configuration cycling | A release and re-attach to the same target produces **zero** moves | pending measurement |
| D5 | Both forms | Limb-aware and limb-agnostic emitted separately and never pooled | pending measurement |
| D6 | Deterministic order | Token order is invariant under input permutation | pending measurement |
| D7 | Unknown propagation | No derived value is confident where its inputs were not | pending measurement |
| D8 | Cause | The cause field cannot hold any value other than `not_claimed` | pending measurement |
| D9 | No generated text | No prose anywhere in the code or the output | pending measurement |

### `[PILOT]` clauses

| # | Clause | Reported as |
| --- | --- | --- |
| P1 | Normalised sequence edit distance against the adjudicated beta | **Separately for each form**, on the frozen test split, as a **distribution over attempts** with its spread, not only a mean |
| P2 | Outcome agreement rate between the derived candidate and the human label | With the `not_compared` count beside it |
| P3 | Move-count agreement against adjudicated moves | Per attempt, as a distribution, not pooled |

### Honest limitation

About fifty attempts `[PLANNING]` yields at most fifty sequence comparisons, of which roughly
fifteen `[PLANNING]` fall in the frozen test split. That supports a distribution with visible
spread and **no tight mean**. The independent cross-check is tighter still: the hand-written beta
covers about ten attempts in total `[PLANNING]` (operating manual Section 5.3, item 28), so the
non-circular half of this gate rests on a single-digit number of attempts per form.

Every distance also inherits Stage 5's contact errors. A single mis-identified hold changes two
tokens, one attach and one release, so a Stage 5 slice that is weak on feet shows up here as a
Stage 6 number. **Therefore report the relationship between an attempt's contact `unknown` rate
and its edit distance**, as a paired per-attempt table, plus a rank statistic computed as an exact
integer rational over concordant and discordant pairs. **No p-value and no significance claim**: at
this sample size a rank statistic is descriptive. If the relationship is strong, this stage is
measuring the previous one, and that must be said in the report rather than discovered later.

## 12. Verification commands

Placeholders in angle brackets. No absolute paths anywhere, in commands or in artifacts.

```bash
uv sync
uv run pytest
uv run ruff check .

# Derive over one asset and one problem
uv run climbvision derive --asset <asset_id> --problem <problem_version_id> --out artifacts

# Compare two attempts, once per form
uv run climbvision compare --reference <attempt_id> --hypothesis <attempt_id> \
  --form limb_aware --out artifacts
uv run climbvision compare --reference <attempt_id> --hypothesis <attempt_id> \
  --form limb_agnostic --out artifacts

# Evaluate on validation data, through the evaluation entry point Stage 2 introduced.
# If Stage 2 named it differently, use that name; do not add a second one.
uv run climbvision <stage-2-evaluation-subcommand> --stage 6 --split validation --out artifacts

# Validate every emitted document through the registry, not by filename
uv run climbvision validate artifacts/<...>/*.json

# Hermetic check: the unit suite must still pass with ffprobe absent from PATH
```

| Command | Proves |
| --- | --- |
| `pytest`, `ruff` | D1 |
| `derive` | D3, D4, D7, and the artifact layout on disk |
| `compare` twice | D5, D6 |
| the evaluation subcommand | P1, P2, P3, or `pending measurement` if the data does not exist |
| `validate` | D2 and the registry seam |
| hermetic run | Rule 13 |

## 13. Traps

| # | Trap | Why it happens | What to do |
| --- | --- | --- | --- |
| 1 | Same-configuration cycling counted as a move | The naive rule is "the configuration changed, then changed back", and both changes look like transitions | Compare the two **stable** configurations across the unstable span. T1 and T2 |
| 2 | `unknown` comparing equal to `unknown` | Structural equality on a mapping treats two `unknown` targets as the same value | Equality is false whenever either side is indeterminate; otherwise indeterminate segments become stable and generate phantom moves |
| 3 | Tie-breaking left to sort stability | Two events at one timestamp look harmless until the input order changes | The four-key total order in Section 7, pinned by T9 and T10 |
| 4 | An empty reference and a division by zero | An attempt with no observed contacts is a legitimate data state | `insufficient_data` with a null normalised distance, and the integer distance still reported |
| 5 | Clamping a normalised distance above one | It "looks wrong" above one, so someone caps it | It is correct above one when the hypothesis is longer. Clamping destroys the distinction between bad and much worse. T13 |
| 6 | Treating the recording as the attempt | Taking everything between the first and last contact is one line of code | It merges two attempts and the rest between them into one. `mvp-contract.md` Section 6: a recording is not an attempt. T5 |
| 7 | Splitting fall from controlled drop | Descent speed or release order looks like evidence | It is a judgement about control, invisible to contact geometry. Decision `outcome-derivation-boundary`. T8 |
| 8 | Treating `unknown` as a failure of the deriver | An `unknown` outcome feels like a bug | It is legitimate and common: the camera cuts, and the honest answer is `unknown`. T7 |
| 9 | Comparing across problem versions | Both attempts have token sequences, so the code runs | The number is meaningless. Hard failure, `PROBLEM_VERSION_MISMATCH`. T14 |
| 10 | Treating the stability thresholds as cosmetic | They are placeholders, so they feel arbitrary | They are load-bearing: too low and every wobble is a move, too high and fast sequences vanish. They are `[PILOT]`, selected on validation data, and the selection is recorded |

## 14. Report format and stop condition

Follow Section 0. In addition, this stage's report must contain:

- the two `[PILOT]` edit-distance distributions, **one per form**, never a pooled figure;
- the outcome agreement rate **with** its `not_compared` count and the size of the compared subset;
- the paired per-attempt table of contact `unknown` rate against edit distance, with the rank statistic and an explicit statement of what it does and does not support;
- the count of attempts that returned `insufficient_data`, as a number in the gate table rather than a remark;
- what this stage does not prove: it does not prove that any move list is correct, only that the derivation is deterministic and that its disagreement with the hand-written beta was measured on a single-digit number of attempts per form;
- the honest sentence from Section 0, attached to every accuracy-shaped number.

Then stop and wait for the owner's decision. Do not open Stage 7.

## 15. Read-first list

| File | Read for |
| --- | --- |
| `AGENTS.md` | All of it. Sections 2, 3, 5, 6, 9 and 11 are binding on every line you write |
| `docs/mvp-contract.md` | Sections 3 (time), 5 (ontology), **6 (definitions: attempt, move, beta, foot adjustment, fall location)**, 9 (the gate), 10 (provenance and confidence) |
| `docs/data-schema.md` | Sections 1 (entities and their stages), 4 (versioning), 5 (provenance fields), 7 (serialization and the no-float rule) |
| `docs/evaluation.md` | Section 1 Stage 6, Section 2 (splits), Section 3 (how results are checked), Section 4.2 (round-trip), Section 5 (when a gate fails) |
| `docs/annotation-guide.md` | Sections 3 (interval bounding), 4 (attempt boundaries), 5 (outcomes), 6 (adjudication) |
| `docs/status.md` | The Stage 5 row and its slices; the current-contents table |
| `docs/agents/00-operating-manual.md` | Sections 1 (code-complete vs gate-measured), 2.2, 5.3 (what is annotated), 14 (the Stage 6 circularity resolution) |
| `docs/agents/briefs/stage-5-*.md` | What Stage 5 actually emits, and the names it chose |
| `src/climbvision/schema/versions.py`, `schema/__init__.py`, `schema/provenance.py` | The three-place registration seam and the shape of `IngestRun` |
| `src/climbvision/serialization.py`, `timebase.py`, `hashing.py`, `errors.py` | `dumps_canonical`, `loads_json`, `parse_rational`, `pts_to_us`, `us_to_pts`, `sha256_file`, `ClimbVisionError` |
| `src/climbvision/quality.py` | The integer cross-multiplication pattern (C2) and the config-threshold accessor that raises `CONFIG_THRESHOLD_MISSING` |
| `src/climbvision/ingest.py`, `cli.py` | Orchestration-only structure, exit codes, and `validate` dispatching on `schema_id` |
| `tests/unit/test_scope_guard.py`, `tests/unit/test_schema.py`, `tests/conftest.py` | `STAGE_ONE_MODULES`, `ALLOWED_THIRD_PARTY`, `BANNED`, `DOCUMENT_MODELS`, `ALL_MODELS`, `block_network` |
| `configs/ingest/v1.json` | The exact config shape to copy, including the `selection` string convention |
