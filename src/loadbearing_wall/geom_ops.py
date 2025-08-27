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
    assert projected_length <= wall_length
    original_length = x1 - x0
    ratio = original_length / projected_length
    projected_w0 = w0 * ratio
    projected_w1 = w1 * ratio
    assert (projected_w0 + projected_w1) / 2 * projected_length == (w0 + w1) / 2 * original_length
    return (projected_w0, projected_w1, projected_x0, projected_x1)