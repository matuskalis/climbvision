from pydantic import BaseModel

from climbvision.schema.frame_index import FrameIndex
from climbvision.schema.provenance import IngestRun
from climbvision.schema.quality import QualityAssessment, QualityFlag, QualityStatus
from climbvision.schema.recording import Recording, Timebase, VideoStreamInfo
from climbvision.schema.versions import (
    FRAME_INDEX_SCHEMA_ID,
    FRAME_INDEX_SCHEMA_VERSION,
    INGEST_RUN_SCHEMA_ID,
    INGEST_RUN_SCHEMA_VERSION,
    RECORDING_SCHEMA_ID,
    RECORDING_SCHEMA_VERSION,
    SCHEMA_IDS,
)

MODEL_REGISTRY: dict[str, type[BaseModel]] = {
    RECORDING_SCHEMA_ID: Recording,
    FRAME_INDEX_SCHEMA_ID: FrameIndex,
    INGEST_RUN_SCHEMA_ID: IngestRun,
}

__all__ = [
    "FRAME_INDEX_SCHEMA_ID",
    "FRAME_INDEX_SCHEMA_VERSION",
    "INGEST_RUN_SCHEMA_ID",
    "INGEST_RUN_SCHEMA_VERSION",
    "MODEL_REGISTRY",
    "RECORDING_SCHEMA_ID",
    "RECORDING_SCHEMA_VERSION",
    "SCHEMA_IDS",
    "FrameIndex",
    "IngestRun",
    "QualityAssessment",
    "QualityFlag",
    "QualityStatus",
    "Recording",
    "Timebase",
    "VideoStreamInfo",
]
