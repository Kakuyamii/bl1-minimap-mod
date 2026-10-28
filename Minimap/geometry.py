from dataclasses import dataclass
from math import isfinite


def coordinate_scale(anchor_size, map_size):

    if not all(isfinite(v) and v > 0 for v in (*anchor_size, *map_size)):
        raise ValueError("Map dimensions must be finite and positive")
    fx, fy = anchor_size[0] / map_size[0], anchor_size[1] / map_size[1]
    return max(1.0, fx / fy), max(1.0, fy / fx)


@dataclass(frozen=True)
class Projection:
    rows: tuple

    def uv(self, position):
        x, y, z = position
        a, b, c, d = self.rows
        return (x*a[1]+y*b[1]+z*c[1]+d[1]+0.5,
                0.5-(x*a[0]+y*b[0]+z*c[0]+d[0]))
