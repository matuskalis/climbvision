# Model Registry

Every model that is downloaded, trained, fine-tuned or bundled must be registered here **before
it is used**. Status tags as defined in [`mvp-contract.md`](mvp-contract.md).

---

## 1. Required fields

An entry without all seven fields is not a registered model and may not be used.

| Field | Meaning |
| --- | --- |
| Source | Where the weights and code came from: repository, release, URL |
| Version | The exact release or commit, not a branch name |
| Weights checksum | SHA-256 of the checkpoint file. A filename is not an identity. |
| Code license | License of the inference code |
| Checkpoint license | License of the **weights**, which is frequently different and frequently more restrictive |
| Known training datasets | What the model was trained on, including datasets inherited from a pretrained backbone |
| Intended use | What it may be used for in ClimbVision, and at which stage |

## 2. Policy

| Rule | Detail |
| --- | --- |
| **No model without a full entry** | No download, no training, no bundling until all seven fields are recorded. |
| **No pretrained model is ground truth** | A generic pretrained model is **never** accepted as ground truth for contacts. Its output is a `prediction` or, after human review, a `preannotation`. Ground truth comes from adjudicated human annotation (`mvp-contract.md` Section 10). |
| **No silent fallback** | A production adapter must **never** silently fall back to synthetic, stubbed, random or fake predictions when a model is missing or fails. It fails loudly or returns `abstained`. A fake prediction is indistinguishable from a real one downstream. |
| **Weights are never committed** | Enforced by `.gitignore` (`weights/`, `checkpoints/`, `*.pt`, `*.pth`, `*.onnx`, `*.safetensors`). |
| Checkpoint identity is recorded per run | Model/checkpoint ID and checksum are provenance fields on every analysis run (`data-schema.md` Section 5). |

### LLM and VLM boundary

An LLM or VLM **may not be the telemetry engine** (`mvp-contract.md` Section 2). Specifically:

| May | May not |
| --- | --- |
| Phrase observations that have **already been computed** by the pipeline | Generate contacts, intervals, moves, beta tokens or metric values |
| Cite the **source telemetry IDs** for every statement it makes | Produce coaching, technique advice, grades or quality judgements |
| Abstain when the telemetry does not support a statement | Fill a gap in the telemetry with a plausible sentence |

A language model's output that cannot be traced to a telemetry ID is not shippable.

---

## 3. Current contents

**Zero models.** No model has been downloaded, trained, benchmarked, licensed or bundled.

### External tools

| Tool | Version | Role | Not |
| --- | --- | --- | --- |
| `ffprobe` (FFmpeg) | 8.0 | Container and packet metadata at the Stage 1 media boundary. Invoked as a **subprocess**. | **Never a predictor.** It reports what the container declares and nothing else. |

`ffprobe` is not a model and has no weights, but its **version is recorded as a provenance
field on every ingest run**, because its behaviour at the media boundary is version-dependent
(see `data-schema.md` Section 9).

---

## 4. Candidates for later stages - **not selected**

Every item below is a name the roadmap mentions. **None has been selected, benchmarked,
licensed or downloaded.** This list is not a plan of record and creates no commitment.

| Candidate | Possible role | Stage | Status |
| --- | --- | --- | --- |
| RTMPose / RTMW WholeBody | 2D pose with hand and foot keypoints | 4 | **Candidate only.** Not selected, not benchmarked, licenses not reviewed. |
| MediaPipe | 2D pose | 4 | **Candidate only.** Not selected, not benchmarked, licenses not reviewed. |
| RTMDet-Ins or similar | Hold instance segmentation | 3 | **Candidate only.** Not selected, not benchmarked, licenses not reviewed. |

Conditions attached to these candidates:

- **Pose (Stage 4)** will be chosen by an **ADR**, and benchmarked on the **ClimbVision gold
  set** - not by published generic COCO AP. Generic benchmark numbers do not describe
  performance on an occluded, extremely-posed climber against a textured wall, which is the only
  case ClimbVision cares about. Endpoint PCK for palm and toe anchors is the deciding metric
  (`evaluation.md` Section 1).
- **Hold segmentation (Stage 3)** would be **assistive preannotation only**, behind a **license
  decision**. Hold maps are user-confirmed by contract; a segmentation model proposes, a human
  confirms.
- No accuracy figure for any candidate appears in this repository. Any that later does will be
  a measurement on the ClimbVision gold set, tagged and dated.
