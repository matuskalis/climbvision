# MVP Contract

Frozen at Stage 0. This document defines what ClimbVision may claim, what it may never claim,
and what each stage must prove before the next begins. Changing anything marked `[FIXED]`
requires an explicit decision, recorded as such.

**Status tags.** Every number carries exactly one.

| Tag | Meaning |
| --- | --- |
| `[FIXED]` | Fixed now. Changing it requires an explicit decision. |
| `[VAL]` | Selected on training/validation data only. **Unused in this repository today.** |
| `[PILOT]` | To be estimated later. Currently unknown. |
| `[PLANNING]` | Illustrative planning guidance. Not a result, not a commitment. |

No number here is tagged `[VAL]`, because no validation data exists yet. An untagged number is
a defect. Version identifiers and stage numbers are names, not thresholds, and are untagged.

---

## 1. Supported operating envelope

| Condition | Requirement |
| --- | --- |
| Climbers | Exactly one climber in frame `[FIXED]` |
| Discipline | Indoor bouldering |
| Camera | Single static phone camera |
| Camera motion | No pan, no zoom, no reframing during the recording |
| Framing | Full body and full problem visible for the entire attempt |
| Resolution | At least 1080p `[FIXED]` |
| Frame rate | At least 30 fps `[FIXED]` |
| Wall | One approximately planar wall facet |
| Reference imagery | A clean wall image, or a usable reference frame from the recording (on the first measured envelope, a clean still of the empty board; see "First measured envelope" below) |
| Hold map | User-confirmed hold masks (on the first measured envelope the positions come from a versioned board definition instead; see "First measured envelope" below) |
| Problem identity | Explicitly user-confirmed by the user |
| Processing | Offline batch processing is acceptable |

Envelope violations are recorded as three-valued quality flags, not rejections. The system
degrades to `unknown` rather than guessing. Ingest hard-fails only on malformed input.

### First measured envelope

The envelope above is the **general target** and is not narrowed. What this subsection fixes is
**where the first numbers are measured**: on a **standardized LED training board** - a flat panel
at a **fixed angle**, holds at **fixed grid positions**, LEDs indicating which holds belong to a
problem, and a **versioned board definition** supplying those positions. The equipment class is a
MoonBoard-type training board, named once so the reader knows what is meant; no vendor product,
service or interface is a dependency of this system.

This is a **strict subset** of the general envelope, not a replacement for it. Every general
condition still applies: exactly one climber `[FIXED]`, one static camera, no pan and no zoom,
full body and full problem visible for the entire attempt, at least 1080p `[FIXED]`, at least
30 fps `[FIXED]`, offline batch processing.

| What the board adds | Consequence |
| --- | --- |
| Fixed grid positions in a versioned board definition | Hold positions come from the **board definition**, not from per-wall polygon annotation |
| LED problem indication | Problem identity is a **user-confirmed set of lit holds**, not per-hold membership annotation |
| A genuinely planar panel with no volumes | The parallax that makes volume-mounted holds unreliable **does not arise** |
| The same problem on many identical boards | The repeated-attempt stages get repeats of one problem identity |
| One board type rather than one wall | The wall and gym terms of the measurement caveat weaken to a **board type** (Section 8). **The single-climber term does not weaken at all.** |
| A steep overhang | **Severe self-occlusion.** The climber hangs beneath the panel and hides the holds in use, and the camera shoots steeply upward with strong foreshortening toward the top of the board |
| Footwork the board does not constrain | **Foot contact targets are poorly defined** on this envelope: climbers smear on plywood and many problems place no constraint on feet |

The last two rows are **costs**, and they fall on the two weakest measurements: keypoint accuracy
at the limb ends and foot visibility. They are the substantive reason the MVP predicts hands only
(Section 5).

**The lit-hold set is entered and confirmed by the user.** No board problem data is fetched from
any service, and no such interface is assumed to exist. An import adapter is a **possible later
addition behind an explicit decision**, never an assumption of this contract.

**The board angle is a property of the board, not a per-recording input.** It is recorded once, as
part of the board definition. A user never sets it per attempt.

**The general envelope is not retired.** It remains the target. Returning to general walls requires
**new measurements on that envelope**, not a new contract.

## 2. Explicitly unsupported / out of scope

Out of scope until the telemetry gates below pass. Not "hard", not "later in the sprint":
**not built, not claimed.**

