# docs/agents

How this project is actually run. `AGENTS.md` at the repository root holds the binding rules for
coding agents; this directory holds the owner's side of the work and the per-stage briefs.

| File | Open it when |
| --- | --- |
| [`00-operating-manual.md`](00-operating-manual.md) | First, and again whenever you lose the thread. How one person who does not read code gets this system built without being lied to by an agent. |
| [`01-prompt-templates.md`](01-prompt-templates.md) | You are about to open a stage, challenge a reported result, or record a decision. Templates T1 through T6, copy-paste. |
| [`02-session-checklist.md`](02-session-checklist.md) | You are packing for the gym, standing at the wall, or sitting down the same evening to ingest. |
| [`03-annotation-checklist.md`](03-annotation-checklist.md) | You are about to label holds, attempts, contacts or keypoints. |
| [`04-consent-and-privacy.md`](04-consent-and-privacy.md) | Before the first frame is shot, and before any pixel leaves your machine. |
| [`05-verification-commands.md`](05-verification-commands.md) | An agent has just reported done. Run this before you believe it. |
| [`briefs/`](briefs/) | A stage is about to open. Seven briefs, one per stage, Stage 2 through Stage 8. Read only the brief for the stage you are opening. |

## Decision index

Decisions only the owner can make. Each is recorded as its own file under `docs/adr/` **at the
moment it is made, one at a time**. Decision records are never pre-stubbed: an empty record is
indistinguishable from a decided one, and a directory of placeholders is a directory of lies.
The briefs and the manual refer to decisions **by slug**, never by number, so no numbering has to
be reserved in advance. Detail on the earliest and most consequential ones is in
[`00-operating-manual.md`](00-operating-manual.md) Section 9.

| Slug | Needed by | Status |
| --- | --- | --- |
| `second-participant` | Before filming (Stage 2 data) | open |
| `capture-settings` | Before filming (Stage 2 data) | open |
| `retention-policy` | Before filming; enforced at Stage 8 | open |
| `audio-handling` | Before filming; release policy at Stage 2 | open |
| `annotation-tooling-deployment` | Stage 2 | open |
| `annotation-storage-and-release-commit-policy` | Stage 2 | open |
| `single-participant-split-policy` | Stage 2 | open |
| `split-names-and-proportions` | Stage 2 | open |
| `test-set-evaluation-policy` | Stage 2 | open |
| `agreement-measurement-design` | Stage 2 | open |
| `labeling-tier` | Stage 2 | open |
| `wall-plane-units-and-scale` | Stage 3 | open |
| `fiducial-layout-policy` | Stage 3 | open |
| `hold-segmentation-model` | Stage 3 | open |
| `pose-backend-selection` | Stage 4 | open |
| `canonical-keypoint-set` | Stage 4 | open |
| `pck-normalization-scale` | Stage 4 | open |
| `dense-trajectory-storage-format` | Stage 4 | open |
| `contact-membership-space` | Stage 5 | open |
| `contact-target-scope` | Stage 5 | open |
| `contact-threshold-selection-protocol` | Stage 5 | open |
| `outcome-derivation-boundary` | Stage 6 | open |
| `beta-token-grammar` | Stage 6 | open |
| `crux-rule` | Stage 7 | open |
| `uncertainty-method-and-support-threshold` | Stage 7 | open |
| `application-stack` | Stage 8 | open |
| `application-auth-model` | Stage 8 | open |
| `application-storage-root` | Stage 8 | open |
