import json
import platform
import shutil
import subprocess
from fractions import Fraction

import pytest

from climbvision.cli import main
from climbvision.errors import ClimbVisionError
from climbvision.hashing import sha256_bytes, sha256_file
from climbvision.ingest import PROBE_PACKETS_SUFFIX, PROBE_STREAMS_SUFFIX, ingest
from climbvision.media import ffprobe
from climbvision.media.normalize import (
    build_frame_index,
    container_facts,
    normalize_video_stream,
    select_video_stream,
)
from climbvision.schema import FrameIndex, IngestRun, QualityFlag, QualityStatus, Recording
from conftest import CONFIG_PATH, VIDEO_DIR, VIDEO_FIXTURES, load_json, probe_document

pytestmark = pytest.mark.skipif(shutil.which("ffprobe") is None, reason="ffprobe is not on PATH")

CFR, VFR, ROT90, RAW_ES, HI_TIMESCALE = VIDEO_FIXTURES


def recording_dir(out_root, asset_id):
    return out_root / "recordings" / asset_id


def run_files(out_root, asset_id):
    runs = (recording_dir(out_root, asset_id) / "runs").glob("run-*.json")
    return sorted(path for path in runs if not path.name.endswith(".raw.json"))


def raw_probe_files(out_root, asset_id, run_id):
    runs_dir = recording_dir(out_root, asset_id) / "runs"
    return (
        runs_dir / f"{run_id}{PROBE_STREAMS_SUFFIX}",
        runs_dir / f"{run_id}{PROBE_PACKETS_SUFFIX}",
    )


def artifact_files(out_root):
    return sorted(path for path in out_root.rglob("*") if path.is_file())


def test_manifest_carries_the_facts_a_later_stage_needs(tmp_path):
    video = VIDEO_DIR / CFR
    recording = ingest(video, tmp_path)
    raw_stream = select_video_stream(probe_document("cfr_320x240_30fps_1s", "streams"))

    assert recording.asset_id == "sha256-" + sha256_file(video)
    assert recording.size_bytes == video.stat().st_size
    assert recording.video_stream.codec_name == raw_stream["codec_name"]
    assert recording.video_stream.width == raw_stream["width"]
    assert recording.video_stream.height == raw_stream["height"]
    assert recording.video_stream.start_pts == raw_stream["start_pts"]
    assert recording.video_stream.rotation_source == "absent"
    assert recording.audio_stream_count == 1

    num, den = recording.video_stream.time_base.num, recording.video_stream.time_base.den
    assert f"{num}/{den}" == raw_stream["time_base"]
    exact = Fraction(recording.video_stream.duration_ts * num * 1_000_000, den)
    assert abs(Fraction(recording.duration_us) - exact) <= Fraction(1, 2)

    written = recording_dir(tmp_path, recording.asset_id)
    run_id = run_files(tmp_path, recording.asset_id)[0].stem
    inventory = {
        path.relative_to(written).as_posix() for path in written.rglob("*") if path.is_file()
    }
    assert inventory == {
        "recording.json",
        "frame_index.json",
        f"runs/{run_id}.json",
        f"runs/{run_id}{PROBE_STREAMS_SUFFIX}",
        f"runs/{run_id}{PROBE_PACKETS_SUFFIX}",
    }
    assert not any(path.is_symlink() for path in written.rglob("*"))


def test_written_documents_hash_to_what_the_records_claim(tmp_path):
    recording = ingest(VIDEO_DIR / CFR, tmp_path)
    written = recording_dir(tmp_path, recording.asset_id)
    assert sha256_bytes((written / "frame_index.json").read_bytes()) == recording.frame_index_sha256

    run_path = run_files(tmp_path, recording.asset_id)[0]
    run = IngestRun.model_validate(load_json(run_path))
    streams_raw, packets_raw = raw_probe_files(tmp_path, recording.asset_id, run.run_id)
    assert sha256_bytes(streams_raw.read_bytes()) == run.probe_streams_sha256
    assert sha256_bytes(packets_raw.read_bytes()) == run.probe_packets_sha256


def test_the_manifest_carries_no_filename_dependent_field(tmp_path):
    recording = ingest(VIDEO_DIR / CFR, tmp_path)
    manifest = load_json(recording_dir(tmp_path, recording.asset_id) / "recording.json")
    assert "probe_streams_sha256" not in manifest
    assert "probe_packets_sha256" not in manifest
    assert set(manifest) == set(Recording.model_fields)


