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

### 1.1 The measured envelope, and the scope this stage inherits

The MVP is measured on a **standardized LED training board**: a flat panel hung at a fixed angle,
holds bolted at fixed positions on an **11-column by 18-row** grid `[FIXED]`, the same in every
installation, with a per-hold LED marking which holds belong to the problem
(`mvp-contract.md` Section 1). This is the commercially standardized board class; a Kilter- or
Moonboard-style panel is the familiar instance of it. The contract stays general; the board is the
first measured envelope.

Stage 5 predicts **hand contacts only**, by the `hands-first-scope` decision recorded there. Feet
are deferred because a steeply overhung panel occludes the climber's own feet from a camera
shooting upward from beneath it, and because footwork on these boards is genuinely unconstrained —
climbers smear on bare board surface and many problems place no constraint on the feet at all, so
the **foot ground truth itself is weak**, not merely the prediction. Stage 6 does not reopen that
decision; it inherits it and must work out what it means here.

**And here it means more than a narrower input.** Every token this stage emits is a Stage 5
contact event, so with feet unpredicted the derived vocabulary is a **hand** vocabulary: hand
configurations, hand-to-hand moves, hand beta. Section 7's `two-limb-stability-criterion` is the
consequence that cannot be absorbed silently, because the stability criterion this brief inherited
counts limbs in contact and a climber has two hands.

### 1.2 Why a hands-only beta is not a degraded beta

**Beta on a standardized board is conventionally shared as a hand sequence.** That is how the
sport already talks about these problems: a climber describing a board problem to another climber
names the holds the hands go to, in order, and says nothing about the feet unless the problem
constrains them. The community's own representation of the object this stage derives is a hand
sequence.

So a hands-only token sequence is **not a truncated version of the real thing; it matches the
domain's own representation.** State this in the report. It is the reason the scope cut is
defensible on the merits rather than merely convenient, and the distinction matters: a convenient
cut is one that should be reversed as soon as possible, while this one should be reversed only
when there is a foot target worth measuring against (Stage 5, `hands-first-scope`).

It remains a **narrower claim** than the contract's general definitions, and Sections 8.3, 8.7 and
11 say so at each point where the narrowing bites.

## 2. Preconditions

Tick every row before starting. An unticked precondition is the reason gates get measured on
nothing (`docs/agents/00-operating-manual.md` Section 7.1).

| # | Precondition | Why | Where it is recorded |
| --- | --- | --- | --- |
| 1 | The Stage 5 gate is recorded in `docs/status.md` **with its slices**: the **hand** slices measured, the **foot** slices reading `not_applicable` with their reason | Every token in this stage is a Stage 5 contact event, so the hand slices bound everything derived here. A **foot slice reported as a number** means Stage 5 exceeded its scope: stop and report, rather than consuming it | `docs/status.md`, Stage 5 row |
| 2 | Adjudicated attempt spans and outcomes exist for every recording to be derived | The derived outcome is a candidate only; the annotated outcome is the one every downstream consumer uses | Stage 2 output, item 23 of the operating manual |
| 3 | The **contact `unknown` rate is measured**, **per hand**, together with the abstention rate Stage 5 clause P5 reports | It determines how much of this stage can run at all. If it is high, most attempts exceed the unknown-token threshold and this stage returns `insufficient_data` by design, not by defect. Under the overhang the rate is expected to be higher than a vertical wall would give, which is exactly why it is a precondition and not a footnote | Stage 5 report |
| 4 | For the `[PILOT]` half of the gate only: the hand-written beta on about ten attempts `[PLANNING]`, written from the video without sight of any derived output, and **recorded as a hand sequence** | Without it the gate is circular: beta derived from adjudicated contacts, scored against beta derived by the same rule. If it carries foot tokens, they are excluded before the comparison and the exclusion is reported (Section 11) | Operating manual Section 5.3 and item 28, Section 14 |

Rows 1 to 3 gate the code. Row 4 gates only the measured `[PILOT]` clauses: the stage may reach
**code-complete** without it, and must then report the `[PILOT]` clauses as `pending measurement`
rather than substituting anything (operating manual Section 1).

