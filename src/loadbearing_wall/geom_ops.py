import math
from typing import Optional


def apply_spread_angle(
    wall_height: float,
    wall_length: float,
    spread_angle: float,
    w0: Optional[float] = None,
    x0: Optional[float] = None,
    w1: Optional[float] = None,
    x1: Optional[float] = None,
    p: Optional[float] = None,
    x: Optional[float] = None
) -> tuple[float, float, float, float]:
    """
    Returns a dictionary representing the load described by
    w0, w1, x0, x1 (if distributed load) or p, x (if point
    load).

    The total spread cannot be longer than the wall length.

    spread_angle is assumed to be in degrees
    """
    angle_rads = math.radians(spread_angle)
    spread_amount = wall_height * math.tan(angle_rads)
    print(f"{spread_amount=} | {wall_height=}")
    if None not in [w0, w1, x0, x1]:
        projected_x0 = max(0.0, x0 - spread_amount)
        projected_x1 = min(wall_length, x1 + spread_amount)
        original_length = x1 - x0
    elif None not in [x, p]:
        projected_x0 = max(0.0, x - spread_amount)
        projected_x1 = min(wall_length, x + spread_amount)
        original_length = 0
    else:
        print(f"Weird condition: {locals()=}")

    projected_length = projected_x1 - projected_x0

    print(f"{projected_length=}")
    ratio = original_length / projected_length

    if None not in [w0, w1, x0, x1]:
        projected_w0 = w0 * ratio
        projected_w1 = w1 * ratio
    elif None not in [x, p]:
        projected_w0 = p / projected_length
        projected_w1 = p / projected_length
    print(f"{projected_w1=}")
    return (
        round_to_close_integer(projected_w0),
        round_to_close_integer(projected_w1),
        round_to_close_integer(projected_x0),
        round_to_close_integer(projected_x1),
    )


def apply_minimum_width(
    magnitude: float,
    location: float,
    spread_width: float,
    wall_length: float,
) -> tuple[float, float, float, float]:
    """
    Returns a dictionary representing a distributed load
    representing the point load converted to a distributed
    load over the 'spread_width' in such a way that the 
    point load will be distributed an equal amount over
    half of the spread_width on each side of point load.

    If the point load location is 0 or wall_length, then
    the point load will be a distributed load over half
    of the spread_width (since there is not room for the
    other half). 

    Load locations between zero/wall_length and half of the 
    spread_width will be linearly interpolated.
    """
    assert spread_width <= wall_length
    if location <= spread_width / 2:
        projected_x0 = 0
        projected_x1 = location + spread_width / 2
    elif (wall_length - location) <= spread_width / 2:
        projected_x0 = location - spread_width / 2
        projected_x1 = wall_length
    else:
        projected_x0 = location - spread_width / 2
        projected_x1 = location + spread_width / 2

    projected_x1 = location + spread_width / 2
    projected_w0 = projected_w1 = magnitude / (projected_x1 - projected_x0)
    print(f"{projected_w0=}")
    return (
        round_to_close_integer(projected_w0),
        round_to_close_integer(projected_w1),
        round_to_close_integer(projected_x0),
        round_to_close_integer(projected_x1),
    )


def round_to_close_integer(x: float, eps=1e-7) -> float | int:
    """
    Rounds to the nearest int if it is REALLY close
    """
    if abs(abs(round(x)) - abs(x)) < eps:
        return round(x)
    else:
        return x
