import platform
import shutil
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

from climbvision import __version__
from climbvision.schema import IngestRun
from climbvision.schema.versions import INGEST_RUN_SCHEMA_ID, INGEST_RUN_SCHEMA_VERSION

_SOURCE_FILE = Path(__file__).resolve()


def build_ingest_run(
    *,
    asset_id: str,
    input_basename: str,
    manifest_sha256: str,
    ffprobe_version: str,
    probe_streams_argv: list[str],
    probe_streams_sha256: str,
    probe_packets_argv: list[str],
    probe_packets_sha256: str,
    config_version: str,
    config_sha256: str,
) -> IngestRun:
    git_commit, git_dirty = _git_state()
    return IngestRun(
        schema_id=INGEST_RUN_SCHEMA_ID,
        schema_version=INGEST_RUN_SCHEMA_VERSION,
        run_id=f"run-{uuid.uuid4().hex}",
        created_at_utc=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        asset_id=asset_id,
        input_basename=input_basename,
        manifest_sha256=manifest_sha256,
        ffprobe_version=ffprobe_version,
        probe_streams_argv=probe_streams_argv,
        probe_streams_sha256=probe_streams_sha256,
        probe_packets_argv=probe_packets_argv,
        probe_packets_sha256=probe_packets_sha256,
        config_version=config_version,
        config_sha256=config_sha256,
        climbvision_version=__version__,
        python_version=platform.python_version(),
        git_commit=git_commit,
        git_dirty=git_dirty,
    )


def _source_checkout() -> Path | None:
    # An installed copy lives in site-packages, where the nearest repository is somebody else's.
    # Reporting its commit as climbvision's revision would be a fabricated provenance value, so
    # anything that is not the source tree being run abstains.
    if _SOURCE_FILE.parents[1].name != "src":
        return None
    root = _SOURCE_FILE.parents[2]
    if not (root / ".git").exists() or not (root / "pyproject.toml").is_file():
        return None
    return root


def _git_state() -> tuple[str | None, bool | None]:
    # git is a second external boundary, deliberately kept out of media/ffprobe.py: an
    # unavailable or commitless repository yields unknown (null), never a fabricated clean flag.
    checkout = _source_checkout()
    if checkout is None:
        return None, None
    commit = _git_output(checkout, ["rev-parse", "HEAD"])
    if commit is None:
        return None, None
    status = _git_output(checkout, ["status", "--porcelain"])
    return commit, None if status is None else bool(status)


def _git_output(checkout: Path, arguments: list[str]) -> str | None:
    git = shutil.which("git")
    if git is None:
        return None
    completed = subprocess.run([git, *arguments], cwd=checkout, capture_output=True, text=True)
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()