| Excluded | Why |
| --- | --- |
| Generated coaching text | Not telemetry. Requires claims the pixels do not support. |
| Route grade prediction | Grade is a community judgement, not an observable. |
| Efficiency / technique / quality scores | No validated construct, no ground truth. |
| 3D biomechanics | Not recoverable from one monocular RGB view under this envelope. |
| Center-of-mass claims | Requires segment masses and 3D pose. See "Hip trajectory". |
| Force or load-bearing contact inference from monocular RGB | Contact is visible; load is not. |
| Automatic beta recommendation | Prescriptive, not descriptive. |
| Named climbing-technique recognition (drop knee, flag, heel hook by name) | Closed label set not defined or validated. |
| Automatic problem merging | Problem identity is user-confirmed by contract. |
| Cross-gym person identity | Privacy boundary and out of envelope. |
| Mobile application | Offline batch only. |
| Distributed infrastructure | Single-machine batch is sufficient. |
| Multi-camera fusion | Envelope is one static camera. |
| Training large models from scratch | No dataset of the required size exists. |
| An LLM or VLM as the telemetry engine | A language model may not generate contacts or metrics. See `model-registry.md`. |

## 3. Time convention

- Intervals are **half-open**: `[start_us, end_us)`. An interval of zero length is empty.
- The original integer presentation timestamps and the container `time_base` are **preserved**
  in the manifest. Derived microsecond values never replace them.
- Time is **never** defined as `frame_number / nominal_fps`.

Why the ban: the container time base is chosen by the muxer, not by the camera. `1/15360`,
`1/90000` and `1/1200000` have all been observed on this machine (ffprobe 8.0). A nominal frame
rate is also meaningless under variable frame rate, and `avg_frame_rate` may be reported as
`"0/0"`, which means unknown. Any code computing time from a frame counter is a defect.

## 4. Coordinate convention

Every geometry value declares exactly one space. A value without a declared space is a defect.

| Space | Meaning |
| --- | --- |
| `source_px` | Pixels in the original decoded frame, before any stabilization or rotation correction |
| `stabilized_px` | Pixels after stabilization/rectification to a common frame |
| `wall_plane` | 2D coordinates on the fitted planar wall facet |
| `body_local_3d` | 3D coordinates in a body-local frame, if and when a stage introduces them |

**Wall-plane coordinates are not physical 3D body coordinates.** A distance on the wall plane is
a distance on a plane, not a limb length, a reach or a displacement of the body in space.

## 5. Ontology

Closed value sets. A value outside its set is a defect, not a new category.

### Contact target

| Value | Meaning |
| --- | --- |
| `hold` | A specific `HoldInstance` in the confirmed hold map |
| `volume` | A wall volume feature rather than a bolt-on hold |
| `wall_region` | Bare wall surface (smear, stem) with no hold instance |
| `none` | The limb is demonstrably not in contact |
| `unknown` | Contact state cannot be determined from the observation |

### Contact label

| Value | Meaning |
| --- | --- |
| `intentional_use` | The limb is being used to bear or direct the climber's position |
| `incidental_touch` | Contact occurred without being used (brush, slip, pass-through) |
| `unknown` | The distinction cannot be made from the observation |

### Visibility

| Value | Meaning |
| --- | --- |
| `visible` | The joint or contact is directly observable |
| `occluded` | It is inside the frame but hidden (by the body, a volume, another object) |
| `out_of_frame` | It is outside the image bounds |
| `unlabeled` | No human or model has assigned a value yet |

### Outcome

| Value | Meaning |
| --- | --- |
| `send` | The problem was completed under its confirmed conditions |
| `fall` | Unrecovered loss of contact before completion |
| `controlled_drop` | The climber deliberately released and descended |
| `aborted` | The attempt ended without a fall and without completion |
| `unknown` | The outcome is not determinable from the recording |

**Two standing rules.**

1. Occluded, unobserved or unknown data is **never** converted into a negative label to
   simplify code. `occluded` is not `none`. `unknown` is not `false`. A missing observation is
   missing, and it propagates as missing.
2. A **problem ID is scoped to a specific `WallSet` revision.** Holds get reset. The same wall
   with a new set is a new `WallSet`, and problem identities do not survive across revisions.

### MVP prediction scope: hands only

