from pydantic import BaseModel, Field
import pathlib
from typing import Optional, Any, Union
import safer

from . import linear_reactions as lr
from . import point_reactions as pr
from . import geom_ops as geom


class LinearWallModel(BaseModel):
    height: float
    length: float
    vertical_spread_angle: float = 0.0
    minimum_point_spread: float = 0.5
    distribute_loads_full_length: bool = False
    distributed_loads: dict = Field(default={})
    point_loads: dict = Field(default={})
    gravity_dir: str = "z"
    inplane_dir: str = "x"
    out_of_plane_dir: str = "y"
    apply_spread_angle_gravity: bool = True
    apply_spread_angle_inplane: bool = True
    magnitude_point_key: str = "p"
    magnitude_start_key: str = "w0"
    magnitude_end_key: str = "w1"
    location_point_key: str = "x"
    location_start_key: str = "x0"
    location_end_key: str = "x1"
    reverse_reaction_force_direction: bool = True
    _projected_loads: Optional[dict] = None
    """
    A model of a linear load-bearing wall segment. The segment is assumed to be linear
    and continuous.

    'height': The height of the wall
    'lenght': The length of the wall
    'vertical_spread_angle': Angle in degrees. Applied loads in the gravity direction
        spread through to the base of the wall according to this angle. The angle is 
        measured as deviation off of the direction of gravity (i.e. 0.0 is the in the
        gravity direction and 30.0 is 30 degrees away from vertical)
    'minimum_point_spread': For point loads applied without a spread angle, this is minimum width
        over which the point load will be spread. Whether this value is realistic or not depends on
        your context and the length unit system you are using. In other words, all applied point loads
        will be converted to distributed loads spread over this distance unless a vertical spread
        angle is applied.
    'distribute_loads_full_length': If True, will override both 'vertical_spread_angle' and
        'minimum_point_spread' and will distribute all loads evenly across the whole wall panel.
    'distributed_loads': A dictionary of loads. Can be set directly or using the .add_dist_load()
        methods
    'point_loads': A dictionary of loads. Can be set directly or using the .add_point_load()
        methods
    'gravity_dir': A label used for the gravity direction. Must match the direction labels
        used in the applied loads for applied loads in the gravity direction.
    'inplane_dir': A label used for the inplane direction. Must match the direction labels
        used in the applied loads for applied loads in the inplane direction.
    'out_of_plane_dir': A label used for the out_of_plane direction. Must match the direction labels
        used in the applied loads for applied loads in the out_of_plane direction.
    'magnitude_point_key': The key that will be used internally to describe the magnitude of
        point loads.
    'magnitude_start_key': The key that will be used internally (and in reaction results) for the
        start magnitude
    'magnitude_end_key': The key that will be used internally (and in reaction results) for the
        end magnitude
    'location_key': The key that will be used internally to describe the location of applied
        point loads.
    'location_start_key': The key that will be used internally (and in reaction results) for the
        start location
    'location_end_key': The key that will be used internally (and in reaction results) for the
        end location
    'reverse_reaction_force_direction': If True, the reactions will be represented with a load
        of the opposite sign as the input load.
    """

    @classmethod
    def from_json(cls, filepath: str | pathlib.Path):
        with safer.open(filepath) as file:
            json_data = file.read()
        return cls.model_validate_json(json_data)

    def to_json(self, filepath: str | pathlib.Path, indent=2):
        json_data = self.model_dump_json(indent=indent)
        with safer.open(filepath, "w") as file:
            file.write(json_data)

    @classmethod
    def from_dict(cls, data: dict):
        return cls.model_validate(data)

    def dump_dict(self):
        return self.model_dump(mode="json")

    def add_dist_load(
        self,
        magnitude_start: float,
        magnitude_end: float,
        location_start: float,
        location_end: float,
        case: str,
        dir: str,
    ) -> None:
        """
        Adds a distributed load to the model

        'magnitude_start': The magnitude at the start of the linear distributed load
        'magnitude_end': The magnitude at the end ...
        'location_start': The start location on the wall of the dist load (>=0.0)
        'location_end': The end location on the wall of the dist load (<= self.length)
        'case': The load case of this load
        'dir': The direction the load is to be applied
        """
        assert location_start >= 0.0
        assert location_end <= self.length

        self.distributed_loads.setdefault(dir, {})
        self.distributed_loads[dir].setdefault(case, [])
        self.distributed_loads[dir][case].append(
            {
                self.magnitude_start_key: magnitude_start,
                self.magnitude_end_key: magnitude_end,
                self.location_start_key: location_start,
                self.location_end_key: location_end,
            }
        )

    def add_point_load(
        self, magnitude: float, location: float, case: str, dir: str
    ) -> None:
        """
        Adds a point load to the model

        'magnitude_start': The magnitude of the point load
        'location_start': The location on the wall of the point load (0.0 <= location <= self.length)
        'case': The load case of this load
        'dir': The direction the load is to be applied
        """
        assert 0.0 <= location <= self.length

        self.point_loads.setdefault(dir, {})
        self.point_loads[dir].setdefault(case, [])
        self.point_loads[dir][case].append(
            {
                self.magnitude_point_key: magnitude,
                self.location_point_key: location,
            }
        )

    def spread_loads(self) -> None:
        """
        Populates self._projected_loads with the loads projected from the distributed
        and point loads.

        This is an intermediate step to retrieving the consolidated reactions.
        """
        self._projected_loads = {}
        proj = self._projected_loads
        w0 = self.magnitude_start_key
        w1 = self.magnitude_end_key
        x0 = self.location_start_key
        x1 = self.location_end_key
        p = self.magnitude_point_key
        x = self.location_point_key
        for load_dir, load_cases in self.distributed_loads.items():
            proj.setdefault(load_dir, {})
            should_apply_spread_angle = (
                load_dir == self.gravity_dir
                and self.apply_spread_angle_gravity
                and self.vertical_spread_angle != 0.0
            ) or (
                load_dir == self.inplane_dir
                and self.apply_spread_angle_inplane
                and self.vertical_spread_angle != 0.0
            )
            for load_case, dist_loads in load_cases.items():
                proj[load_dir].setdefault(load_case, [])
                for dist_load in dist_loads:
                    if should_apply_spread_angle:
                        projected_load = geom.apply_spread_angle(
                            self.height,
                            self.length,
                            self.vertical_spread_angle,
                            w0=dist_load[w0],
                            x0=dist_load[x0],
                            w1=dist_load.get(w1),
                            x1=dist_load.get(x1),
                        )
                        proj[load_dir][load_case].append(
                            {
                                w0: projected_load[0],
                                w1: projected_load[1],
                                x0: projected_load[2],
                                x1: projected_load[3],
                            }
                        )
                    elif self.distribute_loads_full_length:
                        w0 = dist_load[w0]
                        w1 = dist_load[w1]
                        x0 = dist_load[x0]
                        x1 = dist_load[x1]
                        total_load = (w0 + w1) / 2 * (x1 - x0)
                        w_full = total_load / self.length
                        proj[load_dir][load_case].append(
                            {w0: w_full, w1: w_full, x0: 0.0, x1: self.length}
                        )
                    else:
                        proj[load_dir][load_case].append(dist_load)

        for load_dir, load_cases in self.point_loads.items():
            proj.setdefault(load_dir, {})
            should_apply_spread_angle = (
                load_dir == self.gravity_dir
                and self.apply_spread_angle_gravity
                and self.vertical_spread_angle != 0.0
            ) or (
                load_dir == self.inplane_dir
                and self.apply_spread_angle_inplane
                and self.vertical_spread_angle != 0.0
            )
            for load_case, point_loads in load_cases.items():
                proj[load_dir].setdefault(load_case, [])
                for point_load in point_loads:
                    if should_apply_spread_angle:
                        projected_load = geom.apply_spread_angle(
                            self.height,
                            self.length,
                            self.vertical_spread_angle,
                            p=point_load[p],
                            x=point_load[x],
                        )
                        proj[load_dir][load_case].append(
                            {
                                w0: projected_load[0],
                                w1: projected_load[1],
                                x0: projected_load[2],
                                x1: projected_load[3],
                            }
                        )
                    elif self.distribute_loads_full_length:
                        total_load = point_load[p]
                        w_full = total_load / self.length
                        proj[load_dir][load_case].append(
                            {w0: w_full, w1: w_full, x0: 0.0, x1: self.length}
                        )
                    else:
                        projected_load = geom.apply_minimum_width(
                            point_load[p],
                            point_load[x],
                            self.minimum_point_spread,
                            self.length,
                        )
                        proj[load_dir][load_case].append(
                            {
                                w0: projected_load[0],
                                w1: projected_load[1],
                                x0: projected_load[2],
                                x1: projected_load[3],
                            }
                        )

        self._projected_loads = proj

    def get_reactions(
        self,
        flattened: bool = False,
        direction_key: str = "dir",
        case_key: str = "case",
    ):
        self.spread_loads()  # Populates self._projected_loads
        lrs = lr.LinearReactionString.from_projected_loads(
            self._projected_loads,
            self.magnitude_start_key,
            self.magnitude_end_key,
            self.location_start_key,
            self.location_end_key,
            self.reverse_reaction_force_direction,
        )
        return lrs.consolidate_reactions(
            flatten=flattened, dir_key=direction_key, case_key=case_key
        )
