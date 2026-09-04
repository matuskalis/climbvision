# Operating Manual

Status tags are defined in the preamble of [`mvp-contract.md`](../mvp-contract.md); this manual
uses them and does not redefine them. **Every number here is `[PLANNING]` unless it quotes a
`[FIXED]` envelope value**, in which case it is marked and cited. This manual is **not** the
contract: where the two disagree, the contract is right and this manual is the defect, to be
fixed here rather than argued about there. **This manual contains no results.**
[`docs/status.md`](../status.md) is the only place a measured number lives.

---

## 1. The one-paragraph truth

**The code is not the bottleneck. You are.**

An agent can write the Stage 5 contact baseline in an afternoon and Stage 6's move derivation in
another, but no agent can drive to the gym, place a tripod, ask the front desk for permission,
decide that a foot grazing a volume was incidental rather than intentional, or say which of two
identical blue holds is actually on the problem. Every gate in
[`mvp-contract.md`](../mvp-contract.md) Section 9 is measured against data only you can create.
Until that data exists an agent has exactly two honest moves - build code and test it on
synthetic fixtures, or stop and say it is blocked - and one dishonest one: quietly measure a gate
on generated data and report the number. Preventing that third move is most of what this manual
is for. Roughly twelve hours in a gym and forty hours of labelling `[PLANNING]` is the whole
project; the software is the easy part.

**Standing rule.** An idle agent means you are behind on the human work. It never means the
project is stuck. **Never unblock an agent by inventing data**, and that includes telling it to
assume typical values, to use a placeholder until real footage arrives, or to "estimate" a number
so a table is not empty. A number that should not exist yet is worse than an empty cell, because
once written nobody can tell it apart from a measurement.

Two states, used throughout this manual. They are not the same thing and must never be reported
as if they were.

| State | Means | Requires | Recorded as |
| --- | --- | --- | --- |
| **code-complete** | The reviewer approved it, all tests and lint pass, and the behaviour is proven on synthetic fixtures | No real data | In `docs/status.md` as `code complete; gate pending measurement` |
| **gate-measured** | The stage's gate has been measured **on real annotated data** | Filmed and labelled data | In the Gate evidence column of `docs/status.md`, **with the number** |

A stage that is code-complete has shipped nothing you can trust about climbing. It has shipped
software that runs.

---

## 2. Critical path

**Human work runs one stage ahead of code work.** That is the only legitimate parallelism in this
project. An agent may build the code for stage N+1 while you produce the data for stage N. An
agent may **never** run ahead of a gate: it does not measure, claim or report a gate whose data
does not exist yet.

### 2.1 The path

| # | Item | Who | Depends on | Blocks | Done when |
| --- | --- | --- | --- | --- | --- |
| 1 | Read `mvp-contract.md` Sections 1 and 9 | Owner | - | 2 | You can state the envelope and Stage 2's gate without looking |
| 2 | Decide who may appear on camera | Owner | 1 | 3, 4 | Decision `second-participant` recorded. Recommended: **self only** |
| 3 | Gym permission, in writing, **asking the next reset date in the same message** | Owner | 2 | 6 | A written reply naming the wall you may film and when it is next reset |
| 4 | Write your own consent record; get its opaque ID | Owner | 2 | 6 | The record exists under `~/climbvision-data/consent/` and its opaque ID is in the session-log template |
| 5 | Decide camera settings | Owner | 1 | 6 | Resolution, frame rate, orientation, lens, focus/exposure lock and stabilisation written down **before** the phone is mounted |
| 6 | **Pilot session**: one problem, three attempts `[PLANNING]`, reference stills before and after | Owner | 3, 4, 5 | 7 | The clips and both reference stills are on disk |
| 7 | Ingest the pilot **the same evening** and read the four quality flags | Owner | 6 | 8 | Manifests exist; all four flags read and understood |
| 8 | Finalise frame rate and codec | Owner | 7 | 10 | Decision `capture-settings` recorded, citing the pilot's flags |
| 9 | Plan the session-by-problem **block structure**, at least three disconnected components `[PLANNING]` | Owner | 3 | 10 | A written plan: which problems are filmed in which session |
| 10 | Main filming, about 50 attempts `[PLANNING]` with repeats | Owner | 8, 9 | 11, 12 | Blocks shot; **every clip logged, including the excluded ones** |
| 11 | Session logs, same evening | Owner | 10 | 12 | One complete pseudonym-only log per session |
| 12 | Ingest everything | Agent | 10, 11 | 14 | Every clip has a manifest; the flag summary is in the report |
| 13 | Stage 2 code: harness, CVAT adapter, `MetricValue`, leakage tests | Agent | 1 | 14, 15 | Reviewer approves. **Data-independent, so it overlaps 10 and 11** |
| 14 | **Split freeze** | Agent proposes, **owner approves** | 12, 13 | 16, 20, 23 | Split manifests exist, leakage tests pass, and the release declares `participant: accepted_single_participant` (contract Section 8) |
| 15 | CVAT running, **export-import round trip proven byte-stable on two hand-labelled attempts** | Owner + Agent | 13 | 16 | The round trip is demonstrated, not asserted |
| 16 | Hold polygons on **every hold of every used facet**, plus problem membership and roles, plus a blind re-trace of a subset | Owner | 14, 15 | 17, 24 | Polygons complete per facet; membership attached; re-traced subset exists for the Stage 3 gate |
| 17 | Stage 3 code: calibration, hold map, overlay | Agent | 16 | 18 | Reviewer approves |
| 18 | **Stage 3 gate measured** | Agent | 16, 17 | 19 | Reprojection error, hull coverage, re-fit byte-identity and hold self-agreement IoU in `docs/status.md` |
| 19 | Pose backend decision and the canonical keypoint set | Owner | 18, 20 | 21 | Decisions `pose-backend-selection` and `canonical-keypoint-set` recorded; every model registered in `model-registry.md` first |
| 20 | Keypoint **gold set**, validation and test only, frames chosen by a **seeded script** | Owner | 14 | 19, 22 | About 200 frames `[PLANNING]` labelled on the backend-neutral point set. **Does not wait for 19** |
| 21 | Stage 4 code | Agent | 19 | 22 | Reviewer approves |
| 22 | **Stage 4 gate measured** | Agent | 20, 21 | 26 | PCK and endpoint PCK, with the excluded-point counts, in `docs/status.md` |
| 23 | Attempt boundaries and outcomes on all recordings | Owner | 14 | 24, 28 | Every recording's attempts marked, with outcomes and unobserved-boundary flags |
| 24 | **Contact intervals, four limbs. The long pole** | Owner | 16, 23 | 25, 27 | About 30 attempts `[PLANNING]` fully labelled across validation and test |
| 25 | Blind **self-agreement** re-label of ten attempts, about a third of the labelled set `[PLANNING]`, at least seven days later `[PLANNING]` | Owner | 24 | Stage 2 gate, 27 | `self_agreement` measured and reported as such, never as inter-annotator agreement |
| 26 | Stage 5 code | Agent | 22 | 27 | Reviewer approves |
| 27 | **Stage 5 gate measured** | Agent | 24, 25, 26 | 29 | Temporal IoU, event F1, boundary error, false-contact time and risk-coverage in `docs/status.md`, hands and feet as separate slices |
| 28 | Hand-written beta on about ten attempts `[PLANNING]` | Owner | 23 | 29 | Independent token sequences, written **without looking at any derived output** |
| 29 | Stage 6 code and gate | Agent + Owner | 27, 28 | 30 | Edit distance reported separately for the limb-aware and limb-agnostic forms |
| 30 | Stage 7 code and gate | Agent | 29 | 31 | Support threshold set on validation data; `insufficient_data` where support is thin |
| 31 | Stage 8 go or no-go | Owner | 30 | - | A recorded decision: build the surface, or defer it explicitly |