def test_raw_probe_documents_are_kept_verbatim(tmp_path):
    recording = ingest(VIDEO_DIR / CFR, tmp_path)
    run_id = run_files(tmp_path, recording.asset_id)[0].stem
    raw = raw_probe_files(tmp_path, recording.asset_id, run_id)[0].read_bytes()
    assert b'"filename": "cfr_320x240_30fps_1s.mp4"' in raw
    assert b"\n    " in raw
    keys = list(json.loads(raw)["streams"][0])
    assert keys != sorted(keys)
    assert (
        raw
        == subprocess.run(
            [
                "ffprobe",
                "-hide_banner",
                "-loglevel",
                "error",
                "-print_format",
                "json",
                "-show_error",
                "-show_format",
                "-show_streams",
                "-i",
                CFR,
            ],
            cwd=VIDEO_DIR,
            capture_output=True,
            check=True,
        ).stdout
    )


def test_the_run_record_binds_the_manifest_to_its_inputs(tmp_path):
    recording = ingest(VIDEO_DIR / CFR, tmp_path)
    written = recording_dir(tmp_path, recording.asset_id)
    run = IngestRun.model_validate(load_json(run_files(tmp_path, recording.asset_id)[0]))

    assert run.asset_id == recording.asset_id
    assert run.manifest_sha256 == sha256_bytes((written / "recording.json").read_bytes())
    assert run.config_sha256 == sha256_bytes(CONFIG_PATH.read_bytes())
    assert run.config_version == load_json(CONFIG_PATH)["config_version"]
    assert run.input_basename == CFR
    assert run.ffprobe_version
    assert run.probe_streams_argv[-2:] == ["-i", CFR]
    assert run.probe_packets_argv[-2:] == ["-i", CFR]
    streams_raw, packets_raw = raw_probe_files(tmp_path, recording.asset_id, run.run_id)
    assert run.probe_streams_sha256 == sha256_bytes(streams_raw.read_bytes())
    assert run.probe_packets_sha256 == sha256_bytes(packets_raw.read_bytes())
    assert run.python_version == platform.python_version()


def test_a_changed_config_refuses_to_overwrite_an_attested_manifest(tmp_path, capsys):
    out_root = tmp_path / "out"
    original = ingest(VIDEO_DIR / CFR, out_root)
    manifest = recording_dir(out_root, original.asset_id) / "recording.json"
    before = manifest.read_bytes()
    runs_before = run_files(out_root, original.asset_id)

    relaxed = load_json(CONFIG_PATH)
    relaxed["thresholds"]["min_width"]["value"] = 320
    relaxed["thresholds"]["min_height"]["value"] = 240
    relaxed_path = tmp_path / "relaxed.json"
    relaxed_path.write_text(json.dumps(relaxed))

    with pytest.raises(ClimbVisionError) as error:
        ingest(VIDEO_DIR / CFR, out_root, config_path=relaxed_path)
    assert error.value.code == "MANIFEST_CONFLICT"
    assert sha256_bytes(before) in error.value.message

    assert manifest.read_bytes() == before
    assert run_files(out_root, original.asset_id) == runs_before
    stored = IngestRun.model_validate(load_json(runs_before[0]))
    assert stored.manifest_sha256 == sha256_bytes(manifest.read_bytes())


def test_a_conflicting_manifest_exits_one_and_touches_nothing(tmp_path, capsys):
    # Stands in for a manifest written by different code or a different config: whatever is
    # stored is not what this build produces, and an earlier run record attests to it.
    out_root = tmp_path / "out"
    original = ingest(VIDEO_DIR / CFR, out_root)
    written = recording_dir(out_root, original.asset_id)
    manifest = written / "recording.json"
    manifest.write_bytes(
        manifest.read_bytes().replace(b'"participant_id":null', b'"participant_id":"p1"')
    )
    before = {path: path.read_bytes() for path in written.rglob("*") if path.is_file()}

    assert main(["ingest", str(VIDEO_DIR / CFR), "--out", str(out_root)]) == 1
    message = capsys.readouterr().err
    assert "MANIFEST_CONFLICT" in message
    assert "ingest/v1" in message

    after = {path: path.read_bytes() for path in written.rglob("*") if path.is_file()}
    assert after == before


