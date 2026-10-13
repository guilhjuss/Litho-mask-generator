"""Parse and validate a single mask YAML file."""

from dataclasses import dataclass
import math
from pathlib import Path
import re

import yaml


@dataclass(frozen=True)
class Layer:
    number: int
    datatype: int = 0


@dataclass(frozen=True)
class Grid:
    rows: int
    columns: int
    pitch_um: tuple[float, float]


@dataclass(frozen=True)
class Structure:
    type: str
    id: str
    center_um: tuple[float, float]
    width_um: float
    length_um: float
    layer: str
    grid: Grid | None = None
    angle_deg: float = 0.0
    enabled: bool = True
    show_coordinates: bool = False
    label_height_um: float = 20.0


@dataclass(frozen=True)
class MaskConfig:
    id: str
    layers: dict[str, Layer]
    structures: tuple[Structure, ...]


class ConfigError(ValueError):
    """An invalid mask configuration."""


class _UniqueLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ConfigError("YAML keys must be unique strings")
        result[key] = loader.construct_object(value_node)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _fields(value, required, optional, context):
    if not isinstance(value, dict):
        raise ConfigError(f"{context} must be a mapping")
    missing = required - value.keys()
    unknown = value.keys() - required - optional
    if missing or unknown:
        raise ConfigError(f"{context}: missing fields {sorted(missing)}, unknown fields {sorted(unknown)}")
    return value


def _text(value, context):
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{context} must be a nonempty string")
    return value


def _number(value, context, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{context} must be a finite number")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ConfigError(f"{context} is too large") from exc
    if not math.isfinite(value) or (positive and value <= 0):
        raise ConfigError(f"{context} must be finite" + (" and positive" if positive else ""))
    return value


def parse_config(data) -> MaskConfig:
    root = _fields(data, {"mask", "layers", "structures"}, set(), "config")
    mask = _fields(root["mask"], {"id", "unit"}, set(), "mask")
    mask_id = _text(mask["id"], "mask.id")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,31}", mask_id):
        raise ConfigError("mask.id must be a GDS cell name: 1-32 ASCII letters, digits or underscores; start with a letter or underscore")
    if mask["unit"] != "um":
        raise ConfigError("mask.unit must be 'um'")
    if not isinstance(root["layers"], dict) or not root["layers"]:
        raise ConfigError("layers must be a nonempty mapping")
    layers = {}
    for name, raw in root["layers"].items():
        _text(name, "layer name")
        raw = _fields(raw, {"number"}, {"datatype"}, f"layer {name}")
        values = (raw["number"], raw.get("datatype", 0))
        if any(type(v) is not int or not 0 <= v <= 65535 for v in values):
            raise ConfigError(f"layer {name}: number and datatype must be integers from 0 to 65535")
        layers[name] = Layer(*values)
    if not isinstance(root["structures"], list):
        raise ConfigError("structures must be a list")
    structures, ids = [], set()
    for index, raw in enumerate(root["structures"]):
        context = f"structures[{index}]"
        raw = _fields(raw, {"type", "id", "center_um", "width_um", "length_um", "layer"}, {"grid", "angle_deg", "enabled", "show_coordinates", "label_height_um"}, context)
        kind = _text(raw["type"], context + ".type")
        if kind not in ("line", "cross"):
            raise ConfigError(f"{context}: type must be line or cross")
        sid = _text(raw["id"], context + ".id")
        if sid in ids:
            raise ConfigError(f"duplicate structure id: {sid}")
        ids.add(sid)
        center = raw["center_um"]
        if not isinstance(center, list) or len(center) != 2:
            raise ConfigError(f"{context}: center_um must be [x, y]")
        center = tuple(_number(v, context + ".center_um") for v in center)
        width = _number(raw["width_um"], context + ".width_um", True)
        length = _number(raw["length_um"], context + ".length_um", True)
        if kind == "cross" and length < 2 * width:
            raise ConfigError(f"{context}: cross length_um must be at least 2 * width_um")
        layer = _text(raw["layer"], context + ".layer")
        if layer not in layers:
            raise ConfigError(f"{context}: unknown layer {layer}")
        grid = None
        if "grid" in raw:
            values = _fields(raw["grid"], {"rows", "columns", "pitch_um"}, set(), context + ".grid")
            rows, columns = values["rows"], values["columns"]
            if any(type(v) is not int or v <= 0 for v in (rows, columns)):
                raise ConfigError(f"{context}: grid rows and columns must be positive integers")
            pitch = values["pitch_um"]
            if not isinstance(pitch, list) or len(pitch) != 2:
                raise ConfigError(f"{context}: grid pitch_um must be [x_spacing, y_spacing]")
            grid = Grid(rows, columns, tuple(_number(v, context + ".grid.pitch_um", True) for v in pitch))
        angle = _number(raw.get("angle_deg", 0), context + ".angle_deg") % 360
        enabled = raw.get("enabled", True)
        show_coordinates = raw.get("show_coordinates", False)
        if type(enabled) is not bool or type(show_coordinates) is not bool:
            raise ConfigError(f"{context}: enabled and show_coordinates must be true or false")
        if show_coordinates and kind != "cross":
            raise ConfigError(f"{context}: coordinate labels are supported on crosses")
        label_height = _number(raw.get("label_height_um", 20), context + ".label_height_um", True)
        structures.append(Structure(kind, sid, center, width, length, layer, grid, angle, enabled, show_coordinates, label_height))
    return MaskConfig(mask_id, layers, tuple(structures))


def load_config(path: str | Path) -> MaskConfig:
    try:
        with Path(path).open(encoding="utf-8") as stream:
            data = yaml.load(stream, Loader=_UniqueLoader)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML: {exc}") from exc
    return parse_config(data)