## 3. Human inputs required before the agent starts

**No new human input is created by this stage.** Everything it consumes was already scheduled by
the annotation plan. **Two** decisions must be approved before the agent writes code, and one
further decision is inherited and not reopened.

| Item | Detail |
| --- | --- |
| Decision to approve, first | `two-limb-stability-criterion` (Section 7). It is first because it decides **what a stable configuration is**, and every move, token, fall location and comparison in this stage is defined in terms of that |
| Decision to approve, second | `outcome-derivation-boundary` (below) |
| Decision inherited, **not reopened** | `hands-first-scope`, recorded at Stage 5. This stage does not widen it, does not narrow it, and does not re-argue it. If the owner reverses it, this brief changes materially and must be re-issued, starting with Section 7 |

`two-limb-stability-criterion` is stated in full in Section 7, with its options and the
recommendation. `outcome-derivation-boundary` is stated here:

| Item | Detail |
| --- | --- |
| Decision to approve | `outcome-derivation-boundary` |
| Question | May a `fall` ever be distinguished from a `controlled_drop` **by derivation**? |
| Recommendation | **No.** The two are indistinguishable from contact geometry alone: both are "the attempted limbs leave the wall and stay off it", which on this envelope means both hands. The distinction is a judgement about control (`annotation-guide.md` Section 5), which is why the annotation guide lets a human answer `unknown` for exactly this case |
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
| `docs/adr/<slug>.md` x3 | `two-limb-stability-criterion`, `outcome-derivation-boundary` and `beta-token-grammar`, created one at a time, when decided. The stability record is written **first**: the other two are stated in terms of what a stable configuration is |

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
| Contract documents | Edit **only** if the token grammar decision changes a definition. Section 6 of the contract is frozen; an edit there needs its own decision record. **`two-limb-stability-criterion` needs no contract edit**: the contract already marks the stability criterion `[PILOT]`, so the decision record is the right home for it (Section 6 of this brief). The board envelope reaches the contract by its own amendment, not by this stage |
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
| Configuration id | `sha256-<64 hex>`, following `ASSET_ID_PATTERN` in `hashing.py` | Canonical hash of the attempted-limb set **and** the sorted limb-to-target mapping, computed over `dumps_canonical` bytes so identity and serialization cannot drift |
| Attempted limbs | Sorted list, copied from `ContactSeries.attempted_limbs` | For the MVP: `left_hand`, `right_hand`. **Never inferred from which limbs happen to appear in the assignments**, which cannot distinguish "not attempted" from "attempted and absent" |
| Assignments | Sorted list of (limb, target reference) pairs, **over the attempted limbs** | The limb order is the fixed order in Section 8.8. Target values come from the closed contact-target set in `mvp-contract.md` Section 5 |
| Determinacy flag | Boolean | `false` if **any attempted limb's** target is `unknown`. An unattempted limb does not make a configuration indeterminate; it is not part of it |

**The attempted-limb set is part of the configuration identity**, so a hands-only configuration id
can never equal a four-limb one. Without that, restoring feet later would silently make old and
new configurations compare equal by id while differing in meaning, and every stored comparison
would quietly change what it measured.

**Determinacy is evaluated over the attempted limbs only, and this is load-bearing.** Feet are
`unknown` for the whole recording by construction (Stage 5, Section 5.4). If they entered the
determinacy test, **every** configuration would be indeterminate, nothing would ever be stable, no
move would ever be derived, and the stage would return `insufficient_data` for every attempt while
looking like it was being careful. The unattempted limbs are **recorded by the attempted-limb
set** — the reader sees exactly which limbs were in scope — and they are not evaluated. Nothing
anywhere asserts a determinate state for them, and in particular nothing asserts `none`
(Stage 5, Section 5.4).

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
| Unknown time | Integer microseconds | Total time inside the attempt during which any **attempted** limb's target was `unknown`. Reading it over all four limbs would return the whole attempt duration on every attempt, because the feet are `unknown` throughout by construction |

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
| Last stable configuration id | Configuration id | **A hand configuration** for the MVP. See below |
| Last stable configuration end time | Integer microseconds | |
| Loss time | Integer microseconds | |
| Cause | A type that admits **exactly one value**, `not_claimed` | |

