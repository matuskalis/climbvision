import shutil
import subprocess
from pathlib import Path
from typing import NamedTuple

from climbvision.errors import ClimbVisionError
from climbvision.serialization import loads_json

FORMAT_ARGS = ("-hide_banner", "-loglevel", "error", "-print_format", "json")
BASE_ARGS = (*FORMAT_ARGS, "-show_error")
VERSION_ARGS = (*FORMAT_ARGS, "-show_program_version")
# Passed on every probe call so the demuxer options recorded in the manifest are true by
# construction rather than an assumption about ffmpeg's defaults. `-ignore_editlist 1` really
# does shift the reported PTS on our own fixtures, so this is load-bearing, not decorative.
DEMUXER_OPTIONS = {"ignore_editlist": False}
DEMUXER_ARGS = ("-ignore_editlist", "0")
STREAMS_ARGS = ("-show_format", "-show_streams")
PACKETS_ARGS = ("-select_streams", "v:0", "-show_entries", "packet=pts,dts,duration,flags")


class ProbeResult(NamedTuple):
    argv: list[str]
    raw: bytes
    document: dict


def executable() -> str:
    path = shutil.which("ffprobe")
    if path is None:
        raise ClimbVisionError(
            "FFPROBE_NOT_FOUND",
            "ffprobe was not found on PATH; install ffmpeg (brew install ffmpeg) and retry",
        )
    return path


def version() -> str:
    completed = subprocess.run(
        [executable(), *VERSION_ARGS], capture_output=True
    )
    if completed.returncode != 0:
        raise ClimbVisionError(
            "FFPROBE_VERSION_FAILED",
            f"ffprobe -show_program_version exited {completed.returncode}: "
            f"{completed.stderr.decode('utf-8', 'replace').strip()}",
        )
    document = loads_json(completed.stdout)
    reported = document.get("program_version", {}).get("version")
    if not isinstance(reported, str):
        raise ClimbVisionError(
            "FFPROBE_VERSION_UNREADABLE",
            "ffprobe did not report program_version.version; the ffprobe on PATH is not usable",
        )
    return reported


def probe_streams(path: Path) -> ProbeResult:
    return _run(path, STREAMS_ARGS)


def probe_packets(path: Path) -> ProbeResult:
    return _run(path, PACKETS_ARGS)


def _run(path: Path, entry_args: tuple[str, ...]) -> ProbeResult:
    # ffprobe is invoked from the file's own directory with a bare basename so that the
    # `format.filename` it echoes into the raw output is a basename, never an absolute path.
    argv = [*BASE_ARGS, *entry_args, *DEMUXER_ARGS, "-i", path.name]
    completed = subprocess.run(
        [executable(), *argv], cwd=path.parent, capture_output=True
    )
    stderr = completed.stderr.decode("utf-8", "replace").strip()
    if completed.returncode != 0:
        raise ClimbVisionError(
            "FFPROBE_FAILED",
            f"ffprobe exited {completed.returncode} for {path.name}: "
            f"{_reported_error(completed.stdout) or stderr or 'no diagnostic output'}",
        )
    try:
        document = loads_json(completed.stdout)
    except ValueError as exc:
        raise ClimbVisionError(
            "FFPROBE_OUTPUT_UNPARSEABLE",
            f"ffprobe exited 0 for {path.name} but its output is not JSON: {exc}",
        ) from exc
    if not isinstance(document, dict):
        raise ClimbVisionError(
            "FFPROBE_OUTPUT_UNPARSEABLE",
            f"ffprobe returned a {type(document).__name__} for {path.name}, expected an object",
        )
    raise_for_reported_error(document, path.name)
    return ProbeResult(argv=argv, raw=completed.stdout, document=document)


def raise_for_reported_error(document: dict, label: str) -> None:
    if "error" in document:
        raise ClimbVisionError(
            "FFPROBE_REPORTED_ERROR",
            f"ffprobe reported an error for {label}: {_error_text(document)}",
        )


def _reported_error(stdout: bytes) -> str:
    try:
        document = loads_json(stdout)
    except ValueError:
        return ""
    if not isinstance(document, dict) or "error" not in document:
        return ""
    return _error_text(document)


def _error_text(document: dict) -> str:
    error = document.get("error")
    if not isinstance(error, dict):
        return str(error)
    return f"{error.get('string')} (code {error.get('code')})"
