# AGENTS.md

Operating rules for any coding agent working in this repository. Tool-agnostic. These rules are
binding: where this file and a convenient shortcut disagree, this file wins.

---

## 1. What this repository is

ClimbVision is computer-vision **telemetry** for indoor bouldering: video -> timestamped
recording -> calibrated wall and user-confirmed hold map -> pose trajectories -> limb-hold
contact intervals -> stable contact-state transitions -> attempts, moves, beta, falls ->
comparison of repeated attempts. It is not a coach, not a grader and not a scorer.

**Traceability rule.** Every output must be traceable to one of: pixels, a human annotation, a
named model, a deterministic derivation, or a measured aggregate. Nothing else may be emitted.

**Current state.** Stage 0 (frozen contract) and Stage 1 (deterministic ingest) are complete:
423 tests, `ruff` and `mypy` clean, zero models, two CLI commands. **Stages 2 through 8 have not started.**
No pose, no hold detection, no calibration, no annotations, no split manifests, no models, no
application surface. Do not write code for a stage that has not been opened by a brief.

**Where truth lives.** An agent reads these before it writes anything.

| Document | Authority |
| --- | --- |
| `docs/mvp-contract.md` | The **frozen contract**: operating envelope, out-of-scope list, time and coordinate conventions, ontology, definitions, privacy boundary, split policy, acceptance gates, output-to-primitive mapping |
| `docs/data-schema.md` | Canonical entities, Stage 1 field tables, identity rules, schema versioning, **provenance requirements**, serialization rules, the Stage 1 ingest protocol |
| `docs/evaluation.md` | Metric definitions, split and leakage policy, how results are checked, the Stage 1 gate, what to do when a gate fails |
| `docs/status.md` | **Measured evidence only.** The stage ledger. Nothing enters it that was not observed. |
| `docs/annotation-guide.md` | Human decision rules for annotators |
| `docs/model-registry.md` | Model policy, required registration fields, current contents (zero models) |
| `docs/agents/` | The operating manual and the per-stage briefs (`docs/agents/briefs/`). Read the brief for the stage you are working on. |

`docs/agents/` is authored separately. Reference it; do not create or restructure it.

When this file and a contract document disagree on a fact, the contract document is correct and
this file is stale: report the discrepancy, do not resolve it silently.

---

## 2. The fifteen truth rules

These are the rules the project exists to enforce. They are not style preferences.

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

---

## 3. Canonical semantics

| Concept | Rule |
| --- | --- |
| Intervals | **Half-open**: `[start_us, end_us)`. A zero-length interval is empty. |
| Time | The original integer presentation timestamps and the container `time_base` are **preserved**; derived microsecond values never replace them. Time is **never** `frame_number / nominal_fps`, because the container time base is muxer-chosen (`1/15360`, `1/90000` and `1/1200000` have all been observed here) and a nominal rate is meaningless under variable frame rate, where `avg_frame_rate` may be reported as `"0/0"` meaning unknown. |
| Coordinates | Every geometry value declares **exactly one** of `source_px`, `stabilized_px`, `wall_plane`, `body_local_3d`. A value without a declared space is a defect. |
| Problem identity | A problem ID is **scoped to a specific `WallSet` revision**. A reset produces a new `WallSet`; problem identities do not survive it. |
| Ontologies | Four closed value sets (contact target, contact label, visibility, outcome) are defined in `docs/mvp-contract.md` Section 5. Read them there. Do not restate, extend or reorder them here or in code comments; a value outside its set is a defect, not a new category. |
| Missing data | Occluded, unobserved or unknown data is **never** converted into a negative label. `occluded` is not `none`. `unknown` is not `false`. Missing propagates as missing. |

**No float-typed field anywhere.** A float makes byte-identity depend on `repr`, and byte-identity
is a gate clause.

| Quantity | Representation |
| --- | --- |
| Durations and timestamps | Integer **microseconds** (or integer ticks plus the declared `time_base`) |
| Frame rates and ratios | `{num, den}` integer rationals |
| Rotation | Integer **degrees** |
| Coordinates | Integers in **thousandths of a unit** |
| Unknown | An explicit `null`, **never an omitted key**. A key that vanishes is indistinguishable from a schema change; `null` says "we looked and there was nothing". |