The cause field is a single-valued literal so that the **schema itself** enforces rule 10. A
convention can be forgotten in a code review; a type cannot hold a value it does not have.
Nothing else belongs on this document.

**The fall location is a narrower claim than the contract's.** `mvp-contract.md` Section 6 defines
fall location as the last stable **contact configuration** before unrecovered loss of contact,
over all limbs. What this stage emits is the last stable **hand** configuration, because hands are
the attempted limbs (Section 1.1). The two coincide only when the feet were on nothing that
mattered, and the system cannot tell whether that was so.

This is not a naming problem to be smoothed over. It must be **stated as a narrower claim** —
in the ADR, in `docs/status.md`, and beside every reported fall location — because "the last
configuration before the fall" and "the last **hand** configuration before the fall" are different
statements, and only the second one has evidence behind it. The configuration's own
attempted-limb set carries the qualification in the data, so a consumer cannot lose it.

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
| **The stability criterion itself is `[PILOT]`**, by the same contract sentence | `mvp-contract.md` Section 6 | This is what lets `two-limb-stability-criterion` (Section 7) be settled by a decision record rather than by a contract amendment. The criterion is open by contract; **what a move is** is not |
| Feet are not predicted in the MVP; the foot machinery is deferred, not deleted | `hands-first-scope`, recorded at Stage 5 | Sections 1.1, 5, 8.3, 8.4. This stage consumes the decision and does not reopen it |
| Fall location is the last stable configuration and a timestamp; the cause is never claimed | `mvp-contract.md` Section 6 | The fall event carries five fields and no sixth. What this stage can emit is the last stable **hand** configuration, and it says so (Section 5) |
| Both beta forms are maintained and comparison states which form it used | `mvp-contract.md` Section 6, `evaluation.md` Section 1 | The two are never pooled into one number |
| `unknown` is a legitimate outcome; a recording that cuts before the top is `unknown`, not `fall` | `mvp-contract.md` Section 6, `annotation-guide.md` Section 5 | Section 8.5's third end condition |
| Attempt, move, beta and fall are all provenance class `derived` | `mvp-contract.md` Section 10 | One class per artifact, never collapsed |
| Confidence never increases downstream | `mvp-contract.md` Section 10 | Section 8.9 |
| No generated coaching text, ever | `mvp-contract.md` Sections 2 and 11 | No string in any output is composed at runtime |
| The Stage 6 gate metric is the normalised sequence edit distance, reported separately per form | `evaluation.md` Section 1 | Section 11 |
| Conventions C1 to C10 | Section 0 | Ratios are rationals; comparisons are cross-multiplications; configs are versioned |

## 7. Open decisions

### `two-limb-stability-criterion`

**This is a semantic change, not a simplification, and the record must say so.**

The stability test this brief inherited (Section 8.3) requires that **the number of limbs in
contact is at least the minimum supporting limbs**, with three `[PILOT]` as the value it carried.
With hands only, that criterion **cannot hold**: a climber has two hands, so the maximum
attainable count is two and no segment is ever stable, no segment is ever an endpoint of a move,
and the stage derives nothing at all.

Lowering the number from three to two looks like a parameter change. It is not. With four limbs,
"at least three in contact" describes a **body supported at three points with one limb free to
move**. With two hands, "both hands in contact" describes **a climber hanging from both hands**,
which is a different physical claim reached by the same arithmetic. The threshold survives; its
meaning does not. Recording that as a threshold tweak would leave the repository with a number
whose `selection` string describes a criterion nobody chose.

