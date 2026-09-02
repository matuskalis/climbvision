from enum import Enum

from pydantic import BaseModel, ConfigDict


class QualityFlag(str, Enum):  # noqa: UP042
    RESOLUTION_BELOW_MIN = "resolution_below_min"
    FRAME_RATE_BELOW_MIN = "frame_rate_below_min"
    VARIABLE_FRAME_RATE = "variable_frame_rate"
    TIMESTAMPS_ABSENT = "timestamps_absent"


class QualityStatus(str, Enum):  # noqa: UP042
    OK = "ok"
    FAIL = "fail"
    UNKNOWN = "unknown"


class QualityAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    flag: QualityFlag
    status: QualityStatus
    measurement: dict[str, int | str | None]
    threshold: dict[str, int | str | None]