def test_the_manifest_records_the_demuxer_options_actually_passed(tmp_path):
    recording = ingest(VIDEO_DIR / CFR, tmp_path)
    run = IngestRun.model_validate(load_json(run_files(tmp_path, recording.asset_id)[0]))
    for name, value in recording.demuxer_options.items():
        flag = f"-{name}"
        for argv in (run.probe_streams_argv, run.probe_packets_argv):
            assert flag in argv
            assert argv[argv.index(flag) + 1] == str(int(value))
    assert recording.demuxer_options == ffprobe.DEMUXER_OPTIONS


def test_ingesting_twice_leaves_the_manifest_byte_identical_and_appends_a_run(tmp_path):
    first = ingest(VIDEO_DIR / CFR, tmp_path)
    manifest = recording_dir(tmp_path, first.asset_id) / "recording.json"
    first_bytes = manifest.read_bytes()

    second = ingest(VIDEO_DIR / CFR, tmp_path)
    assert second.asset_id == first.asset_id
    assert manifest.read_bytes() == first_bytes

    runs = run_files(tmp_path, first.asset_id)
    assert len(runs) == 2
    records = [IngestRun.model_validate(load_json(path)) for path in runs]
    assert records[0].run_id != records[1].run_id
    assert records[0].manifest_sha256 == records[1].manifest_sha256
    assert {record.run_id for record in records} == {path.stem for path in runs}


def test_a_second_ingest_never_overwrites_the_first_runs_raw_probe_output(tmp_path):
    first = ingest(VIDEO_DIR / CFR, tmp_path)
    first_run = IngestRun.model_validate(load_json(run_files(tmp_path, first.asset_id)[0]))
    first_raw = [
        path.read_bytes() for path in raw_probe_files(tmp_path, first.asset_id, first_run.run_id)
    ]

    ingest(VIDEO_DIR / CFR, tmp_path)

    runs = run_files(tmp_path, first.asset_id)
    assert len(runs) == 2
    records = [IngestRun.model_validate(load_json(path)) for path in runs]
    for record in records:
        streams_raw, packets_raw = raw_probe_files(tmp_path, first.asset_id, record.run_id)
        assert streams_raw.is_file()
        assert packets_raw.is_file()
        assert sha256_bytes(streams_raw.read_bytes()) == record.probe_streams_sha256
        assert sha256_bytes(packets_raw.read_bytes()) == record.probe_packets_sha256

    preserved = [
        path.read_bytes() for path in raw_probe_files(tmp_path, first.asset_id, first_run.run_id)
    ]
    assert preserved == first_raw


def test_a_byte_identical_copy_at_another_path_has_the_same_asset_id(tmp_path):
    elsewhere = tmp_path / "somewhere" / "else"
    elsewhere.mkdir(parents=True)
    copy = elsewhere / CFR
    shutil.copyfile(VIDEO_DIR / CFR, copy)

    original = ingest(VIDEO_DIR / CFR, tmp_path / "out_a")
    duplicate = ingest(copy, tmp_path / "out_b")
    assert duplicate.asset_id == original.asset_id
    duplicate_manifest = recording_dir(tmp_path / "out_b", duplicate.asset_id) / "recording.json"
    original_manifest = recording_dir(tmp_path / "out_a", original.asset_id) / "recording.json"
    assert duplicate_manifest.read_bytes() == original_manifest.read_bytes()


def test_a_renamed_copy_produces_a_byte_identical_manifest(tmp_path):
    renamed = tmp_path / "RENAMED_alice_session.mp4"
    shutil.copyfile(VIDEO_DIR / CFR, renamed)
    original = ingest(VIDEO_DIR / CFR, tmp_path / "out_a")
    duplicate = ingest(renamed, tmp_path / "out_b")

    assert duplicate.asset_id == original.asset_id
    assert duplicate == original
    original_manifest = recording_dir(tmp_path / "out_a", original.asset_id) / "recording.json"
    duplicate_manifest = recording_dir(tmp_path / "out_b", duplicate.asset_id) / "recording.json"
    assert duplicate_manifest.read_bytes() == original_manifest.read_bytes()

    # The filename does change the raw ffprobe output, which echoes it back as format.filename.
    # That difference belongs to the run, not to the asset, so it shows up only in run records.
    original_run = IngestRun.model_validate(
        load_json(run_files(tmp_path / "out_a", original.asset_id)[0])
    )
    duplicate_run = IngestRun.model_validate(
        load_json(run_files(tmp_path / "out_b", duplicate.asset_id)[0])
    )
    assert original_run.input_basename == CFR
    assert duplicate_run.input_basename == renamed.name
    assert original_run.probe_streams_sha256 != duplicate_run.probe_streams_sha256
    assert original_run.manifest_sha256 == duplicate_run.manifest_sha256