The MVP **predicts contacts for the left hand and the right hand only.** The four contact-target
values and the four visibility values above are **unchanged**, and **foot contact targets remain
fully defined and remain annotatable.** The MVP simply does not predict them.

| Rule | Detail |
| --- | --- |
| A foot with no prediction is `unknown` | **Never `none`.** "Not attempted" silently becoming "not in contact" is exactly the coercion standing rule 1 forbids. |
| A metric that was not attempted is `not_applicable` | Reported **with its reason**. Never a failure, never a zero, never a blank. |

Feet are **deferred, not deleted.** The reason is substantive, not clerical: on the first measured
envelope (Section 1) the board itself places no constraint on the feet, so a foot contact target
is poorly defined there. Their definitions stand and apply the moment feet are predicted.

## 6. Definitions

**Attempt.** A contiguous span of one recording in which the climber engages the confirmed
problem. It starts when the climber has established the problem's starting contact
configuration and the body is supported by the wall. It ends at the first of: completion
(`send`), unrecovered loss of contact (`fall`), deliberate release (`controlled_drop`), or
disengagement without either (`aborted`). Multiple attempts may occur in one recording; a
recording is not an attempt. The gap between attempts belongs to no attempt.

**Intentional use vs incidental touch.** `intentional_use` means the limb bears load or directs
position through that contact. `incidental_touch` means the limb contacted the surface without
being used that way. **Visual proximity is never automatically intentional use.** A hand
resting near a hold, passing across it, or overlapping it in projection is not use. Because
load is not observable from monocular RGB (Section 2), this distinction is a **human annotation
decision** with an explicit `unknown` escape, not a model output that can be trusted unreviewed.

**Occlusion.** `visible` when the joint or contact is directly observable. `occluded` when it is
within the image bounds but hidden by the climber's own body, a volume, a hold, or another
object. `out_of_frame` when it lies outside the image bounds. `unlabeled` when no annotator or
model has yet assigned a value. `occluded` and `out_of_frame` are observations about the world;
`unlabeled` is a statement about the dataset. They are never merged.

**Outcome.** One of `send`, `fall`, `controlled_drop`, `aborted`, `unknown`, as defined in
Section 5. `unknown` is a legitimate outcome and must remain available; a recording that cuts
before the top has an `unknown` outcome, not a `fall`.

**Move.** A transition between two stable contact configurations. A contact configuration is the
set of (limb, contact target) pairs held simultaneously. A move is bounded by the end of one
stable configuration and the establishment of the next. Micro-fluctuations that do not change
the configuration are not moves; the stability criterion and its dwell threshold are `[PILOT]`.

**Beta sequence.** An ordered token sequence of attach and release events over an attempt. Two
forms are maintained: **limb-aware** (tokens carry which limb, e.g. attach(left_hand, H7)) and
**limb-agnostic** (tokens carry only the target). Comparison between attempts must state which
form it used; the two are not interchangeable.

**Foot adjustment.** An observable foot release and recontact, or a change of foot contact
target, that does not constitute a move by the definition above. It is a count of observed
events, not an inference about intent or nerves. Under the MVP's hands-only prediction scope
(Section 5) the **count is `not_applicable`**, with that reason recorded: the feet are not
predicted, so no foot event is observed, and a count over events nobody observed is undefined
rather than zero. The definition above is **deferred, not deleted**, and applies unchanged the
moment feet are predicted.

**Hesitation.** **Not a quality judgement.** ClimbVision records only explicit observations:
dwell time in a stable configuration, and low-velocity intervals of the tracked joints. A dwell
observation exceeding the dwell threshold `[PILOT]` may be recorded as a hesitation
*observation*. The system never asserts that the climber was uncertain, scared, tired or
reading the route.

**Fall location.** The **last stable contact configuration before unrecovered loss of contact.**
It is a configuration and a timestamp, not a single hold and not a body position. **The CAUSE
of a fall is never claimed** ("slipped off the crimp", "poor foot placement") without a
separately defined, separately annotated and separately validated cause label, which does not
exist and is not in the MVP.

**Crux.** A **statistically supported failure concentration at the transition level**: a
transition whose observed failure rate is elevated across a supported number of attempts. It is
never merely the slowest move, never merely the last hold reached, and never inferred from a
single attempt. When support is inadequate the system returns `insufficient_data`. Support
threshold: `[PILOT]`.

