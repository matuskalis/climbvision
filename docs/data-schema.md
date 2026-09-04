# Data Schema

Status tags as defined in the preamble of [`mvp-contract.md`](mvp-contract.md): `[FIXED]`,
`[VAL]` (unused, no validation data exists), `[PILOT]`, `[PLANNING]`.

---

## 1. Canonical entities

**Only the Stage 1 entities exist in code today.** Every other row is a **documented target,
not a stub, not a placeholder class and not an empty file.** The repository does not contain a
model for an entity whose real structure is not yet known.

| Entity | Purpose | Stage introduced | In code today |
| --- | --- | --- | --- |
| `DatasetRelease` | A frozen, versioned snapshot of data plus split manifests | 2 | no |
| `ConsentRecord` | Consent for a participant's recordings; referenced by opaque ID only | 2 | no |
| `Participant` | Pseudonymous climber identity, split grouping key | 2 | no |
| `Gym` | Physical venue | 3 | no |
| `Wall` | A named wall within a gym | 3 | no |
| `WallFacet` | One approximately planar facet of a wall | 3 | no |
| `WallSet` | A revision of the holds bolted to a wall; scopes problem identity | 3 | no |
| `HoldInstance` | One physical hold or volume in a `WallSet`, with a mask | 3 | no |
| `ProblemVersion` | A problem as defined on a specific `WallSet` revision | 3 | no |
| `ProblemHold` | Membership of a `HoldInstance` in a `ProblemVersion`, with its role | 3 | no |
| `Recording` | One ingested video file and its container facts | **1** | **yes** |
| `Calibration` | Mapping from image pixels to the wall plane | 3 | no |
| `Attempt` | One engagement with a problem, per `mvp-contract.md` Section 6 | 6 | no |
| `PersonTrack` | A tracked person instance across frames | 4 | no |
| `PoseObservation` | Per-frame keypoints with per-keypoint visibility | 4 | no |
| `ContactEvent` | A limb-to-target contact interval with a contact label | 5 | no |
| `MoveEvent` | A transition between stable contact configurations | 6 | no |
| `BetaSequence` | Ordered attach/release tokens, limb-aware and limb-agnostic | 6 | no |
| `FallEvent` | Unrecovered loss of contact and the last stable configuration | 6 | no |
| `MetricValue` | One measured aggregate with its support and units | 2 | no |
| `PredictionProvenance` | The provenance block attached to any model output | 4 | no |
| `CorrectionEvent` | A human correction of a prediction or annotation, append-only | 2 | no |

**Entity introduced vs workflow exposed.** "Stage introduced" is the stage at which the **model
must exist in code**, not the stage at which a **human-facing control** exists. Read as the
second, three rows look contradictory against `mvp-contract.md` Section 9:

| Entity | Model needed at | Control or UI at |
| --- | --- | --- |
| `ConsentRecord` | 2, because a release cannot be assembled without consent status | 8, consent and retention controls |
| `Participant` | 2, because it is a split grouping key | 8, participant-facing surface |
| `CorrectionEvent` | 2, because adjudication records corrections append-only | 8, correction workflow |

`MetricValue` is at 2 for the same reason: Stage 2's own gate is a measured agreement number,
and `MetricValue` is the output type of every evaluation from Stage 2 onward.

## 2. Stage 1 entities (exist in code)

The Stage 1 models are `Recording`, `VideoStreamInfo`, `Timebase`, `FrameIndex`, `IngestRun`,
the enums `QualityFlag` and `QualityStatus`, and `QualityAssessment`.

**Naming note.** Exact field identifiers are fixed by the Pydantic models under `src/`. Where
this document is not certain of an identifier it **describes the field's meaning instead of
guessing a name.** A guessed identifier in a schema document is worse than a description,
because it will be copied.

### `Recording`

