# Stage 8 - minimal application surface

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

After Stages 1 through 7 have passed their gates, add the **smallest surface** that lets a human
look at validated telemetry:

- an upload and job interface;
- a review timeline;
- an append-only correction workflow;
- a repeated-attempt comparison view over Stage 6 and Stage 7 output;
- consent and retention controls.

**Generate nothing. Compute nothing new.** Every number on every screen was written by an earlier
stage and is read back by hash.

## 2. Preconditions

**All seven prior gates recorded as measured in `docs/status.md`.** This is the one stage whose
precondition is a hard blocker, and `mvp-contract.md` Section 9 states it explicitly: "Stages 1
through 7 have passed their gates first".

| # | Precondition | Check |
| --- | --- | --- |
| 1 | Stage 1 gate measured | `docs/status.md`, Stage 1 row, four clauses with numbers |
| 2 to 7 | Stage 2 through Stage 7 gates measured | `docs/status.md`, one row each, each with its number and its failing slices |
| 8 | The owner has recorded a go decision for Stage 8 | Operating manual Section 2.1, item 31. Deferring Stage 8 explicitly is a legitimate outcome |

**If any gate reads `pending measurement`, stop and report.** Do not build against a gate that has
not been measured, do not build "the parts that do not depend on it", and do not measure it
yourself as part of this stage.

As of the writing of this brief, `docs/status.md` records Stages 2 through 8 as **not started**,
so this precondition currently fails. That is the expected state; it is written here so that an
agent reading only this brief cannot mistake the situation.

## 3. Human inputs required before the agent starts

Four decisions, plus one artifact the owner must produce.

### `application-stack`

| | |
| --- | --- |
| Question | A small web framework with server-rendered HTML, plain client-side scripting and the Stage 3 overlay renderer, or a component framework with a build toolchain? |
| Recommendation | **No component framework.** The surface is a timeline, a table and an overlay. A build toolchain is a maintenance liability for an owner who does not write code, and it adds a package manager, a lockfile and a compilation step to a project whose entire runtime dependency list is currently one package |
| Selection properties, not a product name | Server-rendered HTML templating; an **in-process test client**, so the suite runs with the network-blocking fixture in force; a small dependency tree; no compilation step; a server that runs on loopback without extra infrastructure |
| What the ADR records | The chosen framework and server by name and version, the properties above that decided it, and the packages moved out of `BANNED` |

### `application-auth-model`

| | |
| --- | --- |
| Question | Single-user, loopback-only, with no authentication, or token authentication? |
| Rule to state in the record | **The moment it binds to a non-loopback interface, authentication is mandatory.** It serves video of a person's face |
| Recommendation | Loopback-only with no authentication for the MVP, with the bind address in config and a startup hard failure if a non-loopback address is configured while authentication is absent |
| What the ADR records | The bind policy, the failure behaviour, and the trigger that makes authentication mandatory |

### `retention-policy`

| | |
| --- | --- |
| Question | How long raw media is kept, and **what deletion means for content-addressed artifacts that reference it** |
| Note | The consent record already names a retention period (operating manual Section 4.5), so a provisional answer exists before filming. This stage **enforces** it |
| What the ADR records | The period with its unit, the deletion trigger, and the tombstone semantics in Section 8.6 |

### `application-storage-root`

| | |
| --- | --- |
| Question | Where the application's data root lives |
| Rule | The data root **must live outside the repository tree** and must be configured. No code path may write real footage into a working tree |
| Enforcement | A startup check that resolves the configured root and hard-fails if it is inside the repository. Not a default, not a warning |
| Form | Written in the `~/climbvision-data/...` form used throughout the operating manual. **Absolute paths never appear in artifacts** (`mvp-contract.md` Section 7) |

### The artifact

The owner must produce a **real consent record** for themselves and for any other participant,
stored in the ignored consent directory outside the repository. The application refuses to serve
an asset that does not resolve to one, so an absent record is a blocked surface, not a warning.

## 4. Deliverables

Module paths are **proposals**.

