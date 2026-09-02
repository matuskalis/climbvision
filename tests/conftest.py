import json
import shutil
import socket
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
VIDEO_DIR = FIXTURES_DIR / "video"
PROBE_DIR = FIXTURES_DIR / "probe"
PROBE_INVALID_DIR = FIXTURES_DIR / "probe_invalid"
DOCUMENTS_DIR = FIXTURES_DIR / "documents"
CONFIG_PATH = REPO_ROOT / "configs" / "ingest" / "v1.json"

VIDEO_FIXTURES = (
    "cfr_320x240_30fps_1s.mp4",
    "vfr_160x120_2s.mp4",
    "rot90_160x120_1s.mp4",
    "raw_160x120_1s.h264",
    "hi_timescale_160x120_1s.mp4",
)


def has_ffprobe() -> bool:
    return shutil.which("ffprobe") is not None


def load_json(path: Path) -> dict:
    return json.loads(path.read_bytes())


def probe_document(stem: str, kind: str) -> dict:
    return load_json(PROBE_DIR / f"{stem}.{kind}.json")


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise RuntimeError("the climbvision test suite must not touch the network")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


@pytest.fixture
def ingest_config() -> dict:
    return load_json(CONFIG_PATH)
