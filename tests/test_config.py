from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from nanofab_process.config import ConfigError, load_config, parse_config


EXAMPLE = Path(__file__).resolve().parents[1] / "mask.yaml"


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
    with pytest.raises(ConfigError):
        parse_config(data)
