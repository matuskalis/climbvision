import hashlib
import re
import shutil

import pytest

from climbvision.hashing import (
    ASSET_ID_PATTERN,
    ASSET_ID_PREFIX,
    asset_id_from_digest,
    sha256_bytes,
    sha256_file,
)
from conftest import VIDEO_DIR, VIDEO_FIXTURES

FIXTURE = VIDEO_DIR / VIDEO_FIXTURES[0]


def test_sha256_bytes_matches_hashlib():
    payload = b"climbvision stage 1"
    assert sha256_bytes(payload) == hashlib.sha256(payload).hexdigest()


def test_sha256_file_matches_the_digest_of_its_bytes():
    assert sha256_file(FIXTURE) == sha256_bytes(FIXTURE.read_bytes())


@pytest.mark.parametrize("chunk_size", [1, 7, 4096, 65536, 1024 * 1024, 8 * 1024 * 1024])
def test_sha256_file_is_chunk_size_invariant(chunk_size):
    assert sha256_file(FIXTURE, chunk_size=chunk_size) == sha256_file(FIXTURE)


def test_sha256_of_an_empty_file_is_stable(tmp_path):
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    assert sha256_file(empty) == sha256_bytes(b"")


def test_asset_id_format():
    asset_id = asset_id_from_digest(sha256_file(FIXTURE))
    assert asset_id.startswith(ASSET_ID_PREFIX)
    assert re.fullmatch(ASSET_ID_PATTERN, asset_id)
    assert len(asset_id) == len(ASSET_ID_PREFIX) + 64


def test_asset_id_ignores_name_and_mtime(tmp_path):
    first = tmp_path / "a_climb.mp4"
    second = tmp_path / "renamed_much_later.mp4"
    shutil.copyfile(FIXTURE, first)
    shutil.copyfile(FIXTURE, second)
    second.touch()
    assert asset_id_from_digest(sha256_file(first)) == asset_id_from_digest(sha256_file(second))
    assert first.stat().st_mtime_ns != second.stat().st_mtime_ns
