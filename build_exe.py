from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BUILD_FILE = REPO_ROOT / "intellipal" / "_build.py"
RESOURCES_DIR = REPO_ROOT / "resources"
PALETTES_DIR = REPO_ROOT / "Palettes"
ENTRYPOINT = REPO_ROOT / "intellipal" / "main.py"
EXE_NAME = "intellipal"
EXCLUDED_RESOURCE = "jzintv_pal.exe"


def write_build_id(build_id: str) -> None:
    BUILD_FILE.write_text(
        "# Auto-generated build metadata\n"
        "# Updated by build_exe.py\n"
        f"BUILD_ID = \"{build_id}\"\n",
        encoding="utf-8",
    )


def copy_resources_without_exe(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Resources folder not found: {src}")
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns(EXCLUDED_RESOURCE),
    )


def run_pyinstaller(resources_dir: Path) -> None:
    data_sep = os.pathsep
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        EXE_NAME,
        str(ENTRYPOINT),
        "--add-data",
        f"{resources_dir}{data_sep}resources",
        "--add-data",
        f"{PALETTES_DIR}{data_sep}Palettes",
    ]
    subprocess.run(args, check=True, cwd=str(REPO_ROOT))


def copy_emulator_to_dist() -> None:
    src = RESOURCES_DIR / EXCLUDED_RESOURCE
    dist_dir = REPO_ROOT / "dist"
    if not src.exists():
        raise FileNotFoundError(f"Emulator not found: {src}")
    dist_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dist_dir / EXCLUDED_RESOURCE)


def main() -> int:
    build_id = datetime.now().strftime("%y%m%d%H%M")
    write_build_id(build_id)

    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_resources = Path(tmp_dir) / "resources"
        copy_resources_without_exe(RESOURCES_DIR, temp_resources)
        run_pyinstaller(temp_resources)
        copy_emulator_to_dist()

    print(f"Build complete: {EXE_NAME}. Build ID: {build_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