| | |
| --- | --- |
| Question | What makes a configuration **stable** when the attempted limb set is the two hands? |
| Option A **(recommended)** | **A hand configuration is stable when both hands are in determinate contact and that configuration persists for at least the minimum stable dwell.** A one-handed configuration is therefore never stable: the span between releasing one hand and matching the next is always **inside** a move, never a state of its own |
| Option B | Allow a **single-hand** configuration to be stable if it persists for at least a separate, longer single-hand dwell. This captures a genuine one-handed rest, which does happen: climbers shake out on a good hold with one hand off |
| Why A is recommended | It makes a move a **hand-to-hand transition**, which is how these problems are actually described (Section 1.2). The unit the sport uses is "left hand to the crimp, right hand to the pinch", and under A that is exactly one move. Option A also needs **no new threshold**: it is fully determined by the dwell that already exists |
| The risk B carries | Every **deadpoint** passes through a one-handed span. If that span exceeds the single-hand dwell, a single dynamic move becomes two moves with a state between them, the move count inflates, and both beta forms acquire a token pair for a position the climber was never in. The dwell that separates a rest from a deadpoint is a number **nobody can select without validation data**, and until it is selected, B makes the move count depend on an unselected placeholder |
| Consequence of A, stated plainly | A genuine one-handed rest is **not** represented as a state. It lies inside a long move, and its duration shows up in that move's duration rather than as dwell. That is a real loss, it is the price of A, and the report says so rather than discovering it later |
| Reversibility | B remains available. Adopting it later changes the derived move list, so every stored move-count comparison is invalidated and must be recomputed. It does **not** change the token total order id, which is a separate identity (`beta-token-grammar`) |
| Interaction with `min_supporting_limbs` | The threshold stays in `configs/sequence/v1.json` as the seam, with the value **2** and the status `[FIXED]` on adoption of this decision. It is read as **"all of the attempted limbs"**, not "any two limbs", and the `selection` string says which criterion fixed it. When feet return, the seam is where the criterion is re-decided |
| What the ADR records | That the criterion is a **semantic redefinition** forced by `hands-first-scope`, not a threshold tweak; both options with the deadpoint risk stated; the chosen wording of A verbatim; the consequence that a one-handed rest is not a state; the `min_supporting_limbs` value, status and reading; and that a move is a hand-to-hand transition under this criterion |

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

Under `two-limb-stability-criterion`, option A (Section 7). A segment is stable when **all three**
hold:

1. its duration is at least the minimum stable dwell;
2. **all of the attempted limbs — both hands — are in contact**, which is `min_supporting_limbs`
   read as a count over the attempted set, value **2** `[FIXED]` on adoption of that decision;
3. its configuration is determinate **over the attempted limbs** (Section 5).

Test 3 runs first in effect: an indeterminate configuration can never be stable, whatever its
duration, because a stable segment is an endpoint of a move and a move between unknowns is a
phantom.

**Clause 2 is not satisfied by duration.** A one-handed span is unstable **however long it lasts**
— that is what distinguishes option A from option B, and it has its own test (T2b in Section 10)
with a one-handed span deliberately made **longer** than the dwell threshold, so that the test
fails if someone reintroduces a duration-based escape.

**A foot never enters this test.** Feet are not in the attempted set, so they contribute neither
to clause 2 nor to clause 3. A foot target of `unknown` does not make a configuration
indeterminate; a foot is not a supporting limb here because the system never looked at it, which
is a statement about the measurement and not about the climbing.

### 8.4 Moves - the crux of Stages 6 and 7

A move is the span from the **end of one stable segment** to the **start of the next stable
segment whose configuration differs**. Unstable segments in between are absorbed into the move.

Under the criterion in Section 8.3, a move is therefore a **hand-to-hand transition**: it begins
when a two-handed configuration ends and finishes when the next differing two-handed configuration
is established. That is the unit the sport itself uses to describe these problems (Section 1.2).

**If the next stable configuration equals the previous one, that is not a move.** It is a **hand
re-grab** — a hand released and returned to the same hold — and it is counted at Stage 7
(`mvp-contract.md` Section 6, foot adjustment, and the hand re-grab counted alongside it).

