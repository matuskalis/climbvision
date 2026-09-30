from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from climbvision.hashing import ASSET_ID_PATTERN, SHA256_HEX_PATTERN
from climbvision.schema.quality import QualityAssessment

RotationSource = Literal[
    "display_matrix", "display_matrix_unreadable", "tag", "tag_unreadable", "absent"
]


class Timebase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    num: int
    den: int


class VideoStreamInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    index: int | None
    codec_name: str | None
    codec_long_name: str | None
    profile: str | None
    pix_fmt: str | None
    width: int | None
    height: int | None
    coded_width: int | None
    coded_height: int | None
    has_b_frames: int | None
    nb_frames: int | None
    bit_rate: int | None
    time_base: Timebase
    start_pts: int | None
    duration_ts: int | None
    avg_frame_rate: Timebase | None
    r_frame_rate: Timebase | None
    rotation_degrees: int | None
    rotation_source: RotationSource


class Recording(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_id: Literal["climbvision.recording"]
    schema_version: Literal[3]

    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    size_bytes: int

    format_name: str | None
    format_long_name: str | None
    stream_count: int
    video_stream_count: int
    audio_stream_count: int

    video_stream: VideoStreamInfo
    duration_us: int | None
    video_packet_count: int

    frame_index_sha256: str = Field(pattern=SHA256_HEX_PATTERN)
    demuxer_options: dict[str, bool]

    quality: list[QualityAssessment]

    consent_record_id: str | None
    participant_id: str | None
