from dataclasses import dataclass
from typing import Optional
from load_distribution import Singularity, singularities_to_polygon
from .geom_ops import round_to_close_integer as rtci


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
        if not any(
            [
                self.point_in_reaction(xa),
                self.point_in_reaction(xb),
                self.points_enclose_reaction(xa, xb),
            ]
        ):
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

        return LinearReaction(rtci(yi), rtci(yj), rtci(xi), rtci(xj))


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
        for load_dir, load_cases in projected_loads.items():
            linear_reaction_components.setdefault(load_dir, {})
            for load_case, applied_loads in load_cases.items():
                linear_reaction_components[load_dir].setdefault(load_case, [])
                for applied_load in applied_loads:
                    linear_reaction = LinearReaction(
                        applied_load[w0],
                        applied_load.get(w1),
                        applied_load[x0],
                        applied_load.get(x1),
                    )

                    linear_reaction_components[load_dir][load_case].append(
                        linear_reaction
                    )
        return cls(linear_reaction_components, w0, w1, x0, x1)

    def extract_reaction_string(
        self, xa: float, xb: float, case: str, dir: str
    ):
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
        self, flatten: bool, dir_key: str = "dir", case_key: str = "case"
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
        for load_dir, load_cases in self.linear_reactions.items():
            reaction_components.setdefault(load_dir, {})
            for load_case, linear_reactions in load_cases.items():
                reaction_components[load_dir].setdefault(load_case, [])
                singularity_functions = []
                for lr in linear_reactions:
                    if lr.w1 is None and lr.x1 is None:
                        point_load = {
                            w0: lr.w0,
                            x0: lr.x0,
                            dir_key: load_dir,
                            case_key: load_case,
                        }
                        flattened_reaction_components.append(point_load)
                        reaction_components[load_dir][load_case].append(point_load)
                    else:
                        m = (lr.w1 - lr.w0) / (lr.x1 - lr.x0)
                        y0 = lr.w0
                        singularity_function = Singularity(
                            x0=lr.x0, y0=y0, x1=lr.x1, m=m, precision=6
                        )
                        singularity_functions.append(singularity_function)
                if not singularity_functions:
                    continue
                linear_reactions = singularity_xy_to_distributed_loads(
                    singularities_to_polygon(singularity_functions, xy=True),
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
                reaction_components[load_dir][load_case] += linear_reactions
        if flatten:
            return flattened_reaction_components
        return reaction_components


def filter_repeated_y_values(
    xy_vals: list[list[float], list[float]],
) -> list[list[float, float]]:
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
    dist_loads = []
    prev_x = None
    for idx, (x, y) in enumerate(zip(*xy_vals)):
        if idx == 0:
            continue
        if prev_x is None:
            prev_x = x
            prev_y = y
        elif x - prev_x > 1e-3:
            dist_load = {
                w0: float(rtci(prev_y)),
                w1: float(rtci(y)),
                x0: float(rtci(prev_x)),
                x1: float(rtci(x)),
                case_key: case,
                dir_key: dir,
            }
            dist_loads.append(dist_load)
            prev_x = x
            prev_y = y
        else:
            prev_x = x
            prev_y = y
    return dist_loads