**Foot adjustments are `not_applicable` for the MVP.** Stage 7 counts a foot adjustment as the
**complement** of a move: a release and re-attach whose bracketing stable configurations are
identical. That complement is well defined only because **this section** defines the move, which is
why it is stated here rather than left to Stage 7 to discover. With feet unpredicted there is **no foot release to observe**, so the
foot-adjustment count is not zero and not absent: it is `not_applicable`, with the reason recorded
(`hands-first-scope`). A zero would read as "this climber never adjusted a foot", which is a
measurement nobody made. **Stage 7's brief has not been amended for this**; flag it in the report.

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
| - loss of contact | **The attempted limbs — both hands —** release within the fall release window, followed by at least the minimum off-wall time with zero hand contacts | `loss_of_contact_candidate`, which the decision in Section 7 refuses to split |
| - recording end | The recording ends before either of the above | `unknown` |

**The start condition on this envelope.** The `start`-role holds are the **lit holds the owner
marked as start holds** in the problem definition (Stage 3); they are not inferred from position
on the panel and not guessed from which hold is lowest. On many board problems the start is a
**two-hand position** — both hands on the marked start holds, or both on one of them — and that
fits the stability criterion of Section 8.3 cleanly: the starting configuration is already a
stable two-handed configuration, so the attempt's first stable segment and its first move need no
special case.

Where a problem's start is **not** two-handed, the start condition is still the one above — all
marked start holds held for the dwell — but the resulting configuration is not stable until both
hands are in determinate contact, so the attempt starts before its first stable segment. That is
correct and must not be patched: an attempt boundary and a stable configuration are different
things.

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

For the MVP that last stable configuration is a **hand** configuration, which is a **narrower
claim** than the contract's general fall-location definition (Section 5). The narrowing is carried
in the data by the configuration's attempted-limb set and stated in words wherever a fall location
is reported. It is not repaired by wording: "the last stable configuration" and "the last stable
**hand** configuration" are different statements, and only the second is supported.

### 8.8 Beta tokenisation

Emit the limb-aware sequence first, in the total order from Section 7. Derive the limb-agnostic
sequence as the **order-preserving projection** of the limb-aware sequence with the limb key
dropped. Never sort it independently: two independently sorted sequences can disagree about
relative order on the same input, and then the two forms describe different climbs.

The fixed limb order is a stated constant, proposed as left hand, right hand, left foot, right
foot, and its identity is part of the order id.

**Keep all four limbs in that constant even though the MVP populates only the first two.** The
order id is `[FIXED]` on adoption of `beta-token-grammar`, and a change to the ordering rule is a
new order id that invalidates every stored comparison. Declaring the four-limb order now means
restoring feet later **extends** the populated set without changing the rule, so comparisons made
today remain comparable. Declaring a two-limb order now would guarantee an order-id change on the
day feet return, for no benefit.

**Both token forms still exist and are still reported separately.** For the MVP, *limb-aware*
means **left hand versus right hand**, and *limb-agnostic* means the same sequence with the hand
key dropped. The two forms are not pooled, and the distinction is not weakened by there being only
two limbs: "left hand to the crimp" and "some hand to the crimp" are different sequences, and two
attempts can agree on one and disagree on the other.

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
| `min_supporting_limbs` | count | **`[FIXED]` on adoption of `two-limb-stability-criterion`**, value **2** | Segment stability. Read as **"all of the attempted limbs"**, not "any two limbs" (Sections 7, 8.3). Its `selection` string names the decision that fixed it, not a sweep, because no sweep chose it |
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
`min_stable_dwell_us = 1 000 000`, `min_supporting_limbs = 2` read as all attempted limbs
(Section 8.3), and `attempted_limbs = [left hand, right hand]`:

| Limb | Intervals |
| --- | --- |
| left hand | H1 over `[0, 10 000 000)` |
| right hand | H2 over `[0, 4 000 000)`, no contact over `[4 000 000, 6 000 000)`, then a re-attachment over `[6 000 000, 10 000 000)` |
| left foot, right foot | **Not attempted.** No interval exists and none is invented; they are absent from the assignments and outside the attempted-limb set (Section 5, and Stage 5 Section 5.4) |

