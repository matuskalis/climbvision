import json
from pathlib import Path

import pytest

from climbvision.cli import _build_parser, main
from climbvision.schema import RECORDING_SCHEMA_VERSION
from conftest import DOCUMENTS_DIR, VIDEO_DIR, VIDEO_FIXTURES, load_json

VALID_DOCUMENTS = ("recording.valid.json", "frame_index.valid.json", "ingest_run.valid.json")


def test_validate_accepts_every_valid_document(capsys):
    paths = [str(DOCUMENTS_DIR / name) for name in VALID_DOCUMENTS]
    assert main(["validate", *paths]) == 0
    captured = capsys.readouterr()
    assert captured.out.count("ok: ") == len(paths)
    assert captured.err == ""


def test_validate_dispatches_on_schema_id_not_on_the_filename(tmp_path, capsys):
    misleading = tmp_path / "frame_index.json"
    misleading.write_bytes((DOCUMENTS_DIR / "recording.valid.json").read_bytes())
    assert main(["validate", str(misleading)]) == 0
    assert "climbvision.recording" in capsys.readouterr().out


def test_validate_rejects_an_unknown_schema_id(capsys):
    assert main(["validate", str(DOCUMENTS_DIR / "unknown_schema_id.json")]) == 1
    assert "SCHEMA_ID_UNKNOWN" in capsys.readouterr().err


def test_validate_rejects_a_document_without_a_schema_id(tmp_path, capsys):
    document = tmp_path / "anonymous.json"
    document.write_text(json.dumps({"asset_id": "sha256-" + "0" * 64}))
    assert main(["validate", str(document)]) == 1
    assert "SCHEMA_ID_MISSING" in capsys.readouterr().err


def test_validate_rejects_a_wrong_schema_version(tmp_path, capsys):
    document = load_json(DOCUMENTS_DIR / "recording.valid.json")
    document["schema_version"] = RECORDING_SCHEMA_VERSION + 1
    path = tmp_path / "future.json"
    path.write_text(json.dumps(document))
    assert main(["validate", str(path)]) == 1
    captured = capsys.readouterr()
    assert "DOCUMENT_INVALID" in captured.err
    assert "schema_version" in captured.err


def test_validate_rejects_unparseable_json(tmp_path, capsys):
    path = tmp_path / "broken.json"
    path.write_text("{not json")
    assert main(["validate", str(path)]) == 1
    assert "DOCUMENT_UNPARSEABLE" in capsys.readouterr().err


def test_validate_rejects_a_json_document_that_is_not_an_object(tmp_path, capsys):
    path = tmp_path / "array.json"
    path.write_text("[1, 2, 3]")
    assert main(["validate", str(path)]) == 1
    assert "DOCUMENT_NOT_AN_OBJECT" in capsys.readouterr().err


def test_validate_reports_a_missing_document(tmp_path, capsys):
    assert main(["validate", str(tmp_path / "absent.json")]) == 1
    assert "DOCUMENT_NOT_READABLE" in capsys.readouterr().err


def test_validate_fails_the_batch_but_still_reports_the_good_documents(tmp_path, capsys):
    good = str(DOCUMENTS_DIR / "recording.valid.json")
    bad = str(DOCUMENTS_DIR / "unknown_schema_id.json")
    assert main(["validate", good, bad]) == 1
    captured = capsys.readouterr()
    assert "ok: " in captured.out
    assert "SCHEMA_ID_UNKNOWN" in captured.err


def test_ingest_reports_a_missing_input_and_writes_nothing(tmp_path, capsys):
    out = tmp_path / "artifacts"
    assert main(["ingest", str(tmp_path / "absent.mp4"), "--out", str(out)]) == 1
    assert "INPUT_NOT_FOUND" in capsys.readouterr().err
    assert not out.exists()


def test_ingest_reports_a_directory_input(tmp_path, capsys):
    out = tmp_path / "artifacts"
    assert main(["ingest", str(tmp_path), "--out", str(out)]) == 1
    assert "INPUT_IS_DIRECTORY" in capsys.readouterr().err
    assert not out.exists()


def test_ingest_reports_a_zero_byte_input(tmp_path, capsys):
    empty = tmp_path / "empty.mp4"
    empty.write_bytes(b"")
    out = tmp_path / "artifacts"
    assert main(["ingest", str(empty), "--out", str(out)]) == 1
    assert "INPUT_EMPTY" in capsys.readouterr().err
    assert not out.exists()


def test_ingest_reports_a_missing_ffprobe(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PATH", "")
    out = tmp_path / "artifacts"
    assert main(["ingest", str(VIDEO_DIR / VIDEO_FIXTURES[0]), "--out", str(out)]) == 1
    assert "FFPROBE_NOT_FOUND" in capsys.readouterr().err
    assert not out.exists()


@pytest.mark.parametrize("argv", [[], ["quantify"], ["ingest"], ["validate"], ["--help"]])
def test_usage_errors_exit_with_argparse_status(argv):
    with pytest.raises(SystemExit) as exit_info:
        main(argv)
    assert exit_info.value.code in (0, 2)


def test_out_defaults_to_the_artifacts_directory():
    parsed = _build_parser().parse_args(["ingest", "climb.mp4"])
    assert parsed.out == Path("artifacts")
