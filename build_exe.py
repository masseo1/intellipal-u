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

IS_WINDOWS = os.name == "nt"
EMULATOR_EXE = "jzintv_pal.exe" if IS_WINDOWS else "jzintv_pal"
EXCLUDED_RESOURCES = [EMULATOR_EXE]


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
        ignore=shutil.ignore_patterns(*EXCLUDED_RESOURCES),
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
    ]
    if PALETTES_DIR.exists():
        args.extend(["--add-data", f"{PALETTES_DIR}{data_sep}Palettes"])
    else:
        print(f"Note: Palettes folder not found at {PALETTES_DIR}, skipping.")

    icon_path = REPO_ROOT / "resources" / "icon_snafu.ico"
    if IS_WINDOWS and icon_path.exists():
        args.extend(["--icon", str(icon_path)])
    elif not IS_WINDOWS:
        png_icon = REPO_ROOT / "resources" / "icon_snafu.png"
        if png_icon.exists():
            args.extend(["--icon", str(png_icon)])
    subprocess.run(args, check=True, cwd=str(REPO_ROOT))


def copy_emulator_to_dist() -> None:
    src = RESOURCES_DIR / EMULATOR_EXE
    dist_dir = REPO_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, dist_dir / EMULATOR_EXE)
        print(f"Copied emulator: {EMULATOR_EXE}")
    else:
        print(f"Note: Emulator binary not found at {src}")
        print(f"You will need to place {EMULATOR_EXE} in the dist folder or install it to PATH.")


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
