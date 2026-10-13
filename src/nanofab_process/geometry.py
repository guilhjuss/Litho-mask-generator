"""Pure geometry, expressed as axis-aligned rectangles in micrometers."""

from dataclasses import dataclass, replace

from .config import MaskConfig, Structure


@dataclass(frozen=True)
class Rectangle:
    lower: tuple[float, float]
    upper: tuple[float, float]
    layer: str
    structure_id: str


def structure_rectangles(s: Structure) -> list[Rectangle]:
    x, y = s.center_um
    w, length = s.width_um, s.length_um

    def rect(x0, y0, x1, y1):
        return Rectangle((x + x0, y + y0), (x + x1, y + y1), s.layer, s.id)

    if s.type == "line":
        return [rect(-length / 2, -w / 2, length / 2, w / 2)]
    if s.type == "cross":
        # Two bars and two end caps form the cross; the fifth rectangle
        # is a detached square marker in the upper-right quadrant.
        h = w / 2
        return [
            rect(-length, -h, length, h),
            rect(-h, -length + w, h, length - w),
            rect(-h, length - w, h, length),
            rect(-h, -length, h, -length + w),
            rect(length - w, length - w, length, length),
        ]
    raise ValueError(f"Unsupported structure type: {s.type}")


def generate_geometry(config: MaskConfig) -> list[Rectangle]:
    rectangles = []
    for s in config.structures:
        if s.grid is None:
            rectangles.extend(structure_rectangles(s))
            continue
        # center_um locates the center of the entire matrix.
        grid = s.grid
        for row in range(grid.rows):
            for column in range(grid.columns):
                center = (
                    s.center_um[0] + (column - (grid.columns - 1) / 2) * grid.pitch_um[0],
                    s.center_um[1] + (row - (grid.rows - 1) / 2) * grid.pitch_um[1],
                )
                rectangles.extend(structure_rectangles(replace(s, center_um=center, grid=None)))
    return rectangles