def test_ingesting_a_renamed_copy_into_the_same_root_does_not_mutate_the_manifest(tmp_path):
    renamed = tmp_path / "RENAMED_alice_session.mp4"
    shutil.copyfile(VIDEO_DIR / CFR, renamed)
    out_root = tmp_path / "out"

    original = ingest(VIDEO_DIR / CFR, out_root)
    manifest = recording_dir(out_root, original.asset_id) / "recording.json"
    before = manifest.read_bytes()

    ingest(renamed, out_root)

    assert manifest.read_bytes() == before
    assert len(run_files(out_root, original.asset_id)) == 2


def test_the_source_file_is_never_touched(tmp_path):
    source = tmp_path / "input" / CFR
    source.parent.mkdir()
    shutil.copyfile(VIDEO_DIR / CFR, source)
    before = (sha256_file(source), source.stat().st_size, source.stat().st_mtime_ns)

    ingest(source, tmp_path / "out")

    after = (sha256_file(source), source.stat().st_size, source.stat().st_mtime_ns)
    assert after == before
    assert sorted(path.name for path in source.parent.iterdir()) == [CFR]


@pytest.mark.parametrize("fixture", VIDEO_FIXTURES)
def test_no_absolute_path_leaks_into_an_artifact(tmp_path, fixture):
    source = tmp_path / "input" / fixture
    source.parent.mkdir(exist_ok=True)
    shutil.copyfile(VIDEO_DIR / fixture, source)
    out_root = tmp_path / "out"

    ingest(source, out_root)

    written = artifact_files(out_root)
    assert written
    for path in written:
        payload = path.read_bytes()
        assert str(tmp_path).encode() not in payload, path.name
        assert str(source.parent).encode() not in payload, path.name
        assert b"/Users/" not in payload, path.name


def test_the_variable_frame_rate_fixture_is_flagged_not_rejected(tmp_path):
    recording = ingest(VIDEO_DIR / VFR, tmp_path)
    variable = next(
        item for item in recording.quality if item.flag is QualityFlag.VARIABLE_FRAME_RATE
    )
    assert variable.status is QualityStatus.FAIL
    assert variable.measurement["distinct_pts_delta_count"] > 1

    recorded = probe_document("vfr_160x120_2s", "packets")["packets"]
    expected_deltas = {
        later - earlier
        for earlier, later in zip(
            sorted(packet["pts"] for packet in recorded),
            sorted(packet["pts"] for packet in recorded)[1:],
            strict=False,
        )
    }
    frame_index = FrameIndex.model_validate(
        load_json(recording_dir(tmp_path, recording.asset_id) / "frame_index.json")
    )
    measured_deltas = {
        later - earlier
        for earlier, later in zip(frame_index.pts, frame_index.pts[1:], strict=False)
    }
    assert measured_deltas == expected_deltas
    assert len(measured_deltas) == variable.measurement["distinct_pts_delta_count"]


def test_rotation_is_read_from_the_display_matrix(tmp_path):
    recording = ingest(VIDEO_DIR / ROT90, tmp_path)
    raw_stream = select_video_stream(probe_document("rot90_160x120_1s", "streams"))
    expected = next(
        side["rotation"]
        for side in raw_stream["side_data_list"]
        if side["side_data_type"] == "Display Matrix"
    )
    assert recording.video_stream.rotation_degrees == int(expected)
    assert recording.video_stream.rotation_source == "display_matrix"


def test_a_recording_without_timestamps_is_flagged_not_rejected(tmp_path):
    recording = ingest(VIDEO_DIR / RAW_ES, tmp_path)
    timestamps = next(
        item for item in recording.quality if item.flag is QualityFlag.TIMESTAMPS_ABSENT
    )
    assert timestamps.status is QualityStatus.FAIL
    assert timestamps.measurement["pts_present_count"] == 0
    assert recording.duration_us is None

    frame_index = FrameIndex.model_validate(
        load_json(recording_dir(tmp_path, recording.asset_id) / "frame_index.json")
    )
    assert frame_index.pts == [None] * frame_index.packet_count


