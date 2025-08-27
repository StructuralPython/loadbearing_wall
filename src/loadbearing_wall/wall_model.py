from dataclasses import dataclass
from typing import Optional, Any, Union

from . import linear_reactions as lr
from . import point_reactions as pr
from . import geom_ops as geom
    

@dataclass
class LinearWallModel:
    height: float
    length: float
    vertical_spread_angle: float = 0.0
    distributed_loads: dict = dict() # Check no side-effects for multiple instances
    point_loads: dict = dict() # Check no side-effects for multiple instances
    gravity_dir: str = "z"
    inplane_dir: str = "x"
    out_of_plane_dir: str = "y"
    apply_spread_angle_gravity: True
    apply_spread_angle_inplane: True
    magnitude_start_key: str = "w0"
    magnitude_end_key: str = "w1"
    location_start_key: str = "x0"
    location_end_key: str = "x1"
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
    'magnitude_start_key': The key that will be used internally and in reaction results for the
        start magnitude
    'magnitude_end_key': The key that will be used internally and in reaction results for the
        end magnitude
    'location_start_key': The key that will be used internally and in reaction results for the
        start location
    'location_end_key': The key that will be used internally and in reaction results for the
        end location
    """
    def add_dist_load(
            self, 
            magnitude_start: float, 
            magnitude_end: float, 
            location_start: float, 
            location_end: float,
            case: str, 
            dir: str
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
        self.distributed_loads[dir][case].append({
            self.magnitude_start_key: magnitude_start,
            self.magnitude_end_key: magnitude_end,
            self.location_start_key: location_start,
            self.location_end_key: location_end,
        })

    def add_point_load(
            self, 
            magnitude: float, 
            location: float, 
            case: str, 
            dir: str
        ) -> None:
        """
        Adds a point load to the model

        'magnitude_start': The magnitude of the point load
        'location_start': The location on the wall of the point load (0.0 <= location <= self.length)
        'case': The load case of this load
        'dir': The direction the load is to be applied
        """
        assert 0.0 <= location <= self.length

        self.distributed_loads.setdefault(dir, {})
        self.distributed_loads[dir].setdefault(case, [])
        self.distributed_loads[dir][case].append({
            self.magnitude_start_key: magnitude,
            self.location_start_key: location,
        })
    
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
        for load_dir, load_cases in self.distributed_loads.items():
            proj.setdefault(load_dir, {})
            should_apply_spread_angle = (
                (
                    load_dir == self.gravity_dir
                    and self.apply_spread_angle_gravity
                    and self.vertical_spread_angle != 0.0
                )
                or 
                (
                    load_dir == self.inplane_dir
                    and self.apply_spread_angle_inplane
                    and self.vertical_spread_angle != 0.0
                )
            )
            for load_case, dist_loads in load_cases.items():
                proj[load_dir].setdefault(load_case, [])
                for dist_load in dist_loads:
                    if should_apply_spread_angle:
                        projected_load = geom.apply_spread_angle(
                            self.height, 
                            self.length, 
                            self.vertical_spread_angle,
                            dist_load[w0],
                            dist_load.get(w1),
                            dist_load[x0],
                            dist_load.get(x1),
                        )
                        proj[load_dir][load_case].append(projected_load)
                    else:
                        proj[load_dir][load_case].append(dist_load)
        self._projected_loads = proj


    def get_reactions(self, flattened: bool = False, direction_key: str = "dir", case_key: str = "case"):
        self.spread_loads()
        lrs = lr.LinearReactionString(
            self._projected_loads,
            self.magnitude_start_key,
            self.magnitude_end_key,
            self.location_start_key,
            self.location_end_key,
        )
        return lrs.consolidate_reactions(flatten=flattened, dir_key=direction_key, case_key=case_key)

    