| Path (proposed) | Owns |
| --- | --- |
| `src/climbvision/app/__init__.py` | Package marker and the application factory |
| `src/climbvision/app/api.py` | Routes: upload, job submission, review, comparison, corrections, consent, retention |
| `src/climbvision/app/jobs.py` | Recorded intent to run an existing CLI subcommand, and the append-only job records |
| `src/climbvision/app/review.py` | Read-only assembly of already-written documents into the timeline view model |
| `src/climbvision/app/corrections.py` | Append-only correction capture |
| `src/climbvision/app/comparison.py` | The repeated-attempt view over Stage 6 and Stage 7 output |
| `src/climbvision/app/consent.py` | Consent resolution, the retention scan and deletion |
| `src/climbvision/app/templates/` | Server-rendered HTML templates |
| `src/climbvision/schema/application.py` | The job record, the retention policy and the deletion event |
| `configs/application/v1.json` | The upload size limit, the bind address, the data root and the retention period |
| `docs/adr/<slug>.md` x4 | The four decisions above, created one at a time, when decided |

**No telemetry entity is introduced here.** If this stage needs a field that does not exist, the
answer is a brief for the stage that owns it, not a new model under `app/`.

### Seams to update

| Seam | Concretely |
| --- | --- |
| Schema constants, registry, exports | As every stage: `SCHEMA_IDS`, `MODEL_REGISTRY`, `__all__` |
| Schema tests | `DOCUMENT_MODELS` rows with committed golden fixtures; `ALL_MODELS` for the no-float, `extra="forbid"` and `frozen=True` checks |
| Scope guard | A **new** `STAGE_EIGHT_MODULES` set. The import allowlist becomes **path-scoped**: the newly permitted packages are allowed **only** for files under the application package, everything else keeps the existing allowlist. Extend the one guard; do not add a second guard file |
| Banned list | Move only the chosen packages **out** of `BANNED` and into the application-scoped allowlist, and keep the standing test that the allowlist and `BANNED` never intersect |
| Dependency pin | `test_the_runtime_dependency_list_is_exactly_pydantic` changes here, and **only** here. Update it to the exact new list; do not loosen it into a substring match |
| CLI | A `serve` subcommand with exit-code tests |
| Config | `configs/application/v1.json` in the shape of `configs/ingest/v1.json` |
| Status ledger | The Stage 8 row, with the workflow gate table |
| Contract documents | No edit is authorized by this brief |
| Decision records | Four, one at a time, under `docs/adr/` |
| Ignore rules | Confirm the application data root is outside the tree; the path-scoped ignore rules do not change |

## 5. Entities

`ConsentRecord` and `CorrectionEvent` are **Stage 2 entities** (`docs/data-schema.md` Section 1,
and the "entity introduced vs workflow exposed" table in that section, which says exactly this:
the model exists at 2, the human-facing control exists at 8). **This stage adds the controls, not
the models.** Three records are new.

### Job record

A job is append-only, like `IngestRun`. A job also has a lifecycle, so the honest representation
is **append-only job events folded into a current state**, never an in-place status mutation. The
minimum is two records per job, accepted and finished.

| Field | Representation | Notes |
| --- | --- | --- |
| Job id | Opaque string | |
| Event timestamp | UTC, in the pattern `IngestRun` already uses | Ordering key for the fold |
| Asset id | `sha256-<64 hex>` | |
| Subcommand | String naming an **existing** CLI subcommand | Never a shell string |
| Arguments | List of strings | Passed as an argument list |
| State | `accepted`, `running`, `succeeded`, `failed` | Derived by folding events in timestamp order |
| Exit code | Nullable integer | |
| Error code | Nullable SCREAMING_SNAKE code | The same vocabulary `ClimbVisionError` uses |
| Config version and hash, `climbvision` version, Python version | | As `IngestRun` records them |

### Retention policy

| Field | Representation | Notes |
| --- | --- | --- |
| Policy id | Opaque string | |
| Scope | Which assets or participants it covers, by opaque id | |
| Retention period | Integer, with its unit stated | No float, no "about a year" |
| Basis | The consent record id whose stated period this implements | Opaque id only |
| Effective from, created at | UTC timestamps | |

### Deletion event

| Field | Representation | Notes |
| --- | --- | --- |
| Deletion id | Opaque string | |
| Asset id | `sha256-<64 hex>` | The identity survives the bytes |
| Requested at, executed at | UTC timestamps | |
| Reason | Closed set: `retention_expiry`, `withdrawal`, `owner_request` | |
| Media state after deletion | Literal `deleted` | **Not** `missing`. The difference is the whole point |
| Tombstone | The record itself is the tombstone | No path, ever (`mvp-contract.md` Section 7) |