---

## 4. Implementation discipline

| Area | Rule |
| --- | --- |
| Language and tooling | Python 3.11, `uv`, Pydantic v2, `pytest`, `ruff`, `mypy` (config in `pyproject.toml`) |
| Models | Every Pydantic model carries `model_config = ConfigDict(extra="forbid", frozen=True)` |
| Media boundary | FFmpeg/`ffprobe` or PyAV **only** at the media boundary, never scattered through the codebase |
| Not before Stage 8 | No Postgres, no queues, no cloud services, no Docker, no FastAPI, no React, no mobile code |
| Abstractions | No speculative abstractions. An adapter exists **only** to isolate a real external boundary or to support two real implementations. One caller is not two implementations. |
| Validation | Validate **external and system-boundary input only**. Do not catch errors that framework guarantees make impossible; do not defend against states the type system already excludes. |
| Scope of edits | Do not refactor unrelated code. Do not manually reformat surrounding code. Do not add comments, docstrings or type machinery the current stage does not need. |
| Generated artifacts | Stay **outside `src/`**. `artifacts/` is regenerated, never hand-edited, and is git-ignored. |

A comment earns its place by recording **why** a non-obvious decision was made, usually a measured
behaviour of an external tool. It never restates what the code does.

---

## 5. Repository map

Everything named in this section exists today.

### Modules under `src/climbvision/`

| Module | Owns |
| --- | --- |
| `__init__.py` | `__version__`, recorded on every ingest run |
| `errors.py` | `ClimbVisionError(code, message)`. Codes are SCREAMING_SNAKE; 25 exist today, for example `INPUT_NOT_FOUND`, `MANIFEST_CONFLICT`, `SCHEMA_ID_UNKNOWN`, `DOCUMENT_INVALID`, `CONFIG_THRESHOLD_MISSING`. A new failure mode gets a new code, not a reused one. |
| `hashing.py` | `sha256_file`, `sha256_bytes`, `asset_id_from_digest`, plus `ASSET_ID_PATTERN` and `SHA256_HEX_PATTERN`, which the schema models use to constrain ID fields |
| `serialization.py` | `dumps_canonical(model) -> bytes` and `loads_json`. `dumps_canonical` is the **only** `json.dumps` in the codebase: sorted keys, compact separators, UTF-8, trailing newline, `allow_nan=False`, written in binary mode. Never hand-serialize a document anywhere else. |
| `timebase.py` | `parse_rational`, `pts_to_us`, `us_to_pts`. **Integer arithmetic only**, rounding half away from zero. No float ever enters a timestamp conversion. |
| `media/ffprobe.py` | The **only** subprocess boundary for media. Exposes `probe_streams` and `probe_packets`, each returning `ProbeResult(argv, raw, document)`, plus `version` and `executable`. |
| `media/normalize.py` | **Pure**: no subprocess, no filesystem. Turns raw probe documents into `VideoStreamInfo` and `FrameIndex` (`select_video_stream`, `normalize_video_stream`, `container_facts`, `build_frame_index`, `compute_duration_us`). Purity is why the unit suite runs without `ffprobe` installed; keep it that way. |
| `quality.py` | `assess(video_stream, frame_index, config)` -> the three-valued `QualityAssessment` list. Envelope violations are **flags, never rejections**. |
| `provenance.py` | `build_ingest_run(...)`. The second external boundary (`git`), deliberately kept out of `media/ffprobe.py`; an unavailable repository yields `null`, never a fabricated clean flag. |
| `ingest.py` | `ingest(video_path, out_root, config_path) -> Recording`. Orchestration only. |
| `cli.py` | `main`, `argparse` subcommands `ingest` and `validate`. Exit codes: **0** ok, **1** operation failed, **2** usage. `validate` dispatches on the document's own `schema_id`, never on its filename. |
| `schema/versions.py` | `RECORDING_SCHEMA_VERSION = 3`, `FRAME_INDEX_SCHEMA_VERSION = 2`, `INGEST_RUN_SCHEMA_VERSION = 1`, the three `*_SCHEMA_ID` constants, and the `SCHEMA_IDS` tuple |
| `schema/__init__.py` | `MODEL_REGISTRY` (schema ID -> model class) and the package `__all__` |
| `schema/recording.py`, `schema/frame_index.py`, `schema/provenance.py`, `schema/quality.py` | The Stage 1 document and value models |