| Content | Notes |
| --- | --- |
| Asset ID | `sha256-<64 hex>` of the raw file bytes. The primary key. |
| Schema identity | `schema_id` and `schema_version`. `Recording` is at schema version 3 and the nested `FrameIndex` at version 2; every other document remains at version 1. |
| `consent_record_id` | **Nullable opaque ID.** No `ConsentRecord` model exists. |
| `participant_id` | **Nullable opaque pseudonymous ID.** No `Participant` model exists. |
| Container facts | Format/container name, duration as reported by the container, size in bytes |
| Audio presence | Whether any audio stream exists (privacy-relevant, see contract Section 7) |
| Video stream | One `VideoStreamInfo` |
| Frame index | One `FrameIndex` |
| `frame_index_sha256` | Hash of the frame index. Derives from packet PTS, **not** from the path, so it stays in the manifest. |
| Quality | One `QualityAssessment` |

**Deliberately not in the manifest: `probe_streams_sha256` and `probe_packets_sha256`.** They
hash ffprobe's raw output, which embeds the input filename, and they were the only
filename-dependent fields in the manifest: ingesting the same bytes under a different name
silently rewrote a content-addressed document. They now live only in `IngestRun`. Removing them
is a breaking change, which took `Recording` to schema version 2; making `rotation_degrees`
nullable and extending `rotation_source` took it to 3, since a version-2 reader breaks on a
`null` rotation.

`consent_record_id` and `participant_id` are opaque and nullable **on purpose.** Their real
structure is not yet known, and inventing one now would be fabricated structure that later code
would be forced to honour.

### `VideoStreamInfo`

| Content | Notes |
| --- | --- |
| Codec identity | As reported by ffprobe |
| Coded width and height in pixels | Integers |
| Time base | One `Timebase` |
| Average frame rate | `{num, den}` rational. `0/0` means **unknown**, not zero. |
| Rotation | `rotation_degrees`: **integer degrees, nullable.** `rotation_source`: one of `display_matrix`, `display_matrix_unreadable`, `tag`, `tag_unreadable`, `absent`. The two `_unreadable` values carry `rotation_degrees: null`. See Section 9. |
| Pixel format / colour metadata | As reported, verbatim |

### `Timebase`

A rational `{num, den}`, both integers, preserved exactly as the container declares it. Observed
values on this machine include `1/15360`, `1/90000` and `1/1200000`. **Never** replaced by a
derived frame rate.

### `FrameIndex`

The per-packet table for video stream 0, **sorted by presentation timestamp**. Schema version 2.

| Content | Notes |
| --- | --- |
| Per-packet `pts` | Integer ticks in the stream time base, or **`null` when the container has no timestamp**. Never `0` as a substitute. |
| Per-packet `dts` | Integer ticks, or `null` |
| Per-packet `duration` | Integer ticks, or `null`. The **only** source of per-frame duration. |
| Per-packet `flags` | As reported (keyframe flag and others) |
| `unknown_key_frame_indices` | Indices of packets whose `flags` field was **absent**. Kept separate so that **"unknown" and "not a keyframe" stay distinguishable** rather than the first silently becoming the second. Empty on all five committed fixtures. |
| `decode_order_differs` | True when the demuxed packet order was not presentation order |
| Packet count | Integer |

### `QualityStatus`

Three-valued. There is no boolean.

| Value | Meaning |
| --- | --- |
| `ok` | The check ran and passed |
| `fail` | The check ran and failed |
| `unknown` | The check could not be evaluated (input metadata absent) |

`unknown` is not `fail`. A file whose `avg_frame_rate` is `0/0` has an `unknown` frame-rate
check, not a failing one.

### `QualityFlag` and `QualityAssessment`

`QualityFlag` is the closed set of envelope and integrity checks (resolution, frame rate,
missing timestamps, decode-order reordering, audio presence, rotation source, and similar).
`QualityAssessment` carries one `QualityStatus` per flag. **Envelope violations produce flags,
never rejections** (`mvp-contract.md` Section 1).

### `IngestRun`

One record per ingest execution, **append-only, never overwritten**. It carries the provenance
fields listed in Section 5 and **points at the manifest by hash**, rather than the manifest
pointing at runs. This keeps the manifest byte-identical across repeated ingests of the same
file, which is the Stage 1 idempotence gate.

It also holds `probe_streams_sha256` and `probe_packets_sha256`, beside the argv that produced
them. This keeps the chain **run -> raw probe bytes -> manifest hash** complete while leaving
the manifest dependent on file bytes alone.

