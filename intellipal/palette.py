from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Tuple

ColorTuple = Tuple[int, int, int]

HEX_RE = re.compile(r"^\s*#([0-9a-fA-F]{6})\b")
RGB_RE = re.compile(r"^\s*(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})\b")
COMMENT_RE = re.compile(r"^\s*;")


@dataclass
class PaletteParseResult:
    colors: List[ColorTuple]
    lines: List[str]
    color_line_indices: List[int]
    valid: bool
    error: str | None = None


def parse_color_from_line(line: str) -> ColorTuple | None:
    hex_match = HEX_RE.match(line)
    if hex_match:
        value = hex_match.group(1)
        r = int(value[0:2], 16)
        g = int(value[2:4], 16)
        b = int(value[4:6], 16)
        return (r, g, b)

    rgb_match = RGB_RE.match(line)
    if rgb_match:
        r, g, b = (int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3)))
        if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
            return (r, g, b)
    return None


def parse_palette_file(path: Path) -> PaletteParseResult:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=False)
    colors: List[ColorTuple] = []
    color_line_indices: List[int] = []

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "" or COMMENT_RE.match(stripped):
            continue

        color = parse_color_from_line(line)
        if color is None:
            return PaletteParseResult([], lines, [], False, "Invalid palette file layout")

        colors.append(color)
        color_line_indices.append(index)
        if len(colors) > 16:
            return PaletteParseResult([], lines, [], False, "Invalid palette file layout")

    if len(colors) != 16:
        return PaletteParseResult([], lines, [], False, "Invalid palette file layout")

    return PaletteParseResult(colors, lines, color_line_indices, True, None)


def format_color(color: ColorTuple, fmt: str) -> str:
    r, g, b = color
    if fmt == "#rrggbb":
        return f"#{r:02X}{g:02X}{b:02X}"
    return f"{r} {g} {b}"


def replace_color_in_line(line: str, color: ColorTuple, fmt: str) -> str:
    formatted = format_color(color, fmt)
    if HEX_RE.match(line):
        return HEX_RE.sub(formatted, line, count=1)
    if RGB_RE.match(line):
        return RGB_RE.sub(formatted, line, count=1)
    # If no match, just prepend formatted color
    return f"{formatted} {line}".strip()


def update_palette_file(path: Path, colors: List[ColorTuple], fmt: str) -> None:
    parsed = parse_palette_file(path)
    if not parsed.valid:
        raise ValueError(parsed.error or "Invalid palette file layout")

    lines = parsed.lines[:]
    for index, color in zip(parsed.color_line_indices, colors):
        lines[index] = replace_color_in_line(lines[index], color, fmt)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_palette_color(path: Path, index: int, color: ColorTuple, fmt: str) -> None:
    parsed = parse_palette_file(path)
    if not parsed.valid:
        raise ValueError(parsed.error or "Invalid palette file layout")
    if index < 0 or index >= len(parsed.color_line_indices):
        raise IndexError("Color index out of range")

    lines = parsed.lines[:]
    line_index = parsed.color_line_indices[index]
    lines[line_index] = replace_color_in_line(lines[line_index], color, fmt)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_palette_file(path: Path, colors: List[ColorTuple], fmt: str, labels: List[str]) -> None:
    lines = []
    for color, label in zip(colors, labels):
        lines.append(f"{format_color(color, fmt)} ; {label}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
