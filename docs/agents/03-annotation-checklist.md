# Annotation Checklist

Work the sections in this order. A section is finished when its **Done when** line is true.
Decision rules for individual labels: [`../annotation-guide.md`](../annotation-guide.md).
Why the plan looks like this: [`00-operating-manual.md`](00-operating-manual.md) Section 5.

---

## A. Setup

1. Annotation tool running (deployment: decision `annotation-tooling-deployment`).
2. Hand-label two attempts `[PLANNING]`.
3. Export them, import the export back, export again, compare the two exports byte for byte.
4. Record the export profile you used in the decision. Do not assume one from any document.

**Done when:** the export-import-export round trip is byte-stable on both attempts, demonstrated,
before any labelling at volume.

---

## B. Board definition — once per board type and set version

No polygons are traced on this envelope. Hold positions come from this file instead.

1. Enter the grid: **11 columns by 18 rows** `[FIXED]`, and every occupied grid position.
2. Enter the panel's physical geometry and the board's angle.
3. **Every physical number names its source and its date** - the board's published specification, or
   your own tape measure. A number from memory, yours or an agent's, does not go in the file
   (decision `board-geometry-source`).
4. Do not assign hold numbers. **The grid coordinate is the identity**, so nothing can renumber the
   board when something is corrected later.
5. Know that a grid position is a **point**. How far around it counts as the hold is a separate
   configured number, not something to eyeball while entering the grid (decision
   `hold-extent-model`).
6. Version the file. Any change to any number is a new version, and the session logs name the
   version they were shot under.

**Done when:** the definition exists, is versioned, covers every hold on the panel, and every
physical number in it carries a source and a date.

---

## C. Lit-hold set — per problem

The role names below are a labelling vocabulary. They are not one of the contract's closed value
sets (contract Section 5).

1. Read the problem's lit holds off the board, or off the identity photo from the session.
2. Enter them as grid coordinates: about **8 to 15** `[PLANNING]` per problem.
3. For each one, record its role: `start`, `intermediate` or `finish`.
4. Type them in. **Do not fetch a problem from any service**; no such interface is assumed to exist
   here (decision `lit-hold-entry-and-import`).
5. The foot-only flag does not apply on a board, which places no constraint on feet. It stays in the
   vocabulary for general walls.

**Done when:** every filmed problem has its lit-hold set, with at least one start role and at least
one finish role.

---

## D. Calibration picks — per session

1. Open that session's empty-board reference still as an image task.
2. Click about **six hold centres** `[PILOT]` and name each one by its **grid coordinate** (count
   and layout: decision `fiducial-layout-policy`).
3. Check the picks: well spread across the panel, **including near the top**, where foreshortening
   is worst, and **not nearly in a line**. Coplanarity is given by the panel - the only way to break
   it is to click something that is not the board.
4. **No tape measure.** Physical scale comes from the board definition (wall unit and scale:
   decision `wall-plane-units-and-scale`).

**Done when:** every session has its picks and the calibration overlay shows short residual lines.

---

## E. Attempt boundaries and outcomes — per recording

1. Mark each attempt's start and end (annotation guide Section 4).
2. Flag every boundary that was not observed.
3. Record the outcome from the closed set (contract Section 5), using `unknown` where the
   recording does not decide it (annotation guide Section 5).

**Done when:** every recording has its attempts marked, including the recordings that contain none.

---

## F. Contact intervals — per attempt, two tracks

1. One track per hand: left hand, right hand. **Feet are not tracked** in the MVP (contract
   Section 5, decision `hands-first-scope`).
2. Mark each contact interval as **half-open** `[start_us, end_us)`.
3. On each interval record: target kind from the contract's closed set; the hold number where the
   target is a hold; the contact label; the visibility; the boundary-uncertain flag.
4. The target is one of: a `hold` - normally one of this problem's lit holds, occasionally another
   hold on the panel; `wall_region` for bare board surface; `none`; `unknown`. `volume` does not
   arise on a flat panel.
5. An **occluded hand is never marked as not in contact.** The board is an overhang, so the
   climber's own body hides the hold they are using more often than on a vertical wall. `occluded`
   will be common. Use it.
6. **A foot carries no prediction, so a foot is `unknown` - never `none`.** Not attempted is not
   the same as not in contact, and writing `none` there corrupts the dataset permanently.

**Done when:** both hands are covered for the attempt's full span, with no unlabelled gaps.

---

## G. Keypoint gold set

1. Run the seeded frame-selection script. Label the frames it selects, and only those.
2. Label the canonical points on each extracted frame (point set: decision `canonical-keypoint-set`).
3. Give every point its own visibility value.
4. Do not skip a frame because it is hard (manual 5.5). Label it, or mark its points `occluded`
   or `out_of_frame`. Expect to do that more often than on a vertical wall: on an overhang the
   climber's body sits between the camera and their own hands.

**Done when:** every frame on the selected list is fully labelled.

---

## H. Independent beta — per selected attempt

1. Watch the video.
2. Write the attach and release token sequence by hand.
3. Keep every pipeline output closed while doing it.

**Done when:** a hand-written token file exists for each selected attempt.

---

## I. Blind self-agreement re-label

1. Wait at least seven days `[PLANNING]` after the first pass.
2. Hide the first pass.
3. Re-label the selected subset (subset size and gap: decision `agreement-measurement-design`).
4. Do not consult the first pass at any point.
5. Report the result as `self_agreement`. Never as inter-annotator agreement.

This covers the **contact intervals**. There is no equivalent pass for holds on this envelope:
nothing is traced, so hold-polygon self-agreement has no input and is reported `not_applicable`
with its reason (manual 2.1, item 18).

**Done when:** the subset is fully re-labelled and both passes are retained.

---

## Quality rules

Keep these visible while labelling.

- Answer `unknown` rather than guessing.
- `occluded` is not "not in contact".
- A guessed label is indistinguishable from an observation once it is written down.
- Never edit an old label so that it agrees with a new one.
