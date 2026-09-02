import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from climbvision.errors import ClimbVisionError
from climbvision.ingest import ingest
from climbvision.schema import MODEL_REGISTRY
from climbvision.serialization import loads_json


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "ingest":
        return _run_ingest(args.video, args.out)
    return _run_validate(args.documents)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="climbvision")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser(
        "ingest", help="hash and probe a video into a content-addressed recording manifest"
    )
    ingest_parser.add_argument("video", type=Path)
    ingest_parser.add_argument("--out", type=Path, default=Path("artifacts"))

    validate_parser = subparsers.add_parser(
        "validate", help="validate JSON documents against the schema named by their schema_id"
    )
    validate_parser.add_argument("documents", type=Path, nargs="+")
    return parser


def _run_ingest(video: Path, out: Path) -> int:
    try:
        recording = ingest(video, out)
    except ClimbVisionError as exc:
        print(f"error: {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    print(recording.asset_id)
    return 0


def _run_validate(documents: list[Path]) -> int:
    failures = 0
    for document_path in documents:
        try:
            schema_id = _validate_document(document_path)
        except ClimbVisionError as exc:
            failures += 1
            print(f"error: {document_path.name}: {exc.code}: {exc.message}", file=sys.stderr)
        else:
            print(f"ok: {document_path.name}: {schema_id}")
    return 1 if failures else 0


def _validate_document(document_path: Path) -> str:
    try:
        raw = document_path.read_bytes()
    except OSError as exc:
        raise ClimbVisionError(
            "DOCUMENT_NOT_READABLE", f"cannot read document: {exc.strerror}"
        ) from exc
    try:
        document = loads_json(raw)
    except ValueError as exc:
        raise ClimbVisionError("DOCUMENT_UNPARSEABLE", f"not valid JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise ClimbVisionError(
            "DOCUMENT_NOT_AN_OBJECT",
            f"expected a JSON object, got {type(document).__name__}",
        )
    schema_id = document.get("schema_id")
    if not isinstance(schema_id, str):
        raise ClimbVisionError(
            "SCHEMA_ID_MISSING",
            "document has no string schema_id; validation dispatches on the document's own "
            "schema_id, never on its filename",
        )
    model = MODEL_REGISTRY.get(schema_id)
    if model is None:
        raise ClimbVisionError(
            "SCHEMA_ID_UNKNOWN",
            f"unknown schema_id {schema_id!r}; known ids: {', '.join(sorted(MODEL_REGISTRY))}",
        )
    try:
        model.model_validate(document)
    except ValidationError as exc:
        raise ClimbVisionError("DOCUMENT_INVALID", _validation_summary(exc)) from exc
    return schema_id


def _validation_summary(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}" for item in error.errors()
    )
