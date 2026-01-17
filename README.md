
   ````markdown
   # IntelliPal

   IntelliPal is a palette-management and session helper for the jzIntv NES emulator. It provides a GUI for authoring and testing color palettes, managing game sessions, and interacting with an embedded emulator window for live previewing.

   Key features
   - Palette editing: edit individual NES color entries, preview changes, and save/load palette files.
   - Session management: create and manage game sessions with session IDs, queue ROM loads, and control emulator pause/resume.
   - Embedded emulator preview: embed a jzIntv emulator window so keystrokes and input can be routed while the session dialog is active.
   - Color traffic lighting: visual indicators showing which game sessions are displaying which colors (configurable in the UI).
   - Isolate color support: designate an "isolate background" and related palette operations (setting is exposed in Settings).

   Important implementation detail

   IntelliPal uses a fork/implementation of jzIntv available at: https://github.com/evets17/jzintv_pal

   This project expects to interoperate with that jzIntv implementation for embedding the emulator window and reading/writing shared memory used for live palette updates and session state.

   Quick start
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

   Configuration and data
   - Settings are stored per-user (e.g., in `%APPDATA%\IntelliPal` on Windows).
   - Palettes and example configs are located in the `Palettes/` and `resources/` folders.

   Development notes
   - Source is organized under the `intellipal/` package. Key modules:
      - `intellipal/app.py` — main application and dialogs
      - `intellipal/widgets.py` — UI widgets such as color controls
      - `intellipal/settings.py` — default settings and persistence

   License
   - See project root for license information.

   ````
