from fractions import Fraction

import pytest

from climbvision.errors import ClimbVisionError
from climbvision.media.normalize import (
    build_frame_index,
    compute_duration_us,
    container_facts,
    normalize_video_stream,
    select_video_stream,
)
from conftest import PROBE_INVALID_DIR, load_json, probe_document

ASSET_ID = "sha256-" + "0" * 64
STEMS = (
    "cfr_320x240_30fps_1s",
    "vfr_160x120_2s",
    "rot90_160x120_1s",
    "raw_160x120_1s",
    "hi_timescale_160x120_1s",
)


def normalized(stem: str):
    return normalize_video_stream(select_video_stream(probe_document(stem, "streams")))


def raw_video_stream(stem: str) -> dict:
    return select_video_stream(probe_document(stem, "streams"))


@pytest.mark.parametrize("stem", STEMS)
def test_time_base_is_kept_as_an_integer_rational(stem):
    raw = raw_video_stream(stem)
    stream = normalized(stem)
    expected_num, expected_den = (int(part) for part in raw["time_base"].split("/"))
    assert (stream.time_base.num, stream.time_base.den) == (expected_num, expected_den)


@pytest.mark.parametrize("stem", STEMS)
def test_frame_rates_are_kept_as_rationals_never_quotients(stem):
    raw = raw_video_stream(stem)
    stream = normalized(stem)
    measured = (("avg_frame_rate", stream.avg_frame_rate), ("r_frame_rate", stream.r_frame_rate))
    for field, value in measured:
        num, den = (int(part) for part in raw[field].split("/"))
        if den == 0:
            assert value is None
        else:
            assert (value.num, value.den) == (num, den)


@pytest.mark.parametrize("stem", STEMS)
def test_string_typed_numbers_are_coerced_to_int(stem):
    raw = raw_video_stream(stem)
    stream = normalized(stem)
    for field, value in (("nb_frames", stream.nb_frames), ("bit_rate", stream.bit_rate)):
        if field in raw:
            assert isinstance(raw[field], str)
            assert value == int(raw[field])
        else:
            assert value is None


@pytest.mark.parametrize("stem", STEMS)
def test_absent_stream_facts_become_null_not_zero(stem):
    raw = raw_video_stream(stem)
    stream = normalized(stem)
    for field, value in (("start_pts", stream.start_pts), ("duration_ts", stream.duration_ts)):
        assert value == raw[field] if field in raw else value is None


@pytest.mark.parametrize("stem", STEMS)
def test_duration_us_is_exact_integer_math_over_the_timebase(stem):
    stream = normalized(stem)
    if stream.duration_ts is None:
        assert compute_duration_us(stream) is None
        return
    exact = Fraction(stream.duration_ts * stream.time_base.num * 1_000_000, stream.time_base.den)
    measured = compute_duration_us(stream)
    assert isinstance(measured, int)
    assert abs(Fraction(measured) - exact) <= Fraction(1, 2)


def test_rotation_is_read_from_the_display_matrix():
    raw = raw_video_stream("rot90_160x120_1s")
    expected = next(
        side["rotation"]
        for side in raw["side_data_list"]
        if side["side_data_type"] == "Display Matrix"
    )
    stream = normalized("rot90_160x120_1s")
    assert stream.rotation_degrees == int(expected)
    assert stream.rotation_source == "display_matrix"


def test_rotation_falls_back_to_the_legacy_string_tag():
    document = load_json(PROBE_INVALID_DIR / "zero_frame_rate.streams.json")
    raw = select_video_stream(document)
    assert isinstance(raw["tags"]["rotate"], str)
    stream = normalize_video_stream(raw)
    assert stream.rotation_degrees == int(raw["tags"]["rotate"])
    assert stream.rotation_source == "tag"


def test_rotation_absent_is_zero_degrees_with_the_source_recorded():
    stream = normalized("cfr_320x240_30fps_1s")
    assert stream.rotation_degrees == 0
    assert stream.rotation_source == "absent"


def test_display_matrix_wins_over_the_legacy_tag():
    raw = dict(raw_video_stream("rot90_160x120_1s"))
    raw["tags"] = {**raw.get("tags", {}), "rotate": "180"}
    stream = normalize_video_stream(raw)
    assert stream.rotation_source == "display_matrix"
    assert stream.rotation_degrees == 90


def test_float_rotation_is_coerced_to_int():
    raw = dict(raw_video_stream("rot90_160x120_1s"))
    raw["side_data_list"] = [{"side_data_type": "Display Matrix", "rotation": -90.0}]
    stream = normalize_video_stream(raw)
    assert stream.rotation_degrees == -90
    assert isinstance(stream.rotation_degrees, int)


def test_an_unreadable_display_matrix_is_not_reported_as_absent():
    raw = dict(raw_video_stream("rot90_160x120_1s"))
    raw["side_data_list"] = [{"side_data_type": "Display Matrix", "rotation": "not a number"}]
    stream = normalize_video_stream(raw)
    assert stream.rotation_source == "display_matrix_unreadable"
    assert stream.rotation_degrees is None


def test_an_unreadable_display_matrix_does_not_fall_back_to_the_legacy_tag():
    raw = dict(raw_video_stream("rot90_160x120_1s"))
    raw["side_data_list"] = [{"side_data_type": "Display Matrix"}]
    raw["tags"] = {**raw.get("tags", {}), "rotate": "180"}
    stream = normalize_video_stream(raw)
    assert stream.rotation_source == "display_matrix_unreadable"
    assert stream.rotation_degrees is None


def test_an_unreadable_legacy_tag_is_not_reported_as_absent():
    raw = dict(raw_video_stream("cfr_320x240_30fps_1s"))
    raw["tags"] = {**raw.get("tags", {}), "rotate": "sideways"}
    stream = normalize_video_stream(raw)
    assert stream.rotation_source == "tag_unreadable"
    assert stream.rotation_degrees is None