**One honest wrinkle in this ordering.** Stage 2's gate has two halves (contract Section 9). The
leakage half is deterministic and is measured at the split freeze, item 14. The **agreement**
half is `[PILOT]` and cannot be measured until item 25, which sits after the Stage 3 and Stage 4
gates. So Stage 2 is code-complete at 13/14 and gate-measured at 25, and Stage 3 code starts
while half of Stage 2's gate is still pending. That is a deliberate departure from "a stage does
not start until the previous gate is measured" and it must be **recorded as a decision**
(`agreement-measurement-design`), not adopted quietly. See Section 14.

### 2.2 What the agent builds while you label

| While you are | The agent may build | The agent may **not** |
| --- | --- | --- |
| Filming (items 6 to 11) | The Stage 2 harness, the CVAT adapter, the leakage tests, `MetricValue`, and hand-calculated metric fixtures | Freeze splits, or report any agreement number |
| Tracing hold polygons (item 16) | The Stage 3 homography, the wall-plane transform and the overlay renderer, on a **synthetic planar fixture** | Report mask IoU, or any hold-map accuracy number |
| Building the gold set (item 20) | The Stage 4 pose adapter and the PCK implementation, validated against **hand-computed** fixtures | Report PCK or endpoint PCK |
| Labelling contact intervals (item 24) | The Stage 5 geometric baseline and every Stage 5 metric | Report event F1, temporal IoU, boundary error or false-contact time |

The pattern is the same in every row: the metric **implementation** is code and can be proven
against arithmetic; the metric **value** is a measurement and needs your labels.

### 2.3 Four ordering facts that are not negotiable

| Fact | Why | What breaks if ignored |
| --- | --- | --- |
| **Splits freeze before test footage is inspected for design purposes.** Labelling the test split is required and allowed; **watching test clips to choose a threshold is not** | The test set is frozen and evaluated once (contract Section 8) | Every test number becomes tuned-on-test and is worthless. There is no repair except new footage |
| **Hold polygons before contact intervals** | A contact's target is a `HoldInstance` ID, which must already exist to be referenced | You label contacts against holds you then have to renumber, and every interval's target is wrong |
| **The pose backend decision before the gold set** - unless it is **mitigated by annotating a backend-neutral anatomical point set**, which is the recommendation and which inverts the dependency, so the gold set is built first and then decides the backend (5.5) | A gold set drawn in one backend's keypoint topology cannot score a different backend | Unmitigated: the gold set has to be redone, or the backend is chosen by whatever the gold set already fits, which is circular |
| **All repeats of a problem before the gym resets that wall** | A reset produces a new `WallSet`, and **problem identity does not survive it** (contract Section 5) | Your repeated attempts stop being repeats of the same problem, and Stage 7's transition failure hazard loses its support |

---

## 3. Recording session protocol

Five moments: **before you leave**, **at the wall**, **per attempt**, **before you leave the
gym**, and **the same evening**. The checklist form of this section is in
[`02-session-checklist.md`](02-session-checklist.md); this is the reasoning behind it.

### 3.1 Gear and placement (before you leave, at the wall)

| Item | Setting | Why |
| --- | --- | --- |
| Tripod | Always. Never handheld, never propped on a bag | The envelope is a **static** camera (contract Section 1). One homography per session assumes the camera did not move |
| Height | About 1.2 to 1.5 m `[PLANNING]` | High enough to see the landing zone, low enough not to look down the wall |
| Angle | As close to the wall facet's normal as the floor space allows | Extreme obliqueness stretches the far side of the wall plane and inflates reprojection error |
| Distance | Far enough that the **start holds, the top hold and the landing zone** all sit inside the frame with roughly 10 percent margin `[PLANNING]` | "Full body and full problem visible for the entire attempt" is an envelope condition, not a preference |
| Orientation | **Landscape** | See 3.3 |
| Tripod feet | Taped to the floor, or photographed against a floor seam | So you can return to the same placement for the repeat block |

### 3.2 Resolution and frame rate

At least **1080p `[FIXED]`** and at least **30 fps `[FIXED]`** (contract Section 1). The ingest
thresholds that check them live in `configs/ingest/v1.json` and are copied verbatim from the
contract; they are not tunable at the ingest boundary.

### 3.3 The portrait trap

This one will cost you a session if you meet it cold.

A phone shooting portrait normally still **codes** 1920x1080 and carries a rotation flag, so it
passes the resolution check. A file whose **rotation has been baked into the pixels** codes
1080x1920, and the current check requires width at least 1920 `[FIXED]` **and** height at least
1080 `[FIXED]`, so it is reported as a resolution `fail` on footage that is genuinely 1080p. This
is a **known defect**, recorded in `docs/status.md` under "Known defects", and its repair is
scheduled as **Stage 2's first task**.

Two consequences: **shoot landscape**, and if the flag appears anyway, check the recording's
rotation fields (`rotation_degrees` and `rotation_source`, `data-schema.md` Section 2) **before**
concluding the clip is bad.

### 3.4 Frame rate: 30 or 60

**60 fps `[PLANNING]`, recommended if the pilot shows a constant frame rate at 60.**

The reason is not smoothness. An annotator can only place a contact boundary **on a frame**, so
the label's own resolution is one frame interval: 33.3 ms at 30 fps, 16.7 ms at 60 fps
`[PLANNING]`. Stage 5 reports boundary error in **integer microseconds**
(`evaluation.md` Section 1), so halving the frame interval halves the irreducible floor of that
number. You are buying accuracy in the ground truth, not in the video.

| | 30 fps | 60 fps |
| --- | --- | --- |
| Label resolution `[PLANNING]` | 33.3 ms | 16.7 ms |
| Storage `[PLANNING]` | 1x | roughly 2x |
| Frames to scrub while labelling `[PLANNING]` | 1x | roughly 2x |

**Prefer 1080p60 over 4K30.** Extra pixels buy nothing for timing, and they double your scrubbing
time and your disk for no gain on the metric that is hardest to reach.

