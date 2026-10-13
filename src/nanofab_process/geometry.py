"""Pure geometry: rectangles with optional rotation in micrometers."""

from dataclasses import dataclass, replace
import math

from .config import MaskConfig, Structure
from .coordinate_text import coordinate_rectangles
from .extra_geometry import special_geometry, resolved_text


@dataclass(frozen=True)
class Rectangle:
    lower: tuple[float, float]
    upper: tuple[float, float]
    layer: str
    structure_id: str
    angle_deg: float = 0.0
    rotation_center: tuple[float, float] = (0.0, 0.0)

    @property
    def points(self) -> tuple[tuple[float, float], ...]:
        """Actual vertices; lower/upper describe the rectangle before rotation."""
        x0, y0 = self.lower
        x1, y1 = self.upper
        corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
        if self.angle_deg % 360 == 0:
            return corners
        angle = math.radians(self.angle_deg % 360)
        cosine, sine = math.cos(angle), math.sin(angle)
        cx, cy = self.rotation_center
        return tuple((cx + (x - cx) * cosine - (y - cy) * sine,
                      cy + (x - cx) * sine + (y - cy) * cosine) for x, y in corners)


def structure_rectangles(s: Structure) -> list[Rectangle]:
    if s.type not in ("line", "cross"):
        return special_geometry(s)
    x, y = s.center_um
    w, length = s.width_um, s.length_um

    def rect(x0, y0, x1, y1):
        return Rectangle((x + x0, y + y0), (x + x1, y + y1), s.layer, s.id, s.angle_deg, s.center_um)

    if s.type == "line":
        return [rect(-length / 2, -w / 2, length / 2, w / 2)]
    if s.type == "cross":
        # Two bars and two end caps form the cross; the fifth rectangle
        # is a detached square marker in the upper-right quadrant.
        h = w / 2
        rectangles = [
            rect(-length, -h, length, h),
            rect(-h, -length + w, h, length - w),
            rect(-h, length - w, h, length),
            rect(-h, -length, h, -length + w),
            rect(length - w, length - w, length, length),
        ]
        if s.show_coordinates:
            offset = length + s.label_height_um / 2
            rectangles.extend(rect(x0 + offset, y0, x1 + offset, y1)
                              for x0, y0, x1, y1 in coordinate_rectangles(x, y, s.label_height_um))
        return rectangles
    raise ValueError(f"Unsupported structure type: {s.type}")


def generate_geometry(config: MaskConfig) -> list[Rectangle]:
    rectangles = []
    for s in config.structures:
        if not s.enabled:
            continue
        if s.type == "label":
            s = replace(s, text=resolved_text(s, config), label_auto=False)
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
