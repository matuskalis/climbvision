from climbvision.errors import ClimbVisionError
from climbvision.schema import FrameIndex, Timebase, VideoStreamInfo
from climbvision.schema.versions import FRAME_INDEX_SCHEMA_ID, FRAME_INDEX_SCHEMA_VERSION
from climbvision.timebase import parse_rational, pts_to_us

DISPLAY_MATRIX = "Display Matrix"


def select_video_stream(streams_document: dict) -> dict:
    streams = streams_document.get("streams")
    if not isinstance(streams, list):
        raise ClimbVisionError(
            "NO_VIDEO_STREAM",
            "ffprobe output contains no streams array; the input is not a readable media file",
        )
    for stream in streams:
        if isinstance(stream, dict) and stream.get("codec_type") == "video":
            return stream
    raise ClimbVisionError(
        "NO_VIDEO_STREAM",
        f"the input has {len(streams)} stream(s) and none of them is a video stream",
    )


def normalize_video_stream(raw_stream: dict) -> VideoStreamInfo:
    time_base = parse_rational(raw_stream.get("time_base"))
    if time_base is None:
        raise ClimbVisionError(
            "TIME_BASE_MISSING",
            f"video stream has no usable time_base (reported: {raw_stream.get('time_base')!r}); "
            "timestamps cannot be interpreted without one",
        )
    rotation_degrees, rotation_source = _rotation(raw_stream)
    return VideoStreamInfo(
        index=_as_int(raw_stream.get("index")),
        codec_name=_as_text(raw_stream.get("codec_name")),
        codec_long_name=_as_text(raw_stream.get("codec_long_name")),
        profile=_as_text(raw_stream.get("profile")),
        pix_fmt=_as_text(raw_stream.get("pix_fmt")),
        width=_as_int(raw_stream.get("width")),
        height=_as_int(raw_stream.get("height")),
        coded_width=_as_int(raw_stream.get("coded_width")),
        coded_height=_as_int(raw_stream.get("coded_height")),
        has_b_frames=_as_int(raw_stream.get("has_b_frames")),
        nb_frames=_as_int(raw_stream.get("nb_frames")),
        bit_rate=_as_int(raw_stream.get("bit_rate")),
        time_base=Timebase(num=time_base[0], den=time_base[1]),
        start_pts=_as_int(raw_stream.get("start_pts")),
        duration_ts=_as_int(raw_stream.get("duration_ts")),
        avg_frame_rate=_as_timebase(raw_stream.get("avg_frame_rate")),
        r_frame_rate=_as_timebase(raw_stream.get("r_frame_rate")),
        rotation_degrees=rotation_degrees,
        rotation_source=rotation_source,
    )


def container_facts(streams_document: dict) -> dict[str, str | int | None]:
    raw_streams = streams_document.get("streams")
    streams = raw_streams if isinstance(raw_streams, list) else []
    raw_format = streams_document.get("format")
    container = raw_format if isinstance(raw_format, dict) else {}
    codec_types = [stream.get("codec_type") for stream in streams if isinstance(stream, dict)]
    return {
        "format_name": _as_text(container.get("format_name")),
        "format_long_name": _as_text(container.get("format_long_name")),
        "stream_count": len(streams),
        "video_stream_count": codec_types.count("video"),
        "audio_stream_count": codec_types.count("audio"),
    }


def build_frame_index(
    packets_document: dict, asset_id: str, video_stream: VideoStreamInfo
) -> FrameIndex:
    raw_packets = packets_document.get("packets")
    if not isinstance(raw_packets, list) or not raw_packets:
        raise ClimbVisionError(
            "NO_VIDEO_PACKETS",
            "ffprobe reported zero video packets; there is nothing to index",
        )
    entries = [
        (
            _as_int(packet.get("pts")),
            _as_int(packet.get("dts")),
            _as_int(packet.get("duration")),
            _as_text(packet.get("flags")),
            position,
        )
        for position, packet in enumerate(raw_packets)
        if isinstance(packet, dict)
    ]
    if not entries:
        raise ClimbVisionError(
            "NO_VIDEO_PACKETS",
            f"ffprobe returned {len(raw_packets)} packet entries and none of them is an object",
        )
    ordered = sorted(entries, key=_presentation_order_key)
    return FrameIndex(
        schema_id=FRAME_INDEX_SCHEMA_ID,
        schema_version=FRAME_INDEX_SCHEMA_VERSION,
        asset_id=asset_id,
        stream_index=video_stream.index,
        time_base=video_stream.time_base,
        packet_count=len(ordered),
        decode_order_differs=[entry[4] for entry in ordered] != list(range(len(ordered))),
        pts=[entry[0] for entry in ordered],
        dts=[entry[1] for entry in ordered],
        duration=[entry[2] for entry in ordered],
        key_frame_indices=[
            position
            for position, entry in enumerate(ordered)
            if entry[3] is not None and "K" in entry[3]
        ],
        unknown_key_frame_indices=[
            position for position, entry in enumerate(ordered) if entry[3] is None
        ],
    )


def compute_duration_us(video_stream: VideoStreamInfo) -> int | None:
    if video_stream.duration_ts is None:
        return None
    return pts_to_us(
        video_stream.duration_ts, video_stream.time_base.num, video_stream.time_base.den
    )


def _presentation_order_key(entry: tuple) -> tuple[int, int, int]:
    pts, _dts, _duration, _flags, position = entry
    if pts is None:
        return (1, 0, position)
    return (0, pts, position)


def _rotation(raw_stream: dict) -> tuple[int | None, str]:
    # A rotation that is present but unreadable is not the same fact as no rotation at all, so
    # each gets its own source value and the unreadable ones report unknown degrees.
    side_data_list = raw_stream.get("side_data_list")
    for side_data in side_data_list if isinstance(side_data_list, list) else []:
        if isinstance(side_data, dict) and side_data.get("side_data_type") == DISPLAY_MATRIX:
            degrees = _as_int(side_data.get("rotation"))
            if degrees is None:
                return None, "display_matrix_unreadable"
            return degrees, "display_matrix"
    tags = raw_stream.get("tags")
    if isinstance(tags, dict) and "rotate" in tags:
        degrees = _as_int(tags["rotate"])
        if degrees is None:
            return None, "tag_unreadable"
        return degrees, "tag"
    return 0, "absent"


def _as_timebase(value: object) -> Timebase | None:
    rational = parse_rational(value)
    if rational is None:
        return None
    return Timebase(num=rational[0], den=rational[1])


def _as_text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None
