import copy

import pytest

from climbvision.errors import ClimbVisionError
from climbvision.media.normalize import (
    build_frame_index,
    normalize_video_stream,
    select_video_stream,
)
from climbvision.quality import assess
from climbvision.schema import QualityFlag, QualityStatus
from conftest import PROBE_INVALID_DIR, load_json, probe_document

ASSET_ID = "sha256-" + "0" * 64


def assessed(stem: str, config: dict) -> dict:
    stream = normalize_video_stream(select_video_stream(probe_document(stem, "streams")))
    frame_index = build_frame_index(probe_document(stem, "packets"), ASSET_ID, stream)
    return {item.flag: item for item in assess(stream, frame_index, config)}


def synthetic_stream(**overrides) -> dict:
    stream = {
        "index": 0,
        "codec_type": "video",
        "codec_name": "h264",
        "width": 1920,
        "height": 1080,
        "coded_width": 1920,
        "coded_height": 1080,
        "r_frame_rate": "30/1",
        "avg_frame_rate": "30/1",
        "time_base": "1/30000",
        "start_pts": 0,
        "duration_ts": 30000,
    }
    stream.update(overrides)
    return stream


def synthetic_packets(count: int = 3, step: int = 1000) -> dict:
    return {
        "packets": [
            {
                "pts": position * step,
                "dts": position * step,
                "duration": step,
                "flags": "K__" if position == 0 else "___",
            }
            for position in range(count)
        ]
    }


def assessed_synthetic(config: dict, **overrides) -> dict:
    stream = normalize_video_stream(synthetic_stream(**overrides))
    frame_index = build_frame_index(synthetic_packets(), ASSET_ID, stream)
    return {item.flag: item for item in assess(stream, frame_index, config)}


def with_threshold(config: dict, name: str, value) -> dict:
    changed = copy.deepcopy(config)
    changed["thresholds"][name]["value"] = value
    return changed


def test_every_flag_is_assessed_exactly_once(ingest_config):
    stream = normalize_video_stream(
        select_video_stream(probe_document("cfr_320x240_30fps_1s", "streams"))
    )
    frame_index = build_frame_index(
        probe_document("cfr_320x240_30fps_1s", "packets"), ASSET_ID, stream
    )
    flags = [item.flag for item in assess(stream, frame_index, ingest_config)]
    assert sorted(flags) == sorted(QualityFlag)


def test_below_envelope_resolution_is_flagged_not_raised(ingest_config):
    resolution = assessed("cfr_320x240_30fps_1s", ingest_config)[QualityFlag.RESOLUTION_BELOW_MIN]
    assert resolution.status is QualityStatus.FAIL
    assert resolution.measurement == {"width": 320, "height": 240}
    assert resolution.threshold == {
        "min_width": ingest_config["thresholds"]["min_width"]["value"],
        "min_height": ingest_config["thresholds"]["min_height"]["value"],
    }


def test_resolution_status_follows_the_configured_threshold(ingest_config):
    lowered = with_threshold(with_threshold(ingest_config, "min_width", 320), "min_height", 240)
    assert (
        assessed("cfr_320x240_30fps_1s", lowered)[QualityFlag.RESOLUTION_BELOW_MIN].status
        is QualityStatus.OK
    )
    raised = with_threshold(ingest_config, "min_width", 321)
    assert (
        assessed("cfr_320x240_30fps_1s", raised)[QualityFlag.RESOLUTION_BELOW_MIN].status
        is QualityStatus.FAIL
    )


def test_resolution_passes_at_the_frozen_envelope(ingest_config):
    resolution = assessed_synthetic(ingest_config)[QualityFlag.RESOLUTION_BELOW_MIN]
    assert resolution.status is QualityStatus.OK
    assert resolution.measurement == {"width": 1920, "height": 1080}


@pytest.mark.parametrize(
    ("width", "height"), [(1920, 1079), (1919, 1080), (1280, 720), (3840, 1079)]
)
def test_resolution_fails_anywhere_below_the_frozen_envelope(ingest_config, width, height):
    resolution = assessed_synthetic(ingest_config, width=width, height=height)[
        QualityFlag.RESOLUTION_BELOW_MIN
    ]
    assert resolution.status is QualityStatus.FAIL