### 3.5 Lock everything

| Setting | Do | Why |
| --- | --- | --- |
| Exposure | Lock | An auto-exposure step mid-attempt changes hold appearance between frames |
| Focus | Lock | Hunting focus blurs exactly the frames where a hand meets a hold |
| Zoom | **None `[FIXED]`** | The envelope forbids zoom during a recording (contract Section 1) |
| Automatic lens switching | Disable | A mid-clip lens change is a new camera. It breaks the static-camera assumption silently, without any pan or zoom you would notice |
| Stabilisation | Off if the phone allows | Electronic stabilisation **warps frames** even on a tripod, and a per-frame warp is exactly what one homography cannot model. **If it cannot be turned off, write that in the session log** rather than pretending the camera was rigid |

### 3.6 Reference imagery

Per session, from the **exact tripod position**:

- A clean still of the facet with **no climber**, **before the first attempt**.
- The same still again **after the last attempt**.

The pair is your evidence the camera did not move. If they differ, you know, and Stage 3 can be
told rather than guessing.

Per problem:

- A photo of the gym's own tag.
- A marked-up copy of the wall photo showing which holds belong to the problem and what role each
  plays (`start`, `intermediate`, `finish`, plus the foot-only flag). **Mark it at the gym**, not
  from memory a week later. Two identical blue holds a metre apart are indistinguishable in a
  photograph and unforgettable while you are standing in front of them.

### 3.7 The session log

One log per session. Fields:

| Field | Notes |
| --- | --- |
| Session ID | Stable, opaque, used in every path |
| Date and time | **With the UTC offset** |
| Gym, wall, facet | As **pseudonyms** |
| `WallSet` ID and known reset date | The reset date is why you asked for it in the permission message |
| Camera model and every setting | Including whether stabilisation could be disabled |
| Tripod placement | Position, height, angle, and how it is marked |
| Participant pseudonym | Never a real name (contract Section 7) |
| Consent record ID | The **opaque ID only** |
| Problems filmed | With the gym's own label for each |
| Attempts per problem | Count |
| Reference shots taken | Before and after, yes or no, per problem |
| **Every clip shot, including the excluded ones** | With the reason for exclusion |
| Destination path | In `~/climbvision-data/...` form |
| Free notes | Lighting, crowding, clothing, anything odd |

**Two copies exist.** A **master log** holding the pseudonym-to-person mapping, which never enters
the repository and never leaves your machine. A **pseudonym-only derivative**, which is what feeds
the dataset. They are different files. Do not maintain one file and hope to redact it later.

### 3.8 How many attempts, and of what

About **50 attempts `[PLANNING]`**, as roughly 8 to 10 problems by 5 to 6 attempts each
`[PLANNING]`.

- Choose problems **at or slightly above your limit**, so falls actually happen. A dataset of
  clean sends has no fall events and cannot support Stage 7's transition failure hazard.
- Add one or two **below** your limit for clean sends, so the `send` outcome is represented.
- **Concentrate about 25 of the 50 attempts on a single problem `[PLANNING]`.** The transition
  failure hazard needs **repeats of the same problem by the same climber**. Fifty attempts spread
  over fifty problems produces nothing at all for that stage.

**The block trap.** Splits are group-aware on problem, which the contract requires, **and** on
session, which is the grouping key this manual adds (Section 6.1). If every session contains a bit
of every problem, the problem-session graph collapses into **one connected component** and no
valid split exists at all. Film in **blocks**:
a session covers a small set of problems, and a problem lives in as few sessions as possible.
Aim for at least **three disconnected components `[PLANNING]`**.

### 3.9 What invalidates a clip

| Situation | Verdict |
| --- | --- |
| A second person in frame | **Invalid.** The envelope is exactly one climber `[FIXED]` |
| The camera is bumped | **Invalid from the bump onward.** The remainder becomes a **new session ID**, because the calibration changes |
| Any pan or zoom | **Invalid** |
| The climber leaves the frame during the attempt | **Invalid** |
| Someone stands in front of the camera | **Invalid** |

Two cases that are **valid but flagged**, not invalid:

| Situation | Record it as |
| --- | --- |
| The recording starts with the climber already on the wall | Valid. The **attempt start is unobserved** (`annotation-guide.md` Section 4). Do not use the first frame as the start |
| The phone stopped recording mid-attempt | Valid. The outcome is **`unknown`**, not `fall` (`annotation-guide.md` Section 5) |

**Standing rule with teeth: log every clip you shot, including the ones you excluded, with the
reason.** Silently deleting the messy clips is a bias mechanism. If the clips you drop are
disproportionately falls where you swung out of frame, your fall statistics are wrong, and
**nothing downstream can detect it** - the deleted clips leave no trace to detect.

### 3.10 The same-evening ingest ritual

Do this the evening of the pilot, and the evening of every main session. It is the cheapest
possible place to discover that the camera settings were wrong.

```bash
uv run climbvision ingest <video> --out artifacts
uv run climbvision validate artifacts/recordings/<asset_id>/recording.json
```

Then read exactly four quality flags. Each is three-valued: `ok`, `fail`, `unknown`. `unknown` is
not `fail` - it means the check could not be evaluated.

| Flag | `ok` means | `fail` means | Do |
| --- | --- | --- | --- |
| `resolution_below_min` | At least 1920x1080 `[FIXED]` | Below the envelope **or** portrait pixels (3.3) | Check the rotation fields first. If genuinely below 1080p, change the phone setting and re-shoot |
| `frame_rate_below_min` | At least 30 fps `[FIXED]` | Below the envelope | Change the phone setting and re-shoot. `unknown` here means `avg_frame_rate` was `0/0`, which is unknown, not zero |
| `variable_frame_rate` | Exactly one distinct inter-PTS delta | Two or more distinct deltas, so the stream is VFR | Not a blocker. See Section 12. Fix the phone settings for future sessions and **never transcode the master** |
| `timestamps_absent` | Every packet carries a PTS | Some packet has no timestamp | **Serious.** Timing is the whole product. Re-copy from the phone rather than re-encoding |

One more thing to read, which is **not** a quality flag but a fact recorded in the manifest: a
non-zero `audio_stream_count` means **there is audio in the file**, which means bystander
conversation may be in the file. That is why it is recorded (contract Section 7). See Section 4.

### 3.11 Storage, outside the repository

The `.gitignore` is a **safety net, not the boundary.** Keep footage physically outside the
repository so that a stray `git add -f` cannot defeat it. Nothing in `~/climbvision-data/` is
inside `~/projects/climbvision/`.

```
~/climbvision-data/
  sessions/
    <session-id>/
      raw/          # phone originals, untouched
      reference/    # clean facet stills, tag photos, marked-up wall photos
      session-log.md
  consent/          # consent records, one per participant
  exports/          # annotation exports on their way into the repo adapter
  README.md         # a note to future-you: what this is, how it is backed up
```