@pytest.mark.parametrize("fixture", VIDEO_FIXTURES)
def test_live_ffprobe_normalizes_to_the_recorded_manifest(tmp_path, fixture):
    stem = fixture.rsplit(".", 1)[0]
    recording = ingest(VIDEO_DIR / fixture, tmp_path)

    recorded_streams = probe_document(stem, "streams")
    expected_stream = normalize_video_stream(select_video_stream(recorded_streams))
    assert recording.video_stream == expected_stream
    for key, value in container_facts(recorded_streams).items():
        assert getattr(recording, key) == value

    expected_index = build_frame_index(
        probe_document(stem, "packets"), recording.asset_id, expected_stream
    )
    written_index = FrameIndex.model_validate(
        load_json(recording_dir(tmp_path, recording.asset_id) / "frame_index.json")
    )
    assert written_index == expected_index


@pytest.mark.parametrize("fixture", VIDEO_FIXTURES)
def test_every_written_document_validates_against_its_own_schema(tmp_path, fixture, capsys):
    recording = ingest(VIDEO_DIR / fixture, tmp_path)
    written = recording_dir(tmp_path, recording.asset_id)
    documents = [
        str(written / "recording.json"),
        str(written / "frame_index.json"),
        *[str(path) for path in run_files(tmp_path, recording.asset_id)],
    ]
    assert main(["validate", *documents]) == 0
    assert capsys.readouterr().out.count("ok: ") == len(documents)


@pytest.mark.parametrize("fixture", VIDEO_FIXTURES)
def test_no_written_document_contains_a_float(tmp_path, fixture):
    recording = ingest(VIDEO_DIR / fixture, tmp_path)
    written = recording_dir(tmp_path, recording.asset_id)
    documents = [
        written / "recording.json",
        written / "frame_index.json",
        *run_files(tmp_path, recording.asset_id),
    ]
    for path in documents:
        assert list(floats_in(load_json(path), path.name)) == []


def floats_in(value, path):
    if isinstance(value, float):
        yield path
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from floats_in(item, f"{path}.{key}")
    elif isinstance(value, list):
        for position, item in enumerate(value):
            yield from floats_in(item, f"{path}[{position}]")


def test_cli_ingest_prints_the_asset_id(tmp_path, capsys):
    assert main(["ingest", str(VIDEO_DIR / CFR), "--out", str(tmp_path)]) == 0
    printed = capsys.readouterr().out.strip()
    assert printed == "sha256-" + sha256_file(VIDEO_DIR / CFR)
    assert (tmp_path / "recordings" / printed / "recording.json").is_file()


def test_ffprobe_failure_is_detected_even_though_its_stdout_is_valid_json(tmp_path, capsys):
    broken = tmp_path / "broken.mp4"
    broken.write_bytes(b"this is not a video container")
    probe = subprocess.run(
        [
            "ffprobe",
            "-hide_banner",
            "-loglevel",
            "error",
            "-print_format",
            "json",
            "-show_error",
            "-show_format",
            "-show_streams",
            "-i",
            broken.name,
        ],
        cwd=tmp_path,
        capture_output=True,
    )
    assert probe.returncode != 0
    assert json.loads(probe.stdout)["error"]["string"]

    out_root = tmp_path / "artifacts"
    assert main(["ingest", str(broken), "--out", str(out_root)]) == 1
    message = capsys.readouterr().err
    assert "FFPROBE_FAILED" in message
    assert "Invalid data found" in message
    assert not out_root.exists()


def test_a_truncated_video_leaves_no_artifact_directory(tmp_path, capsys):
    truncated = tmp_path / "truncated.mp4"
    truncated.write_bytes((VIDEO_DIR / CFR).read_bytes()[:512])
    out_root = tmp_path / "artifacts"
    assert main(["ingest", str(truncated), "--out", str(out_root)]) == 1
    assert "error:" in capsys.readouterr().err
    assert not out_root.exists()


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not on PATH")
def test_a_video_without_a_video_stream_is_rejected(tmp_path, capsys):
    audio_only = tmp_path / "audio_only.m4a"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-c:a",
            "aac",
            str(audio_only),
        ],
        check=True,
    )
    out_root = tmp_path / "artifacts"
    assert main(["ingest", str(audio_only), "--out", str(out_root)]) == 1
    assert "NO_VIDEO_STREAM" in capsys.readouterr().err
    assert not out_root.exists()


def test_a_manifest_written_by_ingest_reparses_to_the_same_model(tmp_path):
    recording = ingest(VIDEO_DIR / CFR, tmp_path)
    written = load_json(recording_dir(tmp_path, recording.asset_id) / "recording.json")
    assert Recording.model_validate(written) == recording
