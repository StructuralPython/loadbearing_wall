from loadbearing_wall.wall_model import LinearWallModel
from pytest import fixture

@fixture
def WM0():
    return LinearWallModel(
        height=2.0,
        length=4.0,
        vertical_spread_angle=0.0, # deg
        distributed_loads = {
            "Fz": {
                "D": [
                    {"w1": 10.0, "w2": 10.0, "x1": 1.0, "x2": 3.0}
                ],
                "L": [
                    {"w1": 15.0, "w2": 15.0, "x1": 0.0, "x2": 2.0}
                ]
            }
        },
        point_loads = {
            "Fz": {
                "D": [
                    {"w1": 100.0, "x1": 0.5},
                ],
                "L": [
                    {"w1": 100.0, "x1": 0.5},
                ]
            }
        },
        gravity_dir = "Fz",
        inplane_dir = "Fx",
        magnitude_start_key="w1",
        magnitude_end_key="w2",
        location_start_key="x1",
        location_end_key="x2",
    )

@fixture
def WM1(WM0):
    WM0.vertical_spread_angle=45
    return WM0


def test_wall_model_runs(WM0, WM1):
    assert WM0.get_reactions()
    assert WM1.get_reactions()