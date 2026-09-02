from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from climbvision.hashing import ASSET_ID_PATTERN, SHA256_HEX_PATTERN

CREATED_AT_UTC_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$"


class IngestRun(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_id: Literal["climbvision.ingest_run"]
    schema_version: Literal[1]

    run_id: str
    created_at_utc: str = Field(pattern=CREATED_AT_UTC_PATTERN)

    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    input_basename: str
    manifest_sha256: str = Field(pattern=SHA256_HEX_PATTERN)

    ffprobe_version: str
    probe_streams_argv: list[str]
    probe_streams_sha256: str = Field(pattern=SHA256_HEX_PATTERN)
    probe_packets_argv: list[str]
    probe_packets_sha256: str = Field(pattern=SHA256_HEX_PATTERN)

    config_version: str
    config_sha256: str = Field(pattern=SHA256_HEX_PATTERN)

    climbvision_version: str
    python_version: str
    git_commit: str | None
    git_dirty: bool | None