def test_a_packet_without_flags_is_unknown_not_a_non_keyframe():
    packets = {
        "packets": [
            {"pts": 0, "dts": 0, "duration": 512, "flags": "K__"},
            {"pts": 512, "dts": 512, "duration": 512},
            {"pts": 1024, "dts": 1024, "duration": 512, "flags": "___"},
        ]
    }
    frame_index = build_frame_index(packets, ASSET_ID, normalized("cfr_320x240_30fps_1s"))
    assert frame_index.key_frame_indices == [0]
    assert frame_index.unknown_key_frame_indices == [1]


@pytest.mark.parametrize("stem", STEMS)
def test_real_fixtures_report_no_unknown_key_frames(stem):
    frame_index = build_frame_index(probe_document(stem, "packets"), ASSET_ID, normalized(stem))
    assert frame_index.unknown_key_frame_indices == []
    assert frame_index.key_frame_indices


def test_zero_over_zero_frame_rate_is_unknown_not_zero():
    document = load_json(PROBE_INVALID_DIR / "zero_frame_rate.streams.json")
    stream = normalize_video_stream(select_video_stream(document))
    assert stream.avg_frame_rate is None
    assert stream.r_frame_rate is None


def test_audio_stream_presence_is_recorded():
    facts = container_facts(probe_document("cfr_320x240_30fps_1s", "streams"))
    assert facts["audio_stream_count"] == 1
    assert facts["video_stream_count"] == 1
    assert facts["stream_count"] == 2
    assert container_facts(probe_document("vfr_160x120_2s", "streams"))["audio_stream_count"] == 0


def test_container_facts_of_a_container_less_stream():
    facts = container_facts(probe_document("raw_160x120_1s", "streams"))
    assert facts["format_name"] == "h264"
    assert facts["audio_stream_count"] == 0


@pytest.mark.parametrize("stem", STEMS)
def test_packets_are_sorted_by_presentation_timestamp(stem):
    frame_index = build_frame_index(probe_document(stem, "packets"), ASSET_ID, normalized(stem))
    present = [pts for pts in frame_index.pts if pts is not None]
    assert present == sorted(present)


def test_decode_order_differs_is_recorded_when_the_container_reorders():
    stem = "cfr_320x240_30fps_1s"
    packets = probe_document(stem, "packets")
    frame_index = build_frame_index(packets, ASSET_ID, normalized(stem))
    demux_order = [packet["pts"] for packet in packets["packets"]]
    assert frame_index.decode_order_differs is (demux_order != sorted(demux_order))
    assert frame_index.decode_order_differs is True
    assert frame_index.pts == sorted(demux_order)


def test_decode_order_differs_is_false_without_reordering():
    stem = "raw_160x120_1s"
    frame_index = build_frame_index(probe_document(stem, "packets"), ASSET_ID, normalized(stem))
    assert frame_index.decode_order_differs is False


def test_absent_packet_pts_is_null_never_zero():
    stem = "raw_160x120_1s"
    packets = probe_document(stem, "packets")
    assert all("pts" not in packet for packet in packets["packets"])
    frame_index = build_frame_index(packets, ASSET_ID, normalized(stem))
    assert frame_index.pts == [None] * frame_index.packet_count
    assert frame_index.dts == [None] * frame_index.packet_count
    assert 0 not in frame_index.pts


def test_packets_without_pts_sort_after_packets_with_pts():
    document = load_json(PROBE_INVALID_DIR / "packet_without_pts.packets.json")
    frame_index = build_frame_index(document, ASSET_ID, normalized("cfr_320x240_30fps_1s"))
    assert frame_index.pts == [40000, 80000, None]
    assert frame_index.dts == [80000, 40000, 0]


def test_key_frame_indices_point_into_the_sorted_arrays():
    stem = "cfr_320x240_30fps_1s"
    packets = probe_document(stem, "packets")
    frame_index = build_frame_index(packets, ASSET_ID, normalized(stem))
    expected = sum(1 for packet in packets["packets"] if "K" in packet["flags"])
    assert len(frame_index.key_frame_indices) == expected
    assert frame_index.key_frame_indices[0] == 0
    assert all(index < frame_index.packet_count for index in frame_index.key_frame_indices)


@pytest.mark.parametrize("stem", STEMS)
def test_packet_count_matches_the_probe_document(stem):
    packets = probe_document(stem, "packets")
    frame_index = build_frame_index(packets, ASSET_ID, normalized(stem))
    assert frame_index.packet_count == len(packets["packets"])
    assert len(frame_index.pts) == frame_index.packet_count
    assert len(frame_index.dts) == frame_index.packet_count
    assert len(frame_index.duration) == frame_index.packet_count


def test_missing_time_base_is_a_named_error():
    document = load_json(PROBE_INVALID_DIR / "missing_time_base.streams.json")
    with pytest.raises(ClimbVisionError) as error:
        normalize_video_stream(select_video_stream(document))
    assert error.value.code == "TIME_BASE_MISSING"


def test_no_video_stream_is_a_named_error():
    document = load_json(PROBE_INVALID_DIR / "no_video_stream.streams.json")
    with pytest.raises(ClimbVisionError) as error:
        select_video_stream(document)
    assert error.value.code == "NO_VIDEO_STREAM"


def test_no_packets_is_a_named_error():
    document = load_json(PROBE_INVALID_DIR / "no_packets.packets.json")
    with pytest.raises(ClimbVisionError) as error:
        build_frame_index(document, ASSET_ID, normalized("cfr_320x240_30fps_1s"))
    assert error.value.code == "NO_VIDEO_PACKETS"
