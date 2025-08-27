from dataclasses import dataclass
from typing import Optional
from load_distribution import Singularity, singularities_to_polygon

@dataclass
class LinearReaction:
    w0: float
    w1: float
    x0: float
    x1: float

    def point_in_reaction(self, x: float):
        return self.x0 <= x <= self.x1
    
    def points_enclose_reaction(self, xa: float, xb: float) -> bool:
        """
        Returns True if xa <= self.x0 <= self.x1 <= xb
        """
        return xa <= self.x0 <= self.x1 <= xb

    def extract_reaction(self, xa: float, xb: float) -> "LinearReaction":
        """
        Returns the portion of the reaction that would exist between
        'xa' and 'xb'
        """
        m = (self.w1 - self.w0) / (self.x1 - self.x0)
        y0 = self.w0
        if not any([
            self.point_in_reaction(xa), 
            self.point_in_reaction(xb),
            self.points_enclose_reaction(xa, xb),
        ]):
            return LinearReaction(0.0, 0.0, self.x0, self.x1) 
        if not self.point_in_reaction(xa):
            xi = self.x0
            yi = self.w0
        else:
            xi = xa
            yi = y0 + (xi - self.x0) * m

        if not self.point_in_reaction(xb):
            xj = self.x1
            yj = self.w1
        else:
            xj = xb
            yj = y0 + (xj - self.x0) * m

        return LinearReaction(yi, yj, xi, xj)


@dataclass
class LinearReactionString:
    """
    A class to manage a collection of LinearReactions
    """
    linear_reactions: dict[str, dict[str, list[LinearReaction]]]
    magnitude_start_key: str
    magnitude_end_key: str
    location_start_key: str
    location_end_key: str

    @classmethod
    def from_projected_loads(
        cls, 
        projected_loads: dict[str, dict[str, list[dict]]],
        magnitude_start_key: str,
        magnitude_end_key: str,
        location_start_key: str,
        location_end_key: str,
    ):
        w0 = magnitude_start_key
        w1 = magnitude_end_key
        x0 = location_start_key
        x1 = location_end_key
        linear_reaction_components = {}
        for load_dir, dir_loads in projected_loads.items():
            linear_reaction_components.setdefault(load_dir, {})
            for load_case, distributed_loads in dir_loads.items():
                linear_reaction_components[load_dir].setdefault(load_case, [])
                for distributed_load in distributed_loads:
                    linear_reaction = LinearReaction(
                        distributed_load[w0],
                        distributed_load[w1],
                        distributed_load[x0],
                        distributed_load[x1],
                    )
                linear_reaction_components[load_dir][load_case].append(linear_reaction)
        return cls(linear_reaction_components, w0, w1, x0, x1)


    def extract_reaction_string(self, xa: float, xb: float, case: str, dir: str) -> Optional[list[LinearReaction]]:
        """
        Returns a LinearReactionString representing the linear reactions that
        exist between 'xa' and 'xb' extracted from self.

        Returns None if there are no reactions within the 'x0' and 'x1' extents
        """
        extracted = {}
        extracted.setdefault(dir, {})
        extracted[dir].setdefault(case, [])
        for reaction in self.linear_reactions.get(dir, {}).get(case, {}):
            extracted_linear_reaction = reaction.extract_reaction(xa, xb)
            if extracted_linear_reaction.w0 != 0 and extracted_linear_reaction.w1 != 0:
                extracted[dir][case].append()
        return LinearReactionString(
            extracted,
            self.magnitude_start_key,
            self.magnitude_end_key,
            self.location_start_key,
            self.location_end_key,
        )
        
    
    def consolidate_reactions(
            self,
            flatten: bool, 
            dir_key: str = "dir", 
            case_key: str = "case"
        ):
        """
        Collects distributed loads from the top of a wall run and
        converts them into a LinearReactionString which can sum and
        parcel out the reactions into wall segments or beams that are
        supporting the wall run.

        A dict of 'dist_loads' should be organized as follows:

            {
                "dir1": {
                    "lc": [
                        {"w0": float, "w1": float, "x0": float, "x1": float}
                    ],
                    ...
                },
                ...
            }

        If 'flatten' is True then the results will be a list of load dicts.
            In this case then 'dir_key' and 'case_key' will be used to embed
            the direction and load case into each load_dict.
            Otherwise, the result will be a tree nested by direction and then
            by load case.
        """
        w0 = self.magnitude_start_key
        w1 = self.magnitude_end_key
        x0 = self.location_start_key
        x1 = self.location_end_key
        reaction_components = {}
        flattened_reaction_components = []
        for load_dir, dir_loads in self.linear_reactions.items():
            reaction_components.setdefault(load_dir, {})
            for load_case, distributed_loads in dir_loads.items():
                reaction_components[load_dir].setdefault(load_case, [])
                singularity_functions = []
                for dist_load in distributed_loads:
                    m = (dist_load[w1] - dist_load[w0]) / (dist_load[x1] - dist_load[x0])
                    y0 = dist_load[w0]
                    singularity_function = Singularity(x0=dist_load[x0], y0=y0, x1=dist_load[x1], m=m, precision=3)
                    singularity_functions.append(singularity_function)
                linear_reactions = singularity_xy_to_distributed_loads(
                    singularities_to_polygon(
                        singularity_functions, xy=True
                    ),
                    magnitude_start_key=w0,
                    magnitude_end_key=w1,
                    location_start_key=x0,
                    location_end_key=x1,
                    case=load_case,
                    dir=load_dir,
                    case_key="case",
                    dir_key="dir",
                )
                flattened_reaction_components.append(linear_reactions)

                # Get ride of the extrandious dir and case keys for unflattened results
                linear_reactions.pop(dir_key)
                linear_reactions.pop(case_key)
                reaction_components[load_dir][load_case] = linear_reactions
        if flatten:
            return flattened_reaction_components
        return reaction_components
            
        
def filter_repeated_y_values(xy_vals: list[list[float], list[float]]) -> list[list[float, float]]:
    """
    Returns xy_vals but with any "repeating" data points removed and
    returns a list of coordinates, list[list[float, float]]
    """
    coords = list(zip(*xy_vals))
    filtered = []
    for idx, (x, y) in enumerate(coords):
        next_y_idx = min(idx + 1, len(coords) - 1)
        next_y = coords[next_y_idx][1]
        if idx == 0:
            filtered.append([x, y])
            prev_y = y
        else:
            if prev_y == y == next_y:
                continue
            else:
                filtered.append([x, y])
        prev_y = y
    return filtered
        

def singularity_xy_to_distributed_loads(
    xy_vals: list[list[float], list[float]],
    magnitude_start_key: str,
    magnitude_end_key: str,
    location_start_key: str,
    location_end_key: str,
    case: str,
    dir: str,
    case_key: str = "case",
    dir_key: str = "dir",
) -> list[dict]:
    """
    Returns dicts representing distributed 
    """
    w0 = magnitude_start_key
    w1 = magnitude_end_key
    x0 = location_start_key
    x1 = location_end_key
    filtered = filter_repeated_y_values(xy_vals)
    dist_loads = []
    prev_x = None
    for idx, (x, y) in enumerate(filtered):
        if idx == 0: continue
        if prev_x is None:
            prev_x = x
            prev_y = y
        elif x - prev_x > 1e-3:
            dist_load = {w0: prev_y, w1: y, x0: prev_x,  x1: x, case_key: case, dir_key: dir}
            dist_loads.append(dist_load)
            prev_x = x
            prev_y = y
        else:
            prev_x = x
            prev_y = y
    return dist_loads