def test_frame_rate_passes_at_the_frozen_envelope(ingest_config):
    frame_rate = assessed_synthetic(ingest_config)[QualityFlag.FRAME_RATE_BELOW_MIN]
    assert frame_rate.status is QualityStatus.OK
    assert frame_rate.measurement == {"avg_frame_rate": "30/1"}


def test_ntsc_frame_rate_falls_just_below_the_frozen_envelope(ingest_config):
    frame_rate = assessed_synthetic(ingest_config, avg_frame_rate="30000/1001")[
        QualityFlag.FRAME_RATE_BELOW_MIN
    ]
    assert frame_rate.status is QualityStatus.FAIL
    assert frame_rate.measurement == {"avg_frame_rate": "30000/1001"}


def test_a_missing_dimension_is_unknown_not_fail(ingest_config):
    stream = normalize_video_stream(
        select_video_stream(probe_document("cfr_320x240_30fps_1s", "streams"))
    ).model_copy(update={"width": None})
    frame_index = build_frame_index(
        probe_document("cfr_320x240_30fps_1s", "packets"), ASSET_ID, stream
    )
    resolution = next(
        item
        for item in assess(stream, frame_index, ingest_config)
        if item.flag is QualityFlag.RESOLUTION_BELOW_MIN
    )
    assert resolution.status is QualityStatus.UNKNOWN
    assert resolution.measurement["width"] is None


def test_frame_rate_is_compared_as_an_exact_rational(ingest_config):
    frame_rate = assessed("vfr_160x120_2s", ingest_config)[QualityFlag.FRAME_RATE_BELOW_MIN]
    assert frame_rate.measurement == {"avg_frame_rate": "810/59"}
    assert frame_rate.status is QualityStatus.FAIL
    lowered = with_threshold(ingest_config, "min_frame_rate", {"num": 13, "den": 1})
    assert (
        assessed("vfr_160x120_2s", lowered)[QualityFlag.FRAME_RATE_BELOW_MIN].status
        is QualityStatus.OK
    )


def test_unknown_frame_rate_is_unknown_not_fail(ingest_config):
    stream = normalize_video_stream(
        select_video_stream(load_json(PROBE_INVALID_DIR / "zero_frame_rate.streams.json"))
    )
    frame_index = build_frame_index(
        probe_document("cfr_320x240_30fps_1s", "packets"), ASSET_ID, stream
    )
    frame_rate = next(
        item
        for item in assess(stream, frame_index, ingest_config)
        if item.flag is QualityFlag.FRAME_RATE_BELOW_MIN
    )
    assert frame_rate.status is QualityStatus.UNKNOWN
    assert frame_rate.measurement["avg_frame_rate"] is None


def test_variable_frame_rate_is_measured_then_judged(ingest_config):
    variable = assessed("vfr_160x120_2s", ingest_config)[QualityFlag.VARIABLE_FRAME_RATE]
    assert variable.measurement["distinct_pts_delta_count"] > 1
    assert variable.measurement["r_frame_rate"] == "30/1"
    assert variable.status is QualityStatus.FAIL
    tolerant = with_threshold(ingest_config, "max_distinct_pts_delta_count", 2)
    assert (
        assessed("vfr_160x120_2s", tolerant)[QualityFlag.VARIABLE_FRAME_RATE].status
        is QualityStatus.OK
    )


def test_constant_frame_rate_has_a_single_distinct_delta(ingest_config):
    variable = assessed("cfr_320x240_30fps_1s", ingest_config)[QualityFlag.VARIABLE_FRAME_RATE]
    assert variable.measurement["distinct_pts_delta_count"] == 1
    assert variable.status is QualityStatus.OK


def test_variability_abstains_when_only_some_packets_carry_a_pts(ingest_config):
    # Constant frame rate at 512 ticks per packet, with one packet missing its PTS. Measuring
    # across the hole would report a fabricated 1024 delta and a fail; the honest answer is that
    # the evidence is partial.
    stream = normalize_video_stream(synthetic_stream(time_base="1/15360"))
    packets = {
        "packets": [
            {"pts": 0, "dts": 0, "duration": 512, "flags": "K__"},
            {"pts": 512, "dts": 512, "duration": 512, "flags": "___"},
            {"dts": 1024, "duration": 512, "flags": "___"},
            {"pts": 1536, "dts": 1536, "duration": 512, "flags": "___"},
        ]
    }
    frame_index = build_frame_index(packets, ASSET_ID, stream)
    assert frame_index.pts == [0, 512, 1536, None]

    variable = next(
        item
        for item in assess(stream, frame_index, ingest_config)
        if item.flag is QualityFlag.VARIABLE_FRAME_RATE
    )
    assert variable.measurement["distinct_pts_delta_count"] is None
    assert variable.status is QualityStatus.UNKNOWN


