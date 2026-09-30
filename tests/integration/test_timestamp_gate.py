import shutil

import pytest

from climbvision.ingest import ingest
from climbvision.schema import FrameIndex
from climbvision.timebase import pts_to_us, us_to_pts
from conftest import VIDEO_DIR, VIDEO_FIXTURES, load_json

CFR, VFR, ROT90, RAW_ES, HI_TIMESCALE = VIDEO_FIXTURES

pytestmark = pytest.mark.skipif(shutil.which("ffprobe") is None, reason="ffprobe is not on PATH")

MICROSECOND_TIMEBASE_LIMIT = 1_000_000


@pytest.fixture(scope="module")
def ingested(tmp_path_factory):
    out_root = tmp_path_factory.mktemp("gate")
    indices = {}
    for fixture in VIDEO_FIXTURES:
        recording = ingest(VIDEO_DIR / fixture, out_root)
        indices[fixture] = FrameIndex.model_validate(
            load_json(out_root / "recordings" / recording.asset_id / "frame_index.json")
        )
    return indices


def packet_duration_ticks(frame_index: FrameIndex) -> list[int]:
    durations = [ticks for ticks in frame_index.duration if ticks is not None and ticks > 0]
    if durations:
        return durations
    present = [pts for pts in frame_index.pts if pts is not None]
    deltas = sorted(later - earlier for earlier, later in zip(present, present[1:], strict=False))
    return [deltas[len(deltas) // 2]] if deltas else []


def gate(frame_index: FrameIndex) -> dict:
    num, den = frame_index.time_base.num, frame_index.time_base.den
    present = [pts for pts in frame_index.pts if pts is not None]
    recovered = [us_to_pts(pts_to_us(pts, num, den), num, den) for pts in present]
    tick_errors = [abs(back - pts) for back, pts in zip(recovered, present, strict=True)]
    microsecond_errors = [
        abs(pts_to_us(back, num, den) - pts_to_us(pts, num, den))
        for back, pts in zip(recovered, present, strict=True)
    ]
    durations = packet_duration_ticks(frame_index)
    return {
        "time_base": f"{num}/{den}",
        "packets_with_pts": len(present),
        "max_roundtrip_error_ticks": max(tick_errors, default=0),
        "max_roundtrip_error_us": max(microsecond_errors, default=0),
        "min_packet_duration_us": (
            min(pts_to_us(ticks, num, den) for ticks in durations) if durations else None
        ),
    }


@pytest.mark.parametrize("fixture", VIDEO_FIXTURES)
def test_timestamp_round_trip_gate(ingested, fixture):
    measured = gate(ingested[fixture])
    print(f"{fixture}: {measured}")
    if measured["packets_with_pts"] == 0:
        print(
            f"{fixture}: the round-trip numbers above are vacuous, the stream carries no PTS; "
            "the timestamp math for this timebase is covered by tests/unit/test_timebase.py"
        )

    assert measured["min_packet_duration_us"] is not None
    assert measured["min_packet_duration_us"] > 0
    assert measured["max_roundtrip_error_us"] <= measured["min_packet_duration_us"]

    # Assert what is measured, not the weaker bound the math merely guarantees: every
    # PTS-bearing fixture round-trips exactly, including the sub-microsecond timebase, and a
    # regression from 0 to 1 tick must fail here rather than pass as slack.
    if measured["packets_with_pts"]:
        assert measured["max_roundtrip_error_ticks"] == 0
        assert measured["max_roundtrip_error_us"] == 0


def test_the_bounded_branch_of_the_gate_runs_on_measured_timestamps(ingested):
    denominators = {fixture: index.time_base.den for fixture, index in ingested.items()}
    print(f"time_base denominators: {denominators}")
    assert any(value > MICROSECOND_TIMEBASE_LIMIT for value in denominators.values())

    bounded = [
        fixture
        for fixture, index in ingested.items()
        if index.time_base.den > MICROSECOND_TIMEBASE_LIMIT and gate(index)["packets_with_pts"] > 0
    ]
    print(f"fixtures exercising the bounded branch with real PTS: {bounded}")
    assert bounded


def test_the_general_bound_below_a_microsecond_tick_is_one_tick(ingested):
    # Stated separately from the gate above. The fixtures happen to carry PTS that convert
    # exactly; for an arbitrary PTS at a sub-microsecond tick the guarantee the integer math
    # offers is one tick, and that weaker claim is checked here on values the fixtures do not
    # contain, so neither claim can hide behind the other.
    index = ingested[HI_TIMESCALE]
    num, den = index.time_base.num, index.time_base.den
    assert den > MICROSECOND_TIMEBASE_LIMIT

    adversarial = [1, 3, 7, 13, 999_999, 1_200_001, -3, -7, -999_999]
    recovered = [us_to_pts(pts_to_us(pts, num, den), num, den) for pts in adversarial]
    errors = [abs(back - pts) for back, pts in zip(recovered, adversarial, strict=True)]
    print(f"adversarial PTS at {num}/{den}: max error {max(errors)} tick(s)")
    assert max(errors) <= 1
    assert any(error == 1 for error in errors)


def test_the_packet_duration_fallback_uses_a_real_observed_delta(ingested):
    # The fallback is unreachable through the committed fixtures because every packet carries a
    # duration. It is kept because footage whose demuxer reports no packet duration is a real
    # possibility, so it is exercised directly rather than left as untested code.
    measured = ingested[CFR]
    without_durations = measured.model_copy(update={"duration": [None] * measured.packet_count})
    deltas = sorted(
        later - earlier for earlier, later in zip(measured.pts, measured.pts[1:], strict=False)
    )
    assert packet_duration_ticks(without_durations) == [deltas[len(deltas) // 2]]
    assert deltas[len(deltas) // 2] in deltas


def test_fixtures_without_timestamps_report_no_round_trip_evidence(ingested):
    for fixture, index in ingested.items():
        measured = gate(index)
        if measured["packets_with_pts"] == 0:
            print(f"{fixture}: no PTS-bearing packets; the round-trip gate has no data to run on")
            assert index.pts == [None] * index.packet_count