Write paths in the `~/...` form everywhere, **never with a real user name**: an absolute path can
contain a person's name, and absolute paths never appear in written artifacts (contract
Section 7).

Naming rules, with the reason that makes them stick. **The ingest run record stores the input
basename verbatim** (`input_basename`), so **a filename is provenance**:

| Rule | Because |
| --- | --- |
| No real names in filenames | The basename ends up in a committed run record |
| Lowercase ASCII, no spaces | It is copied into paths, logs and reports |
| Zero-padded indices (`attempt-003`) | So sorting is stable |
| **Never rename a file after ingest** | The asset ID is the SHA-256 of the bytes and survives a rename, but the recorded basename would then disagree with reality, and the disagreement is silent |

Back up **raw footage and consent records** separately, on their own schedule. Artifacts
regenerate from the footage in minutes. Footage does not regenerate at all.

---

## 4. Consent and bystanders

**This is not legal advice.** If other people are involved, if anyone is a minor, or if anything
will ever be published, get real advice from someone qualified. What follows is the operating
minimum for a solo project filming itself.

### 4.1 Three decisions

| Decision | Recommended default | Consequence |
| --- | --- | --- |
| Who is on camera | **Self only, for the whole MVP** | Stated plainly: **one participant means within-climber claims only.** Nothing you measure estimates anything about any other climber |
| Gym permission | **Ask, in writing** | A verbal yes from whoever was at the desk is not a record, and the person who gave it will not be there next month |
| Bystanders | **Exclude** | A clip with a second person in frame is invalid anyway (3.9), so this costs you nothing you were allowed to keep |

### 4.2 Five things to ask the gym, in one message

1. May I film **myself** on a tripod, on a specific wall?
2. Other members may occasionally appear in the background - is that acceptable to you?
3. Do you have your own filming policy or signage I should follow?
4. May I ever **publish** a clip? (Ask now even if the answer is no; it costs nothing.)
5. **When is that wall next reset?**

Question 5 is the one people forget, and it sets your whole schedule (2.3).

### 4.3 Managing bystanders in practice

- Film at quiet hours.
- Pick a facet whose adjacent zone is empty.
- Frame tight enough that mat traffic falls outside the frame.
- Tell the two or three people nearest you what you are doing.
- **Re-shoot rather than use a clip someone walked through.** Re-shooting costs one attempt.

### 4.4 The one hard rule that needs no lawyer

**Raw footage never leaves your machine.** Not to a cloud annotation service. Not pasted into a
chat with an agent. Not attached to a bug report. Not into any model API. Not "just this once, to
show the problem".

If you must share a frame to debug something, it contains **no third party and no face**, and it
is a **derived artifact with its own identity** - never the master file.

### 4.5 The consent record

Minimum fields:

| Field | Notes |
| --- | --- |
| Opaque ID | The **only** part of this that ever enters the repository |
| Date | |
| Participant pseudonym | |
| What was recorded | Which sessions, which wall, what content |
| What it will be used for | Be specific and narrow |
| Retention period and deletion date | See decision `retention-policy` |
| How to withdraw | A concrete mechanism, not "ask me" |
| Where it is stored | `~/climbvision-data/consent/` |
| Signature or typed confirmation | |

Stored **outside the repository**. The repository sees the opaque ID only, which is already a
nullable field on `Recording` (`data-schema.md` Section 2).

### 4.6 Withdrawal is expensive after a split freeze

Honouring a withdrawal after item 14 means: deleting the raw files; deleting every artifact
derived from them; deleting every derived record referencing them; removing those assets from the
split manifest; **re-freezing the split**; and **invalidating every gate measured against the old
split**, because the split it was measured on no longer exists.

That is the real reason self-only footage is the recommended default, and the reason anyone
else's consent must be obtained **before** filming, not after.

### 4.7 Audio

The phone records audio, and the manifest records its presence, **precisely because bystander
speech is personal data** (contract Section 7).

- **Ingest the phone original unchanged.** Never share it.
- **Do not strip audio after ingest.** Stripping audio changes the bytes, therefore changes the
  asset ID, therefore **orphans every run record that attests to the old manifest**. If audio must
  be removed, that is a decision about what is ingested in the first place, not an edit afterwards.

Recorded as decision `audio-handling`.

---

## 5. Annotation plan

### 5.1 The tool decision, bluntly

**Self-hosted CVAT, via docker compose, on your own Mac.**

Cloud annotation means uploading footage containing faces to a third party, which contradicts
4.4. That alone decides it; nothing else about the comparison matters.

**The repository's no-Docker rule is about the project's own dependencies, not about the tools on
the annotator's laptop.** `AGENTS.md` Section 4 forbids Docker as a runtime dependency of
ClimbVision. CVAT is not a dependency of ClimbVision. Nothing from CVAT enters the repository
except **exported files** and the **Stage 2 adapter** that reads them, and the internal schema
stays the source of truth (`annotation-guide.md` Section 7).

**Risk `[PLANNING]`: arm64 image availability.** Verify the compose stack actually starts on
Apple Silicon before planning around it. Two fallbacks, both legitimate:

| Fallback | Covers |
| --- | --- |
| A Linux VM | Everything CVAT does |
| **A spreadsheet keyed to presentation timestamps**, read off a frame-stepping player | Attempt boundaries and contact intervals. Not hold polygons |

The spreadsheet fallback is not a hack. Contact intervals are pairs of timestamps with
attributes, and a spreadsheet represents that honestly as long as the timestamps are the
**recorded presentation timestamps** and never `frame_number / fps`
(contract Section 3).

Recorded as decision `annotation-tooling-deployment`.

### 5.2 The rule that saves a week

**Label two attempts `[PLANNING]`. Prove the export - import - export round trip is byte-stable.
Then scale.**

The riskiest part of Stage 2 is how per-limb contact intervals are represented: four parallel
timelines with attributes on each interval. Demand a **demonstrated** round trip on a hand-made
example before labelling anything at volume. If the adapter loses an attribute, you find out
after two attempts, not after thirty.

### 5.3 What gets labelled

