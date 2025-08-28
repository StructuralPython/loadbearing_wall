# Load-bearing Walls

Calculating the linear reactions for a load bearing wall _can_ be a pain in the but if you have anything more than one load source.

This package provides a simple analysis technique (like, the loads go down through the wall) for calculating the _consolidated_ reactions at the bottom of the wall when you have multiple load sources and multiple load directions. No FE here!

This package is intended to be material agnostic and allows the designer to specify behaviour such as the load spread, the spread angle, and if the spread applies to gravity, in-plane lateral, or both.

Point loads and distributed loads can be added to the wall. The designer defines the convention of their loading directions (e.g the `gravity` direction can be `"y"` or `"Fz"` or whatever you want).

## How to install

`pip install loadbearing_wall`

## How to use

```python
from loadbearing_wall import LinearWallModel

# Here is the example from the test suite

wall = LinearWallModel(
    height=2.0,
    length=4.0,
    vertical_spread_angle=0.0, # deg
    gravity_dir = "Fz",
    inplane_dir = "Fx",
    magnitude_start_key="w1",
    magnitude_end_key="w2",
    location_start_key="x1",
    location_end_key="x2",
)
```

> **Note:** You can add distributed loads and point loads at time of initialization (as dicts) or you can use the supplied `add_dist_load` and `add_point_load` methods.

### Adding loads

```python
# DEAD loads

wall.add_dist_load(
    magnitude_start=10,
    magnitude_end=10,
    location_start=0,
    location_end=4,
    case="D",
    dir="Fz"
)

wall.add_dist_load(
    magnitude_start=8,
    magnitude_end=8,
    location_start=1.5,
    location_end=3.25,
    case="D",
    dir="Fz"
)

# LIVE loads

wall.add_dist_load(
    magnitude_start=15,
    magnitude_end=15,
    location_start=0,
    location_end=4,
    case="L",
    dir="Fz"
)

wall.add_dist_load(
    magnitude_start=17.5,
    magnitude_end=17.5,
    location_start=1.5,
    location_end=3.25,
    case="L",
    dir="Fz"
)

## Wind load (in plane as point load)

wall.add_point_load(
    magnitude=100,
    location=0.0,
    case="W",
    dir="Fx" 
)
```

### Get Reactions

```python
wall.spread_loads() # Execute this first if you are spreading loads
reactions = wall.get_reactions()
```

### Results

In the results below, notice how there are two UDLs of different magnitudes for both the `"D"` and `"L"` load cases. This is because the point load spread out and, due to super-position, is added to the applied distributed load.

Note also how the point load is resisted by only `2.0` units of wall at the bottom. If the wall were really long (say `6` or `8` units), and a load is applied at a point, is it reasonable to say that the whole wall is engaged to resist the shear? This would not be the case if the wall had some sort of drag element on top to engage the whole wall. In that case, you would apply a distributed `"Fx"` load and then the whole wall would resist the shear.

```python
{'Fz': {'D': [{'w1': 9.333334,
    'w2': 9.333334,
    'x1': 0.0,
    'x2': 5.249999999999,
    'case': 'D',
    'dir': 'Fz'},
   {'w1': 6.666667,
    'w2': 6.666667,
    'x1': 5.250000000001,
    'x2': 6.0,
    'case': 'D',
    'dir': 'Fz'}],
  'L': [{'w1': 15.833333,
    'w2': 15.833333,
    'x1': 0.0,
    'x2': 5.249999999999,
    'case': 'L',
    'dir': 'Fz'},
   {'w1': 10.0,
    'w2': 10.0,
    'x1': 5.250000000001,
    'x2': 6.0,
    'case': 'L',
    'dir': 'Fz'}]},
 'Fx': {'W': [{'w1': 50.0,
    'w2': 50.0,
    'x1': 0.0,
    'x2': 2.0,
    'case': 'W',
    'dir': 'Fx'}]}}
```

## Limitations

- Does not calculate overturning moment on lateral loads (it would be nice if it can calculate the tension/compression forces based on a given `d`)
- I am sure there are others but I cannot think of them in the present moment when I am trying to upload this README.md!