## 6. Decisions already frozen

| Frozen item | Where | Consequence here |
| --- | --- | --- |
| Stage 8 is a **workflow gate with no accuracy target** | `mvp-contract.md` Section 9 | Do not invent one |
| The surface exposes **only validated primitives, each carrying its provenance** | `mvp-contract.md` Section 9 | Every rendered value shows its provenance class |
| Corrections are captured **append-only** | `mvp-contract.md` Section 9, `annotation-guide.md` Section 6 | No destructive edit path exists |
| **No mobile application** until real web usage validates the workflow | `mvp-contract.md` Sections 2, 9 | Not started, not scaffolded, not discussed |
| Generated coaching text is out of scope permanently | `mvp-contract.md` Sections 2, 11 | No summary text, no advice, no narration |
| No real user video, faces, consent records or model weights in the repository | `mvp-contract.md` Section 7 | The data root is outside the tree |
| Absolute filesystem paths never appear in written artifacts | `mvp-contract.md` Section 7 | Records carry hashes and opaque ids |
| Confidence never increases downstream | `mvp-contract.md` Section 10 | Section 8.4 |
| An overlay is never the only result | `docs/data-schema.md` Section 6 | The view renders documents; it never replaces them |
| Security sign-off is **never fully automated** | `evaluation.md` Section 3 | Section 10, last row |
| Media touches only the existing media boundary | `AGENTS.md` Section 4 | Section 8.1 |
| Conventions C1 to C10 | Section 0 | |

## 7. Open decisions

The four in Section 3: `application-stack`, `application-auth-model`, `retention-policy`,
`application-storage-root`. All four are in the decision index in `docs/agents/README.md` and all
four are currently open. Each is recorded as its own file under `docs/adr/`, **one at a time, at
the moment it is made**. An empty decision record is indistinguishable from a decided one.

## 8. Approach

### 8.1 Upload

1. Stream to a temporary file. Never read the whole body into memory.
2. Enforce the size limit from config, as a hard failure with its own error code.
3. Hash the bytes to an asset id, using `sha256_file` and `asset_id_from_digest`.
4. **Probe the file to decide whether it is media. Never by file extension.** The probe is the
   existing media boundary, and the existing hard-fail conditions apply unchanged: a non-zero
   return code, an `error` key in the parsed output, or no video stream
   (`docs/data-schema.md` Section 9).

**Never interpolate a filename into a shell string.** The existing probe boundary already passes
an **argument list**, runs from the file's own directory, and refers to the file by a **bare
basename** so that the filename ffprobe echoes back is never an absolute path. Keep that pattern
exactly; do not add a second way to invoke a subprocess.

### 8.2 Jobs

A job is a **recorded intent to run an existing command-line subcommand**, executed with an
argument list. The job record is append-only.

**No queue. No worker pool. No retries that hide failures.** A failed job stays failed and shows
its error code. A retry, if the owner wants one, is a new job with its own record, visibly linked
to the first.

### 8.3 The review timeline

A **read-only assembly of already-written documents**. It reads; it never derives.

| Layer | Source |
| --- | --- |
| Contact intervals, as bars per limb | Stage 5 documents |
| Moves, as markers | Stage 6 documents |
| Attempt spans | Stage 6 documents |
| The hip trajectory, as a polyline over the reference frame | Stage 7 documents, in their declared coordinate space |
| Hold overlays | The Stage 3 renderer, reused. Do not write a second renderer |

### 8.4 Rendering uncertainty - the most dangerous code in the project

**Every value renders its provenance class**, and any `abstained`, `unknown` or
`insufficient_data` status renders as **that literal word**. Never as an empty cell. Never as
zero. Never as a dash.

This is the most likely place in the whole project to violate rule 15, because user-interface code
falls back to empty by nature: a template that prints nothing when a value is null looks correct
in every review and is a fabrication on screen. An empty cell says "nothing here"; the truth is
"we looked and could not tell", and those are different claims. The test in Section 10 fails on a
blank and on a zero.