| Label type | Tool and mode | Unit | Granularity | Time per unit `[PLANNING]` | Export | Needed for |
| --- | --- | --- | --- | --- | --- | --- |
| Hold polygons | CVAT image annotation on the clean facet still | One polygon per hold | Outline the **graspable surface**, not the bounding box. Volumes are **separate instances** | 10 to 25 s per hold; 20 to 50 min per facet | Polygon export, converted to COCO polygons by the adapter (`data-schema.md` Section 6) | Stage 3, and every contact target |
| Problem membership | Attribute pass over the existing polygons | One attribute set per hold per problem | Membership plus **role** (`start`, `intermediate`, `finish`) and a separate **foot-only** flag | 3 to 8 min per problem | Same export, attributes carried through | Stage 3, Stage 6 |
| Attempt boundaries and outcomes | CVAT video, or the spreadsheet fallback | One record per attempt | Start and end timestamps, outcome, **unobserved-boundary flags** | 2 to 5 min per recording | Interval export | Stage 6, Stage 7 |
| **Per-limb contact intervals** | CVAT video, **one track per limb** | One interval per (limb, target) | **Half-open `[start_us, end_us)`**. Attributes: target, `intentional_use` / `incidental_touch` / `unknown`, visibility, and a **boundary-uncertain** flag | **15 to 40 min per attempt. The dominant cost** | Track export with attributes | Stage 5, Stage 6 |
| Keypoint gold set | CVAT image annotation on sampled frames | One frame | 12 to 16 anatomical points `[PLANNING]`, each with a visibility value | 1 to 2 min per frame | Keypoint export | Stage 4 |
| Hand-written beta | Text, one line per attempt | One attempt | An ordered token sequence, written **from the video**, not from any derived output | 3 to 6 min per attempt | Plain text into the adapter | Stage 6 cross-check |

The exact export profile is settled by decision `annotation-tooling-deployment` and **proved** by
the round trip in 5.2, not assumed from this table.

### 5.4 Two budget levers

Both cut the largest cost, and both are honest.

1. **Contact intervals are needed only for the validation and test splits.** Stage 5's baseline is
   **interpretable geometry** whose thresholds are selected on validation data (the repository
   `README.md` roadmap, Stage 5). **Nothing is trained.** So: film about **50** attempts
   `[PLANNING]`, fully label about **30** `[PLANNING]`, and let the remainder flow through the
   validated pipeline as **Stage 7 input** rather than as ground truth. Recorded as decision
   `labeling-tier`.
2. **The gold set likewise needs only validation and test**, for a pretrained, non-finetuned
   backend. There is no training set to build because there is no training.

### 5.5 The keypoint gold set

The gold set exists to decide the pose backend, which creates a circular dependency if the gold
set is annotated in a backend's own topology. It is broken like this:

**Annotate a backend-neutral, anatomically defined point set.** Palm centre and shoe toe as the
four endpoint anchors, plus wrists, ankles, elbows, knees, hips and shoulders: **12 to 16 points
`[PLANNING]`**. Then give **each candidate backend a documented mapping** onto those points,
**exclude from that backend's score any point it does not emit**, and **report the excluded
count** alongside the score.

That is what lets the backend decision be settled by a comparison **on your own gold set**
(`model-registry.md` Section 4) rather than by reading model cards, and it is why the gold set
does not have to wait for the decision. Endpoint PCK for palm and toe anchors is the deciding
metric (`evaluation.md` Section 1); keypoints labelled `occluded` or `out_of_frame` are excluded
from both numerator and denominator, and their count is reported.

**Frame selection must be a seeded script, not your taste.** Stratify across:

- attempt,
- time-decile within the attempt,
- occlusion level,
- and a deliberate **oversample of frames where a hand or foot is near a hold**.

Hand-picking clean frames inflates the score, and **the inflation is undetectable afterwards** -
the resulting number looks exactly like an honest one. Reserve about **50 extra frames
`[PLANNING]`** to be drawn near **contact boundaries** once contact labels exist, because that is
where endpoint accuracy actually decides a contact.

### 5.6 Adjudication with one annotator

There is no second annotator, so inter-annotator agreement is unavailable. The honest substitute:

| Step | Detail |
| --- | --- |
| Re-label | A random **ten attempts, about a third of the labelled set `[PLANNING]`** |
| Gap | At least **seven days `[PLANNING]`** |
| Blind | The first pass is **hidden**. If you can see it, you are not measuring agreement, you are measuring your ability to copy |
| Report as | **`self_agreement`**, and **never** as inter-annotator agreement (`annotation-guide.md` Section 6) |
| Limitation | **Self-agreement measures the stability of one person's interpretation, not the shareability of the ontology. It is an upper bound on what a second annotator would achieve** |
| Disagreements | Resolved into an explicit **adjudicated** record with a separate provenance class; **both originals are retained** (`annotation-guide.md` Section 6) |

The limitation row is not a footnote. It is the caveat that must travel with the number every
time the number is quoted.

### 5.7 What not to annotate, at first

- Technique names. There is no validated closed label set (contract Section 2).
- Body segmentation. Nothing consumes it.
- Anything 3D. Out of scope, permanently, for the MVP.
- Efficiency, quality or difficulty. No validated construct.
- Hesitations. **Stage 7 derives them** from dwell and velocity; hand-labelling them creates a
  second, conflicting definition.
- Facets you did not film.

**And one anti-shortcut.** Do **not** label only the holds that belong to a problem. Two costs,
one immediate and one deferred. Immediately: a contact whose target is an unlabelled hold has **no
`HoldInstance` ID to reference**, so it degrades to `wall_region` or `unknown` and the interval
stops being about a hold. Later: **mask scoring counts a prediction on an unlabelled hold as a
false positive**, so partial labelling makes that metric meaningless in a way that looks exactly
like a bad model. Mask IoU and AP are `not_applicable` until a segmenter is adopted
(`evaluation.md` Section 1, decision `hold-segmentation-model`), so the second cost is deferred,
not avoided - and it is paid by re-labelling. **Label every hold on each facet you use** - that is
one image per facet, not one per attempt - or explicitly **restrict evaluation to a declared
region** and say so in the artifact.

---

## 6. Split design

### 6.1 The grouping keys, and their real state

| Key | State here |
| --- | --- |
| Participant | **Degenerate.** One climber. See 6.3 |
| Problem | **Real.** The primary grouping key |
| Session | **Real.** Carries lighting, chalk state, clothing and tripod placement |
| `WallSet` | Weak. Few values, and it moves with the gym's reset schedule |
| Gym | Weak. One value |
| Asset SHA-256 | **Real**, and tested: no asset hash may appear in more than one split (`evaluation.md` Section 2) |

### 6.2 The method, stated so you can check it was done

1. Build a **bipartite graph** of problems and sessions: an edge joins a problem to every session
   it appears in.
2. Take the graph's **connected components**.
3. Assign **whole components** to splits.

A problem and every session containing it therefore always land in the same split. This is the
mechanism the block-filming advice in 3.8 exists to serve: if you film everything everywhere, the
graph is one component and no split exists.

Ask the agent to report the component sizes. If there is one component, the split is impossible
and the honest output is a refusal, not a split.

### 6.3 The degenerate-participant honesty rule

The leakage test asserting that **no participant appears in more than one split cannot hold** with
one participant. It must do exactly one of two things:

- **Fail loudly**, with a message saying participant-level leakage control is unavailable on this
  release; or
- record the result as **`not_applicable`, with the reason attached**.

And the release manifest must **explicitly declare** `participant: accepted_single_participant`;
the leakage test **fails** if the release declares neither that nor `none` for that key (contract
Section 8).

