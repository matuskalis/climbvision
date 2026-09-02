import pytest

from climbvision.errors import ClimbVisionError
from climbvision.media.ffprobe import raise_for_reported_error
from climbvision.media.normalize import (
    build_frame_index,
    normalize_video_stream,
    select_video_stream,
)
from conftest import PROBE_INVALID_DIR, load_json, probe_document

ASSET_ID = "sha256-" + "0" * 64

# Every file in tests/fixtures/probe_invalid/ is listed here. Two of them are not errors at all:
# an unknown frame rate and a packet without a PTS are abstention cases, and coercing either one
# into a failure would be exactly the fabrication rule 4 forbids.
EXPECTED_ERRORS = {
    "error_field_present.streams.json": "FFPROBE_REPORTED_ERROR",
    "no_video_stream.streams.json": "NO_VIDEO_STREAM",
    "missing_time_base.streams.json": "TIME_BASE_MISSING",
    "no_packets.packets.json": "NO_VIDEO_PACKETS",
}
EXPECTED_ABSTENTIONS = ("zero_frame_rate.streams.json", "packet_without_pts.packets.json")


def exercise(name: str):
    document = load_json(PROBE_INVALID_DIR / name)
    if name.endswith(".packets.json"):
        stream = normalize_video_stream(
            select_video_stream(probe_document("cfr_320x240_30fps_1s", "streams"))
        )
        return build_frame_index(document, ASSET_ID, stream)
    raise_for_reported_error(document, name)
    return normalize_video_stream(select_video_stream(document))


def test_every_malformed_fixture_is_covered_by_this_test():
    on_disk = {path.name for path in PROBE_INVALID_DIR.glob("*.json")}
    assert on_disk == set(EXPECTED_ERRORS) | set(EXPECTED_ABSTENTIONS)


@pytest.mark.parametrize(("name", "code"), sorted(EXPECTED_ERRORS.items()))
def test_malformed_probe_output_raises_a_named_actionable_error(name, code):
    with pytest.raises(ClimbVisionError) as error:
        exercise(name)
    assert error.value.code == code
    assert len(error.value.message) > 30
    assert str(error.value).startswith(f"{code}: ")


def test_unknown_frame_rate_abstains_instead_of_raising():
    stream = exercise("zero_frame_rate.streams.json")
    assert stream.avg_frame_rate is None


def test_a_packet_without_pts_abstains_instead_of_raising():
    frame_index = exercise("packet_without_pts.packets.json")
    assert None in frame_index.pts
    assert frame_index.packet_count == 3
