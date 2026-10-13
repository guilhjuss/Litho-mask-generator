from pathlib import Path

import gdstk
import pytest

from nanofab_process.cli import main
from nanofab_process.config import Structure, load_config
from nanofab_process.gds import export_gds
from nanofab_process.geometry import structure_rectangles


EXAMPLE = Path(__file__).with_name("example.yaml")


def test_line_dimensions_and_translation():
    rect, = structure_rectangles(Structure("line", "L", (20, -5), 10, 400, "metal"))
    assert rect.lower == (-180, -10)
    assert rect.upper == (220, 0)
    assert rect.layer == "metal"


def test_cross_bounds_marker_and_area():
    rects = structure_rectangles(Structure("cross", "C", (500, 30), 2, 6, "metal"))
    assert len(rects) == 5
    assert (min(r.lower[0] for r in rects), min(r.lower[1] for r in rects)) == (494, 24)
    assert (max(r.upper[0] for r in rects), max(r.upper[1] for r in rects)) == (506, 36)
    assert rects[-1].lower == (504, 34)
    assert rects[-1].upper == (506, 36)
    polygons = [gdstk.rectangle(r.lower, r.upper) for r in rects]
    # Cross union: 12*2 + 12*2 - 2*2; marker adds 2*2.
    assert sum(p.area() for p in gdstk.boolean(polygons, [], "or")) == pytest.approx(48)


def test_gds_round_trip(tmp_path):
    config = load_config(EXAMPLE)
    output = export_gds(config, tmp_path / "nested" / "mask.gds")
    library = gdstk.read_gds(output)
    assert library.unit == pytest.approx(1e-6)
    assert library.precision == pytest.approx(1e-9)
    cell, = library.top_level()
    assert cell.name == "demo"
    assert len(cell.polygons) == 6
    assert {(p.layer, p.datatype) for p in cell.polygons} == {(1, 0)}
    assert cell.bounding_box() == ((-200, -6), (506, 6))
    assert cell.polygons[0].area() == pytest.approx(4000)


def test_cli_success_and_failure(tmp_path, capsys):
    output = tmp_path / "cli.gds"
    assert main([str(EXAMPLE), "-o", str(output)]) == 0
    assert output.exists()
    assert "Wrote" in capsys.readouterr().out
    with pytest.raises(SystemExit) as exc:
        main([str(tmp_path / "missing.yaml")])
    assert exc.value.code == 2
    assert "Error:" in capsys.readouterr().err


@pytest.mark.parametrize("width,center", [(0.0001, (0, 0)), (10, (3e6, 0))])
def test_export_rejects_unrepresentable_geometry(tmp_path, width, center):
    config = load_config(EXAMPLE)
    from dataclasses import replace
    line = replace(config.structures[0], width_um=width, center_um=center)
    config = replace(config, structures=(line,))
    with pytest.raises(ValueError):
        export_gds(config, tmp_path / "bad.gds")
    assert not (tmp_path / "bad.gds").exists()


@pytest.mark.parametrize("rows,columns", [(3, 4), (2, 3), (1, 1)])
def test_grid_positions_and_export(tmp_path, rows, columns):
    from dataclasses import replace
    from nanofab_process.config import Grid
    from nanofab_process.geometry import generate_geometry
    config = load_config(EXAMPLE)
    cross = replace(config.structures[1], center_um=(10, -20), grid=Grid(rows, columns, (30, 40)))
    config = replace(config, structures=(cross,))
    rectangles = generate_geometry(config)
    assert len(rectangles) == rows * columns * 5
    centers = [((r.lower[0] + r.upper[0]) / 2, (r.lower[1] + r.upper[1]) / 2) for r in rectangles[::5]]
    assert centers == [(10 + (c - (columns - 1) / 2) * 30, -20 + (r - (rows - 1) / 2) * 40)
                       for r in range(rows) for c in range(columns)]
    library = gdstk.read_gds(export_gds(config, tmp_path / "matrix.gds"))
    assert len(library.top_level()[0].polygons) == rows * columns * 5
