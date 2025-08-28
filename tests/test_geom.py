from loadbearing_wall.geom_ops import apply_spread_angle


def test_apply_spread_angle():
    ret = apply_spread_angle(4, 3, spread_angle=10, w0=10, x0=1, w1=10, x1=2)
    assert ret == (
        4.148317542163208,
        4.148317542163208,
        0.2946920771661401,
        2.70530792283386,
    )
