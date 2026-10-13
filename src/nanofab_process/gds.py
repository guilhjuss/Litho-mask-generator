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
        coords = (*rect.lower, *rect.upper)
        if any(not math.isfinite(v) or abs(v) > 2147483.647 for v in coords):
            raise ValueError(f"{rect.structure_id}: coordinates exceed the GDS range at 1 nm precision")
        if any(round(rect.upper[i] * 1000) <= round(rect.lower[i] * 1000) for i in (0, 1)):
            raise ValueError(f"{rect.structure_id}: rectangle collapses at 1 nm precision")
        layer = config.layers[rect.layer]
        cell.add(gdstk.rectangle(rect.lower, rect.upper, layer=layer.number, datatype=layer.datatype))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    library.write_gds(path)
    return path
