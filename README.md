# Litho mask generator

A small, standalone nanofabrication mask generator. Edit one YAML file to choose structures, dimensions, positions and layers.

`mask.yaml -> config.py -> geometry.py -> gds.py -> output.gds`

## Install and run

Requires Python 3.10 or newer. From this repository folder:

```sh
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
nanofab mask.yaml -o output.gds
python -m pytest
```

You can also run `python -m nanofab_process.cli mask.yaml -o output.gds`.
Open the generated GDSII file in a layout viewer such as KLayout.

## One YAML file

```yaml
mask:
  id: demo3
  unit: um
layers:
  metal:
    number: 1
    datatype: 0
structures:
  - type: line
    id: L1
    center_um: [0, 0]
    width_um: 10
    length_um: 400
    layer: metal
  - type: cross
    id: C1
    center_um: [0, 0]
    width_um: 50
    length_um: 200
    layer: metal
    grid:
      rows: 3
      columns: 4
      pitch_um: [600, 600]
```

All dimensions and coordinates are micrometers. Positive x is right, positive y is up.

- **line:** horizontal rectangle. `length_um` is its full x extent, `width_um` is its full y extent.
- **cross:** alignment cross centered at `center_um`, with arm thickness `width_um`. `length_um` is the distance from center to an outer arm tip; overall bounds are `2 * length_um` by `2 * length_um`. Width 2 and length 6 therefore gives a 12 x 12 um cross.
- The cross uses five rectangles: two bars, two end caps, and a detached square orientation marker in the upper-right quadrant. The marker has side `width_um` and stays within the overall bounds. `length_um` must be at least twice `width_um` to keep it detached.

This preserves the cross concept and dimension convention from the earlier project; it is a fresh implementation, not an exact copy of its geometry.

Each structure has a unique `id` and refers to a named layer. Layer `datatype` defaults to 0. IDs identify geometry in Python; they do not add labels to the mask. GDS export creates one top-level cell named `mask.id` using [gdstk](https://heitzmann.github.io/gdstk/library/gdstk.Library.html), with 1 um units and 1 nm precision. Coordinates are rounded to that grid; rectangles that collapse or exceed GDS coordinate limits are rejected.

Validation rejects unknown fields, duplicate YAML keys or structure IDs, unsupported types, unknown layers, nonfinite coordinates, and nonpositive dimensions. Cell names use 1-32 ASCII letters, digits and underscores, starting with a letter or underscore. Layer numbers and datatypes are integers from 0 to 65535.

## Files

```text
README.md
pyproject.toml
mask.yaml
src/nanofab_process/
    __init__.py
    config.py
    geometry.py
    coordinate_text.py
    gds.py
    cli.py
tests/
    test_config.py
    test_geometry.py
```

## Matrices

Add an optional `grid` to any line or cross entry:

```yaml
    grid:
      rows: 3
      columns: 4
      pitch_um: [600, 600]
```

`center_um` is the center of the entire matrix. `pitch_um` specifies the center-to-center spacing in x and y, in micrometers. Rows run along y and columns along x. All copies have the same dimensions and layer. Positive integer row/column counts and positive finite pitches are required. Copies may overlap if the pitch is too small; spacing is not an edge-to-edge gap.

Always edit `mask.yaml` and run `nanofab mask.yaml -o output.gds`. The included mask contains one line and 12 crosses, each 400 x 400 um with 50 um thick arms, spaced 600 um apart. Existing entries without `grid` remain single structures. Remove the `grid` block to return to one cross, or add more entries under `structures` to combine other structures in the same mask.

## Rotation

Each entry under `structures` can have its own optional `angle_deg`, beside `type`, `id`, and `center_um`. It defaults to 0. Positive angles rotate counterclockwise around the structure center; negative angles rotate clockwise. For example, `angle_deg: 90` makes a line vertical, and `angle_deg: 45` makes it diagonal. Any finite numeric angle is allowed; angles wrap at 360 degrees.

For a matrix, each copy rotates around its own center with the entry's angle. The grid centers and x/y pitch do not rotate. A cross's orientation marker rotates with its arms. Use separate structure entries for different angles, including separate grid entries for differently rotated matrices. No global angle is required. Rotation can increase the overall bounding box and cause nearby copies to overlap.

```yaml
  - type: line
    id: diagonal_lines
    center_um: [1000, 0]
    width_um: 5
    length_um: 100
    layer: metal
    angle_deg: 45
    grid:
      rows: 2
      columns: 3
      pitch_um: [150, 150]
```

## Object options and coordinate labels

Any entry can use `enabled: false` to keep its settings in the YAML while omitting it from the generated mask. It defaults to true.

Cross entries can use `show_coordinates: true` and optional `label_height_um: 20`. The center coordinates are generated as physical polygon text, in micrometers rounded to 0.001 um, on the same layer as the cross. Each matrix copy displays its own absolute center coordinates. The two-line text starts to the right of the cross and rotates with it. Text is included in GDS geometry, bounds and range checks; it is not a viewer-only annotation. Default text height is 20 um. Unsupported options and nonpositive text heights are rejected.

The generator has no recursive YAML includes or titles. Add structures directly to `structures`. Export overwrites the selected output file. This project is independent of the existing shared repository.
