import json

import pytest

from climbvision.media.normalize import normalize_video_stream, select_video_stream
from climbvision.schema import MODEL_REGISTRY, FrameIndex, Recording, Timebase
from climbvision.serialization import dumps_canonical, loads_json
from conftest import DOCUMENTS_DIR, load_json, probe_document

VALID_DOCUMENTS = ("recording.valid.json", "frame_index.valid.json", "ingest_run.valid.json")


def model_for(document: dict):
    return MODEL_REGISTRY[document["schema_id"]]


@pytest.mark.parametrize("name", VALID_DOCUMENTS)
def test_round_trip_is_lossless_and_byte_identical(name):
    document = load_json(DOCUMENTS_DIR / name)
    model = model_for(document)
    original = model.model_validate(document)
    reparsed = model.model_validate(loads_json(dumps_canonical(original)))
    assert reparsed == original
    assert dumps_canonical(reparsed) == dumps_canonical(original)


@pytest.mark.parametrize("name", VALID_DOCUMENTS)
def test_canonical_output_carries_no_float(name):
    document = load_json(DOCUMENTS_DIR / name)
    model = model_for(document)
    canonical = loads_json(dumps_canonical(model.model_validate(document)))
    assert list(floats_in(canonical, name)) == []


@pytest.mark.parametrize("name", VALID_DOCUMENTS)
def test_canonical_output_ends_with_a_single_newline(name):
    document = load_json(DOCUMENTS_DIR / name)
    canonical = dumps_canonical(model_for(document).model_validate(document))
    assert canonical.endswith(b"}\n")
    assert not canonical.endswith(b"}\n\n")


def test_canonical_bytes_do_not_depend_on_key_insertion_order():
    document = load_json(DOCUMENTS_DIR / "recording.valid.json")
    reversed_document = json.loads(json.dumps(dict(reversed(list(document.items())))))
    assert list(document) != list(reversed_document)
    assert dumps_canonical(Recording.model_validate(document)) == dumps_canonical(
        Recording.model_validate(reversed_document)
    )


def test_unknown_values_serialize_as_explicit_null():
    raw_stream = select_video_stream(probe_document("raw_160x120_1s", "streams"))
    video_stream = normalize_video_stream(raw_stream)
    assert video_stream.start_pts is None
    assert video_stream.duration_ts is None
    canonical = dumps_canonical(video_stream)
    assert b'"start_pts":null' in canonical
    assert b'"duration_ts":null' in canonical
    assert set(loads_json(canonical)) == set(type(video_stream).model_fields)


def test_absent_keys_are_never_dropped_from_a_document():
    document = load_json(DOCUMENTS_DIR / "recording.valid.json")
    recording = Recording.model_validate(document)
    canonical = loads_json(dumps_canonical(recording))
    assert canonical["consent_record_id"] is None
    assert canonical["participant_id"] is None
    assert "consent_record_id" in canonical
    assert "participant_id" in canonical


def test_enums_serialize_as_strings():
    document = load_json(DOCUMENTS_DIR / "recording.valid.json")
    canonical = loads_json(dumps_canonical(Recording.model_validate(document)))
    for assessment in canonical["quality"]:
        assert isinstance(assessment["flag"], str)
        assert isinstance(assessment["status"], str)


def test_rationals_are_serialized_as_integer_pairs_not_quotients():
    document = load_json(DOCUMENTS_DIR / "frame_index.valid.json")
    canonical = loads_json(dumps_canonical(FrameIndex.model_validate(document)))
    assert set(canonical["time_base"]) == set(Timebase.model_fields)
    assert isinstance(canonical["time_base"]["num"], int)
    assert isinstance(canonical["time_base"]["den"], int)


def floats_in(value, path):
    if isinstance(value, float):
        yield path
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from floats_in(item, f"{path}.{key}")
    elif isinstance(value, list):
        for position, item in enumerate(value):
            yield from floats_in(item, f"{path}[{position}]")
