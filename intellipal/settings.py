from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict

DEFAULT_LABELS = [
    "Black",
    "Blue",
    "Red",
    "Tan",
    "Dark Green",
    "Light Green",
    "Yellow",
    "White",
    "Gray",
    "Cyan",
    "Orange",
    "Brown",
    "Magenta",
    "Light Blue",
    "Yellow-Green",
    "Purple",
]

SCREENSHOT_RES_OPTIONS = [
    "1x (320x200)",
    "2x (640x400)",
    "3x (960x600)",
    "4x (1280x800)",
]

DEFAULT_SETTINGS = {
    "palette_dir": "./palettes",
    "palette_extensions": ".cfg|.txt",
    "color_save_format": "#rrggbb",
    "color_labels": DEFAULT_LABELS,
    "save_extension": ".txt",
    "start_dock_state": "Left",
    "emulator_poll_rate": 10,
    "emulator_start_res": "1024x768,8",
    "exec_file_path": "./exec.bin",
    "grom_file_path": "./grom.bin",
    "log_file": "",
    "roms_folder": "",
    "screenshot_path": "./Screenshots",
    "default_screenshot_res": "1x (320x200)",
    "jzintv_flags": "",
    "game_resolutions": [
        "320x240,8",
        "400x300,8",
        "512x384,8",
        "640x480,8",
        "800x600,16",
        "960x720,16",
        "1024x768,16",
        "1280x960,16",
        "1400x1050,32",
        "1600x1200,32",
        "720x405,8",
        "1280x720,8",
        "1600x900,8",
        "2560x1440,16",
    ],
    "isolate_background": "#000000",
}


def get_config_path() -> Path:
    if os.name == "nt":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "IntelliPal" / "settings.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "IntelliPal" / "settings.json"
    base = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "intellipal" / "settings.json"


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def normalize_settings(settings: Dict) -> Dict:
    normalized = dict(DEFAULT_SETTINGS)
    normalized.update(settings or {})

    labels = normalized.get("color_labels")
    if not isinstance(labels, list) or len(labels) != 16:
        normalized["color_labels"] = DEFAULT_LABELS

    if normalized.get("color_save_format") not in ("#rrggbb", "R G B", "RRR GGG BBB"):
        normalized["color_save_format"] = "#rrggbb"

    palette_extensions = normalized.get("palette_extensions")
    if not palette_extensions or not isinstance(palette_extensions, str):
        normalized["palette_extensions"] = DEFAULT_SETTINGS["palette_extensions"]

    save_extension = normalized.get("save_extension")
    if not save_extension or not isinstance(save_extension, str):
        normalized["save_extension"] = DEFAULT_SETTINGS["save_extension"]

    palette_dir = normalized.get("palette_dir")
    if not palette_dir or not isinstance(palette_dir, str):
        normalized["palette_dir"] = DEFAULT_SETTINGS["palette_dir"]

    start_dock_state = normalized.get("start_dock_state")
    if start_dock_state not in ("Left", "Right", "None"):
        normalized["start_dock_state"] = DEFAULT_SETTINGS["start_dock_state"]

    emulator_poll_rate = normalized.get("emulator_poll_rate")
    if not isinstance(emulator_poll_rate, int) or emulator_poll_rate < 0:
        normalized["emulator_poll_rate"] = DEFAULT_SETTINGS["emulator_poll_rate"]

    emulator_start_res = normalized.get("emulator_start_res")
    if not emulator_start_res or not isinstance(emulator_start_res, str):
        normalized["emulator_start_res"] = DEFAULT_SETTINGS["emulator_start_res"]

    exec_file_path = normalized.get("exec_file_path")
    if not exec_file_path or not isinstance(exec_file_path, str):
        normalized["exec_file_path"] = DEFAULT_SETTINGS["exec_file_path"]

    grom_file_path = normalized.get("grom_file_path")
    if not grom_file_path or not isinstance(grom_file_path, str):
        normalized["grom_file_path"] = DEFAULT_SETTINGS["grom_file_path"]

    log_file = normalized.get("log_file")
    if log_file is None or not isinstance(log_file, str):
        normalized["log_file"] = DEFAULT_SETTINGS["log_file"]

    roms_folder = normalized.get("roms_folder")
    if roms_folder is None or not isinstance(roms_folder, str):
        normalized["roms_folder"] = DEFAULT_SETTINGS["roms_folder"]

    screenshot_path = normalized.get("screenshot_path")
    if screenshot_path is None or not isinstance(screenshot_path, str):
        normalized["screenshot_path"] = DEFAULT_SETTINGS["screenshot_path"]

    default_screenshot_res = normalized.get("default_screenshot_res")
    if default_screenshot_res not in SCREENSHOT_RES_OPTIONS:
        normalized["default_screenshot_res"] = DEFAULT_SETTINGS["default_screenshot_res"]

    jzintv_flags = normalized.get("jzintv_flags")
    if jzintv_flags is None or not isinstance(jzintv_flags, str):
        normalized["jzintv_flags"] = DEFAULT_SETTINGS["jzintv_flags"]

    game_resolutions = normalized.get("game_resolutions")
    if not isinstance(game_resolutions, list) or len(game_resolutions) == 0:
        normalized["game_resolutions"] = DEFAULT_SETTINGS["game_resolutions"]

    isolate_background = normalized.get("isolate_background")
    if not isolate_background or not isinstance(isolate_background, str):
        normalized["isolate_background"] = DEFAULT_SETTINGS["isolate_background"]

    return normalized


def load_settings(log_callback=None) -> Dict:
    def log(msg: str):
        if log_callback:
            log_callback(msg)
    
    path = get_config_path()
    log(f"Loading settings from: {path}")
    log(f"Settings file exists: {path.exists()}")
    if not path.exists():
        log(f"Creating new settings file at: {path}")
        _ensure_dir(path)
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)

    log(f"Reading existing settings file")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        log(f"Successfully loaded settings with {len(data)} keys")
    except Exception as e:
        log(f"Error reading settings: {e}, using defaults")
        data = dict(DEFAULT_SETTINGS)

    normalized = normalize_settings(data)
    if normalized != data:
        log(f"Settings were normalized, saving updated version")
        save_settings(normalized)
    return normalized


def save_settings(settings: Dict) -> None:
    path = get_config_path()
    _ensure_dir(path)
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
