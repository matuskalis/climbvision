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

## B. Hold polygons — per facet

1. Open that facet's clean reference still as an image task.
2. Trace **every hold on the facet**, not only the holds that are on a problem.
3. Outline the **graspable surface**.
4. Give each polygon a stable, human-assigned hold number.
5. Set the on-volume flag on each polygon.
6. Trace volumes as **separate instances**.

**Done when:** every hold on the facet has one polygon, and every polygon has a unique hold number.

---

## C. Problem membership — per problem

The role names below are a labelling vocabulary. They are not one of the contract's closed value
sets (contract Section 5).

1. For each hold on the problem, record its role: `start`, `intermediate` or `finish`.
2. Set the foot-only flag on holds the problem restricts to feet. A start hold and a start foot are
   both role `start`; the foot-only flag is the only thing that separates them.

**Done when:** every problem has at least one start role and at least one finish role.

---

## D. Wall fiducials — per facet

1. Place six to ten `[PLANNING]` point shapes on identifiable wall features (count and layout:
   decision `fiducial-layout-policy`).
2. Check the points: coplanar, well spread, **not on volumes**, and **not nearly in a line**.
3. Write the fiducial file, giving each point's wall coordinates in millimetres from any origin
   (wall unit and scale: decision `wall-plane-units-and-scale`).
4. Tape-measure the distance between two identifiable points and record it.

**Done when:** the fiducial file exists and the calibration overlay shows short residual lines.

---

## E. Attempt boundaries and outcomes — per recording

1. Mark each attempt's start and end (annotation guide Section 4).
2. Flag every boundary that was not observed.
3. Record the outcome from the closed set (contract Section 5), using `unknown` where the
   recording does not decide it (annotation guide Section 5).

**Done when:** every recording has its attempts marked, including the recordings that contain none.

---

## F. Contact intervals — per attempt, four tracks

1. One track per limb: left hand, right hand, left foot, right foot.
2. Mark each contact interval as **half-open** `[start_us, end_us)`.
3. On each interval record: target kind; the hold number where the target is a hold; the contact
   label; the visibility; the boundary-uncertain flag.
4. An **occluded limb is never marked as not in contact**.

**Done when:** all four limbs are covered for the attempt's full span, with no unlabelled gaps.

---

## G. Keypoint gold set

1. Run the seeded frame-selection script. Label the frames it selects, and only those.
2. Label the canonical points on each extracted frame (point set: decision `canonical-keypoint-set`).
3. Give every point its own visibility value.
4. Do not skip a frame because it is hard (manual 5.5). Label it, or mark its points `occluded`
   or `out_of_frame`.

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

**Done when:** the subset is fully re-labelled and both passes are retained.

---

## Quality rules

Keep these visible while labelling.

- Answer `unknown` rather than guessing.
- `occluded` is not "not in contact".
- A guessed label is indistinguishable from an observation once it is written down.
- Never edit an old label so that it agrees with a new one.