**Hip trajectory.** The midpoint of the observed 2D hip joints, in a declared coordinate space,
with a visibility label per sample. **It is never called center of mass**, and never used as
one. It is a 2D image-plane or wall-plane quantity derived from two keypoints, nothing more.

## 7. Privacy and consent boundary

| Rule | Enforcement |
| --- | --- |
| No real user video, faces, consent records or model weights in the repository | Path-scoped `.gitignore` (`data/raw/`, `data/recordings/`, `data/consent/`, `weights/`, `checkpoints/`, checkpoint extensions) |
| Participants appear only as pseudonyms | No real names in any written artifact or filename |
| A consent record is referenced by opaque ID, never embedded | `Recording` carries a nullable opaque consent record ID only |
| **Absolute filesystem paths never appear in written artifacts** | A path can contain a person's name (`/Users/<realname>/...`). Artifacts record content hashes and relative or basename-free references. |
| Test fixtures are synthetic and contain no people | Fixtures are generated, small, and committed deliberately (`!tests/fixtures/**`) |

The `.gitignore` is deliberately **path-scoped, not extension-scoped**: a global `*.mp4` or
`*.json` ban would silently untrack the synthetic fixtures the test suite depends on.

Audio presence is privacy-relevant (a bystander conversation is personal data) and is therefore
recorded at ingest as a fact about the file.

## 8. Benchmark split policy

- Splits are **group-aware on two keys simultaneously**: by participant and by problem. The
  same climber never straddles a split, and the same problem never straddles a split.
- The **participant clause applies to multi-participant releases.** A single-participant release
  must **explicitly declare** `participant: accepted_single_participant` in its release manifest,
  and the leakage test **fails** if the release declares neither that nor `none` for that key.
  Every number measured on such a release carries the caveat that it supports **within-climber
  claims only** and estimates nothing about other climbers.
- On the **first measured envelope** (Section 1) the **wall and gym terms of that caveat weaken to
  a board type**: the board is standardized, so a number measured on one board is **plausibly
  informative** about another board of the same type. That is a statement about the envelope, not
  a demonstration. **Transfer has not been shown**, and showing it requires measuring on a second
  board. **The single-climber term does not weaken at all.**
- The **test set is frozen** and evaluated **once**.
- **Never tune on the frozen test set.** Model selection, threshold selection and prompt
  selection all happen on validation data only.
- **Leakage is tested, not assumed**: named tests assert that no participant ID, no problem ID
  and no asset SHA-256 appears in more than one split.

The split manifests themselves are a **Stage 2 deliverable and do not exist yet.** This section
is the rule they must satisfy, not a description of an existing artifact.

## 9. Provisional acceptance table

One gate per stage. A stage is not complete until its gate is measured and reported in
`docs/status.md`.

| Stage | Scope | Gate |
| --- | --- | --- |
| 1 | Deterministic ingest: video to content-addressed manifest | **Real and measurable, executing now.** All tests and lint pass; schema round-trip succeeds; repeated ingest is idempotent; timestamp round-trip error is no greater than one source frame `[FIXED]`. Full statement in `evaluation.md`. |
| 2 | Annotation harness, CVAT adapter, group-aware split manifests | Target `[PILOT]`: agreement on the contact ontology, to be set on validation data - **inter-annotator agreement where two or more annotators exist; otherwise blind intra-annotator test-retest consistency, reported as `self_agreement` and never as inter-annotator agreement** (`annotation-guide.md` Section 6). Leakage tests pass (deterministic, not `[PILOT]`). |
| 3 | Wall calibration and confirmed hold map | Deterministic clauses (not `[PILOT]`), **both branches**: reprojection error reported in wall units; fiducial hull coverage reported; re-fitting identical inputs yields a byte-identical calibration. **Known board** (Section 1): the hold map comes from the versioned board definition, so the hold-polygon self-agreement clause is **`not_applicable`** with that reason, and one further deterministic clause applies - **every hold position the system reports round-trips to its grid coordinate**, mismatch count exactly `0` `[FIXED]`. **General wall**: target `[PILOT]`, hold-polygon **self-agreement IoU** on a re-traced subset, to be set on validation data. Model **mask IoU and AP are recorded as `not_applicable`** until a segmenter is adopted by an explicit decision; the hold map is user-confirmed by contract, so no segmenter is required to reach this gate. |
| 4 | Climber pose trajectories | Target `[PILOT]`: PCK, including endpoint PCK for palm and toe anchors, to be set on validation data. |
| 5 | Limb-hold contact intervals and stable contact-state transitions | **MVP scope is hands only** (Section 5). Target `[PILOT]`: temporal IoU, event F1, boundary error, false-contact time, risk-coverage, all to be set on validation data, all reported for the **hand slices**. The **foot slices are `not_applicable` with the reason recorded** - not absent, not zero. |
| 6 | Attempts, moves, beta sequences, fall events | Target `[PILOT]`: normalized sequence edit distance against adjudicated beta, to be set on validation data. |
| 7 | Descriptive aggregates (durations, dwell, adjustment counts, transition failure hazard) | **MVP scope is hands only** (Section 5). Target `[PILOT]`: support threshold below which the aggregate returns `insufficient_data`, to be set on validation data. The **foot-adjustment count is `not_applicable` with the reason recorded** - not absent, not zero. |
| 8 | Minimal application surface: upload/job API, web review timeline, correction workflow, repeated-attempt comparison as a view over Stage 6 and 7 output, consent and retention controls | **Workflow gate, not accuracy-shaped.** Stages 1 through 7 have passed their gates first; the surface exposes only validated primitives, each carrying its provenance; corrections are captured append-only; consent and retention controls are exercised. No mobile app until real web usage validates the workflow. |