### 8.5 Corrections

A correction writes a **new correction event** and a **new document version**. The prior version
stays, byte-for-byte. The interface has **no destructive edit path**: no delete button, no
in-place field edit, no overwrite.

Disagreement is data (`annotation-guide.md` Section 6). An interface that lets a human tidy away a
disagreement destroys the only signal that measures ontology quality.

### 8.6 Consent, retention and deletion

| Control | Behaviour |
| --- | --- |
| Consent gate | Every asset must resolve to a consent record before it can be served. A missing record is a **refusal**, with its own error code, not a warning banner |
| Retention scan | Lists assets past their retention window. Read-only; it deletes nothing |
| Deletion | Removes the raw media and **writes a tombstone**. The content-addressed derived graph **survives**, with the media marked `deleted` |

Deletion must not break provenance. A derived document referencing an asset id whose media is gone
should report the media as **deleted**, with its deletion event, rather than as missing or
unreadable. A broken chain and a deliberate deletion look identical from the outside unless the
tombstone exists.

## 9. Dependencies

The permission here is narrow, and it is additional to the dependencies Stage 4 authorized.

| Package class | Status | Scope |
| --- | --- | --- |
| A small web framework and its server | **Unbanned at this stage only** | Importable **only** from files under the application package, enforced by the path-scoped allowlist in the scope guard |
| An HTTP client | Unbanned in the **development group only** | For the in-process test client. Never a runtime dependency |
| Object-relational mappers, database drivers, caches, cloud SDKs, task queues | **Still banned** | Documents on disk are the store. There is no database in this project |
| Any JavaScript package manager | **Recommend not unbanning at all** | Plain client-side scripting and the existing overlay renderer are sufficient for a timeline, a table and an overlay |

Two consequences worth stating before the framework is chosen:

- The autouse `block_network` fixture in `tests/conftest.py` **stays in force**. The suite must
  exercise the application through an **in-process test client** that opens no socket. A candidate
  framework with no in-process client is a candidate that cannot be tested here, which is a reason
  to choose a different one.
- The dependency-pin test changes exactly once, in this change set, to the exact new list. It is
  not loosened into a pattern match, because the point of the pin is that the next addition is
  also visible.

## 10. Tests

Numbers in this section are fixture facts, not thresholds, and are untagged by the convention in
`AGENTS.md` Section 8.

| # | Test | Expected |
| --- | --- | --- |
| T1 | Oversize upload | Rejected at the configured limit, with its own error code, without writing a stored asset |
| T2 | Non-media upload | Rejected **by probing**, not by extension. Include a file whose extension says `.mp4` and whose bytes are not media, and a real media file whose extension is wrong: the first is rejected, the second is accepted |
| T3 | Filename handling | The filename is never interpolated into a shell string. The probe is invoked with an argument list, from the file's own directory, with a bare basename. A filename containing shell metacharacters and spaces round-trips without effect |
| T4 | Content-addressed naming | The stored asset is named by its hash. The same bytes uploaded twice under different names are the same asset |
| T5 | Correction | After a correction, the target document's bytes are **unchanged**, a correction event exists, and a new version exists |
| T6 | Uncertainty rendering | `abstained`, `unknown` and `insufficient_data` render as those literal words. **A blank fails the test. A zero fails the test.** Assert on the rendered output, not on the view model |
| T7 | No advice | A grep over the templates **and** `src/` for advice vocabulary (`should`, `try`, `improve`, `tip`, `recommend`, `better`, `coach`) in user-facing strings, and for any text-generation call, returns nothing |
| T8 | Consent | An asset with no consent record is **refused**, with its error code. The refusal is tested on the serving path, not only on the upload path |
| T9 | Deletion | Deletion writes a tombstone; derived documents survive; the provenance chain reports the media as **deleted**, not missing |
| T10 | Comparison | The comparison endpoint **reads Stage 6 output** and computes no distance itself. Assert that the rendered distance equals the stored one byte-for-byte, and that the module imports no alignment code |
| T11 | Storage root | A data root configured **inside** the repository tree is a startup hard failure |
| T12 | Bind policy | A non-loopback bind address with no authentication configured is a startup hard failure |
| T13 | Integration smoke | Local client only, with `block_network` still in force: upload, job, timeline, correction, comparison, retention scan, deletion |
| T14 | Registry and round-trip | The three new documents validate through `MODEL_REGISTRY` by their own `schema_id`, and re-serialize byte-identically |

