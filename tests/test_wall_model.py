from loadbearing_wall.wall_model import LinearWallModel
from pytest import fixture


@fixture
def WM0():
    return LinearWallModel(
        height=2.0,
        length=4.0,
        vertical_spread_angle=0.0,  # deg
        distributed_loads={
            "Fz": {
                "D": [{"w1": 10.0, "w2": 10.0, "x1": 1.0, "x2": 3.0}],
                "L": [{"w1": 15.0, "w2": 15.0, "x1": 0.0, "x2": 2.0}],
            }
        },
        point_loads={
            "Fz": {
                "D": [
                    {"p": 100.0, "x": 2.0},
                ],
                "L": [
                    {"p": 100.0, "x": 2.0},
                ],
            },
            "Fx": {"W": [{"p": 2000, "x": 0.0}]},
        },
        gravity_dir="Fz",
        inplane_dir="Fx",
        magnitude_start_key="w1",
        magnitude_end_key="w2",
        location_start_key="x1",
        location_end_key="x2",
    )


@fixture
def WM1(WM0):
    WM0.vertical_spread_angle = 45
    return WM0


def test_wall_model_runs(WM0, WM1):
    assert WM0.get_reactions()
    assert WM1.get_reactions()


def test_no_spread(WM0):
    rxn = WM0.get_reactions(flattened=False)
    assert rxn["Fz"]["D"] == [
        {"dir": "Fz", "case": "D", "w1": 10.0, "w2": 10.0, "x1": 1.00, "x2": 1.75},
        {"dir": "Fz", "case": "D", "w1": 210.0, "w2": 210.0, "x1": 1.750000000001, "x2": 2.249999999999},
        {"dir": "Fz", "case": "D", "w1": 10.0, "w2": 10.0, "x1": 2.250000000001, "x2": 3.0},
    ]
    assert rxn["Fz"]["L"] == [
        {"dir": "Fz", "case": "L", "w1": 15.0, "w2": 15.0, "x1": 0.00, "x2": 1.75},
        {"dir": "Fz", "case": "L", "w1": 215.0, "w2": 215.0, "x1": 1.750000000001, "x2": 2.00},
        {"dir": "Fz", "case": "L", "w1": 200.0, "w2": 200.0, "x1": 2.00, "x2": 2.249999999999},

        # {"dir": "Fz", "case": "L", "w1": 100.0, "x1": 0.5},
        # {"dir": "Fz", "case": "L", "w1": 15.0, "w2": 15.0, "x1": 0.0, "x2": 2.0},
    ]


def test_45_spread(WM1):
    rxn = WM1.get_reactions()
    assert rxn["Fz"]["D"] == [
        {
            "dir": "Fz",
            "case": "D",
            "w1": 30.0,
            "w2": 30.0,
            "x1": 0.0,
            "x2": 4.0,
        },
    ]

    assert rxn["Fz"]["L"] == [
        {
            "dir": "Fz",
            "case": "L",
            "w1": 32.5,
            "w2": 32.5,
            "x1": 0.0,
            "x2": 4.0,
        },
    ]


def test_serialization(WM0):
    serialized_dict = WM0.dump_dict()
    reconstituted = LinearWallModel.from_dict(serialized_dict)
    assert reconstituted == WM0

    import pathlib

    tempfile = pathlib.Path("tempfile.json")
    WM0.to_json(tempfile)
    recon2 = LinearWallModel.from_json(tempfile)
    assert WM0 == recon2
