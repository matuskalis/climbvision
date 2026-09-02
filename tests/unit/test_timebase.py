from fractions import Fraction

import pytest

from climbvision.timebase import parse_rational, pts_to_us, us_to_pts

TIMEBASES = [(1, 15360), (1001, 30000), (1, 90000), (1, 1000), (1, 44100)]
PTS_VALUES = [0, 1, 2, 512, 1024, 15360, 90000, 1_000_003, -1, -512, -1024, -90000]


def round_half_away_oracle(value: Fraction) -> int:
    sign = -1 if value < 0 else 1
    magnitude = abs(value)
    whole = magnitude.numerator // magnitude.denominator
    if magnitude - whole >= Fraction(1, 2):
        whole += 1
    return sign * whole


@pytest.mark.parametrize(("num", "den"), TIMEBASES)
@pytest.mark.parametrize("pts", PTS_VALUES)
def test_pts_to_us_round_trip_is_exact_below_a_microsecond_tick(pts, num, den):
    assert us_to_pts(pts_to_us(pts, num, den), num, den) == pts


@pytest.mark.parametrize(("num", "den"), TIMEBASES)
@pytest.mark.parametrize("pts", PTS_VALUES)
def test_pts_to_us_matches_an_independent_fraction_oracle(pts, num, den):
    expected = round_half_away_oracle(Fraction(pts * num * 1_000_000, den))
    assert pts_to_us(pts, num, den) == expected


@pytest.mark.parametrize("us", [0, 1, 500, -1, -500, 33333, -33333, 1_000_000])
def test_us_to_pts_matches_an_independent_fraction_oracle(us):
    num, den = 1, 90000
    expected = round_half_away_oracle(Fraction(us * den, num * 1_000_000))
    assert us_to_pts(us, num, den) == expected


def test_rounding_is_symmetric_about_zero():
    num, den = 1, 2_000_000
    assert pts_to_us(1, num, den) == 1
    assert pts_to_us(-1, num, den) == -1
    assert pts_to_us(3, num, den) == 2
    assert pts_to_us(-3, num, den) == -2


@pytest.mark.parametrize("pts", [0, 1, 40000, 1_200_000, -40000, -1_200_000])
def test_round_trip_above_a_microsecond_tick_stays_within_one_tick(pts):
    num, den = 1, 1_200_000
    recovered = us_to_pts(pts_to_us(pts, num, den), num, den)
    assert abs(recovered - pts) <= 1
    assert abs(pts_to_us(recovered, num, den) - pts_to_us(pts, num, den)) <= 1


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("30/1", (30, 1)),
        ("1/15360", (1, 15360)),
        ("30000/1001", (30000, 1001)),
        ("810/59", (810, 59)),
        ("0/0", None),
        ("1/0", None),
        ("0/1", (0, 1)),
        ("1/-2", (-1, 2)),
        ("", None),
        ("30", None),
        ("a/b", None),
        ("1/2/3", None),
        (None, None),
        (30, None),
    ],
)
def test_parse_rational(text, expected):
    assert parse_rational(text) == expected


def test_parse_rational_never_raises_on_zero_denominator():
    assert parse_rational("0/0") is None
