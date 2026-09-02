from typing import Literal, get_args, get_origin

import pytest
from pydantic import BaseModel, ValidationError

from climbvision.schema import (
    FRAME_INDEX_SCHEMA_ID,
    FRAME_INDEX_SCHEMA_VERSION,
    INGEST_RUN_SCHEMA_ID,
    INGEST_RUN_SCHEMA_VERSION,
    MODEL_REGISTRY,
    RECORDING_SCHEMA_ID,
    RECORDING_SCHEMA_VERSION,
    SCHEMA_IDS,
    FrameIndex,
    IngestRun,
    QualityAssessment,
    Recording,
    Timebase,
    VideoStreamInfo,
)
from conftest import DOCUMENTS_DIR, load_json

DOCUMENT_MODELS = [
    (Recording, RECORDING_SCHEMA_ID, RECORDING_SCHEMA_VERSION, "recording.valid.json"),
    (FrameIndex, FRAME_INDEX_SCHEMA_ID, FRAME_INDEX_SCHEMA_VERSION, "frame_index.valid.json"),
    (IngestRun, INGEST_RUN_SCHEMA_ID, INGEST_RUN_SCHEMA_VERSION, "ingest_run.valid.json"),
]
ALL_MODELS = [
    Recording,
    FrameIndex,
    IngestRun,
    VideoStreamInfo,
    Timebase,
    QualityAssessment,
]


def literal_value(model, field: str):
    annotation = model.model_fields[field].annotation
    assert get_origin(annotation) is Literal
    values = get_args(annotation)
    assert len(values) == 1
    return values[0]


@pytest.mark.parametrize(("model", "schema_id", "version", "name"), DOCUMENT_MODELS)
def test_model_literals_agree_with_the_exported_constants(model, schema_id, version, name):
    assert literal_value(model, "schema_id") == schema_id
    assert literal_value(model, "schema_version") == version


@pytest.mark.parametrize(("model", "schema_id", "version", "name"), DOCUMENT_MODELS)
def test_a_wrong_schema_version_is_rejected(model, schema_id, version, name):
    document = {**load_json(DOCUMENTS_DIR / name), "schema_version": version + 1}
    with pytest.raises(ValidationError):
        model.model_validate(document)


@pytest.mark.parametrize(("model", "schema_id", "version", "name"), DOCUMENT_MODELS)
def test_a_wrong_schema_id_is_rejected(model, schema_id, version, name):
    document = {**load_json(DOCUMENTS_DIR / name), "schema_id": "climbvision.something_else"}
    with pytest.raises(ValidationError):
        model.model_validate(document)


def test_every_schema_id_resolves_to_a_model():
    assert set(MODEL_REGISTRY) == set(SCHEMA_IDS)
    for schema_id, model in MODEL_REGISTRY.items():
        assert literal_value(model, "schema_id") == schema_id


def annotation_mentions_float(annotation) -> bool:
    if annotation is float:
        return True
    return any(annotation_mentions_float(argument) for argument in get_args(annotation))


@pytest.mark.parametrize("model", ALL_MODELS)
def test_no_field_is_typed_as_a_float(model):
    # The value walkers in test_serialization.py cannot see a `float | None` field that happens
    # to hold None today, because rule 8 bans the type, not just the emitted value.
    offenders = [
        name
        for name, field in model.model_fields.items()
        if annotation_mentions_float(field.annotation)
    ]
    assert offenders == []


def test_the_float_annotation_walker_would_catch_a_float_field():
    class Tempting(BaseModel):
        confidence: float | None = None
        nested: dict[str, list[float]] = {}
        honest: int = 0

    assert annotation_mentions_float(Tempting.model_fields["confidence"].annotation)
    assert annotation_mentions_float(Tempting.model_fields["nested"].annotation)
    assert not annotation_mentions_float(Tempting.model_fields["honest"].annotation)


@pytest.mark.parametrize("model", ALL_MODELS)
def test_models_forbid_unknown_fields(model):
    assert model.model_config["extra"] == "forbid"


@pytest.mark.parametrize("model", ALL_MODELS)
def test_models_are_frozen(model):
    assert model.model_config["frozen"] is True


def test_an_unknown_field_is_rejected():
    document = {**load_json(DOCUMENTS_DIR / "recording.valid.json"), "gym_id": "boulderbar"}
    with pytest.raises(ValidationError):
        Recording.model_validate(document)


def test_a_malformed_asset_id_is_rejected():
    document = {**load_json(DOCUMENTS_DIR / "recording.valid.json"), "asset_id": "md5-abc"}
    with pytest.raises(ValidationError):
        Recording.model_validate(document)


def test_a_frozen_model_rejects_assignment():
    recording = Recording.model_validate(load_json(DOCUMENTS_DIR / "recording.valid.json"))
    with pytest.raises(ValidationError):
        recording.asset_id = "sha256-" + "1" * 64


def test_unknown_values_are_representable_on_every_nullable_field():
    document = load_json(DOCUMENTS_DIR / "recording.valid.json")
    recording = Recording.model_validate(document)
    assert recording.consent_record_id is None
    assert recording.participant_id is None
