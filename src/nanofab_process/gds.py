"""Export validated geometry with 1 um user units and 1 nm precision."""

import math
from pathlib import Path

import gdstk

from .config import MaskConfig
from .geometry import generate_geometry


def export_gds(config: MaskConfig, path: str | Path) -> Path:
    library = gdstk.Library(name=config.id, unit=1e-6, precision=1e-9)
    cell = library.new_cell(config.id)
    for rect in generate_geometry(config):
        points = rect.points
        coords = [v for point in points for v in point]
        if any(not math.isfinite(v) or abs(v) > 2147483.647 for v in coords):
            raise ValueError(f"{rect.structure_id}: coordinates exceed the GDS range at 1 nm precision")
        rounded = [(round(x * 1000), round(y * 1000)) for x, y in points]
        ox, oy = rounded[0]
        relative = [(x - ox, y - oy) for x, y in rounded]
        twice_area = sum(x * relative[(i + 1) % len(relative)][1] - y * relative[(i + 1) % len(relative)][0]
                         for i, (x, y) in enumerate(relative))
        if len(set(rounded)) < 3 or twice_area == 0:
            raise ValueError(f"{rect.structure_id}: rectangle collapses at 1 nm precision")
        layer = config.layers[rect.layer]
        cell.add(gdstk.Polygon(points, layer=layer.number, datatype=layer.datatype))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    library.write_gds(path)
    return path