Breakpoints are `0, 4 000 000, 6 000 000, 10 000 000`: three segments of `4 000 000`, `2 000 000`
and `4 000 000` microseconds, summing to `10 000 000`. Segment 2 has **one** hand in contact.

**The middle segment is deliberately long.** At `2 000 000` microseconds it is **twice** the dwell
threshold, so duration alone would make it stable, and clause 2 of Section 8.3 is the **only**
thing that excludes it. The fixture is built that way so that a duration-based escape, or a quiet
adoption of option B, changes a test result instead of passing unnoticed.

| # | Test | Expected |
| --- | --- | --- |
| **T1** | **The decisive test.** The right hand re-attaches to **H2**, so segment 3's configuration equals segment 1's | **Zero moves.** One same-configuration cycle — a **hand re-grab**, counted at Stage 7, not here |
| **T2** | **The decisive test, mirrored.** The right hand re-attaches to **H5** instead | **One move**, interval `[4 000 000, 6 000 000)`, duration `2 000 000` microseconds, changed limbs exactly `[right hand]` |
| **T2b** | **The criterion test.** Segment 2 is one-handed and exceeds the dwell threshold | Segment 2 is **unstable** under both T1 and T2. Under option B of `two-limb-stability-criterion` it would be stable and **T1 would yield two moves instead of zero**, so this test is what pins option A rather than merely describing it |
| T3 | Breakpoints and segments from the hand-authored interval set | Three segments; durations `4 000 000`, `2 000 000`, `4 000 000`; sum equals the attempt duration |
| T4 | A segment in which the **left hand's** target is `unknown` | Never stable, at any duration. Two such segments do **not** compare equal, and their configuration ids differ |
| T5 | Two attempts in one recording with a rest between | Two attempt records; the gap belongs to neither; no derived record carries a timestamp inside the gap |
| T6 | A recording starting mid-attempt | `start_observed = false`; the first frame is not used as the start |
| T7 | A recording cutting before the top | Candidate `unknown`. **Never** a loss-of-contact candidate |
| T8 | The derived candidate vocabulary | The candidate field's type admits neither `fall` nor `controlled_drop`; a schema test asserts the closed set, and the deriver has no code path that separates them |
| T9 | Two events at an identical timestamp: the **right** hand releases H2 and the **left** hand attaches H6 at `5 000 000`. H2 is the right hand's target in the shared fixture above | Order is `release(right_hand, H2)` then `attach(left_hand, H6)`, deterministically. Release precedes attach whatever the limb order says (Section 7) |
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
| **T20** | **Unattempted limbs.** Four assertions on the shared fixture: no derived document asserts a determinate contact state for either foot; a foot absent from the attempted set does **not** make any configuration indeterminate, so segments 1 and 3 are stable; two configurations with identical hand assignments but **different attempted-limb sets** have **different** configuration ids; and an input contact series containing a foot event with `target_kind = "none"` never reaches the deriver, because the input is parsed through the Stage 5 model whose validator rejects it as `DOCUMENT_INVALID` (Stage 5, Section 10.11) | The third assertion is the one that protects the future: it is what stops a hands-only configuration silently comparing equal to a four-limb one when feet return |
| **T21** | **The two forms still differ under two limbs.** Reference `attach(left_hand, H1)` at `t1` then `attach(right_hand, H2)` at `t2`; hypothesis `attach(right_hand, H1)` at `t1` then `attach(left_hand, H2)` at `t2` — the same holds in the same order, with the hands swapped | **Limb-aware**: two substitutions, distance `2`, normalised `RatioValue{num: 1, den: 1}`. **Limb-agnostic**: distance `0`, normalised `RatioValue{num: 0, den: 1}`. Pooling the forms would report one of these as though it were the other |

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
| D4 | Same-configuration cycling | A hand release and re-attach to the same target produces **zero** moves | pending measurement |
| D5 | Both forms | Limb-aware and limb-agnostic emitted separately and never pooled | pending measurement |
| D6 | Deterministic order | Token order is invariant under input permutation | pending measurement |
| D7 | Unknown propagation | No derived value is confident where its inputs were not | pending measurement |
| D8 | Cause | The cause field cannot hold any value other than `not_claimed` | pending measurement |
| D9 | No generated text | No prose anywhere in the code or the output | pending measurement |
| D10 | Two-limb stability | A one-handed segment is **never** stable, however long it lasts; T2b, and T1 still yields zero moves | pending measurement |
| D11 | Unattempted limbs | No derived record asserts a determinate contact state for a limb outside the attempted set; configuration identity **includes** the attempted-limb set; T20 | pending measurement |