Every accuracy-shaped gate for Stages 2 through 7 is a **target to be set on validation data**.
None is a claim, a result or a commitment. Stage 8's gate is a **workflow** gate and carries no
accuracy target. No accuracy, F1, IoU or PCK number appears anywhere in this repository as an
achieved value.

## 10. Output-to-primitive mapping

Provenance classes: `prediction`, `preannotation`, `reviewed_annotation`,
`adjudicated_ground_truth`, `derived`.

| Product output | Derived from | Provenance class | Stage |
| --- | --- | --- | --- |
| Hold map, **board envelope** (Section 1) | A versioned board definition, plus a calibration fitted to named grid positions | `derived`. Nobody traces or reviews an outline here; the human confirmation sits once on the board definition, which is recorded with its own per-value provenance | 3 |
| Hold map, **general wall** | Wall reference image, hold masks | `preannotation` -> `reviewed_annotation` (user-confirmed by contract) | 3 |
| Attempt list | Contact intervals, pose observations | `derived` | 6 |
| Move list | Stable contact configurations over time | `derived` | 6 |
| Beta sequence | Ordered attach/release contact events | `derived` | 6 |
| Fall event | Last stable configuration before unrecovered loss | `derived` | 6 |
| Hip trajectory | Two observed 2D hip keypoints per frame, with visibility | `prediction` (pose model) -> `derived` (midpoint) | 4 |
| Move duration | Move boundaries, integer microseconds | `derived` | 6 |
| Contact dwell | Contact interval length, integer microseconds | `derived` | 5 |
| Hesitation observation | Dwell and joint velocity, threshold `[PILOT]` | `derived` | 7 |
| Foot-adjustment count | Foot contact events within an attempt | `derived`. **`not_applicable` under the hands-only MVP scope** (Section 5), with that reason recorded: no foot contact event is predicted, so there is nothing to derive from. Deferred, not deleted | 7 |
| Transition failure hazard | Failures per transition aggregated over attempts | `derived`, from `adjudicated_ground_truth` outcomes | 7 |

**Confidence never increases downstream.** An `abstained` or `unknown` upstream result can never
become a confident downstream result. If a contact is `unknown`, every move, beta token, dwell
and aggregate depending on it inherits that uncertainty.

When evidence is insufficient the system returns one of: `unknown` (the value is not
determinable), `review` (a human must decide), `abstained` (the model declined to predict), or
`insufficient_data` (the aggregate lacks support). It never returns a confident default.

## 11. Closing statement

**Out of scope, explicitly and permanently for the MVP:** generated coaching text; force or
load-bearing contact inference from monocular RGB; 3D biomechanics and center-of-mass claims;
and any causal claim, including the cause of a fall.

**In scope, allowed and expected in the MVP:** human-confirmed hold maps and user-confirmed
problem identity. Human confirmation is not a weakness of the design. It is how the system
obtains ground truth it is entitled to rely on, and it is what makes the derived telemetry
traceable.