Raw ffprobe documents are **run-scoped, not asset-scoped**:

```
recordings/<asset_id>/runs/<run_id>.probe.streams.raw.json
recordings/<asset_id>/runs/<run_id>.probe.packets.raw.json
```

They were previously written to `recordings/<asset_id>/probe.streams.raw.json`, where a second
ingest **overwrote the first run's preserved raw output**, breaking both raw-output preservation
and per-run provenance separation.

## 3. Identity rules

| Rule | Detail |
| --- | --- |
| Asset ID | `sha256-<64 hex>` of the **raw file bytes**. Path, filename, mtime, permissions and location therefore **never** affect identity. The same video copied, renamed or moved is the same asset. |
| Problem ID | **Scoped to a `WallSet` revision.** A reset produces a new `WallSet`; problem identities do not survive it. |
| Participant and consent IDs | Opaque pseudonyms. Never derived from a name, an email or a path. |

## 4. Schema versioning

Every document declares `schema_id` and `schema_version`. A document of the wrong version
**fails loudly at the boundary** where it is read. It is never silently coerced, upgraded in
place, or best-effort parsed. Silent coercion is how a schema change becomes a data corruption
that is discovered a stage later.

## 5. Provenance

Predictions, preannotations, reviewed annotations, adjudicated ground truth and derived data
**each carry separate provenance and are never collapsed into one field.** A reviewed annotation
that happens to agree with a prediction is still a reviewed annotation.

Run records are **append-only, one per run, never overwritten.**

Every analysis run must record:

| Field | Reason |
| --- | --- |
| Input SHA-256 hashes | Identifies the exact bytes consumed |
| Schema version and ontology version | A label set changes meaning over time |
| Code revision, when available | Reproducibility |
| Configuration hash | Two runs with different config are different runs |
| Model / checkpoint ID and checksum | A checkpoint name is not an identity |
| Score type | A raw logit, a calibrated probability and a distance are not comparable |
| Coordinate space and units | Per `mvp-contract.md` Section 4 |
| Upstream artifact IDs | The provenance chain back to pixels |
| Quality flags | Downstream consumers must see degraded input |
| Runtime environment | Tool versions, notably the external `ffprobe` version |
| Creation timestamp | Ordering of runs |

## 6. Storage formats

| Data | Format | Stage |
| --- | --- | --- |
| Sparse events and manifests | Versioned JSON | 1 |
| Masks | COCO polygons. **RLE deferred**, because it would require a numerical array dependency at a stage that otherwise needs none. | 3 |
| Dense trajectories | Canonical JSON with parallel integer arrays, following the `FrameIndex` pattern Stage 1 already proves. **Parquet / Arrow deferred** until a stage demonstrates a need and records how it handles the no-float rule, because Parquet means a dependency of roughly 40 MB `[PLANNING]` and a float-native columnar format for a volume of roughly one megabyte per attempt `[PLANNING]`. | 4 |
| Overlays and rendered video | Derived diagnostics only | 3+ |

An overlay is **never the only result.** A rendered video is not queryable, not comparable and
not auditable; it is a view of an artifact that must also exist in a structured form.

## 7. Serialization

Canonical JSON, so that byte-identity is a meaningful test:

| Rule | Reason |
| --- | --- |
| Sorted keys | Dict ordering is not semantic |
| Compact separators | Whitespace must not vary |
| UTF-8, trailing newline, **written in binary mode** | Text mode rewrites newlines per platform, breaking byte-identity |
| **No float-typed field anywhere** | A float makes byte-identity depend on `repr`. Durations are **integer microseconds**; frame rates are `{num, den}` **rationals**; rotation is **integer degrees**. |
| Unknown is an explicit `null`, **never an omitted key** | A key that vanishes is indistinguishable from a schema change. `null` says "we looked and there was nothing". |

## 8. Source of truth

**The internal schema is the source of truth.** CVAT import/export is an **adapter** (Stage 2),
not the domain model. CVAT's shapes, attributes and track semantics are mapped onto the internal
entities on the way in and out. No CVAT-specific concept leaks into the internal schema, and no
internal concept is dropped because CVAT lacks a field for it.

---

