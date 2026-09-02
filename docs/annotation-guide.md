# Annotation Guide

Human decision rules for the labels defined in [`mvp-contract.md`](mvp-contract.md) Sections 5
and 6. Read the contract first; this document tells you how to apply it, not what it means.

**No annotation has been collected yet.** The annotation harness, the CVAT adapter and the
split manifests are **Stage 2 deliverables**. This guide is written before the first annotation
so that the first annotation is already consistent with the contract.

Status tags as defined in the contract. Nothing here is tagged `[VAL]`: no validation data
exists.

---

## 0. The standing rule

**Answer `unknown` rather than guessing.**

Once written, a guessed label is **indistinguishable from an observation.** Nobody downstream
can tell that you were unsure. A dataset of confident guesses looks exactly like a dataset of
careful observations, and it will train and evaluate models that inherit your guesses as truth.

`unknown` is a correct answer. It is not a failure to complete the task, it is not penalised,
and it is not something to minimise. If the evidence in the frames does not decide the question,
the answer is `unknown`.

The same applies to the visibility set: **never label an occluded limb as not in contact.**
`occluded` is not `none`.

---

## 1. `intentional_use` vs `incidental_touch`

**Proximity alone never decides this.** A hand overlapping a hold in the image, resting beside
it, or passing across it is **not** use.

| Label | Apply when |
| --- | --- |
| `intentional_use` | The limb visibly bears or directs the climber's position through that contact: the body is supported by it, pulled or pushed against it, or held in position by it |
| `incidental_touch` | Contact occurred without being used that way: a brush past, a slip off, a hand landing and immediately leaving, a foot grazing on the way to another target |
| `unknown` | The frames do not let you distinguish the two |

Evidence that supports `intentional_use`:

- Body weight visibly shifts onto or against the contact.
- The limb stays in contact while another limb moves.
- The contact is part of establishing the next stable configuration.

Evidence that does **not** support it:

- The hand or foot is near the hold.
- The hold belongs to the problem.
- The climber's other limbs suggest they "should" be using it.

**Do not infer load.** Load is not observable from a single RGB view; that is why this
distinction is a human judgement with an explicit `unknown` escape rather than a model output.
If you find yourself reasoning about how much force a limb "must" be taking, you have left the
evidence and the answer is `unknown`.

---

## 2. `occluded` vs `out_of_frame` vs `unlabeled`

| Label | Apply when |
| --- | --- |
| `visible` | You can directly see the joint or contact |
| `occluded` | It is **inside the image bounds** but hidden: behind the climber's own body, behind a volume, behind a hold, behind another object, or lost in motion blur or shadow to the point of not being locatable |
| `out_of_frame` | It is **outside the image bounds** |
| `unlabeled` | **No one has looked yet.** |

`occluded` and `out_of_frame` are statements about the world. `unlabeled` is a statement about
the dataset: it means the annotation pass has not reached this item. **Never use `unlabeled` to
mean "I could not tell"** - that is `occluded` (if hidden) or `unknown` (for a contact
question).

Borderline: a limb partly at the image edge. If the **joint or contact point being labelled** is
outside the bounds, it is `out_of_frame`, even if the rest of the limb is visible.

---

## 3. Bounding a contact interval

Intervals are **half-open: `[start_us, end_us)`**.

| Boundary | Rule |
| --- | --- |
| `start_us` | The timestamp of the **first frame in which contact is established** |
| `end_us` | The timestamp of the **first frame in which contact is no longer present** |

The end frame is therefore **not** part of the interval. Two consecutive contacts of the same
limb share a boundary value: the first ends at exactly the timestamp the second begins, with no
gap and no overlap.

- Use the **recorded presentation timestamp** of the frame. Do not compute a time from a frame
  number (`mvp-contract.md` Section 3).
- If the frames do not let you place a boundary within tolerance, mark the boundary uncertain
  rather than picking the visually pleasing frame.
- If contact **begins before the recording starts** or **ends after it stops**, say so with the
  interval's boundary marked as unobserved. Do not clamp silently to the recording bounds; a
  clamped boundary looks like a measured one.
- If the limb becomes `occluded` mid-contact, the contact does **not** end. Occlusion is a
  visibility label on the observation, not a termination of the interval.

---

## 4. Attempt boundaries

| Boundary | Rule |
| --- | --- |
| Start | The frame at which the climber has established the problem's **starting contact configuration** and is supported by the wall |
| End | The **first** of: completion, unrecovered loss of contact, deliberate release, or disengagement |

- **A recording is not an attempt.** Mark every attempt in the recording separately.
- The time between attempts (resting, chalking, walking away, discussing) belongs to **no
  attempt**. Do not stretch an attempt to cover it.
- A start that is ambiguous because the climber adjusts on the start holds repeatedly: the
  attempt begins when the starting configuration is **established and held**, not at the first
  touch.
- If the recording begins with the climber already on the wall, the attempt start is
  **unobserved**. Mark it as such; do not use the first frame as the start.

---

## 5. Recording an outcome

| Outcome | Apply when |
| --- | --- |
| `send` | The problem was completed under its confirmed conditions, and you can see it |
| `fall` | Unrecovered loss of contact before completion |
| `controlled_drop` | The climber deliberately released and descended under control |
| `aborted` | The attempt ended without a fall and without completion |
| `unknown` | The recording does not show you which of the above happened |

`unknown` is used more often than annotators expect. Use it when:

- The recording **cuts before the top**. This is `unknown`, **not** `fall`.
- The camera loses the climber at the decisive moment.
- You cannot tell a `fall` from a `controlled_drop` because the release is occluded or too fast.
- The problem's completion condition (a confirmed top hold, a matched finish) is not visible.

Distinguishing `fall` from `controlled_drop` is a judgement about control, not about height or
speed. If the climber's release looks deliberate and the descent is managed, it is a
`controlled_drop`. If you are unsure, it is `unknown`.

---

## 6. Adjudication

When two annotators disagree, the disagreement is **resolved into an adjudicated ground truth
with its own provenance.**

| Rule | Detail |
| --- | --- |
| Never silently overwrite | The original annotations are retained. An adjudication is a new record, not an edit of an existing one. |
| Separate provenance class | The result carries `adjudicated_ground_truth`, distinct from `reviewed_annotation` (`mvp-contract.md` Section 10). |
| Corrections are append-only | A correction is recorded as a `CorrectionEvent` (Stage 2), never as a mutation. |
| Disagreement is data | The rate and location of disagreements measure ontology quality. Erasing disagreements destroys that signal. |
| `unknown` is a valid adjudication | If two annotators disagree and the evidence does not decide it, the adjudicated value is `unknown`. Adjudication does not mean picking a winner. |

Inter-annotator agreement targets are `[PILOT]`: they will be set on Stage 2 validation data and
do not exist yet.

---

## 7. CVAT

CVAT is an **import/export adapter, not the domain model.** The internal schema
([`data-schema.md`](data-schema.md)) is the source of truth.

| Implication | Detail |
| --- | --- |
| CVAT fields **map onto** internal entities | Shapes, tracks and attributes are translated on import and export |
| No CVAT concept leaks inward | A CVAT-specific notion never becomes an internal field |
| No internal concept is dropped | If CVAT lacks a field, it is carried alongside, not discarded |
| Round-trip is tested | Export then import must preserve the internal record |

If a label cannot be expressed in CVAT, that is a limitation of the tool to be worked around in
the adapter. It is **not** a reason to change the ontology.