def test_variability_abstains_on_the_committed_mixed_presence_fixture(ingest_config):
    document = load_json(PROBE_INVALID_DIR / "packet_without_pts.packets.json")
    stream = normalize_video_stream(
        select_video_stream(probe_document("cfr_320x240_30fps_1s", "streams"))
    )
    frame_index = build_frame_index(document, ASSET_ID, stream)
    assert None in frame_index.pts
    assert any(pts is not None for pts in frame_index.pts)

    assessments = {item.flag: item for item in assess(stream, frame_index, ingest_config)}
    variable = assessments[QualityFlag.VARIABLE_FRAME_RATE]
    assert variable.measurement["distinct_pts_delta_count"] is None
    assert variable.status is QualityStatus.UNKNOWN

    timestamps = assessments[QualityFlag.TIMESTAMPS_ABSENT]
    assert timestamps.status is QualityStatus.FAIL
    assert timestamps.measurement["pts_present_count"] == 2
    assert timestamps.measurement["packet_count"] == 3


def test_frame_rate_variability_is_unknown_without_timestamps(ingest_config):
    variable = assessed("raw_160x120_1s", ingest_config)[QualityFlag.VARIABLE_FRAME_RATE]
    assert variable.measurement["distinct_pts_delta_count"] is None
    assert variable.status is QualityStatus.UNKNOWN


def test_absent_timestamps_fail_without_rejecting_the_recording(ingest_config):
    timestamps = assessed("raw_160x120_1s", ingest_config)[QualityFlag.TIMESTAMPS_ABSENT]
    assert timestamps.status is QualityStatus.FAIL
    assert timestamps.measurement["pts_present_count"] == 0
    assert timestamps.measurement["packet_count"] > 0


def test_present_timestamps_pass(ingest_config):
    timestamps = assessed("cfr_320x240_30fps_1s", ingest_config)[QualityFlag.TIMESTAMPS_ABSENT]
    assert timestamps.status is QualityStatus.OK
    assert timestamps.measurement["pts_present_count"] == timestamps.measurement["packet_count"]


def test_a_config_without_a_threshold_is_a_named_error(ingest_config):
    broken = copy.deepcopy(ingest_config)
    del broken["thresholds"]["min_width"]
    with pytest.raises(ClimbVisionError) as error:
        assessed("cfr_320x240_30fps_1s", broken)
    assert error.value.code == "CONFIG_THRESHOLD_MISSING"
    assert "min_width" in error.value.message


def test_a_non_integer_threshold_is_a_named_error(ingest_config):
    with pytest.raises(ClimbVisionError) as error:
        assessed("cfr_320x240_30fps_1s", with_threshold(ingest_config, "min_width", "640"))
    assert error.value.code == "CONFIG_THRESHOLD_MALFORMED"


def test_the_configured_envelope_matches_the_frozen_mvp_contract(ingest_config):
    thresholds = ingest_config["thresholds"]
    assert thresholds["min_width"]["value"] == 1920
    assert thresholds["min_height"]["value"] == 1080
    assert thresholds["min_frame_rate"]["value"] == {"num": 30, "den": 1}
    for name in ("min_width", "min_height", "min_frame_rate"):
        assert thresholds[name]["status"] == "[FIXED]"
        assert "mvp-contract.md" in thresholds[name]["selection"]


def test_the_unmeasured_detectability_question_is_kept_on_the_record(ingest_config):
    assert "detectability" in ingest_config["notes"]
    assert "own threshold" in ingest_config["notes"]


def test_every_configured_threshold_declares_a_unit_and_a_selection_rationale(ingest_config):
    assert ingest_config["config_version"] == "ingest/v1"
    for name, entry in ingest_config["thresholds"].items():
        assert entry["unit"], name
        assert entry["status"] in ingest_config["status_tag_meaning"], name
        assert len(entry["selection"]) > 40, name