### Artifact layout

```
<out>/recordings/<asset_id>/recording.json
<out>/recordings/<asset_id>/frame_index.json
<out>/recordings/<asset_id>/runs/<run_id>.json
<out>/recordings/<asset_id>/runs/<run_id>.probe.streams.raw.json
<out>/recordings/<asset_id>/runs/<run_id>.probe.packets.raw.json
```

| Rule | Detail |
| --- | --- |
| Run records are **append-only** | One record per execution, never overwritten. The run points at the manifest by hash, not the reverse, so the manifest stays byte-identical while run history grows. |
| Raw probe output is preserved **verbatim** | Beside the `argv` that produced it, and **run-scoped**, so a second ingest cannot overwrite the first run's preserved bytes. |
| `MANIFEST_CONFLICT` | Ingest **refuses** to overwrite a stored `recording.json` whose bytes would change, because earlier run records attest to the stored bytes by hash. Identical bytes are a silent no-op, so idempotent re-ingest is unaffected. |

### Configuration format

Thresholds live in `configs/<area>/v1.json`, never in code:

```json
{
  "config_version": "<area>/v1",
  "thresholds": {
    "<name>": {
      "value": "<integer, or an object of integers for a rational>",
      "unit": "<unit>",
      "status": "[FIXED] | [PILOT] | [PLANNING] | [VAL]",
      "selection": "<how this number was chosen>"
    }
  }
}
```

`selection` states how the number was chosen and against what evidence. A number taken verbatim
from the frozen contract says so and cites the contract section. A number that has not been
chosen on data reads `"Not selected. [PILOT] placeholder; no validation data exists."` until a
selection run is recorded in `docs/status.md`. A threshold with no `value` is a hard failure
(`CONFIG_THRESHOLD_MISSING`), not a default.

---

## 6. The guards a new module must satisfy

Read this section before adding a file. It is the difference between a five-minute change and an
hour of confusion.

| Guard | Location | What it does |
| --- | --- | --- |
| Module inventory pin | `tests/unit/test_scope_guard.py`, set literal `STAGE_ONE_MODULES` | Asserts the on-disk set of `*.py` files under `src/` **equals** the literal. A new module fails this test until its repository-relative path is added to the set. |
| Import allowlist | same file, `ALLOWED_THIRD_PARTY = {"pydantic"}` | Asserts every import root under `src/` is in the standard library or the allowlist |
| Banned imports | same file, `BANNED` (43 names, including `cv2`, `numpy`, `torch`, `onnxruntime`, `mediapipe`, `fastapi`, `requests`, `socket`, `sqlite3`) | Asserts no later-stage dependency has leaked into Stage 1 |
| Dependency pin | same file, `test_the_runtime_dependency_list_is_exactly_pydantic` | String-parses `pyproject.toml` and pins the runtime dependency list to exactly `pydantic` |

An import allowlist cannot see a later-stage module that happens to import nothing banned, which
is why the file inventory itself is pinned.

### Registering a new document model

A new document model must be registered in **three** places or its tests fail:

| Place | What to add |
| --- | --- |
| `src/climbvision/schema/versions.py` | Its `*_SCHEMA_ID`, its `*_SCHEMA_VERSION`, and an entry in the `SCHEMA_IDS` tuple |
| `src/climbvision/schema/__init__.py` | An entry in `MODEL_REGISTRY` and in `__all__` |
| `tests/unit/test_schema.py` | A row in `DOCUMENT_MODELS` with a golden fixture committed under `tests/fixtures/documents/`, **and** every nested model added to `ALL_MODELS`, which drives the no-float, `extra="forbid"` and `frozen=True` checks |

