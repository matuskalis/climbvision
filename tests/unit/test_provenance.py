from pathlib import Path

import pytest

from climbvision import provenance
from climbvision.provenance import _git_state, _source_checkout, build_ingest_run
from conftest import REPO_ROOT

DIGEST = "0" * 64
ASSET_ID = f"sha256-{DIGEST}"
INSTALLED_PATH = Path("/opt/env/lib/python3.11/site-packages/climbvision/provenance.py")


def sample_run(**overrides):
    arguments = {
        "asset_id": ASSET_ID,
        "input_basename": "climb.mp4",
        "manifest_sha256": DIGEST,
        "ffprobe_version": "8.0",
        "probe_streams_argv": ["-i", "climb.mp4"],
        "probe_streams_sha256": DIGEST,
        "probe_packets_argv": ["-i", "climb.mp4"],
        "probe_packets_sha256": DIGEST,
        "config_version": "ingest/v1",
        "config_sha256": DIGEST,
    }
    arguments.update(overrides)
    return build_ingest_run(**arguments)


def test_the_source_checkout_is_this_repository():
    assert _source_checkout() == REPO_ROOT


def test_an_installed_copy_is_not_treated_as_a_source_checkout(monkeypatch):
    monkeypatch.setattr(provenance, "_SOURCE_FILE", INSTALLED_PATH)
    assert _source_checkout() is None


def test_git_is_never_invoked_outside_the_source_checkout(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("git must not run outside the climbvision source checkout")

    monkeypatch.setattr(provenance, "_SOURCE_FILE", INSTALLED_PATH)
    monkeypatch.setattr(provenance.subprocess, "run", refuse)
    assert _git_state() == (None, None)


def test_a_source_layout_without_a_repository_abstains(monkeypatch, tmp_path):
    fake = tmp_path / "src" / "climbvision" / "provenance.py"
    fake.parent.mkdir(parents=True)
    fake.write_text("")
    (tmp_path / "pyproject.toml").write_text("")
    monkeypatch.setattr(provenance, "_SOURCE_FILE", fake)
    assert _source_checkout() is None


def test_a_source_layout_without_a_pyproject_abstains(monkeypatch, tmp_path):
    fake = tmp_path / "src" / "climbvision" / "provenance.py"
    fake.parent.mkdir(parents=True)
    fake.write_text("")
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(provenance, "_SOURCE_FILE", fake)
    assert _source_checkout() is None


def test_an_unknown_git_state_is_recorded_as_null_not_as_clean(monkeypatch):
    monkeypatch.setattr(provenance, "_SOURCE_FILE", INSTALLED_PATH)
    run = sample_run()
    assert run.git_commit is None
    assert run.git_dirty is None


def test_the_run_record_carries_the_environment_it_ran_in():
    run = sample_run()
    assert run.run_id.startswith("run-")
    assert run.python_version.count(".") == 2
    assert run.climbvision_version
    assert run.created_at_utc.endswith("Z")


@pytest.mark.parametrize("field", ["asset_id", "manifest_sha256", "config_sha256"])
def test_the_run_record_rejects_a_malformed_digest(field):
    with pytest.raises(ValueError):
        sample_run(**{field: "not-a-digest"})
