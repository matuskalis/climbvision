from itertools import pairwise

from climbvision.errors import ClimbVisionError
from climbvision.schema import (
    FrameIndex,
    QualityAssessment,
    QualityFlag,
    QualityStatus,
    Timebase,
    VideoStreamInfo,
)


def assess(
    video_stream: VideoStreamInfo, frame_index: FrameIndex, config: dict
) -> list[QualityAssessment]:
    return [
        _resolution(video_stream, config),
        _frame_rate(video_stream, config),
        _variable_frame_rate(video_stream, frame_index, config),
        _timestamps(frame_index),
    ]


def _resolution(video_stream: VideoStreamInfo, config: dict) -> QualityAssessment:
    min_width = _require_int(_threshold(config, "min_width"), "thresholds.min_width.value")
    min_height = _require_int(_threshold(config, "min_height"), "thresholds.min_height.value")
    width = video_stream.width
    height = video_stream.height
    if width is None or height is None:
        status = QualityStatus.UNKNOWN
    elif width >= min_width and height >= min_height:
        status = QualityStatus.OK
    else:
        status = QualityStatus.FAIL
    return QualityAssessment(
        flag=QualityFlag.RESOLUTION_BELOW_MIN,
        status=status,
        measurement={"width": width, "height": height},
        threshold={"min_width": min_width, "min_height": min_height},
    )


def _frame_rate(video_stream: VideoStreamInfo, config: dict) -> QualityAssessment:
    minimum = _threshold(config, "min_frame_rate")
    min_num = _require_int(_member(minimum, "num"), "thresholds.min_frame_rate.value.num")
    min_den = _require_int(_member(minimum, "den"), "thresholds.min_frame_rate.value.den")
    measured = video_stream.avg_frame_rate
    if measured is None:
        status = QualityStatus.UNKNOWN
    elif measured.num * min_den >= min_num * measured.den:
        status = QualityStatus.OK
    else:
        status = QualityStatus.FAIL
    return QualityAssessment(
        flag=QualityFlag.FRAME_RATE_BELOW_MIN,
        status=status,
        measurement={"avg_frame_rate": _rational_text(measured)},
        threshold={"min_frame_rate": f"{min_num}/{min_den}"},
    )


def _variable_frame_rate(
    video_stream: VideoStreamInfo, frame_index: FrameIndex, config: dict
) -> QualityAssessment:
    maximum = _require_int(
        _threshold(config, "max_distinct_pts_delta_count"),
        "thresholds.max_distinct_pts_delta_count.value",
    )
    distinct = _distinct_pts_delta_count(frame_index)
    if distinct is None:
        status = QualityStatus.UNKNOWN
    elif distinct <= maximum:
        status = QualityStatus.OK
    else:
        status = QualityStatus.FAIL
    return QualityAssessment(
        flag=QualityFlag.VARIABLE_FRAME_RATE,
        status=status,
        measurement={
            "distinct_pts_delta_count": distinct,
            "avg_frame_rate": _rational_text(video_stream.avg_frame_rate),
            "r_frame_rate": _rational_text(video_stream.r_frame_rate),
        },
        threshold={"max_distinct_pts_delta_count": maximum},
    )


def _timestamps(frame_index: FrameIndex) -> QualityAssessment:
    present = sum(1 for pts in frame_index.pts if pts is not None)
    status = QualityStatus.OK if present == frame_index.packet_count else QualityStatus.FAIL
    return QualityAssessment(
        flag=QualityFlag.TIMESTAMPS_ABSENT,
        status=status,
        measurement={
            "packet_count": frame_index.packet_count,
            "pts_present_count": present,
        },
        threshold={},
    )


def _distinct_pts_delta_count(frame_index: FrameIndex) -> int | None:
    # Dropping the packets without a PTS and measuring across the hole would invent a delta
    # between packets that were never adjacent, so partial evidence abstains outright.
    timestamps = [pts for pts in frame_index.pts if pts is not None]
    if len(timestamps) != len(frame_index.pts) or len(timestamps) < 2:
        return None
    return len({later - earlier for earlier, later in pairwise(timestamps)})


def _rational_text(rational: Timebase | None) -> str | None:
    if rational is None:
        return None
    return f"{rational.num}/{rational.den}"


def _threshold(config: dict, name: str):
    thresholds = config.get("thresholds") if isinstance(config, dict) else None
    entry = thresholds.get(name) if isinstance(thresholds, dict) else None
    if not isinstance(entry, dict) or "value" not in entry:
        raise ClimbVisionError(
            "CONFIG_THRESHOLD_MISSING",
            f"ingest config has no thresholds.{name}.value; every Stage 1 threshold must be "
            "declared in the config with a unit and a selection rationale",
        )
    return entry["value"]


def _member(value: object, key: str) -> object:
    return value.get(key) if isinstance(value, dict) else None


def _require_int(value: object, location: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ClimbVisionError(
            "CONFIG_THRESHOLD_MALFORMED",
            f"ingest config {location} must be an integer, got {value!r}",
        )
    return value