What it must **never** do is silently pass, silently skip, or quietly disappear from the test
file. **This is the single most likely place in the whole project for an agent to produce a green
check that means nothing.** Check it by name. Recorded as decision `single-participant-split-policy`.

### 6.4 The scope sentence

Attach this, verbatim, to every reported metric:

> All measured values come from one climber, one gym, a small number of wall facets and a fixed
> camera placement per session; they support within-climber claims only and do not estimate
> performance on other climbers, gyms, camera placements or wall sets.

### 6.5 Leakage channels that no test covers

| Channel | Status | What to do |
| --- | --- | --- |
| The **same clothing** across splits | Real, and not tested by anything | **Change clothes between session blocks.** Cheap, takes no time, removes the channel outright |
| Lighting and chalk state within a session | Handled by session grouping | Nothing extra |
| The **same physical hold appearing in two problems** | Real and **unavoidable** in a bouldering gym | Note it in the release. It is a known limit of the split, not a bug to be fixed |

### 6.6 Names and proportions

Recommend calling them **dev**, **test** and **reserve**, rather than train, validation and test.
Nothing is trained in this MVP, and a "training set" that trains nothing is a fiction that will
mislead every future reader, including you. Rough proportions **40/40/20 `[PLANNING]`**.

Because 6.2 assigns whole components to splits, the problem that 3.8 concentrates sets a floor on
the largest split, so these proportions are a target the block structure may override, and the
release records what was actually achieved.

Recorded as decision `split-names-and-proportions`. Until it is decided, the contract's own words
(validation and test) are used in these documents.

### 6.7 "Frozen and evaluated once", operationalised

The contract says the test set is frozen and evaluated **once** (Section 8). Across **eight
stages** that needs a reading, because eight gates cannot share one evaluation.

**Proposal: one test evaluation per stage gate attempt, each logged in `docs/status.md` with its
date and its reason.** Repeatedly re-running the test set to chase a gate is tuning on test, no
matter what it is called.

Recorded as decision `test-set-evaluation-policy`. It is a **decision**, recorded as such - not a
quiet reinterpretation slipped into a code change.

---

## 7. The per-stage loop

### 7.1 The checklist

1. Open the stage brief in [`briefs/`](briefs/) and read **only its preconditions**.
2. **Tick every precondition. If one is unticked, stop.** An unticked precondition is the whole
   reason gates get measured on nothing.
3. Start a **fresh session** and paste template **T1** from
   [`01-prompt-templates.md`](01-prompt-templates.md).
4. Let the implementer and the reviewer run **without intervening**. Mid-run steering is how a
   reviewer ends up reviewing your opinion instead of the code.
5. Read **exactly four things**: the reviewer's verdict **verbatim**; the `docs/status.md` diff;
   the verification commands **with their claimed output**; and the list of **what could not be
   measured**.
6. **Run the commands yourself.**
7. Run the anti-bluff table from
   [`05-verification-commands.md`](05-verification-commands.md).
8. Commit and push.
9. **Stop.** Decide whether the next stage opens.

Step 6 is not optional and is not rude. Claimed output and real output diverge for boring reasons
as often as dishonest ones.

### 7.2 Bluff signals

| Signal | Why it matters | Your move |
| --- | --- | --- |
| Modal verbs where a measurement belongs: "should work", "presumably", "typically" | These are the grammar of an untested claim | Ask for the command and its output |
| An **untagged number** anywhere in `docs/` | An untagged number is a defect by definition (`AGENTS.md` Section 8) | Ask which tag it carries and why |
| A gate marked **passed with no number** | A gate is a measurement; without the number there is nothing to check | Reject. `pending measurement` is the honest value |
| A **test count below 423** | Tests were deleted or silently excluded | Ask which tests disappeared, and why |
| **Skipped tests when `ffprobe` is present** | Expected here is **423 passed, 0 skipped**. The 51 skips exist **only** in the hermetic run without `ffprobe` (`docs/status.md`) | Ask what was skipped and whether `ffprobe` was on `PATH` |
| A `[PILOT]` that has become `[VAL]` | `[VAL]` requires validation data **and** a selection run recorded in `docs/status.md` | Ask which selection run. If there is none, it is a fabrication |
| A gate number **exactly equal to its threshold** | Measurements rarely land exactly on the bar; numbers written to match it always do | Ask for the raw distribution and the per-slice values |
| Gate evidence citing `tests/fixtures/` | **Fixtures prove code runs. They never measure a gate** (`AGENTS.md` Section 11) | Reject outright |
| The words **simulated, mock, placeholder, TODO** inside something described as complete | Rule 14: no silent fallback to synthetic output | Ask where, and what it stands in for |
| **Dependencies the brief did not name** | The module inventory pin and the import allowlist exist exactly to catch this (`AGENTS.md` Section 6) | Ask which brief authorised it. If none, it is out of scope |
| The **contract or a config changed inside a code-only change set** | Contract documents are edited surgically and only where a brief authorises it | Revert that part and ask for a decision record |
| A **threshold changed in the same change set that measured a gate** | This is gate-lowering, whatever it is called | Reject. "A failed gate is information. A moved gate is nothing" (`evaluation.md` Section 5) |
| A **paraphrased** reviewer verdict instead of the verdict | Paraphrase is where "approved with findings" becomes "approved" | Ask for the verdict verbatim |
| A **missing failing slice** | Failing slices by participant, problem and `WallSet` are required (`AGENTS.md` Section 10) | Ask for the per-slice table |
| Any **unknown or occluded value mapped to a negative** | Standing rule 1: `occluded` is not `none`, `unknown` is not `false` | Reject. This corrupts the dataset permanently |

### 7.3 What "send it back" looks like

**Do not argue with the implementer.** You will lose, not because you are wrong but because you
are arguing about code with the thing that wrote it.

Send **the specific line** to the **reviewer**, using template **T2**, which asks for
verification by **independent measurement** rather than by re-reading the implementer's report.
That is precisely what caught both Stage 1 defects: the review passed on the second pass with zero
new findings only after independently measuring every clause (`docs/status.md`, Stage 1 row).

---

## 8. Anti-bluff checks

The runnable table lives in [`05-verification-commands.md`](05-verification-commands.md). Run it
yourself, after every stage, before you believe anything.

It covers three things: the **commands** that reproduce each claimed result and the exact output
you should see; the **greps** that catch a forbidden pattern in one line, such as an untagged
number, a `[VAL]` tag, or a gate cited against `tests/fixtures/`; and the **diff checks** that
show what a change set touched beyond what its brief authorised. None of it requires reading code.

---

## 9. Decisions you must personally make

The full list of slugs, with the stage that needs each, is the decision index in
[`docs/agents/README.md`](README.md). Each is recorded as a file under `docs/adr/` **when it is
made**. Below
is the detail for the ones that come early or cost the most to get wrong.