### `[PILOT]` clauses

| # | Clause | Reported as |
| --- | --- | --- |
| P1 | Normalised sequence edit distance against the adjudicated beta | **Separately for each form**, on the frozen test split, as a **distribution over attempts** with its spread, not only a mean. Both forms are **hand** sequences for the MVP, and the report says so beside the number |
| P2 | Outcome agreement rate between the derived candidate and the human label | With the `not_compared` count beside it |
| P3 | Move-count agreement against adjudicated moves | Per attempt, as a distribution, not pooled. The adjudicated move list must be a **hand-to-hand** move list under the same criterion, or the comparison is between two different definitions and the disagreement measures the definitions |

**Foot-adjustment counts are `not_applicable`** and are Stage 7's to report (Section 8.4). They
appear in no clause here, and this stage emits no zero for them.

### Honest limitation

About fifty attempts `[PLANNING]` yields at most fifty sequence comparisons, of which roughly
fifteen `[PLANNING]` fall in the frozen test split. That supports a distribution with visible
spread and **no tight mean**. The independent cross-check is tighter still: the hand-written beta
covers about ten attempts in total `[PLANNING]` (operating manual Section 5.3, item 28), so the
non-circular half of this gate rests on a single-digit number of attempts per form.

Every distance also inherits Stage 5's contact errors. A single mis-identified hold changes two
tokens, one attach and one release, so a weak Stage 5 **hand** slice shows up here as a Stage 6
number — and on this envelope the hand slice is the only slice there is, so there is no other
slice to absorb it. **Therefore report the relationship between an attempt's contact `unknown`
rate and its edit distance**, as a paired per-attempt table, plus a rank statistic computed as an
exact integer rational over concordant and discordant pairs. **No p-value and no significance
claim**: at this sample size a rank statistic is descriptive. If the relationship is strong, this
stage is measuring the previous one, and that must be said in the report rather than discovered
later.

**What the hands-only scope does and does not cost here.** It does not cost comparability with how
the sport describes these problems: a hand sequence is the domain's own representation
(Section 1.2), so the derived sequence is the same kind of object the humans write, not a
truncation of a richer one. That holds **only if the hand-written beta is itself recorded as a
hand sequence**. If it was written with foot tokens, they are excluded before the comparison, and
**the exclusion and the number of tokens it removed are reported** — a silent exclusion would make
the derived sequence look better by deleting the part it never attempted.

