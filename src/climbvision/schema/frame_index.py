from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from climbvision.hashing import ASSET_ID_PATTERN
from climbvision.schema.recording import Timebase


class FrameIndex(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_id: Literal["climbvision.frame_index"]
    schema_version: Literal[2]

    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    stream_index: int | None
    time_base: Timebase
    packet_count: int
    decode_order_differs: bool

    pts: list[int | None]
    dts: list[int | None]
    duration: list[int | None]
    key_frame_indices: list[int]
    unknown_key_frame_indices: list[int]
