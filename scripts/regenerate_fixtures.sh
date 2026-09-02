#!/usr/bin/env bash
# Regenerates every file under tests/fixtures/. MANUAL ONLY — never run this in CI.
#
# The fixtures are committed. CI must consume them as-is, because a regenerated fixture is a
# different observation: ffmpeg/ffprobe encode and report differently across versions, so a CI
# regeneration would silently rewrite the very bytes the tests are supposed to pin.
#
# All fixtures are synthetic (lavfi test patterns). No people, no faces, no consent records.
#
# Usage: scripts/regenerate_fixtures.sh

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
video_dir="${repo_root}/tests/fixtures/video"
probe_dir="${repo_root}/tests/fixtures/probe"
documents_dir="${repo_root}/tests/fixtures/documents"

mkdir -p "${video_dir}" "${probe_dir}" "${documents_dir}"

command -v ffmpeg >/dev/null || { echo "ffmpeg not on PATH" >&2; exit 1; }
command -v ffprobe >/dev/null || { echo "ffprobe not on PATH" >&2; exit 1; }

cfr="cfr_320x240_30fps_1s.mp4"
vfr="vfr_160x120_2s.mp4"
rot90="rot90_160x120_1s.mp4"
raw_es="raw_160x120_1s.h264"
hi_timescale="hi_timescale_160x120_1s.mp4"

echo "==> generating video fixtures in tests/fixtures/video/"

# Constant frame rate, with an audio track: audio presence is privacy-relevant and the
# manifest must record it, so at least one fixture has to carry a second stream.
ffmpeg -y -loglevel error \
  -f lavfi -i "testsrc=size=320x240:rate=30:duration=1" \
  -f lavfi -i "sine=frequency=440:duration=1" \
  -c:v libx264 -pix_fmt yuv420p -c:a aac \
  "${video_dir}/${cfr}"

# Genuinely variable frame rate: `select` drops frames and `-fps_mode passthrough` keeps their
# original timestamps, so the PTS deltas really are non-uniform. Adding `setpts` here would
# re-time the stream back to uniform CFR and produce a fixture that only looks variable.
ffmpeg -y -loglevel error \
  -f lavfi -i "testsrc=size=160x120:rate=30:duration=2" \
  -vf "select='lt(mod(n,7),3)'" -fps_mode passthrough \
  -c:v libx264 -pix_fmt yuv420p \
  "${video_dir}/${vfr}"

# Rotation carried as a Display Matrix side datum. `-noautorotate` and `-display_rotation` are
# INPUT options and must precede `-i`: as output options `-display_rotation` errors out, and
# without `-noautorotate` ffmpeg bakes the rotation into the pixels and drops the side data.
ffmpeg -y -loglevel error \
  -noautorotate -display_rotation:v:0 90 \
  -f lavfi -i "testsrc=size=160x120:rate=30:duration=1" \
  -c:v libx264 -pix_fmt yuv420p \
  "${video_dir}/${rot90}"

# Raw H.264 elementary stream, no container: gives a time_base denominator above 1_000_000 and
# packets that carry no PTS at all. It is the absent-timestamp abstention fixture; it carries no
# timestamp evidence, so it cannot exercise the round-trip gate.
ffmpeg -y -loglevel error \
  -f lavfi -i "testsrc=size=160x120:rate=30:duration=1" \
  -c:v libx264 -pix_fmt yuv420p -f h264 \
  "${video_dir}/${raw_es}"

# mp4 whose track timescale is forced above 1_000_000: a time_base denominator larger than a
# microsecond WITH real packet timestamps, so the bounded branch of the timestamp round-trip
# gate runs on measured data instead of passing vacuously.
ffmpeg -y -loglevel error \
  -f lavfi -i "testsrc=size=160x120:rate=30:duration=1" \
  -c:v libx264 -pix_fmt yuv420p -video_track_timescale 1200000 \
  "${video_dir}/${hi_timescale}"

echo "==> verifying the rotated fixture really carries Display Matrix side data"
rot90_streams="$(ffprobe -hide_banner -loglevel error -print_format json -show_streams \
  -i "${video_dir}/${rot90}")"