| Slug | The decision | What you need before deciding | Recommended default | Deadline |
| --- | --- | --- | --- | --- |
| `second-participant` | Does anyone other than you appear on camera? | Nothing. Decide before filming | **No, not during the MVP.** If it ever happens, film them as a **separate session block** so they can become their own split component | Before item 6 |
| `capture-settings` | Resolution, frame rate, codec, orientation, stabilisation | The pilot's four quality flags | **1080p60 `[PLANNING]` if the pilot shows constant frame rate at 60**; landscape; everything locked | Before item 10 |
| `retention-policy` | How long footage is kept and when it is deleted | Your own tolerance, and the consent record needs a period stated | A definite period with a definite deletion date. A provisional period must exist **before filming**, because the consent record names it | Consent record now; enforced at Stage 8 |
| `audio-handling` | Is audio ingested, and what may ever be shared | Section 4.7 | Ingest the phone original **unchanged**; never share the audio; never strip it after ingest | Before item 12 |
| `annotation-tooling-deployment` | Which annotation tool, deployed how | Whether CVAT's compose stack starts on Apple Silicon | **Self-hosted CVAT.** Cloud is excluded by 4.4, not by preference | Before item 15 |
| `annotation-storage-and-release-commit-policy` | What annotation output enters the repository, and in what form | The round trip in 5.2 | Exported labels enter the repository; **pixels never do**. Releases reference assets by SHA-256 | Stage 2 |
| `single-participant-split-policy` | How the participant leakage clause behaves on a one-climber release | Section 6.3 | Declare `participant: accepted_single_participant`; the test records `not_applicable` **with a reason**, or fails loudly. Never a silent pass | Item 14 |
| `agreement-measurement-design` | How and **when** `self_agreement` is measured, and whether Stage 3 may start on a code-complete Stage 2 | Sections 2.1 and 5.6 | Blind re-label of ten attempts, about a third of the labelled set `[PLANNING]`, after at least seven days `[PLANNING]`; Stage 3 code may proceed on a code-complete Stage 2, recorded here explicitly | Stage 2 |
| `split-names-and-proportions` | dev/test/reserve versus train/validation/test, and the proportions | Section 6.6 | **dev / test / reserve**, roughly 40/40/20 `[PLANNING]` | Item 14 |
| `test-set-evaluation-policy` | What "evaluated once" means across eight gates | Section 6.7 | **One test evaluation per stage gate attempt**, each logged in `docs/status.md` with its date and reason | Item 14 |
| `labeling-tier` | Which splits get full contact labels | Section 5.4 | Fully label about 30 of about 50 attempts `[PLANNING]`; the rest are Stage 7 input, not ground truth | Stage 2 |
| `hold-segmentation-model` | Adopt a hold segmenter, or not | Nothing. The default is the cheap one | **None, at first.** The hold map is **user-confirmed by contract**, so no segmenter is needed to reach the Stage 3 gate, and adopting one adds a licence review, weights management and **preannotation bias**. Until adopted, mask IoU and AP are `not_applicable` (`evaluation.md` Section 1) | Stage 3 |
| `pose-backend-selection` | Which pose backend | A comparison **on your own gold set** (5.5), endpoint PCK deciding | Decide by measurement, **never by model cards**. Two traps: the **checkpoint licence and the code licence differ**, frequently with the checkpoint more restrictive; and a **wholebody pipeline usually needs a second detector model**, which is a second model needing its own registry entry with all seven fields (`model-registry.md` Section 1) | Item 19 |
| `canonical-keypoint-set` | The anatomical points the gold set defines | 5.5 | 12 to 16 backend-neutral anatomical points `[PLANNING]`, with a documented per-backend mapping and a reported excluded-point count | Item 19 |
| `application-stack` and **when Stage 8 may start** | Whether to build the application surface, and on what | Stages 1 through 7 gates measured | **Stage 8 does not start until Stages 1 through 7 gates are measured and in `docs/status.md`** (contract Section 9). Deferring Stage 8 explicitly is a legitimate outcome | Item 31 |

Every model named in any of these decisions is registered in `docs/model-registry.md` with all
seven fields **before its weights are downloaded**, not after.

---

## 10. Time and effort

**Every number in this section is a guess made by an agent reading a repository. None of it is a
measurement.** Replace each one with your own observed number the moment you have it. The first
filming session and the first five labelled attempts will tell you more than this whole table
does.

| Phase | Owner hours `[PLANNING]` | Agent wall-clock `[PLANNING]` | Note |
| --- | --- | --- | --- |
| Consent and gym permission | 1 to 2 | - | Mostly waiting for a reply |
| Camera decisions and the pilot | 1.5 to 2.5 | - | |
| Pilot ingest and reading the flags | 0.5 to 1 | - | **The highest-value hour in the project.** It is where a wrong camera setting costs one evening instead of one dataset |
| Main filming | 12 to 15 | - | Across several sessions, in blocks |
| Session logs | 3 | - | Same evening, every time |
| Ingest everything | 0.5 | 1 to 2 hours | |
| Stage 2 | 3 to 6 | 1 to 2 days | **Code is data-independent and overlaps filming** |
| Stage 3 | 4 to 8 | 1 to 2 days | Hold polygons dominate the owner hours |
| Stage 4 | 6 to 12 | 1 to 2 days | Gold set dominates |
| **Stage 5** | **15 to 30** | 2 to 4 days | **The long pole. This sets the schedule** |
| Stage 6 | 2 to 4 | 1 to 2 days | Hand-written beta dominates |
| Stage 7 | 1 to 2 | 1 day | |
| Stage 8 | 2 to 4 | 1 to 3 days | Only if it goes ahead |
| **Total** | **roughly 55 to 90** | **9 to 16 working days** | **6 to 12 weeks part-time `[PLANNING]`**, dominated by labelling and by when the gym resets |

One honest closing line: the agent column assumes **prompt review turnaround**. If a reviewer
verdict sits unread for three days, the calendar is set entirely by you, and no number in this
table means anything.

---

## 11. What "done" means

The MVP is done when:

- **Stages 1 through 7** each have a gate **measured** and reported in `docs/status.md`, **with
  the number**, its **failing slices**, and the **scope caveat** from 6.4; and
- **Stage 8** has either been delivered against its workflow gate or **explicitly deferred by a
  recorded decision**.

State the asymmetry deliberately: **a gate that is measured and fails, and is reported honestly,
is a completed stage in the sense that matters** - you know where you stand and what the next
experiment is. **An unmeasured gate is not a completed stage**, however much code sits behind it.

### 11.1 What you can actually see

| You can see | Behind it |
| --- | --- |
| An **overlay video** of one attempt: the hold map, the tracked endpoints, and a contact timeline | The **structured contact records** the overlay renders. An overlay is a diagnostic view and **never the only result** (`data-schema.md` Section 6) |
| A **JSON of attempts, moves and beta tokens**, in **both** the limb-aware and limb-agnostic forms | Every value carries its **provenance class** (contract Section 10) |
| A **comparison of two attempts on the same problem**, aligned by contact events | Stage 6 output, aligned on events rather than on wall-clock time |
| An **analytics table** with **support** shown, and `insufficient_data` where support is thin | Stage 7 aggregates over validated primitives |
| A **`docs/status.md`** in which every number is measured, tagged and dated | The stage ledger. Nothing enters it that was not observed |