## 9. Ingest protocol (Stage 1 media boundary)

Verified against **ffprobe 8.0** on this machine. Every rule below exists because of an observed
behaviour, not a guess about the tool.

### Two ffprobe calls

| Call | Arguments | Purpose |
| --- | --- | --- |
| 1 | `-show_format -show_streams` over **all** streams | Container and stream metadata. Covers all streams because **audio presence is privacy-relevant** and must be recorded. |
| 2 | `-select_streams v:0 -show_entries packet=pts,dts,duration,flags` | Per-packet timing. **Demuxes without decoding.** |

Both invocations additionally pass `-ignore_editlist 0` explicitly; see "Edit lists" below.

### Failure detection

ffprobe **exits non-zero on malformed input while still printing valid JSON.** A successful JSON
parse is therefore **not** a success test. Checks run in this order:

1. Process return code.
2. Presence of an `error` key in the parsed output.
3. Presence of a video stream.

Only after all three does the output count as usable.

### Decode order vs presentation order

Packets are returned in **decode order, not presentation order.** A real B-frame mp4 on this
machine produced the pts sequence `0, 6000, 3000`. Therefore:

- The frame index is **sorted by pts**.
- A `decode_order_differs` flag records that the reordering happened, so a later stage that sees
  odd timing can tell whether reordering was involved.

**`-show_frames` is explicitly not used as the fix.** It forces a full decode, and its
`best_effort_timestamp` **invents timestamps where the container has none**, which the
traceability rule forbids. A guessed timestamp is indistinguishable from a measured one once
written.

### Absent values

- A packet's `pts` key is **absent** when the timestamp is unknown. Absent becomes **`null`,
  never `0`.** Zero is a valid timestamp; conflating the two corrupts the first frame.
- `avg_frame_rate` can be `"0/0"`, which means **unknown**. It is recorded as unknown, not as a
  zero frame rate, and it is never used to compute a frame duration.

### Rotation

Read in this order, with the **source recorded** alongside the value:

1. Display Matrix side data -> `display_matrix`.
2. Legacy `tags.rotate` -> `tag`.
3. Neither present -> `absent`, rotation `0` `[FIXED]`.

A side datum that is **present but unparseable** is recorded as `display_matrix_unreadable`
(or `tag_unreadable` for the legacy tag) with `rotation_degrees: null`. Present-but-unreadable
is **not** `absent`: reporting it as absent with rotation 0 was exactly the unknown-to-negative
coercion banned by standing rule 1 of `mvp-contract.md` Section 5. An unreadable Display Matrix
also **does not fall back** to `tags.rotate`, because that would report a different source's
value as if it were the matrix.

### Edit lists

**mp4 edit lists shift the PTS the demuxer reports.** Every ffprobe invocation therefore passes
`-ignore_editlist 0` **explicitly**, and the demuxer options in force are recorded in the
manifest so that a later stage comparing timestamps against another tool can diagnose the
difference rather than rediscover it.

The option was previously a hardcoded constant that merely happened to match ffprobe's default.
Passing it makes the recorded value **true by construction** and stable across ffmpeg versions.
It is load-bearing, not cosmetic: measurement showed the flag shifts every PTS on this
repository's own CFR fixture by 1024 ticks.

### Failure policy

| Condition | Behaviour |
| --- | --- |
| Envelope violation (below `min_width` 1920 `[FIXED]` or `min_height` 1080 `[FIXED]`, below `min_frame_rate` `30/1` `[FIXED]`, audio present, rotation applied) | Recorded as a three-valued quality flag. Ingest succeeds. |
| Malformed input (bad return code, `error` key, no video stream) | **Hard fail.** No manifest is written. |
| `MANIFEST_CONFLICT`: an existing `recording.json` for the same video bytes whose bytes differ, because config or schema version changed | **Hard fail.** The stored manifest is **never overwritten**, because earlier run records attest to those bytes by hash. Identical bytes remain a silent no-op, so idempotent re-ingest is unaffected. |

The three envelope thresholds live in `configs/ingest/v1.json` and are taken **verbatim** from
`mvp-contract.md` Section 1. They are not tuned at the ingest boundary; changing one means
changing the contract.