Then **run the security review over the diff.** This stage crosses authentication, file upload,
new endpoints and sensitive data simultaneously, which is four trust boundaries in one change set.
Note in the report that **an automated scan is evidence, not approval** (`evaluation.md`
Section 3), and that the human sign-off is recorded separately.

## 11. Gate

A **workflow gate with no accuracy target**, as `mvp-contract.md` Section 9 states.

| # | Clause | Assertion | Evidence |
| --- | --- | --- | --- |
| W1 | Prior gates | All seven prior gates recorded as **measured** in `docs/status.md` | pending measurement |
| W2 | End to end | A video uploads, a job runs, and the timeline renders **from validated documents only** | pending measurement |
| W3 | Provenance | Every displayed value carries its provenance class | pending measurement |
| W4 | Corrections | A correction is captured append-only, with the original intact | pending measurement |
| W5 | Comparison | The comparison renders Stage 6 output **without recomputation** | pending measurement |
| W6 | Consent | Consent is enforced; an asset without a record is refused | pending measurement |
| W7 | Retention | The retention scan and deletion are exercised end to end, with a tombstone | pending measurement |
| W8 | No coaching text | None anywhere, enforced by the grep in T7 | pending measurement |
| W9 | No mobile application | None started | pending measurement |
| W10 | Security | The security checklist completed, **with a human sign-off recorded** | pending measurement |

## 12. Verification commands

No absolute paths, in commands or in artifacts. The data root is written in the
`~/climbvision-data/...` form.

```bash
uv sync
uv run pytest
uv run ruff check .

# Serve on loopback, with a data root outside the repository
uv run climbvision serve --host 127.0.0.1 --port <port> --data-root ~/climbvision-data/app

# Validate every document the surface wrote
uv run climbvision validate ~/climbvision-data/app/<...>/*.json

# Working-tree check: no video, no consent record, no weights are tracked
git status --porcelain
git ls-files | grep -Ei '\.(mp4|mov|m4v|pt|pth|onnx|safetensors)$' | grep -v '^tests/fixtures/'
git ls-files | grep -Ei '(consent|weights|checkpoints)/'
```

The browser walkthrough, named step by step, with the expected observation at each step:

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open the surface on loopback | The index lists assets, each showing its consent state |
| 2 | Upload a recording | Accepted by probe, stored under its hash, a job accepted |
| 3 | Watch the job | It reaches `succeeded` or `failed` with a visible error code. No silent retry |
| 4 | Open the review timeline | Contact bars per limb, move markers, attempt spans, the hip polyline, hold overlays |
| 5 | Find an abstained or unknown value | It reads `abstained` / `unknown` / `insufficient_data` as a word, never blank, never zero |
| 6 | Read any value's provenance | Its provenance class is shown beside it |
| 7 | Make a correction | A new version appears; the original is still readable |
| 8 | Open the comparison of two attempts | Stage 6 alignment and distance, stated per form, with no recomputation |
| 9 | Run the retention scan | Lists assets past their window; deletes nothing |
| 10 | Delete one asset | Raw media gone, tombstone written, derived documents still resolve, media reported as `deleted` |

## 13. Traps

| # | Trap | Why it happens | What to do |
| --- | --- | --- | --- |
| 1 | Serving faces beyond loopback | Binding to all interfaces is one flag, and it is the default in many examples | It serves video of a person's face. Authentication becomes mandatory the moment the bind address is not loopback. T12 |
| 2 | Extension sniffing | It is one line and it works on the happy path | It is wrong on both sides: a mislabelled media file is rejected and a disguised non-media file is accepted. Probe. T2 |
| 3 | A storage root defaulting inside the repository | Every example defaults to the current directory | One careless default lands real footage in a working tree, and `.gitignore` is a safety net, not the boundary. T11 |
| 4 | Destructive edits | An edit form is the obvious interface for a correction | It destroys the disagreement signal the annotation guide protects. Append-only, no delete path. T5 |
| 5 | Abstention rendered as blank or zero | Templates print nothing for a null, and nobody notices | It converts "we could not tell" into "nothing happened". T6 |
| 6 | Recomputing in the view | The value is right there and the function already exists | Two answers that diverge, with no way to tell which is stored. Read the document. T10 |
| 7 | Deletion breaking provenance | Deleting the row is tidier than leaving a tombstone | A broken chain and a deliberate deletion become indistinguishable. Tombstones. T9 |
| 8 | Scope creep into coaching | A timeline invites a helpful one-line summary | It is banned permanently (`mvp-contract.md` Sections 2, 11). T7 |
| 9 | Adding a queue | "Jobs" sounds like it needs one | One user, one machine, offline batch. A queue adds a broker, a worker and a class of silent failures |
| 10 | Starting a mobile application | The surface works, so the phone feels next | Not until real web usage validates the workflow (`mvp-contract.md` Section 9) |

