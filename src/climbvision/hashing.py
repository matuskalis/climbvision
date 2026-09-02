import hashlib
from pathlib import Path

ASSET_ID_PREFIX = "sha256-"
SHA256_HEX_PATTERN = r"^[0-9a-f]{64}$"
ASSET_ID_PATTERN = r"^sha256-[0-9a-f]{64}$"
DEFAULT_CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def asset_id_from_digest(digest_hex: str) -> str:
    return ASSET_ID_PREFIX + digest_hex