if ! printf '%s' "${rot90_streams}" | grep -q "Display Matrix"; then
  echo "FAILED: ${rot90} has no Display Matrix side data; refusing to accept it" >&2
  exit 1
fi

echo "==> verifying the high-timescale fixture has a sub-microsecond tick AND real timestamps"
hi_timescale_streams="$(ffprobe -hide_banner -loglevel error -print_format json -show_streams \
  -i "${video_dir}/${hi_timescale}")"
hi_timescale_packets="$(ffprobe -hide_banner -loglevel error -print_format json \
  -select_streams v:0 -show_entries packet=pts -i "${video_dir}/${hi_timescale}")"
python3 - "${hi_timescale}" <<PYCHECK
import json, sys
streams = json.loads(r"""${hi_timescale_streams}""")
packets = json.loads(r"""${hi_timescale_packets}""")
video = next(s for s in streams["streams"] if s["codec_type"] == "video")
denominator = int(video["time_base"].split("/")[1])
with_pts = [p for p in packets["packets"] if "pts" in p]
if denominator <= 1_000_000:
    sys.exit(f"FAILED: {sys.argv[1]} has time_base {video['time_base']}, denominator must exceed 1000000")
if not with_pts:
    sys.exit(f"FAILED: {sys.argv[1]} carries no packet PTS; the bounded gate would be vacuous")
print(f"    time_base {video['time_base']}, {len(with_pts)} packets carry a PTS")
PYCHECK

echo "==> capturing ffprobe output into tests/fixtures/probe/"
# ffprobe is invoked from the file's own directory with a bare basename and with the same
# demuxer options the ingest pipeline passes, so the capture is the observation the pipeline
# makes and the captured `format.filename` is a basename, never a path.
capture_probe() {
  local video_name="$1"
  local stem="${video_name%.*}"
  ( cd "${video_dir}" && ffprobe -hide_banner -loglevel error -print_format json -show_error \
      -show_format -show_streams -ignore_editlist 0 -i "${video_name}" ) \
      > "${probe_dir}/${stem}.streams.json"
  ( cd "${video_dir}" && ffprobe -hide_banner -loglevel error -print_format json -show_error \
      -select_streams v:0 -show_entries packet=pts,dts,duration,flags -ignore_editlist 0 \
      -i "${video_name}" ) > "${probe_dir}/${stem}.packets.json"
}

capture_probe "${cfr}"
capture_probe "${vfr}"
capture_probe "${rot90}"
capture_probe "${raw_es}"
capture_probe "${hi_timescale}"

echo "==> recording the tool versions that produced the capture"
ffprobe_version="$(ffprobe -hide_banner -loglevel error -print_format json -show_program_version \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["program_version"]["version"])')"
ffmpeg_version="$(ffmpeg -version | head -1 | cut -d" " -f3)"
cat > "${probe_dir}/capture_metadata.json" <<EOF
{
  "captured_on": "$(date -u +%Y-%m-%d)",
  "ffprobe_version": "${ffprobe_version}",
  "ffmpeg_version": "${ffmpeg_version}",
  "platform": "$(uname -s)-$(uname -m)"
}
EOF

echo "==> regenerating document fixtures from a live ingest"
tmp_out="$(mktemp -d)"
trap 'rm -rf "${tmp_out}"' EXIT
( cd "${repo_root}" && uv run climbvision ingest "tests/fixtures/video/${cfr}" --out "${tmp_out}" ) >/dev/null
recording_dir="$(find "${tmp_out}/recordings" -mindepth 1 -maxdepth 1 -type d | head -1)"
cp "${recording_dir}/recording.json" "${documents_dir}/recording.valid.json"
cp "${recording_dir}/frame_index.json" "${documents_dir}/frame_index.valid.json"
run_record="$(find "${recording_dir}/runs" -name 'run-*.json' ! -name '*.raw.json' | head -1)"
cp "${run_record}" "${documents_dir}/ingest_run.valid.json"

echo "==> done. Hand-built fixtures under tests/fixtures/probe_invalid/ are NOT regenerated"
echo "    by this script; they are deliberate malformed inputs, not observations."
ls -la "${video_dir}" "${probe_dir}" "${documents_dir}"
