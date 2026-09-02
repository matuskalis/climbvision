from pathlib import Path

from climbvision import quality
from climbvision.errors import ClimbVisionError
from climbvision.hashing import asset_id_from_digest, sha256_bytes, sha256_file
from climbvision.media import ffprobe, normalize
from climbvision.provenance import build_ingest_run
from climbvision.schema import IngestRun, Recording
from climbvision.schema.versions import RECORDING_SCHEMA_ID, RECORDING_SCHEMA_VERSION
from climbvision.serialization import dumps_canonical, loads_json

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "ingest" / "v1.json"
PROBE_STREAMS_SUFFIX = ".probe.streams.raw.json"
PROBE_PACKETS_SUFFIX = ".probe.packets.raw.json"


def ingest(
    video_path: Path, out_root: Path, config_path: Path = DEFAULT_CONFIG_PATH
) -> Recording:
    source = _validated_source(video_path)
    config_bytes = _read_config(config_path)
    config = _parse_config(config_bytes, config_path)
    config_version = _config_version(config, config_path)

    digest = sha256_file(source)
    asset_id = asset_id_from_digest(digest)

    ffprobe_version = ffprobe.version()
    streams = ffprobe.probe_streams(source)
    packets = ffprobe.probe_packets(source)

    video_stream = normalize.normalize_video_stream(normalize.select_video_stream(streams.document))
    frame_index = normalize.build_frame_index(packets.document, asset_id, video_stream)
    frame_index_bytes = dumps_canonical(frame_index)

    recording = Recording(
        schema_id=RECORDING_SCHEMA_ID,
        schema_version=RECORDING_SCHEMA_VERSION,
        asset_id=asset_id,
        size_bytes=source.stat().st_size,
        **normalize.container_facts(streams.document),
        video_stream=video_stream,
        duration_us=normalize.compute_duration_us(video_stream),
        video_packet_count=frame_index.packet_count,
        frame_index_sha256=sha256_bytes(frame_index_bytes),
        demuxer_options=ffprobe.DEMUXER_OPTIONS,
        quality=quality.assess(video_stream, frame_index, config),
        consent_record_id=None,
        participant_id=None,
    )
    recording_bytes = dumps_canonical(recording)

    run = build_ingest_run(
        asset_id=asset_id,
        input_basename=source.name,
        manifest_sha256=sha256_bytes(recording_bytes),
        ffprobe_version=ffprobe_version,
        probe_streams_argv=streams.argv,
        probe_streams_sha256=sha256_bytes(streams.raw),
        probe_packets_argv=packets.argv,
        probe_packets_sha256=sha256_bytes(packets.raw),
        config_version=config_version,
        config_sha256=sha256_bytes(config_bytes),
    )
    run_bytes = dumps_canonical(run)

    recording_dir = out_root / "recordings" / asset_id
    manifest_path = recording_dir / "recording.json"
    _refuse_conflicting_manifest(manifest_path, recording_bytes, run)

    runs_dir = recording_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(recording_bytes)
    (recording_dir / "frame_index.json").write_bytes(frame_index_bytes)
    (runs_dir / f"{run.run_id}{PROBE_STREAMS_SUFFIX}").write_bytes(streams.raw)
    (runs_dir / f"{run.run_id}{PROBE_PACKETS_SUFFIX}").write_bytes(packets.raw)
    (runs_dir / f"{run.run_id}.json").write_bytes(run_bytes)
    return recording


def _refuse_conflicting_manifest(
    manifest_path: Path, recording_bytes: bytes, run: IngestRun
) -> None:
    if not manifest_path.is_file():
        return
    existing = manifest_path.read_bytes()
    if existing == recording_bytes:
        return
    raise ClimbVisionError(
        "MANIFEST_CONFLICT",
        f"this asset already has a recording.json with different bytes "
        f"(stored sha256 {sha256_bytes(existing)}, new sha256 {run.manifest_sha256}); the "
        f"manifest is a function of the video bytes, the ingest config ({run.config_version}, "
        f"sha256 {run.config_sha256}) and climbvision {run.climbvision_version}, and earlier "
        "run records attest to the stored bytes. Ingest into a different --out root, or remove "
        "that recording directory deliberately",
    )


def _validated_source(video_path: Path) -> Path:
    source = video_path.expanduser()
    if not source.exists():
        raise ClimbVisionError("INPUT_NOT_FOUND", f"no such file: {video_path}")
    if source.is_dir():
        raise ClimbVisionError(
            "INPUT_IS_DIRECTORY", f"{video_path} is a directory; pass a single video file"
        )
    if not source.is_file():
        raise ClimbVisionError(
            "INPUT_NOT_A_REGULAR_FILE", f"{video_path} is not a regular file"
        )
    if source.stat().st_size == 0:
        raise ClimbVisionError("INPUT_EMPTY", f"{video_path} is zero bytes")
    return source.resolve()


def _read_config(config_path: Path) -> bytes:
    try:
        return config_path.read_bytes()
    except OSError as exc:
        raise ClimbVisionError(
            "CONFIG_NOT_READABLE",
            f"cannot read ingest config {config_path.name}: {exc.strerror}",
        ) from exc


def _parse_config(config_bytes: bytes, config_path: Path) -> dict:
    try:
        config = loads_json(config_bytes)
    except ValueError as exc:
        raise ClimbVisionError(
            "CONFIG_UNPARSEABLE", f"ingest config {config_path.name} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(config, dict):
        raise ClimbVisionError(
            "CONFIG_UNPARSEABLE",
            f"ingest config {config_path.name} must be a JSON object, "
            f"got {type(config).__name__}",
        )
    return config


def _config_version(config: dict, config_path: Path) -> str:
    version = config.get("config_version")
    if not isinstance(version, str):
        raise ClimbVisionError(
            "CONFIG_VERSION_MISSING",
            f"ingest config {config_path.name} has no string config_version",
        )
    return version