## 14. Report format and stop condition

Follow Section 0. In addition, this stage's report must contain:

- the seven prior gate rows **quoted from `docs/status.md`**, with their numbers, as the evidence for W1;
- the browser walkthrough table with what was actually observed at each of the ten steps;
- the security review output, with the explicit note that an automated scan is evidence and not approval, and the **name and date of the human sign-off**;
- the exact new dependency list and the diff to the dependency-pin test;
- the working-tree check output showing no video, no consent record and no weights;
- what this stage does not prove: it proves no accuracy, it validates a workflow on one user and one machine, and nothing on any screen is more reliable than the gate that produced it;
- the honest sentence from Section 0, shown in the surface itself beside any accuracy-shaped number.

Then stop. The MVP is complete when Stages 1 through 7 have measured gates and Stage 8 has either
been delivered against this gate or explicitly deferred by a recorded decision (operating manual
Section 11).

## 15. Read-first list

| File | Read for |
| --- | --- |
| `AGENTS.md` | All of it. Section 4 ("Not before Stage 8"), Section 6 (the guards), Section 11 (reporting), Section 13 (what to do when asked to violate a rule) |
| `docs/mvp-contract.md` | Sections 2 (out of scope, including the mobile application), **7 (privacy and consent boundary)**, 9 (the Stage 8 workflow gate), 10 (provenance classes and the abstention vocabulary) |
| `docs/data-schema.md` | Section 1 and its "entity introduced vs workflow exposed" table; Section 3 (identity); Section 5 (provenance); Section 6 (an overlay is never the only result); **Section 9 (the media boundary and its failure detection)** |
| `docs/evaluation.md` | Section 3, in particular the row stating that security sign-off is never fully automated |
| `docs/annotation-guide.md` | Section 6, on why corrections are append-only and why disagreement is data |
| `docs/status.md` | All seven prior gate rows. This is precondition 1 to 7 |
| `docs/agents/00-operating-manual.md` | Sections 3.11 (storage outside the repository), 4 (consent, bystanders, withdrawal), 9 (the Stage 8 decision row), 11 (what "done" means) |
| `docs/agents/05-verification-commands.md` | The owner's anti-bluff table, which this stage's report will be checked against |
| `docs/agents/briefs/stage-6-attempts-moves-beta.md`, `docs/agents/briefs/stage-7-analytics.md` | What the comparison view and the analytics table are allowed to display, and the exact status vocabulary they emit |
| `src/climbvision/media/ffprobe.py` | The **only** subprocess boundary: `probe_streams`, `probe_packets`, the argument list, the working directory and the bare basename |
| `src/climbvision/ingest.py`, `cli.py` | `ingest`, `MANIFEST_CONFLICT`, exit codes, and `validate` dispatching on `schema_id` |
| `src/climbvision/hashing.py`, `serialization.py`, `errors.py` | `sha256_file`, `dumps_canonical`, `loads_json`, `ClimbVisionError` |
| `src/climbvision/schema/provenance.py` | `IngestRun`, the model for every append-only record this stage writes |
| `tests/unit/test_scope_guard.py`, `tests/conftest.py` | `ALLOWED_THIRD_PARTY`, `BANNED`, the module inventory pins, the dependency-pin test and `block_network` |
| `configs/ingest/v1.json` | The config shape and the `selection` string convention |
| `.gitignore` | The path-scoped rules, and why they are path-scoped rather than extension-scoped |
