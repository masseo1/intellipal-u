# IntelliPal
See https://github.com/evets17/intellipal/releases/latest for latest built release.

IntelliPal is a palette-management and session helper for the jzIntv Intellivision emulator. It provides a GUI for authoring and testing color palettes, managing game sessions, and interacting with an embedded emulator window for live previewing.

Key features
- Palette editing: edit individual color entries, preview changes, and save/load palette files.
- Session management: create and manage game sessions with session IDs, queue ROM loads, and control emulator pause/resume.
- Embedded emulator preview: embed a jzIntv emulator window so keystrokes and input can be routed while the session dialog is active.
- Color traffic lighting: visual indicators showing which game sessions are displaying which colors (configurable in the UI).
- Isolate color support: designate an "isolate background" and related palette operations (setting is exposed in Settings).
- **Cross-platform Linux support**: Full GTK integration with Wayland detection and support for X11/Xwayland environments.
- **Linux window embedding**: Native window embedding using xdotool for X11 environments, with graceful fallback to separate windows on Wayland.
- **About dialog**: System information display showing OS, session type, and desktop environment.
- **Setup health check**: Diagnostic tool to verify jzIntv configuration and dependencies.
- **Palette export**: Export palette designs as PNG images.
- **Screenshot feedback**: Visual confirmation when screenshots are captured.

Important implementation detail

IntelliPal uses a fork/implementation of jzIntv available at: https://github.com/evets17/jzintv_pal

   This project expects to interoperate with that jzIntv implementation for embedding the emulator window and reading/writing shared memory used for live palette updates and session state.

   Quick start

   ### Windows

   1. Create and activate a Python virtual environment.

   ```powershell
   python -m venv .venv
   . .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

   2. Run the application

   ```powershell
   python -m intellipal.main
   ```

   ### Linux (Ubuntu/Debian)

   #### Quick Setup (Automated)

   The easiest way to get started is using the provided installation script:

   ```bash
   sudo ./tools/install_linux_deps.sh
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python -m intellipal.main
   ```

   #### Manual Setup

   1. Install system dependencies for PySide6 and window embedding:

   ```bash
   sudo apt update
   sudo apt install python3-venv python3-pip xdotool libxcb-cursor0 libgl1
   ```

   If you're on a minimal system, you may also need:
   ```bash
   sudo apt install libxkbcommon0 libxkbcommon-x11-0 libdbus-1-3
   ```

   2. Create and activate a Python virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   3. Run the application:

   ```bash
   python -m intellipal.main
   ```

   #### Building a Standalone Linux Executable

   Create a self-contained executable for distribution or system installation:

   ```bash
   # Install PyInstaller (if not already installed)
   pip install pyinstaller

   # Build the executable
   python build_exe.py

   # Run from dist folder
   ./dist/intellipal
   ```

   **Optional**: Install to system binary directory:
   ```bash
   sudo cp dist/intellipal /usr/local/bin/intellipal
   intellipal  # Now runnable from anywhere
   ```

   #### Notes

   - **Window Embedding**: The `xdotool` package is required for native window embedding on X11. Without it, the emulator will run in a separate window (still fully functional).
   - **Wayland Detection**: On Wayland desktop sessions, IntelliPal automatically switches to compact UI mode (separate emulator window). This is expected behavior.
   - **Session Type**: To check your current session:
     ```bash
     echo $XDG_SESSION_TYPE  # Shows 'wayland' or 'x11'
     ```

   #### Troubleshooting Linux

   **Missing display or connection errors**:
   ```bash
   # Ensure X11/Wayland is properly configured
   export QT_QPA_PLATFORM=wayland  # Force Wayland
   export QT_QPA_PLATFORM=xcb     # Force X11
   ```

   **xdotool not working**:
   ```bash
   # Verify xdotool is installed and working
   xdotool search --name ".*"
   # If command not found, reinstall: sudo apt install xdotool
   ```

   **Library not found errors**:
   ```bash
   # Install additional runtime libraries
   sudo apt install libfontconfig1 libfreetype6 libxext6 libxrender1
   ```

   ### Building a standalone executable

   On either platform, you can build a standalone executable using PyInstaller:

   ```bash
   pip install pyinstaller
   python build_exe.py
   ```

   The built executable will be in the `dist/` folder.

   Configuration and data
   - Settings are stored per-user:
     - Windows: `%APPDATA%\IntelliPal`
     - Linux: `~/.config/intellipal`
     - macOS: `~/Library/Application Support/IntelliPal`
   - Palettes and example configs are located in the `Palettes/` and `resources/` folders.

   Development notes
   - Source is organized under the `intellipal/` package. Key modules:
      - `intellipal/app.py` — main application and dialogs
      - `intellipal/widgets.py` — UI widgets such as color controls
      - `intellipal/settings.py` — default settings and persistence

   License
   - See project root for license information.

   ````
