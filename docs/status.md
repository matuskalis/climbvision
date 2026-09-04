# Status

Stage ledger. Status tags as defined in [`mvp-contract.md`](mvp-contract.md).

**How this file is maintained.** Updated at the end of every stage with **measured evidence
only, never with expectations.** A gate that has not been measured reads `pending measurement`.
No number is written here before it is observed. Numbers in a "measured evidence" column are
observations, not thresholds, and so carry no status tag; thresholds keep theirs.

---

## Stage ledger

| Stage | Scope | Status | Gate evidence |
| --- | --- | --- | --- |
| 0 | Frozen contract and documentation | **complete** | The seven Stage 0 documents exist: `README.md`, `docs/mvp-contract.md`, `docs/data-schema.md`, `docs/annotation-guide.md`, `docs/evaluation.md`, `docs/model-registry.md`, `docs/status.md` |
| 1 | Deterministic ingest: video to content-addressed manifest | **complete** | All four clauses measured and passing; see the Stage 1 table below. Code review verified every clause by **independent measurement** rather than by accepting the implementation's report, and passed on the second pass with zero new findings. The first pass found two defects, both closed at the root before approval: a fabricated frame-rate delta computed across a timestamp gap, and a content-addressed manifest that could be silently overwritten out from under the run record attesting to it. |
| 2 | Annotation harness, CVAT adapter, group-aware split manifests | not started | - |
| 3 | Wall calibration and confirmed hold map | not started | - |
| 4 | Climber pose trajectories | not started | - |
| 5 | Limb-hold contact intervals and stable contact-state transitions | not started | - |
| 6 | Attempts, moves, beta sequences, fall events | not started | - |
| 7 | Descriptive aggregates | not started | - |
| 8 | Minimal application surface: upload/job API, web review timeline, correction workflow, repeated-attempt comparison as a view over Stage 6 and 7 output, consent and retention controls | not started | - |

Stages 2 through 8 have **not started**. No code, no data, no annotations and no models exist
for them. Their acceptance gates are in `mvp-contract.md` Section 9: `[PILOT]` targets for
Stages 2 through 7, and a workflow gate for Stage 8.

---

## Stage 1 gate (measured, review passed)

The gate is defined in `evaluation.md` Section 4. All four clauses pass.

| Clause | Assertion | Measured evidence |
| --- | --- | --- |
| Tests and lint | All tests pass, `ruff` passes | `uv run pytest` -> 423 passed. `uv run ruff check .` -> All checks passed. |
| Schema round-trip | `model == parse(dump(model))` | Passes |
| Schema round-trip | `dump(parse(dump(model))) == dump(model)` byte-for-byte | Passes, byte-identical re-serialization |
| Idempotent ingest | Same asset ID on re-ingest | Passes. `sha256-de7ab859…` (abbreviated) across two ingests, and across a byte-identical copy under a **different filename**. |
| Idempotent ingest | Byte-identical manifest on re-ingest | Passes, including the different-filename copy |
| Idempotent ingest | A second append-only run record is added | Passes. Each ingest appends its own run record. |
| Timestamp round-trip | `max_roundtrip_error_ticks == 0` `[FIXED]` | 0 on all four fixtures that carry PTS |
| Timestamp round-trip | `max_roundtrip_error_us <=` smallest per-packet duration in microseconds `[FIXED]` | 0, against `min_packet_duration_us = 33333` taken from each packet's own duration in ticks. The gate asserts the measured `== 0` on these fixtures rather than the looser bound; the weaker general guarantee is tested separately on adversarial values, so this table's claim and the test assertion cannot drift apart. |

Supporting facts:

| Item | Value |
| --- | --- |
| Fixtures exercising the lossless branch (time base denominator at most `1000000` `[FIXED]`) | `cfr_320x240_30fps_1s.mp4`, `vfr_160x120_2s.mp4`, `rot90_160x120_1s.mp4`, at `time_base 1/15360` |
| Fixture exercising the bounded branch (larger denominator) | `hi_timescale_160x120_1s.mp4` at `time_base 1/1200000`. Measured error 0 in both ticks and microseconds, so the bound was not binding on this fixture. |
| Fixture with no PTS at all | A raw `.h264` elementary stream, recorded as the **absent-timestamp abstention case**, explicitly **not** as timestamp evidence |
| Fixtures exercising decode-order reordering (`decode_order_differs`) | `true` for `cfr_320x240_30fps_1s.mp4` and `vfr_160x120_2s.mp4`; `false` for `rot90_160x120_1s.mp4`, `hi_timescale_160x120_1s.mp4` and `raw_160x120_1s.h264` (the last carries no PTS at all, so there is no ordering to differ). All four mp4 fixtures report `has_b_frames=2` from ffprobe, but only two actually present packets out of presentation order: a declared B-frame count is not itself evidence of reordering. The reordering path is therefore exercised by real committed fixtures, not only by synthetic unit-test input. |
| Hermetic unit suite (ffprobe absent, sockets blocked) | 372 passed, 51 skipped |
| `ffprobe` version used | 8.0 |

No value above may be filled in with an expectation, an estimate or a number from a previous
run on a different fixture set.

---

## Current repository contents

| Item | State |
| --- | --- |
| Models | **Zero.** See `docs/model-registry.md`. |
| External tools | `ffprobe` (FFmpeg) 8.0, media boundary only |
| Annotations | **None collected.** Harness is a Stage 2 deliverable. |
| Split manifests | **Do not exist.** Stage 2 deliverable. |
| Real user video, faces, consent records | **None, by contract.** See `mvp-contract.md` Section 7. |
| Test fixtures | Synthetic, containing no people |
| CLI commands that exist | `climbvision ingest`, `climbvision validate` |
| Operational documents | `AGENTS.md`, `CLAUDE.md` and `docs/agents/` (the operating manual, the checklists and the per-stage briefs). They direct how work is done and claim no results. |
| Known defects | The resolution check requires coded width at least `min_width` 1920 `[FIXED]` **and** coded height at least `min_height` 1080 `[FIXED]`, so portrait-orientation 1080p footage whose **rotation is baked into the pixels** transposes the two and is recorded as a resolution `fail`, although the same pixels in landscape pass. The fix is scheduled as **Stage 2's first task**. Workaround until then: **film in landscape.** |
