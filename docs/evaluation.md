# Evaluation

Status tags as defined in [`mvp-contract.md`](mvp-contract.md).

**No metric in Section 1 has been measured.** Every accuracy-shaped number is a `[PILOT]` target
to be set on validation data. **Nothing is tagged `[VAL]`, because no validation data exists.**
No value in this document is a result.

The one exception is Section 4, the **Stage 1 gate**, which is deterministic, concrete and is
being measured now.

---

## 1. Metric definitions

### Stage 3 - wall calibration and confirmed hold map

| Metric | Unit | Computed over | Target |
| --- | --- | --- | --- |
| Max reprojection error | **Integer milli-wall-units** | The single worst fiducial correspondence used to fit the calibration | Reported, not thresholded |
| RMS reprojection error | **Integer milli-wall-units** | The same correspondences, pooled | Reported, not thresholded |
| Hold-polygon self-agreement IoU | Unitless ratio | Two blind tracings of the same hold by the same annotator, on a re-traced subset, per `WallSet` | `[PILOT]` |
| Mask IoU | Unitless ratio | Per predicted hold mask against its adjudicated mask, on the wall reference image | `[PILOT]`, **`not_applicable` until a segmenter is adopted** |
| Mask AP | Unitless ratio | Averaged over IoU thresholds, per `WallSet` | `[PILOT]`, **`not_applicable` until a segmenter is adopted** |

Reprojection error is reported in **integer milli-wall-units** because no field may be
float-typed (`data-schema.md` Section 7).

The two mask metrics apply **only once a segmenter is adopted by an explicit decision.** The hold
map is user-confirmed by contract, so until that decision they are recorded as `not_applicable`,
which is neither zero nor a failure: the accuracy of a model that does not exist is undefined,
not bad.

Self-agreement IoU measures the stability of one annotator's tracing, not model accuracy, and is
**never** reported as inter-annotator agreement (`annotation-guide.md` Section 6).

Mask metrics are reported per `WallSet` as well as pooled: a model that works on one gym's hold
colours and fails on another's is not visible in a pooled number.

### Stage 4 - pose

| Metric | Unit | Computed over | Target |
| --- | --- | --- | --- |
| PCK | Percentage of keypoints | Keypoints whose predicted position falls within a normalization-scaled distance of the adjudicated position | `[PILOT]` |
| **Endpoint PCK** | Percentage | **Palm and toe anchors only** | `[PILOT]` |

Endpoint PCK is reported separately and is the one that matters. Contact detection depends on
the **ends of the limbs**, not on torso and hip joints, which are easier and inflate a pooled
PCK. The normalization scale and the distance threshold are `[PILOT]`.

Keypoints labelled `occluded` or `out_of_frame` are excluded from the numerator and the
denominator, and their count is reported. Scoring a model on joints no annotator could see
measures the annotation, not the model.

### Stage 5 - contact intervals

| Metric | Unit | Computed over | Target |
| --- | --- | --- | --- |
| Temporal IoU | Unitless ratio | Predicted vs adjudicated contact intervals, per (limb, target) | Reported at tIoU `0.1`, `0.3` and `0.5` `[FIXED]` (reporting convention); target values `[PILOT]` |
| Event F1 | Unitless ratio | Matched contact events at each tIoU level above | `[PILOT]` |
| Boundary error | **Integer microseconds** | Signed difference between predicted and adjudicated interval boundaries; reported as a distribution, not a mean alone | `[PILOT]` |
| False-contact time | **Integer microseconds** | Total predicted contact duration with no adjudicated contact | `[PILOT]` |
| Risk-coverage | Ratio vs ratio curve | Error rate as a function of the fraction of predictions retained after abstention | `[PILOT]` |

Risk-coverage exists because abstention is a first-class output. A model that abstains on hard
cases and is accurate on the rest is more useful than one that guesses everywhere at the same
pooled accuracy, and only a risk-coverage curve shows the difference.

### Stage 6 - beta sequences

| Metric | Unit | Computed over | Target |
| --- | --- | --- | --- |
| Normalized sequence edit distance | Unitless ratio | Predicted vs adjudicated token sequence, normalized by reference length | `[PILOT]` |

Reported **separately for the limb-aware and limb-agnostic forms** (`mvp-contract.md`
Section 6). The two are not comparable and must never be pooled into one number.

### Stage 7 - descriptive aggregates

Move duration, contact dwell, hesitation observations, foot-adjustment counts and transition
failure hazard are **descriptive statistics, not predictions.** They are reported with:

- their unit (durations are **integer microseconds**);
- their coordinate space where geometric;
- their **support** (the number of underlying observations);
- their uncertainty.

