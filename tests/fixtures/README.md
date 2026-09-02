# Test fixtures

Everything here is committed and consumed as-is. Regeneration is manual, never CI:
`scripts/regenerate_fixtures.sh` rewrites `video/`, `probe/` and `documents/`; the malformed
documents in `probe_invalid/` and `documents/unknown_schema_id.json` are hand-built and are not
touched by the script.

All video is synthetic (`lavfi` test patterns). No people, no faces, no consent records, no
model weights. Total size is well under 100 KB.

## Tool versions that produced the capture

Recorded in `probe/capture_metadata.json`:

| field | value |
|---|---|
| captured_on | 2026-08-27 |
| ffprobe_version | 8.0 |
| ffmpeg_version | 8.0 |
| platform | Darwin-arm64 |

## `video/` — generated with ffmpeg

Every command is prefixed `ffmpeg -y -loglevel error` and encodes with
`-c:v libx264 -pix_fmt yuv420p` into a non-fragmented container.

| file | command (after the common prefix) | why it exists |
|---|---|---|
| `cfr_320x240_30fps_1s.mp4` | `-f lavfi -i "testsrc=size=320x240:rate=30:duration=1" -f lavfi -i "sine=frequency=440:duration=1" -c:a aac` | constant frame rate, and the only fixture with an audio stream — audio presence is privacy-relevant and the manifest must record it |
| `vfr_160x120_2s.mp4` | `-f lavfi -i "testsrc=size=160x120:rate=30:duration=2" -vf "select='lt(mod(n,7),3)'" -fps_mode passthrough` | genuinely variable frame rate: 27 packets with two distinct PTS deltas. Adding `setpts` would re-time the stream back to uniform CFR and produce a fake VFR fixture |
| `rot90_160x120_1s.mp4` | `-noautorotate -display_rotation:v:0 90 -f lavfi -i "testsrc=size=160x120:rate=30:duration=1"` | rotation carried as a Display Matrix side datum. Both flags are **input** options and must precede `-i`; as output options `-display_rotation` errors out, and without `-noautorotate` ffmpeg bakes the rotation into the pixels and drops the side data. The script fails loudly if the produced file has no Display Matrix |
| `raw_160x120_1s.h264` | `-f lavfi -i "testsrc=size=160x120:rate=30:duration=1" -f h264` | raw H.264 elementary stream, no container: its packets carry **no PTS and no DTS at all**, which is the `TIMESTAMPS_ABSENT` abstention case, not a hard failure. It carries no timestamp evidence, so it cannot exercise the round-trip gate and must not be presented as if it did |
| `hi_timescale_160x120_1s.mp4` | `-f lavfi -i "testsrc=size=160x120:rate=30:duration=1" -video_track_timescale 1200000` | mp4 with the track timescale forced above a microsecond: `time_base 1/1200000` **with real packet PTS** (`0, 40000, 80000, …`), so the bounded branch of the timestamp round-trip gate runs on measured data instead of passing vacuously. The script fails loudly if the produced file has a denominator ≤ 1 000 000 or no packet PTS |

Observed facts (read by the tests from these files, never hardcoded in test code):

| file | time_base | start_pts | duration_ts | packets | avg_frame_rate | rotation |
|---|---|---|---|---|---|---|
| `cfr_320x240_30fps_1s.mp4` | 1/15360 | 0 | 15360 | 30, all with PTS | 30/1 | absent |
| `vfr_160x120_2s.mp4` | 1/15360 | 0 | 30208 | 27, all with PTS | 810/59 | absent |
| `rot90_160x120_1s.mp4` | 1/15360 | 0 | 15360 | 30, all with PTS | 30/1 | 90, display matrix |
| `raw_160x120_1s.h264` | 1/1200000 | absent | absent | 30, **none with PTS** | 25/1 | absent |
| `hi_timescale_160x120_1s.mp4` | 1/1200000 | 0 | 1200000 | 30, all with PTS | 30/1 | absent |

Every fixture is below the frozen 1080p envelope, so `resolution_below_min` reports `fail` on all
of them. That is the real expectation, not a defect: the passing side of the envelope is covered
in `tests/unit/test_quality.py` with synthetic probe dictionaries (1920x1080, 30/1) rather than by
committing a large video.

## `probe/` — captured ffprobe output

Two calls per fixture, both prefixed
`ffprobe -hide_banner -loglevel error -print_format json -show_error`, run from inside
`tests/fixtures/video/` with a bare basename so the echoed `format.filename` is a basename and
never a path:

- `<stem>.streams.json` — `-show_format -show_streams -ignore_editlist 0 -i <file>`
- `<stem>.packets.json` — `-select_streams v:0 -show_entries packet=pts,dts,duration,flags -ignore_editlist 0 -i <file>`

`-ignore_editlist 0` is passed on every call, exactly as the ingest pipeline passes it, so the
`demuxer_options` recorded in the manifest are true by construction instead of assuming
ffmpeg's default. On `cfr_320x240_30fps_1s.mp4` the setting is not cosmetic: `-ignore_editlist 1`
shifts the reported PTS from `0, 2048, 1024, …` to `1024, 3072, 2048, …`.

These are captured observations, not authored data. They are legitimate because the script
produces them from the committed videos and because
`tests/integration/test_ingest.py::test_live_ffprobe_normalizes_to_the_recorded_manifest`
re-runs ffprobe live and asserts the **normalized** manifest matches. The comparison is on the
normalized manifest, not on the raw JSON: raw ffprobe output gains fields on every ffmpeg
upgrade, so asserting on it would break the suite for zero signal.

`capture_metadata.json` is the version sidecar for the capture.

## `probe_invalid/` — hand-built, deliberately malformed

Validator inputs, not observations, so authoring them by hand is correct. Every file is listed
in `tests/unit/test_probe_invalid.py`, which fails if a file here is not covered.

| file | expected outcome |
|---|---|
| `error_field_present.streams.json` | `FFPROBE_REPORTED_ERROR` (the real payload ffprobe prints on stdout while exiting 1) |
| `no_video_stream.streams.json` | `NO_VIDEO_STREAM` (audio-only container) |
| `missing_time_base.streams.json` | `TIME_BASE_MISSING` |
| `no_packets.packets.json` | `NO_VIDEO_PACKETS` |
| `zero_frame_rate.streams.json` | **not an error**: `avg_frame_rate: "0/0"` normalizes to `null` (unknown), and its legacy string `tags.rotate` exercises the rotation fallback |
| `packet_without_pts.packets.json` | **not an error**: a packet whose `pts` key is absent becomes `null`, never `0` |

The last two are abstention cases. Coercing either into a failure would be the fabrication that
rule 4 forbids, so they are asserted as abstentions rather than as raised errors.

## `documents/`

- `recording.valid.json` (schema version 3), `frame_index.valid.json` (schema version 2),
  `ingest_run.valid.json` (schema version 1) —
  produced by a real `climbvision ingest` of `cfr_320x240_30fps_1s.mp4` into a temporary
  directory, copied here by the regeneration script. Used for round-trip, no-float and
  CLI-validation tests. The run record is selected by name (`run-*.json`, excluding
  `*.raw.json`) because raw ffprobe output is written per run, alongside the run record.
- `unknown_schema_id.json` — hand-built. A `schema_id` no Stage 1 model claims, so
  `climbvision validate` must dispatch on the field and refuse rather than guess from the
  filename.