### The rule about pins

**These pins are decision records, not obstacles.** A stage brief that authorizes a new
dependency or a new module says so explicitly, and updating the pin is then part of the
authorized change. **An agent never edits a pin to make its own change pass.** If a guard fails
and no brief authorizes the change, the change is out of scope: stop and report.

---

## 7. Provenance

Five classes, never collapsed into one field:

| Class | Meaning |
| --- | --- |
| `prediction` | Model output, unreviewed |
| `preannotation` | Model output offered to a human for review |
| `reviewed_annotation` | A human reviewed it. A reviewed annotation that happens to agree with a prediction is still a reviewed annotation. |
| `adjudicated_ground_truth` | Disagreement resolved by the adjudication procedure in `docs/annotation-guide.md` |
| `derived` | Deterministically computed from upstream artifacts |

Every artifact carries exactly one class. Every analysis run records: input SHA-256 hashes;
schema and ontology versions; code revision when available; configuration hash; model/checkpoint
ID and checksum; score type; coordinate space and units; upstream artifact IDs; quality flags;
runtime environment (notably the external tool versions); and the creation timestamp.

Run records are **append-only** and point at their outputs by hash, **never the reverse**.

A model is registered in `docs/model-registry.md` with all seven required fields **before its
weights are downloaded**. Weights are never committed. The checkpoint checksum is recorded and
**verified per run**; a checkpoint filename is not an identity.

---

## 8. Threshold status tags

Canonical definitions are in the preamble of `docs/mvp-contract.md`. In summary:

| Tag | Meaning |
| --- | --- |
| `[FIXED]` | Fixed now. Changing it requires an explicit, recorded decision. |
| `[VAL]` | Selected on training/validation data only |
| `[PILOT]` | To be estimated later. Currently unknown. |
| `[PLANNING]` | Illustrative planning guidance. Not a result, not a commitment. |

**An untagged number is a defect.** Identifiers, schema versions, stage numbers, test counts and
already-measured observations are names or evidence, not thresholds, and are untagged by
convention.

**Nothing may be tagged `[VAL]` until validation data exists and a selection run is recorded in
`docs/status.md`.** No number in this repository carries `[VAL]` today.

---

## 9. Working protocol per stage

1. Inspect the relevant files and `git status`. Establish what actually exists before planning.
2. Restate the stage's acceptance criteria from `docs/mvp-contract.md` Section 9, `docs/evaluation.md` and the stage brief under `docs/agents/briefs/`.
3. Write a short implementation plan: dependencies, risks, phases.
4. Implement **only the current stage**. Anything a later stage needs is a later stage's work.
5. Add focused unit tests and **one** integration fixture exercising the real path end to end.
6. When a stage introduces a metric, add **hand-calculated** metric fixtures: a case whose expected value was computed by hand, so the metric implementation is checked against arithmetic and not against itself.
7. Run the smallest relevant test subset while working; keep the inner loop fast.
8. Before reporting, run the full gate:

   | Command | Expectation |
   | --- | --- |
   | `uv sync` | Environment resolves |
   | `uv run pytest` | All tests pass. **No skipped test counts as a pass.** |
   | `uv run ruff check .` | Clean |
   | `uv run ruff format --check .` | Clean |
   | `uv run mypy` | Clean |
   | The stage's CLI smoke command, for Stage 1 `uv run climbvision ingest <video> --out artifacts` followed by `uv run climbvision validate artifacts/recordings/<asset_id>/recording.json` | Exit code 0 and the expected artifact layout on disk |
   | The offline check: run the suite in an environment where `ffprobe` is **not** on `PATH` | The `ffprobe`-dependent integration tests **skip**, they do not fail, and the unit suite still passes. Sockets are already blocked in every test by the autouse `block_network` fixture in `tests/conftest.py`. Stage 1 observed 372 passed, 51 skipped, against 423 total. |