### 11.2 What is not promised

No accuracy level. No claim about another climber, another gym or another camera placement. No
grade. No score. No coaching. No 3D. No force.

And one expectation to set now: **expect a lot of `insufficient_data` cells** with 50 attempts,
and **expect Stage 5's numbers to be worse than you hoped.** Both are the system working
correctly. That is exactly why the gates are **targets to be set on validation data**, and not
promises made in advance.

---

## 12. Failure protocol

| Situation | First move | Never | Recorded in |
| --- | --- | --- | --- |
| **A gate fails** | Report the measured gap **with the number**, report the failing slices, propose the smallest next experiment, and stop for a decision | Lower the gate, narrow the slice, or hide a failing slice in a pooled average | `docs/status.md`, plus a decision record if the gate itself changes |
| **An agent violates a rule** | Name the rule, stop the stage, and send the specific line to the reviewer with T2 | Accept the work "just this once because it is nearly right" | The stage report, and the decision record if a rule genuinely needs changing |
| **Self-agreement comes out poor** | **Sharpen `annotation-guide.md` with a new decision rule, then re-label under it, retaining the old labels** | **Quietly change labels so that they agree. That is fabrication**, and it is undetectable afterwards | `annotation-guide.md`, plus the re-label round in `docs/status.md` |
| **Footage is out of envelope** | Read the flag, fix the phone setting, re-shoot | Ingest it anyway and forget the flag was `fail` | The session log and the manifest's quality flags |
| **`variable_frame_rate` fires** (some phones will) | **Not a blocker.** Timing comes from **per-packet presentation timestamps**, not a frame counter (contract Section 3). Fix the phone settings for future sessions | **Never transcode the master.** Re-encoding resamples frames, invents timestamps, changes the bytes and therefore **changes the asset ID** | The session log; the flag is already in the manifest |
| **`timestamps_absent` fires** | **Serious.** Re-copy the file from the phone; suspect the transfer, not the camera | Re-encode to "add" timestamps. An invented timestamp is indistinguishable from a measured one | The session log |
| **A resolution `fail` on genuinely 1080p footage** | **Check rotation first** (3.3). Then shoot landscape | Conclude the clip is unusable, or re-encode to rotate it | The session log; the defect is already in `docs/status.md` |
| **`MANIFEST_CONFLICT` on ingest** | **Ingest into a fresh output directory**, then ask which change (config or schema version) caused the difference | **Never overwrite the stored manifest.** Earlier run records attest to those bytes by hash (`data-schema.md` Section 9) | The stage report |
| **The camera was bumped mid-session** | The clip is invalid from the bump onward; the remainder becomes a **new session ID** | Keep the whole clip and hope one homography still fits | The session log, both halves |
| **The gym reset the wall** | Stop. A new `WallSet` means **new problem identities** (contract Section 5). Everything filmed after the reset is a different problem, even if it looks identical | Merge across the reset to get more attempts | The session log and the `WallSet` record |
| **You lost the thread after a gap** | **Re-read `docs/status.md`, then run the verification table in `05-verification-commands.md`, and only then read any agent's summary** | Start by reading an agent's summary. It is the most persuasive and least verified thing in the repository | Nothing to record; this is a reading order |
| **Backup loss** | Stop all work. Establish what raw footage and consent records still exist before regenerating anything | Regenerate artifacts first. Artifacts are cheap; footage and consent records do not regenerate | A note in the session log directory README |

---

## 13. Prompt templates

The templates live in [`01-prompt-templates.md`](01-prompt-templates.md); their text is there and
is not duplicated here. **T1** opens a stage: paste it into a fresh session once every
precondition in that stage's brief is ticked (7.1). **T2** challenges a reported result: send it
to the **reviewer**, not the implementer, naming the specific line you doubt and asking for
verification by **independent measurement** (7.3). The remaining templates, **T3 through T6**,
each carry their own trigger condition at the top of the entry, and they cover the other
recurring situations this manual names: recording a decision (Section 9), a failed gate
(Section 12), stopping an agent for a rule violation (Section 12), and resuming after a gap
(Section 12). Read the trigger line, not the whole file, and use the template whose trigger
matches your situation.

---

## 14. Tensions in the existing documents

These are the places where the Stage 0 documents were silent, circular, or in tension with each
other. Each is resolved below so a future reader does not have to rediscover it.

| Tension | Resolution |
| --- | --- |
| "A stage does not start until the previous gate is measured" (the repository `README.md` roadmap) versus agents idling for weeks while data is produced | **Human work runs one stage ahead** (Section 2), and the **code-complete versus gate-measured** vocabulary (Section 1) makes the distinction reportable. Where this lets Stage 3 code begin on a code-complete Stage 2, it is recorded under `agreement-measurement-design`, not adopted quietly |
| The test set is "evaluated **once**" (contract Section 8), but there are **eight** gates | **One test evaluation per stage gate attempt**, each logged in `docs/status.md` with its date and reason. Recorded as decision `test-set-evaluation-policy` (Section 6.7) |
| One participant **vacates** the participant leakage clause, so the test passes on an empty condition | The contract now requires a single-participant release to **explicitly declare** `participant: accepted_single_participant`, and the leakage test **fails** if it declares neither that nor `none`. The test must fail loudly or record `not_applicable` **with a reason**; a silent pass is the failure mode (Section 6.3) |
| Labelling only the holds on a problem leaves contacts with **no `HoldInstance` to reference**, and **destroys the mask metric** whenever a segmenter is adopted, because a prediction on an unlabelled hold scores as a false positive | **Label every hold on each facet you use** (one image per facet), **or** explicitly restrict evaluation to a declared region and say so (Section 5.7) |
| The gold set's keypoint topology depends on the backend, but the backend is chosen **on the gold set** | Annotate a **backend-neutral anatomical point set**, map each candidate onto it, exclude unemitted points and report the excluded count (Section 5.5) |
| Stage 6's gate is **circular** if beta is derived from adjudicated contacts by the same rule the derivation uses | Report **both**: the derived form, **and** an **independently hand-written beta** on about ten attempts `[PLANNING]`, written from the video without looking at any derived output (Section 5.3, item 28) |
| Filming everything everywhere **collapses the split graph** into one component, so no valid group-aware split exists | **Film in blocks**, aiming for at least three disconnected components `[PLANNING]` (Sections 3.8 and 6.2) |
| Portrait footage that is genuinely 1080p **fails the width check** | **Shoot landscape.** The defect is recorded in `docs/status.md` and its fix is scheduled as **Stage 2's first task** (Section 3.3) |