**Below the support threshold `[PILOT]`, the aggregate returns `insufficient_data`.** It does
not return a value with a wide interval, and it does not return a point estimate with a
disclaimer. A number that should not be read must not be printed.

---

## 2. Split and leakage policy

| Rule | Detail |
| --- | --- |
| Group-aware splits | Grouped on **participant and problem simultaneously**. The same climber never straddles a split; the same problem never straddles a split. The participant clause is qualified by the next row. |
| Single-participant releases | The participant clause applies to **multi-participant releases**. A single-participant release must **explicitly declare** `participant: accepted_single_participant` in its release manifest, and the leakage test **fails** if it declares neither that nor `none` for that key. Every number measured on such a release carries the caveat that it supports **within-climber claims only** and estimates nothing about other climbers. |
| Frozen test set | Fixed once, evaluated **once**. |
| Never tune on test | Model selection, threshold selection and prompt selection use validation data only. |
| Leakage is **tested**, not assumed | Named tests assert no participant ID and no problem ID appears in more than one split, and that no asset SHA-256 appears in more than one split. |

Split manifests are a **Stage 2 deliverable and do not exist yet.**

## 3. How results are checked

| Principle | Detail |
| --- | --- |
| Capability vs regression | **Capability checks** ask whether the new thing works. **Regression checks** ask whether previously working behaviour still works. They are reported separately. |
| Regressions held to a stricter bar | A capability target may be missed and reported as a gap. A regression is a **blocking failure**. |
| Deterministic graders preferred | Byte-identity, exact assertions, targeted tests, schema validation and grep-for-required-symbols before any model or human judgement. |
| Model judgement is last resort | Reserved for open-ended quality questions where no deterministic grader exists, and always labelled as such. |
| **Security sign-off is never fully automated.** | An automated scan is evidence, not approval. |

---

## 4. The Stage 1 gate (concrete, being measured now)

All four clauses must pass.

### 4.1 Tests and lint

All tests pass and lint passes (`ruff`, per `pyproject.toml`). No skipped tests count as passes.

### 4.2 Schema round-trip

**Both** of these must hold:

```
model == parse(dump(model))
dump(parse(dump(model))) == dump(model)     # byte-for-byte
```

The second clause is not redundant. **The first alone passes even when serialization is lossy in
ways that normalize back** - for example a value that is dropped on dump and reconstructed with
the same default on parse, or a type that round-trips to an equal-but-differently-serialized
form. Only byte-identity catches that.

This is why `data-schema.md` Section 7 bans float-typed fields and requires sorted keys, compact
separators, binary-mode writes and explicit `null`s: byte-identity is only a meaningful test if
serialization is canonical.

### 4.3 Idempotent ingest

Ingesting the same file twice yields:

- the **same asset ID** (it is the SHA-256 of the file bytes, so this holds across path, name
  and mtime changes); and
- a **byte-identical manifest**; while
- **adding a second append-only run record.**

The run record is separate from the manifest precisely so that the manifest can be
byte-identical while the run history still grows.

### 4.4 Timestamp round-trip error

**No greater than one source frame `[FIXED]`**, measured as **two reported numbers**:

| Number | Assertion |
| --- | --- |
| `max_roundtrip_error_ticks` | **Exactly `0` `[FIXED]`** |
| `max_roundtrip_error_us` | **At most the smallest per-packet duration in microseconds** `[FIXED]` |

The frame duration used in the second assertion comes from **that packet's own `duration` in
ticks**, converted through the stream time base. It is **never** computed from
`1/avg_frame_rate`: a nominal frame rate is the banned definition (`mvp-contract.md` Section 3),
`avg_frame_rate` may be `"0/0"` meaning unknown, and it is undefined under variable frame rate.

**Honest limitation.** `max_roundtrip_error_ticks == 0` holds automatically whenever the time
base denominator is at most `1000000` `[FIXED]`, because one tick is then at least one
microsecond and the conversion to integer microseconds loses nothing. For such fixtures the
round trip is **exactly lossless, so that clause proves little on its own.** A fixture with a
larger denominator (`1/1200000` has been observed on this machine) exists specifically to
exercise the **bounded** branch, where ticks do not divide evenly into microseconds and the
second assertion is not vacuous by construction, though it did not bind on the current fixture
set.

---

## 5. When a gate fails

| Do | Do not |
| --- | --- |
| Report the **measured gap**, with the number | Lower the gate to match the result |
| Propose the **smallest next experiment** that would close it | Tune on the frozen test set |
| Report failing **slices** by participant, problem and `WallSet` | Hide a failed slice inside a pooled average |
| **Stop and ask for a decision** | Continue to the next stage on a failed gate |

A failed gate is information. A moved gate is nothing.
