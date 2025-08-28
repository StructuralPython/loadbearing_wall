import math
from typing import Optional

def apply_spread_angle(
    wall_height: float,
    wall_length: float,
    spread_angle: float,
    w0: float,
    x0: float,
    w1: Optional[float] = None,
    x1: Optional[float] = None,
) -> dict:
    """
    Returns a dictionary representing the load described by
    w0, w1, x0, x1. If only w0 and x0 are provided, the 
    load is assumed to be a point load.

    The total spread cannot be longer than the wall length.

    spread_angle is assumed to be in degrees
    """
    angle_rads = math.radians(spread_angle)
    spread_amount = wall_height * math.tan(angle_rads)
    projected_x0 = max(0.0, x0 - spread_amount)
    if x1 is None:
        projected_x1 = min(wall_length, x0 + spread_amount)
    else:
        projected_x1 = min(wall_length, x1 + spread_amount)
    projected_length = projected_x1 - projected_x0
    if x1 is not None:
        original_length = x1 - x0
    else:
        original_length = 1
    ratio = original_length / projected_length
    projected_w0 = w0 * ratio
    if w1 is not None:
        projected_w1 = w1 * ratio
    else:
        projected_w1 = w0 * ratio
    return (round_to_close_integer(projected_w0), round_to_close_integer(projected_w1), round_to_close_integer(projected_x0), round_to_close_integer(projected_x1))


def round_to_close_integer(x: float, eps = 1e-7) -> float | int:
    """
    Rounds to the nearest int if it is REALLY close
    """
    if abs(abs(round(x)) - abs(x)) < eps:
        return round(x)
    else:
        return x