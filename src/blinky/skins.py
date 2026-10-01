"""The blinky roster: name and look of each slot, defaults plus the user's skins.json.

A blinky is a slot in this list; placements refer to slots, so edited looks show up at once.
Not here: drawing them. quickshell/Blinky/BlinkyFace.qml knows each shape and eye style.
"""

import json
import re
from pathlib import Path

from .config import ConfigError, config_file

SHAPES = ("circle", "squircle", "pebble", "cloud", "capsule")
EYES = ("tall", "round", "wide")
HEX = re.compile(r"#[0-9a-fA-F]{6}")
MAX_SKINS = 32
MAX_NAME = 24

DEFAULTS = (
    {"name": "Pip", "color": "#f2a7a0", "shape": "circle", "eyes": "tall", "blush": True},
    {"name": "Nori", "color": "#9fd4b0", "shape": "squircle", "eyes": "round", "blush": False},
    {"name": "Yuzu", "color": "#f3d27a", "shape": "pebble", "eyes": "tall", "blush": True},
    {"name": "Boba", "color": "#b9a4e8", "shape": "cloud", "eyes": "wide", "blush": True},
    {"name": "Kiwi", "color": "#c4dc7e", "shape": "capsule", "eyes": "round", "blush": False},
    {"name": "Miso", "color": "#e8b48a", "shape": "pebble", "eyes": "wide", "blush": True},
    {"name": "Sumi", "color": "#a9c8ef", "shape": "circle", "eyes": "round", "blush": False},
    {"name": "Ume", "color": "#ee9cc6", "shape": "squircle", "eyes": "tall", "blush": True},
    {"name": "Taro", "color": "#c9b8d8", "shape": "capsule", "eyes": "wide", "blush": True},
    {"name": "Mint", "color": "#8fd8d2", "shape": "cloud", "eyes": "tall", "blush": False},
)


def user_file() -> Path:
    """Where the settings page saves edited looks."""
    return config_file().parent / "skins.json"


def _validated(skin: object, where: str) -> dict:
    if not isinstance(skin, dict):
        raise ConfigError(f"{where}: expected an object")
    name, color = skin.get("name"), skin.get("color")
    if not isinstance(name, str) or not 0 < len(name.strip()) <= MAX_NAME:
        raise ConfigError(f"{where}: name must be 1-{MAX_NAME} characters")
    if not isinstance(color, str) or not HEX.fullmatch(color):
        raise ConfigError(f"{where}: color must look like #a1b2c3, got {color!r}")
    if skin.get("shape") not in SHAPES:
        raise ConfigError(f"{where}: shape must be one of {SHAPES}")
    if skin.get("eyes") not in EYES:
        raise ConfigError(f"{where}: eyes must be one of {EYES}")
    return {"name": name.strip(), "color": color.lower(), "shape": skin["shape"], "eyes": skin["eyes"],
            "blush": bool(skin.get("blush", False))}


def load() -> list[dict]:
    """The user's looks if skins.json exists, else the defaults."""
    path = user_file()
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return [dict(skin) for skin in DEFAULTS]
    except (OSError, json.JSONDecodeError) as err:
        raise ConfigError(f"{path}: {err}") from err
    if not isinstance(data, list) or not 0 < len(data) <= MAX_SKINS:
        raise ConfigError(f"{path}: expected a list of 1-{MAX_SKINS} looks")
    return [_validated(skin, f"{path} entry {i + 1}") for i, skin in enumerate(data)]


def load_or_defaults() -> tuple[list[dict], str]:
    """The looks to use, plus the error to show when skins.json is broken (defaults then)."""
    try:
        return load(), ""
    except ConfigError as err:
        return [dict(skin) for skin in DEFAULTS], str(err)