9. If the stage produces visual output, render a **deterministic** overlay and **look at it**. An overlay is a diagnostic view, never the only result: the structured artifact must exist too.
10. Run the reviewer. The agent that wrote the code does not sign off on it.
11. Report in the format of Section 11.

---

## 10. When a gate fails

| Do | Do not |
| --- | --- |
| Report the **measured gap**, with the number | Lower the gate to match the result |
| Report the **failing slices** by participant, problem and `WallSet` | Hide a failing slice inside a pooled average |
| Propose the **smallest next experiment** that would close the gap | Tune on the frozen test set |
| **Stop and wait for a decision** | Continue to the next stage on a failed gate |

Selection of any kind (model, threshold, prompt) happens on validation data only. The test set is
frozen and evaluated once.

**A failed gate is information. A moved gate is nothing.**

---

## 11. Reporting format

Every stage report contains, in order:

1. **Files changed.** Repository-relative paths, one line each, with what changed.
2. **Verification.** The exact commands run and their **real output**, pasted, not paraphrased.
3. **Measured gate evidence.** A table with **one row per gate clause**: clause, assertion, measured evidence.
4. **Known limitations.** Including any clause that could not be measured and why.
5. **Proposed next stage.** One paragraph, ending in a request for a decision.

Honesty clauses, stated flatly:

- Never claim a gate passed without the number that proves it.
- Never write `docs/status.md` from an expectation. It records measured evidence only.
- A gate number comes from **real annotated data** and **never** from `tests/fixtures/`. Fixtures prove the code runs; they do not measure accuracy.
- "Should work" is not a result. Neither is "the implementation reports success".
- If the data needed to measure a clause does not exist yet, the clause reads **`pending measurement`** and the agent says so, rather than substituting synthetic data.

---

## 12. Documentation ownership

| File | May contain | Must not contain |
| --- | --- | --- |
| `README.md` | What the project is, the envelope, the stage table, install, the commands that exist, documentation index | Any claim about a stage that has not shipped |
| `docs/mvp-contract.md` | The frozen contract | Anything changed without an explicit, recorded decision |
| `docs/data-schema.md` | Entities, fields, identity, versioning, provenance, serialization, the ingest protocol | A guessed field identifier. Describe the field's meaning rather than invent a name. |
| `docs/evaluation.md` | Metric definitions and gates | Any number presented as achieved |
| `docs/annotation-guide.md` | Human decision rules and adjudication | Rules the ontology does not support |
| `docs/model-registry.md` | Model policy, registered models, unselected candidates | An accuracy figure for a candidate |
| `docs/status.md` | **Measured evidence only.** A gate not yet measured reads `pending measurement`. | An expectation, an estimate, or a number from a previous run on a different fixture set |
| `docs/agents/`, `docs/agents/briefs/` | The operating manual and per-stage briefs | Duplication of the contract; the brief points at it |

The seven contract documents (`README.md` and the six under `docs/`) are edited **surgically**,
and only where the stage brief authorizes the edit. The per-stage briefs under
`docs/agents/briefs/` are updated when a stage changes its own scope.

**No new top-level document without the owner asking for it.** When behaviour changes, update its
whole cluster in one change set: code, config, tests and the documents above.

---

## 13. When the human asks for something that violates a rule

Name the rule, offer the nearest compliant alternative, and **do not silently comply**. The two
most likely cases:

**"Make the gate pass."** Name the gate and the measured gap. The compliant alternatives are: run
the smallest experiment that could close the gap; or record an explicit, dated decision to change
the gate, made by the owner and written down as a decision, not as an edit. Tuning on the frozen
test set, relaxing an assertion, quietly narrowing a slice, or reporting a pooled average that
hides a failing slice are all refusals, not options.

**"Fill in the missing data."** Name rule 6 and rule 1. The compliant alternatives are: emit
`unknown`, `review`, `abstained` or `insufficient_data`; or collect and annotate the data. A
synthetic stand-in, an interpolated value, a default that looks plausible, or a fixture-derived
number reported as a measurement are all indistinguishable from real data once written, which is
exactly why they are forbidden.

In both cases: state the rule, state the alternative, and stop for the owner's decision.
