MICROSECONDS_PER_SECOND = 1_000_000


def parse_rational(value: object) -> tuple[int, int] | None:
    if not isinstance(value, str):
        return None
    parts = value.split("/")
    if len(parts) != 2:
        return None
    try:
        num = int(parts[0])
        den = int(parts[1])
    except ValueError:
        return None
    if den == 0:
        return None
    if den < 0:
        num, den = -num, -den
    return num, den


def pts_to_us(pts: int, num: int, den: int) -> int:
    return _divide_round_half_away(pts * num * MICROSECONDS_PER_SECOND, den)


def us_to_pts(us: int, num: int, den: int) -> int:
    return _divide_round_half_away(us * den, num * MICROSECONDS_PER_SECOND)


def _divide_round_half_away(numerator: int, denominator: int) -> int:
    sign = -1 if numerator < 0 else 1
    quotient, remainder = divmod(abs(numerator), denominator)
    if 2 * remainder >= denominator:
        quotient += 1
    return sign * quotient
