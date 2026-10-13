from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from nanofab_process.config import ConfigError, load_config, parse_config


EXAMPLE = Path(__file__).with_name("example.json")


def test_example():
    config = load_config(EXAMPLE)
    assert config.id == "demo"
    assert config.layers["metal"].number == 1
    assert [s.type for s in config.structures] == ["line", "cross"]
    assert config.structures[1].center_um == (500, 0)


@pytest.mark.parametrize("field,value", [
    ("type", "circle"), ("width_um", 0), ("length_um", -1),
    ("width_um", True), ("width_um", float("nan")),
    ("center_um", [0]), ("center_um", [0, float("inf")]),
    ("layer", "missing"), ("id", ""), ("width_um", "2"),
])
def test_invalid_structure(field, value):
    data = yaml.safe_load(EXAMPLE.read_text())
    data["structures"][0][field] = value
    with pytest.raises(ConfigError):
        parse_config(data)


def test_duplicates_unknown_fields_and_cross_ratio():
    data = yaml.safe_load(EXAMPLE.read_text())
    variants = []
    duplicate = deepcopy(data)
    duplicate["structures"][1]["id"] = "L1"
    variants.append(duplicate)
    typo = deepcopy(data)
    typo["structures"][0]["widht_um"] = 2
    variants.append(typo)
    cross = deepcopy(data)
    cross["structures"][1]["length_um"] = 3
    variants.append(cross)
    for variant in variants:
        with pytest.raises(ConfigError):
            parse_config(variant)


@pytest.mark.parametrize("text", ["", "[]", "mask: [", "mask: {}\nmask: {}"])
def test_bad_yaml(tmp_path, text):
    path = tmp_path / "bad.yaml"
    path.write_text(text)
    with pytest.raises(ConfigError):
        load_config(path)


@pytest.mark.parametrize("number", [-1, 65536, 1.5, True])
def test_invalid_layer(number):
    data = yaml.safe_load(EXAMPLE.read_text())
    data["layers"]["metal"]["number"] = number
    with pytest.raises(ConfigError):
        parse_config(data)


def test_unit_cell_name_and_empty_structures():
    data = yaml.safe_load(EXAMPLE.read_text())
    for section, key, value in [("mask", "unit", "mm"), ("mask", "id", "bad name")]:
        variant = deepcopy(data)
        variant[section][key] = value
        with pytest.raises(ConfigError):
            parse_config(variant)
    data["structures"] = []
    assert parse_config(data).structures == ()


@pytest.mark.parametrize("grid", [
    {"rows": 0, "columns": 2, "pitch_um": [20, 20]},
    {"rows": True, "columns": 2, "pitch_um": [20, 20]},
    {"rows": 2, "columns": 1.5, "pitch_um": [20, 20]},
    {"rows": 2, "columns": 2, "pitch_um": [0, 20]},
    {"rows": 2, "columns": 2, "pitch_um": [20]},
    {"rows": 2, "columns": 2, "pitch_um": [20, float("inf")]},
    {"rows": 2, "columns": 2},
    None,
])
def test_invalid_grid(grid):
    data = yaml.safe_load(EXAMPLE.read_text())
    data["structures"][1]["grid"] = grid
    with pytest.raises(ConfigError):
        parse_config(data)


@pytest.mark.parametrize("angle", [True, "45", None, float("nan"), float("inf")])
def test_invalid_angle(angle):
    data = yaml.safe_load(EXAMPLE.read_text())
    data["structures"][0]["angle_deg"] = angle
    with pytest.raises(ConfigError):
        parse_config(data)


def test_independent_angles_and_default():
    data = yaml.safe_load(EXAMPLE.read_text())
    assert parse_config(data).structures[0].angle_deg == 0
    data["structures"][0]["angle_deg"] = -45
    data["structures"][1]["angle_deg"] = 450
    config = parse_config(data)
    assert [s.angle_deg for s in config.structures] == [315, 90]


@pytest.mark.parametrize("field,value", [("enabled", 0), ("show_coordinates", "true"), ("label_height_um", 0)])
def test_invalid_object_options(field, value):
    data = yaml.safe_load(EXAMPLE.read_text())
    data["structures"][1][field] = value
    with pytest.raises(ConfigError):
        parse_config(data)


def test_labeled_cross_options():
    data = yaml.safe_load(EXAMPLE.read_text())
    data["structures"][0]["enabled"] = False
    data["structures"][1].update(show_coordinates=True, label_height_um=14)
    config = parse_config(data)
    assert not config.structures[0].enabled
    assert config.structures[1].show_coordinates
    assert config.structures[1].label_height_um == 14
