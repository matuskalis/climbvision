# ClimbVision

Computer-vision telemetry for indoor bouldering. It measures what a camera can observe about a
climb and records where every number came from. It is not a coach: no grades, no scores, no
generated advice.

**What exists today is Stage 1 of 8, ingest.** A video file becomes a content-addressed manifest,
a frame-timing index and an append-only run record, all linked by hash. Pose, hold maps and
contact intervals are specified in detail and not started. There is no model in this repository
and no accuracy number. Those two facts are related.

![Twenty-seven frames of a synthetic variable-frame-rate clip drawn twice, once at the container's timestamps and once at frame number divided by the average frame rate, disagreeing by up to 119 ms. Below it, the four quality flags and the hashes the run wrote.](docs/img/hero.svg)

One real ingest of `tests/fixtures/video/vfr_160x120_2s.mp4`, a synthetic clip with frames dropped
on purpose. The figure is drawn from the files the run wrote, after re-hashing them against the
run record. `uv run python scripts/render_hero.py` regenerates it byte for byte.

## Try it

Python 3.11 or newer, [uv](https://docs.astral.sh/uv/), and `ffprobe` from FFmpeg on your `PATH`
(`brew install ffmpeg` or `apt install ffmpeg`; the fixtures were captured with 8.0). No footage is
needed: the repository ships five small synthetic clips.

```console
$ uv sync
$ uv run climbvision ingest tests/fixtures/video/vfr_160x120_2s.mp4 --out artifacts
sha256-a303e1847f4c0554f902b23819c6a5f1c398421adaf1183952b7c5d063ab5ace
$ uv run climbvision validate artifacts/recordings/sha256-a303*/recording.json
ok: recording.json: climbvision.recording
```

The identifier is the SHA-256 of the file's bytes. Copy the clip under another name and ingest it
again: same identifier, a manifest with the same digest, and one more run record.

```console
$ cp tests/fixtures/video/vfr_160x120_2s.mp4 my_boulder_attempt.mp4
$ uv run climbvision ingest my_boulder_attempt.mp4 --out artifacts
sha256-a303e1847f4c0554f902b23819c6a5f1c398421adaf1183952b7c5d063ab5ace
$ shasum -a 256 artifacts/recordings/sha256-a303*/recording.json | cut -c1-64
883cd1a6e028a723276809af4cfd07b7372555a58343aac58b3ea3a4868ece17
```

That digest is what ffprobe 8.0 gives; another ffprobe may report other container details.

## What a run leaves behind

```
artifacts/recordings/<asset_id>/
  recording.json                    what the file is: container, stream, duration, quality flags
  frame_index.json                  one row per video packet: PTS, DTS, duration, in container ticks
  runs/
    <run_id>.json                   this execution: tool versions, config hash, git commit, hashes of the rest
    <run_id>.probe.streams.raw.json ffprobe's answer, verbatim
    <run_id>.probe.packets.raw.json ffprobe's answer, verbatim
```

Every re-ingest adds a `runs/` triple and leaves the two files above it alone. The quality block
of `recording.json` for the clip in the figure (an excerpt of the real file):

```json
{"flag": "variable_frame_rate", "status": "fail",
 "measurement": {"avg_frame_rate": "810/59", "distinct_pts_delta_count": 2, "r_frame_rate": "30/1"},
 "threshold": {"max_distinct_pts_delta_count": 1}}
```

Out-of-envelope input is flagged, not rejected: this clip fails three of four checks and ingest
still exits 0. Malformed input (no video stream, no time base, no packets, a file ffprobe cannot
read) is a hard failure. [`docs/data-model.md`](docs/data-model.md) walks through every document
and where each field comes from.

## The provenance model

The project's one rule: every output must be traceable to pixels, a human annotation, a named
model, a deterministic derivation, or a measured aggregate. Nothing else may be emitted.

At Stage 1 that is concrete. Every value in the manifest is one of: the bytes of the file (hashed),
what ffprobe reported (kept verbatim), integer arithmetic over those, a threshold from versioned
config, or an explicit `null`. The run record says what produced it and pins everything by hash:

| The run record holds | So you can answer |
| --- | --- |
| `asset_id`, `manifest_sha256` | which bytes went in, and exactly which manifest came out |
| `probe_streams_sha256`, `probe_packets_sha256`, and the `argv` behind each | what ffprobe said, and how it was asked |
| `ffprobe_version`, `python_version`, `climbvision_version` | what ran |
| `config_version`, `config_sha256` | which thresholds judged the file |
| `git_commit`, `git_dirty` (or `null` when not run from a checkout) | which code |

Thresholds carry a unit, a status tag (`[FIXED]`, `[PILOT]`, `[PLANNING]`) and a sentence on how
the number was chosen. An untagged number is a defect. Later stages add five provenance classes
(prediction, preannotation, reviewed annotation, adjudicated ground truth, derived) that are never
merged into one field; none of them exists in code yet.

## Three decisions, and what they cost

**1. Time is what the container says, never frame number over frame rate.** Each packet's
presentation timestamp is stored as an integer tick count beside the stream's time base exactly as
declared (`1/15360` here). Microseconds are derived with integer arithmetic, rounding half away
from zero, and never replace the ticks. The figure is the reason: on this deliberately extreme
clip, `frame_number / avg_frame_rate` puts frame 24 some 119 ms from where the container has it.
*Cost:* every consumer carries (ticks, time base) pairs instead of a frame counter, and a file with
no timestamps at all (a raw H.264 stream, one of the fixtures) is flagged `timestamps_absent` and
left that way. Ingest reads packets without decoding and never asks ffprobe for a derived,
best-effort timestamp, because a guessed timestamp is indistinguishable from a measured one once
written.

**2. Unknown is a value, not a default.** A packet with no PTS stores `null`, never `0`. A check
that cannot run says `unknown`, not `fail`: with timestamps on only some packets, the
variable-frame-rate check abstains instead of measuring across the hole. A rotation that is present
but unreadable is recorded as unreadable, not as no rotation. *Cost:* every field is nullable,
quality checks are three-valued instead of pass or fail, and every later stage has to branch on
`unknown`. That is the price of never turning missing data into a negative label.

**3. The manifest is a function of the file's bytes, the config and the code. Nothing that varies
per run goes in it. Runs are receipts.** `recording.json` is canonical JSON (sorted keys, no
floats, explicit nulls) and is byte-identical on every re-ingest of the same bytes, under any
filename. Everything that varies (run id, time, filename, tool versions, git commit, the raw
ffprobe output) goes into a new run record that points at the manifest by hash, never the
reverse. If a config or schema change would make the manifest differ, ingest stops with
`MANIFEST_CONFLICT` instead of overwriting bytes that earlier run records vouch for. *Cost:* a
manifest cannot be upgraded in place (ingest into a new `--out`), and raw probe output is kept on
every run: for a 60 s, 1,800-frame 1080p clip each re-ingest adds 239 KB, most of it the packet
list.

## Measured

| Check | Result | Command |
| --- | --- | --- |
| Tests | 423 passed, 22 s on an M1 Pro | `uv run pytest` |
| Tests, `ffprobe` absent from `PATH` | 372 passed, 51 skipped: the tests that need it skip, they do not fail | `uv run pytest -rs` |
| Line coverage | 96 % of 572 statements | `uv run --with pytest-cov pytest --cov=climbvision` |
| Lint, format, types | clean | `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` |
| Python | 3.11.14 and 3.14.7 both pass | `uv run --python 3.14 pytest` |
| A 60 s, 1080p, 30 fps synthetic clip (1,800 frames, 21.6 MB) | ingest in 0.7 to 1.1 s, all four quality flags `ok`, 273 KB of artifacts | see below |

The 1080p clip is not committed. This makes it:

```bash
ffmpeg -f lavfi -i testsrc2=size=1920x1080:rate=30:duration=60 \
  -c:v libx264 -preset ultrafast -crf 40 -pix_fmt yuv420p clip.mp4
```

These are timings and sizes of the ingest stage on synthetic input. They say nothing about
climbing, because nothing here sees a climber yet.

CI runs these checks on every pull request and every push to `main`:
[`ci.yml`](.github/workflows/ci.yml).

## Status and limits

| Stage | State |
| --- | --- |
| 0 - Frozen contract and documentation | complete |
| 1 - Deterministic ingest: video to content-addressed manifest | complete |
| 2 - Annotation harness, CVAT adapter, group-aware split manifests | not started |
| 3 - Wall calibration and confirmed hold map | not started |
| 4 - Climber pose trajectories | not started |
| 5 - Limb-hold contact intervals and stable contact-state transitions | not started |
| 6 - Attempts, moves, beta sequences, fall events | not started |
| 7 - Descriptive aggregates | not started |
| 8 - Minimal application surface | not started |

- **No footage, no pose, no accuracy.** The fixtures prove the code runs. They cannot show that it
  can see a climber.
- **Work is paused at Stage 1.** Every later gate needs footage that only the owner can film, and
  the filming protocol was written before a one-clip feasibility check. The reasoning and the four
  routes to unblock it are in [`docs/status.md`](docs/status.md#work-stopped-2026-09-05).
- **Runs from a checkout.** The ingest config is read from `configs/` next to `src/`, and the wheel
  does not bundle it: an installed copy stops with `CONFIG_NOT_READABLE`.
- **Known defect.** Portrait footage whose rotation is baked into the pixels has its width and
  height transposed by the resolution check, so it gets a resolution `fail` that the same pixels in
  landscape would not. It is scheduled as Stage 2's first task; until then, film in landscape.
- **Thresholds are the contract's, not tuned.** 1920x1080 and 30 fps are `[FIXED]` from the
  envelope. Whether that is enough to resolve a hand on a hold is unmeasured.

## What it is and is not

| ClimbVision is | ClimbVision is not |
| --- | --- |
| A telemetry system: intervals, counts, durations, sequences | An AI coach or a text generator |
| Provenance-first: every value names its source | A grade predictor |
| Deterministic where determinism is possible | A technique, efficiency or quality scorer |
| Explicit about uncertainty (`unknown`, `abstained`, `insufficient_data`) | A 3D biomechanics or force/load estimator |
| Offline batch processing | A mobile app or a distributed service |

## Operating envelope

One climber in frame `[FIXED]`, indoor bouldering, one static phone camera, the full body and the
full problem visible throughout, at least 1080p `[FIXED]` and 30 fps `[FIXED]`, one roughly planar
wall facet with a user-confirmed hold map. The first numbers are to be measured on a smaller
envelope, a standardized LED training board, and the MVP predicts hand contacts only. The reasons,
and what each choice costs, are in [`docs/mvp-contract.md`](docs/mvp-contract.md) Sections 1 and 5.

## Roadmap

Stages 2 through 8 do not exist. This is what they would be, in order. A stage does not start
until the previous gate is measured and reported in [`docs/status.md`](docs/status.md).

| Stage | Delivers | Constraint that keeps this telemetry, not coaching |
| --- | --- | --- |
| 2 | Annotation harness, CVAT adapter, group-aware split manifests | CVAT is an **adapter**; the internal schema stays the source of truth. Splits are frozen and leakage is **tested, not assumed**. With a single annotator the agreement target is blind intra-annotator test-retest, reported as `self_agreement`. |
| 3 | Wall calibration and the confirmed hold map | Manual hold polygons and explicit problem membership **first**. Automatic segmentation only as assistive preannotation behind a model adapter. On the first envelope, positions come from a versioned board definition. |
| 4 | Climber pose trajectories | **One** pretrained backend, chosen by an ADR and benchmarked on the project's own gold set, not by generic COCO AP. Raw keypoints and visibility stored **before** any filtering. |
| 5 | Limb-hold contact intervals and stable contact-state transitions | An interpretable geometry and temporal baseline **before** any learned model. Hands and feet are separate slices; feet are `not_applicable` on the first envelope. |
| 6 | Attempts, moves, beta sequences, fall events, comparison of two attempts | Moves are **derived from contact transitions**. No generated coaching text. |
| 7 | Repeated-attempt descriptive analytics | Only metrics derived from validated primitives. Returns `insufficient_data` when support is inadequate. |
| 8 | Upload and job API, web review timeline, correction workflow, consent and retention controls | Only after the telemetry gates pass. No mobile app until real web usage validates the workflow. |

## Documentation

| Document | Contents |
| --- | --- |
| [`docs/data-model.md`](docs/data-model.md) | The four documents Stage 1 writes, how they point at each other, and the source of every field |
| [`docs/mvp-contract.md`](docs/mvp-contract.md) | The frozen contract: envelope, out-of-scope list, ontology, definitions, privacy boundary, acceptance gates |
| [`docs/data-schema.md`](docs/data-schema.md) | Canonical entities, field tables, identity and serialization rules, the ingest protocol |
| [`docs/annotation-guide.md`](docs/annotation-guide.md) | Human decision rules for annotators |
| [`docs/evaluation.md`](docs/evaluation.md) | Metric definitions, split and leakage policy, the Stage 1 gate |
| [`docs/model-registry.md`](docs/model-registry.md) | Model policy and current contents (zero models) |
| [`docs/status.md`](docs/status.md) | Stage ledger with measured evidence |
| [`AGENTS.md`](AGENTS.md) | Operating rules for coding agents |
| [`docs/agents/`](docs/agents/) | The operating manual and one brief per remaining stage |

## Privacy

No real user video, faces, consent records or model weights are stored here. A path-scoped
`.gitignore` enforces that boundary, not good intentions. Participants appear only as pseudonyms,
consent records are referenced by opaque ID, and test fixtures are synthetic and contain no people.
