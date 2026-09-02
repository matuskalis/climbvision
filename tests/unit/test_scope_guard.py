import ast
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT

SOURCE_ROOT = REPO_ROOT / "src"
ALLOWED_THIRD_PARTY = {"pydantic"}
ALLOWED_FIRST_PARTY = {"climbvision"}
# Stage 1 turns a video file into a manifest. Anything from this list means a later stage has
# leaked into it.
BANNED = {
    "http",
    "socketserver",
    "wsgiref",
    "xmlrpc",
    "ftplib",
    "smtplib",
    "imaplib",
    "poplib",
    "telnetlib",
    "webbrowser",
    "sqlite3",
    "dbm",
    "ctypes",
    "aiohttp",
    "websockets",
    "grpc",
    "psycopg2",
    "pymongo",
    "redis",
    "fastapi",
    "flask",
    "django",
    "starlette",
    "uvicorn",
    "requests",
    "httpx",
    "urllib",
    "urllib3",
    "socket",
    "cv2",
    "numpy",
    "scipy",
    "pandas",
    "torch",
    "torchvision",
    "tensorflow",
    "onnxruntime",
    "ultralytics",
    "mediapipe",
    "sklearn",
    "matplotlib",
    "sqlalchemy",
    "boto3",
}


def source_files() -> list[Path]:
    return sorted(SOURCE_ROOT.rglob("*.py"))


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_the_package_actually_has_modules_to_guard():
    assert len(source_files()) >= 15


@pytest.mark.parametrize("path", source_files(), ids=lambda path: path.name)
def test_only_the_stage_one_dependency_surface_is_imported(path):
    allowed = set(sys.stdlib_module_names) | ALLOWED_THIRD_PARTY | ALLOWED_FIRST_PARTY
    assert imported_roots(path) <= allowed


@pytest.mark.parametrize("path", source_files(), ids=lambda path: path.name)
def test_no_later_stage_dependency_is_imported(path):
    assert imported_roots(path) & BANNED == set()


STAGE_ONE_MODULES = {
    "climbvision/__init__.py",
    "climbvision/cli.py",
    "climbvision/errors.py",
    "climbvision/hashing.py",
    "climbvision/ingest.py",
    "climbvision/media/__init__.py",
    "climbvision/media/ffprobe.py",
    "climbvision/media/normalize.py",
    "climbvision/provenance.py",
    "climbvision/quality.py",
    "climbvision/schema/__init__.py",
    "climbvision/schema/frame_index.py",
    "climbvision/schema/provenance.py",
    "climbvision/schema/quality.py",
    "climbvision/schema/recording.py",
    "climbvision/schema/versions.py",
    "climbvision/serialization.py",
    "climbvision/timebase.py",
}


def test_the_stage_one_module_inventory_is_pinned():
    # An import allowlist cannot see a later-stage module that happens to import nothing banned,
    # so the file inventory itself is pinned. A new module here is a deliberate decision, not a
    # silent one: adding it to this set is the decision record.
    on_disk = {path.relative_to(SOURCE_ROOT).as_posix() for path in source_files()}
    assert on_disk == STAGE_ONE_MODULES


def test_the_runtime_dependency_list_is_exactly_pydantic():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()
    dependencies = pyproject.split("dependencies = [", 1)[1].split("]", 1)[0]
    assert dependencies.strip() == '"pydantic>=2.7,<3"'
