from __future__ import annotations

import mmap
import os
import struct
from dataclasses import dataclass
from typing import Iterable, List

MAP_SIZE = 0x0200
MAGIC = b"JZPL"
VERSION = 3
HEADER_SIZE = 16

OFF_PALETTE_SEQ = 0x0010
OFF_PALETTE_DIRTY = 0x0014
OFF_PALETTE_COLORS = 0x0018

OFF_REF_PALETTE_SEQ = 0x0058
OFF_REF_PALETTE_DIRTY = 0x005C
OFF_REF_PALETTE_COLORS = 0x0060

OFF_REF_SPLIT = 0x00A0
OFF_POLLING_RATE = 0x00C0
OFF_RESOLUTION = 0x00C4
OFF_COMMAND = 0x00E4
OFF_LABEL1 = 0x0104
OFF_LABEL2 = 0x0144
OFF_DISPLAYED_COLORS = 0x0184
OFF_EMULATOR_PAUSED = 0x01A4
OFF_HEARTBEAT = 0x01A8
OFF_SCALE_SCREENSHOT = 0x01AC
OFF_SCREENSHOT_PREFIX = 0x01B0


@dataclass
class SharedMemoryMap:
    name: str
    size: int = MAP_SIZE
    _mm: mmap.mmap | None = None
    _path: str | None = None

    def open(self) -> None:
        if self._mm is not None:
            return
        if os.name == "nt":
            self._mm = mmap.mmap(-1, self.size, tagname=self.name, access=mmap.ACCESS_WRITE)
            self._mm[:] = b"\x00" * self.size
        else:
            base_dir = "/dev/shm" if os.path.isdir("/dev/shm") else "/tmp"
            self._path = os.path.join(base_dir, self.name)
            fd = os.open(self._path, os.O_CREAT | os.O_RDWR, 0o600)
            try:
                os.ftruncate(fd, self.size)
                self._mm = mmap.mmap(fd, self.size, access=mmap.ACCESS_WRITE)
                self._mm[:] = b"\x00" * self.size
            finally:
                os.close(fd)
        self.ensure_header()

    def close(self) -> None:
        if self._mm is not None:
            self._mm.close()
            self._mm = None
        if self._path:
            try:
                os.unlink(self._path)
            except OSError:
                pass
            self._path = None

    def ensure_header(self) -> None:
        mm = self._require_map()
        mm[0:4] = MAGIC
        struct.pack_into("<H", mm, 0x0004, VERSION)
        struct.pack_into("<H", mm, 0x0006, HEADER_SIZE)
        struct.pack_into("<I", mm, 0x0008, self.size)
        struct.pack_into("<I", mm, 0x000C, 0)

    def set_polling_rate(self, value: int) -> None:
        self._write_u32(OFF_POLLING_RATE, value)

    def set_resolution(self, text: str) -> None:
        self._write_fixed_string(OFF_RESOLUTION, 32, text)

    def set_command(self, text: str) -> None:
        self._write_fixed_string(OFF_COMMAND, 32, text)

    def set_scale_screenshot(self, value: int) -> None:
        self._write_u32(OFF_SCALE_SCREENSHOT, value)

    def set_screenshot_prefix(self, text: str) -> None:
        self._write_fixed_string(OFF_SCREENSHOT_PREFIX, 32, text)

    def set_label1(self, text: str) -> None:
        self._write_fixed_string(OFF_LABEL1, 64, text)

    def set_label2(self, text: str) -> None:
        self._write_fixed_string(OFF_LABEL2, 64, text)

    def set_ref_palette_start(self, text: str) -> None:
        self._write_fixed_string(OFF_REF_SPLIT, 32, text)

    def write_palette(self, colors: Iterable[int]) -> None:
        self._write_palette(OFF_PALETTE_SEQ, OFF_PALETTE_DIRTY, OFF_PALETTE_COLORS, colors)

    def write_ref_palette(self, colors: Iterable[int]) -> None:
        self._write_palette(OFF_REF_PALETTE_SEQ, OFF_REF_PALETTE_DIRTY, OFF_REF_PALETTE_COLORS, colors)

    def read_displayed_colors(self) -> List[int]:
        mm = self._require_map()
        raw = bytes(mm[OFF_DISPLAYED_COLORS : OFF_DISPLAYED_COLORS + 16])
        return [1 if value else 0 for value in raw]

    def read_emulator_paused(self) -> bool:
        return bool(self._read_u32(OFF_EMULATOR_PAUSED))

    def read_heartbeat(self) -> int:
        return self._read_u32(OFF_HEARTBEAT)

    def _write_palette(self, seq_off: int, dirty_off: int, colors_off: int, colors: Iterable[int]) -> None:
        mm = self._require_map()
        desired = [c & 0xFFFFFF for c in colors]
        if len(desired) != 16:
            return
        current = [self._read_u32(colors_off + i * 4) & 0xFFFFFF for i in range(16)]
        if current == desired:
            return
        for i, color in enumerate(desired):
            self._write_u32(colors_off + i * 4, color)
        seq = (self._read_u32(seq_off) + 1) & 0xFFFFFFFF
        self._write_u32(seq_off, seq)
        self._write_u32(dirty_off, 1)

    def _write_u32(self, offset: int, value: int) -> None:
        mm = self._require_map()
        struct.pack_into("<I", mm, offset, value & 0xFFFFFFFF)

    def _read_u32(self, offset: int) -> int:
        mm = self._require_map()
        return struct.unpack_from("<I", mm, offset)[0]

    def _write_fixed_string(self, offset: int, size: int, text: str) -> None:
        mm = self._require_map()
        data = text.encode("utf-8")[: size - 1]
        mm[offset : offset + size] = data + b"\x00" * (size - len(data))

    def _require_map(self) -> mmap.mmap:
        if self._mm is None:
            raise RuntimeError("Shared memory map not opened")
        return self._mm
