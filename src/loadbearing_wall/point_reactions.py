from dataclasses import dataclass

@dataclass
class PointReactionCollection:
    _reaction_components: dict[str, dict[str, list[float]]]


    def extract_reactions(self, case: str, dir: str) -> float:
        """
        Returns a float representing the total sum of loads for the
        given 'dir' (direction) and 'case' (load case).
        """
        return sum(self._reaction_components.get(case, {}).get(dir, []))
    

    @classmethod
    def from_point_loads(cls, point_loads: dict[str, dict[str, str | float]]):
        """
        
        """
        reaction_components = {}
        for load_case in point_loads.items():
            reaction_components.setdefault(load_case, {})
            for load_dir, pt_loads in load_case.items():
                reaction_components[load_case].setdefault(load_dir, [])
                for point_load in pt_loads:
                    reaction_components[load_dir][load_case].append(point_load['magnitude'])
        return cls(reaction_components)
    
    
    

                    