What the scope does cost is stated plainly: no foot adjustment is observed, no one-handed rest is
a state (Section 7), and the fall location is a hand configuration (Section 8.7). None of those is
measured by any clause in this stage, and none may be described as though it were.

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
| `pytest`, `ruff` | D1, and the fixture clauses of D10 and D11 |
| `derive` | D3, D4, D7, D10, D11 on real inputs, and the artifact layout on disk |
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
| 10 | Treating the stability thresholds as cosmetic | They are placeholders, so they feel arbitrary | They are load-bearing: too low and every wobble is a move, too high and fast sequences vanish. `min_stable_dwell_us` is `[PILOT]`, selected on validation data, and the selection is recorded. `min_supporting_limbs` is **not** swept: it is fixed by a decision (Section 7) |
| 11 | Lowering `min_supporting_limbs` from three to two as a "config fix" | The inherited criterion is unsatisfiable with two limbs, and the smallest edit that makes the code run is to change the number | It is a **semantic redefinition**, not a parameter change (Section 7). Landing it as a config edit leaves a repository whose `selection` string describes a criterion nobody chose, and whose move counts mean something different from the day before |
| 12 | Letting a one-handed span become a state | It has a duration, it is determinate over the hand that is on, and it looks like a configuration | Under the adopted criterion it is **inside a move**. Admitting it turns every deadpoint into a state and doubles the move count on exactly the dynamic problems these boards are built for. T2b |
| 13 | Feet making every configuration indeterminate | The determinacy rule says "`false` if any limb's target is `unknown`", and the feet are `unknown` for the whole recording | Determinacy is evaluated **over the attempted limbs** (Section 5). The naive reading makes nothing ever stable and the stage returns `insufficient_data` everywhere while appearing rigorous |
| 14 | An unattempted foot recorded as `none` | It is the tidy-looking value for "nothing here", and it arrives through a default rather than a decision | It asserts a foot was off the wall in frames where no code looked at a foot. `unknown`, never `none` (Stage 5, Section 5.4). T20 |
| 15 | Calling the hands-only beta a degraded beta | Two limbs feel like half of four | Beta on these boards **is** a hand sequence in the sport's own usage (Section 1.2). Describing it as degraded invites someone to "fix" it by inferring feet, which is the one thing the ground truth cannot support |

## 14. Report format and stop condition

Follow Section 0. In addition, this stage's report must contain:

- the two `[PILOT]` edit-distance distributions, **one per form**, never a pooled figure, each labelled as a **hand** sequence;
- the outcome agreement rate **with** its `not_compared` count and the size of the compared subset;
- the paired per-attempt table of contact `unknown` rate against edit distance, with the rank statistic and an explicit statement of what it does and does not support;
- the count of attempts that returned `insufficient_data`, as a number in the gate table rather than a remark;
- the **stability criterion actually implemented**, in the wording adopted from Section 7, stated once beside the move counts, because a move count read without its criterion is not interpretable;
- a statement that the reported **fall location is a hand configuration**, which is narrower than the contract's general definition (Sections 5, 8.7);
- a statement that **foot-adjustment counts are `not_applicable`** for the MVP and that **Stage 7's brief has not been amended to say so** — this is a hand-off item for the owner, not a defect in this stage;
- what this stage does not prove: it does not prove that any move list is correct, only that the derivation is deterministic and that its disagreement with the hand-written beta was measured on a single-digit number of attempts per form; and it proves nothing whatever about feet, one-handed rests, or a wall that is not this board;
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
| `docs/agents/briefs/stage-5-*.md` | What Stage 5 actually emits, and the names it chose. **Sections 1.1 (the board envelope), 5.2 (`attempted_limbs`), 5.4 (an unattempted limb is `unknown`, never `none`) and 7.4 (`hands-first-scope`) are preconditions for everything in this brief** |
| `docs/adr/hands-first-scope.md` | The decision this stage inherits, in the owner's own record rather than in a brief's summary of it |
| `src/climbvision/schema/versions.py`, `schema/__init__.py`, `schema/provenance.py` | The three-place registration seam and the shape of `IngestRun` |
| `src/climbvision/serialization.py`, `timebase.py`, `hashing.py`, `errors.py` | `dumps_canonical`, `loads_json`, `parse_rational`, `pts_to_us`, `us_to_pts`, `sha256_file`, `ClimbVisionError` |
| `src/climbvision/quality.py` | The integer cross-multiplication pattern (C2) and the config-threshold accessor that raises `CONFIG_THRESHOLD_MISSING` |
| `src/climbvision/ingest.py`, `cli.py` | Orchestration-only structure, exit codes, and `validate` dispatching on `schema_id` |
| `tests/unit/test_scope_guard.py`, `tests/unit/test_schema.py`, `tests/conftest.py` | `STAGE_ONE_MODULES`, `ALLOWED_THIRD_PARTY`, `BANNED`, `DOCUMENT_MODELS`, `ALL_MODELS`, `block_network` |
| `configs/ingest/v1.json` | The exact config shape to copy, including the `selection` string convention |
