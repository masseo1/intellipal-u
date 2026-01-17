from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Dict, List, Tuple

from PySide6.QtCore import Qt, QTimer, QProcess, QEvent
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap, QPainter, QPalette, QGuiApplication, QAction, QWindow, QColor
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QTextEdit,
    QInputDialog,
    QColorDialog,
    QStyle,
    QSizePolicy,
    QSplitter,
    QMenu,
    QSlider,
    QWidgetAction,
    QToolBar,
    QTabWidget,
    QCheckBox,
)

from .palette import parse_palette_file, update_palette_color, update_palette_file, write_palette_file
from .settings import load_settings, save_settings, DEFAULT_LABELS
from .memory_map import SharedMemoryMap
from .widgets import ColorControl

ColorTuple = Tuple[int, int, int]


@dataclass
class PaletteState:
    name: str
    path: Path | None
    colors: List[ColorTuple]
    base_colors: List[ColorTuple]
    dirty_colors: List[bool]
    dirty: bool = False
    invalid: bool = False


@dataclass
class GameSession:
    session_id: int
    map_name: str
    memory_map: SharedMemoryMap
    displayed_colors: List[int]
    emulator_paused: bool
    dialog: "GameDialog | None" = None


class SettingsDialog(QDialog):
    def __init__(self, settings: Dict, on_change):
        super().__init__()
        self.setWindowTitle("Settings")
        self._settings = dict(settings)
        self._on_change = on_change

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        tabs.addTab(general_tab, "General")

        emulator_tab = QWidget()
        emulator_layout = QFormLayout(emulator_tab)
        tabs.addTab(emulator_tab, "Emulator")

        session_tab = QWidget()
        session_layout = QFormLayout(session_tab)
        tabs.addTab(session_tab, "Game Session")

        logging_tab = QWidget()
        logging_layout = QFormLayout(logging_tab)
        tabs.addTab(logging_tab, "Logging")

        self.palette_dir = QLineEdit(self._settings["palette_dir"])
        browse_btn = QToolButton()
        browse_btn.setText("...")
        browse_btn.clicked.connect(self._browse_palette_dir)

        palette_dir_row = QHBoxLayout()
        palette_dir_row.addWidget(self.palette_dir)
        palette_dir_row.addWidget(browse_btn)
        palette_dir_widget = QWidget()
        palette_dir_widget.setLayout(palette_dir_row)

        self.palette_extensions = QLineEdit(self._settings["palette_extensions"])
        self.color_save_format = QComboBox()
        self.color_save_format.addItems(["#rrggbb", "R G B"])
        self.color_save_format.setCurrentText(self._settings["color_save_format"])
        self.save_extension = QLineEdit(self._settings["save_extension"])

        self.start_dock_state = QComboBox()
        self.start_dock_state.addItems(["Left", "Right", "None"])
        self.start_dock_state.setCurrentText(self._settings.get("start_dock_state", "Left"))

        self.emulator_poll_rate = QLineEdit(str(self._settings.get("emulator_poll_rate", 10)))
        self.emulator_start_res = QLineEdit(self._settings.get("emulator_start_res", "1024x768,8"))

        self.exec_file_path = QLineEdit(self._settings.get("exec_file_path", ".\\exec.bin"))
        exec_browse_btn = QToolButton()
        exec_browse_btn.setText("...")
        exec_browse_btn.clicked.connect(self._browse_exec_file)
        exec_row = QHBoxLayout()
        exec_row.addWidget(self.exec_file_path)
        exec_row.addWidget(exec_browse_btn)
        exec_widget = QWidget()
        exec_widget.setLayout(exec_row)

        self.grom_file_path = QLineEdit(self._settings.get("grom_file_path", ".\\grom.bin"))
        grom_browse_btn = QToolButton()
        grom_browse_btn.setText("...")
        grom_browse_btn.clicked.connect(self._browse_grom_file)
        grom_row = QHBoxLayout()
        grom_row.addWidget(self.grom_file_path)
        grom_row.addWidget(grom_browse_btn)
        grom_widget = QWidget()
        grom_widget.setLayout(grom_row)

        self.log_file_path = QLineEdit(self._settings.get("log_file", ""))
        log_browse_btn = QToolButton()
        log_browse_btn.setText("...")
        log_browse_btn.clicked.connect(self._browse_log_file)
        log_row = QHBoxLayout()
        log_row.addWidget(self.log_file_path)
        log_row.addWidget(log_browse_btn)
        log_widget = QWidget()
        log_widget.setLayout(log_row)

        self.roms_folder_path = QLineEdit(self._settings.get("roms_folder", ""))
        roms_browse_btn = QToolButton()
        roms_browse_btn.setText("...")
        roms_browse_btn.clicked.connect(self._browse_roms_folder)
        roms_row = QHBoxLayout()
        roms_row.addWidget(self.roms_folder_path)
        roms_row.addWidget(roms_browse_btn)
        roms_widget = QWidget()
        roms_widget.setLayout(roms_row)

        self.color_labels = QTextEdit()
        self.color_labels.setPlainText("\n".join(self._settings["color_labels"]))
        self.color_labels.setFixedHeight(140)

        self.isolate_background = QLineEdit(self._settings.get("isolate_background", "#000000"))
        isolate_browse_btn = QToolButton()
        isolate_browse_btn.setText("...")
        isolate_browse_btn.clicked.connect(self._pick_isolate_background)
        isolate_row = QHBoxLayout()
        isolate_row.addWidget(self.isolate_background)
        isolate_row.addWidget(isolate_browse_btn)
        isolate_widget = QWidget()
        isolate_widget.setLayout(isolate_row)

        self.game_resolutions = QTextEdit()
        self.game_resolutions.setPlainText("\n".join(self._settings.get("game_resolutions", [])))
        self.game_resolutions.setFixedHeight(140)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #b00020;")

        general_layout.addRow("Palette folder", palette_dir_widget)
        general_layout.addRow("Palette extensions", self.palette_extensions)
        general_layout.addRow("Color save format", self.color_save_format)
        general_layout.addRow("Save extension", self.save_extension)
        general_layout.addRow("Start dock state", self.start_dock_state)
        general_layout.addRow("Color labels (16 lines)", self.color_labels)

        emulator_layout.addRow("Emulator poll rate", self.emulator_poll_rate)
        emulator_layout.addRow("Emulator start resolution", self.emulator_start_res)
        emulator_layout.addRow("Exec file path", exec_widget)
        emulator_layout.addRow("GROM file path", grom_widget)

        session_layout.addRow("ROMs folder", roms_widget)
        session_layout.addRow("Game resolutions", self.game_resolutions)
        session_layout.addRow("Isolate background", isolate_widget)

        logging_layout.addRow("Log file", log_widget)

        layout.addWidget(self.error_label)

        # Button row with close and open settings file
        button_layout = QHBoxLayout()
        
        open_settings_btn = QToolButton()
        open_settings_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogContentsView))
        open_settings_btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
        open_settings_btn.setToolTip("Open settings file in default editor")
        open_settings_btn.clicked.connect(self._open_settings_file)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(open_settings_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        button_widget = QWidget()
        button_widget.setLayout(button_layout)
        layout.addWidget(button_widget)

        self.palette_dir.editingFinished.connect(self._apply)
        self.palette_extensions.editingFinished.connect(self._apply)
        self.color_save_format.currentTextChanged.connect(lambda: self._apply())
        self.save_extension.editingFinished.connect(self._apply)
        self.start_dock_state.currentTextChanged.connect(lambda: self._apply())
        self.emulator_poll_rate.editingFinished.connect(self._apply)
        self.emulator_start_res.editingFinished.connect(self._apply)
        self.exec_file_path.editingFinished.connect(self._apply)
        self.grom_file_path.editingFinished.connect(self._apply)
        self.log_file_path.editingFinished.connect(self._apply)
        self.roms_folder_path.editingFinished.connect(self._apply)
        self.color_labels.textChanged.connect(self._apply)
        self.game_resolutions.textChanged.connect(self._apply)
        self.isolate_background.editingFinished.connect(self._apply)

    def _browse_palette_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Palette Folder")
        if directory:
            self.palette_dir.setText(directory)
            self._apply()

    def _browse_exec_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select exec.bin", "", "BIN Files (*.bin);;All Files (*.*)")
        if path:
            self.exec_file_path.setText(path)
            self._apply()

    def _browse_grom_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select grom.bin", "", "BIN Files (*.bin);;All Files (*.*)")
        if path:
            self.grom_file_path.setText(path)
            self._apply()

    def _browse_log_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Select log file", "", "Log Files (*.log);;All Files (*.*)")
        if path:
            self.log_file_path.setText(path)
            self._apply()

    def _browse_roms_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select ROMs Folder")
        if directory:
            self.roms_folder_path.setText(directory)
            self._apply()

    def _pick_isolate_background(self):
        current = self.isolate_background.text().strip() or "#000000"
        initial = QColor(current)
        color = QColorDialog.getColor(initial, self, "Select isolate background")
        if color.isValid():
            self.isolate_background.setText(color.name().upper())
            self._apply()

    def _apply(self):
        labels = [line.strip() for line in self.color_labels.toPlainText().splitlines() if line.strip()]
        if len(labels) != 16:
            self.error_label.setText("Color labels must contain exactly 16 lines.")
            return

        resolutions = [line.strip() for line in self.game_resolutions.toPlainText().splitlines() if line.strip()]
        if not resolutions:
            self.error_label.setText("Game resolutions must contain at least one entry.")
            return
        for res in resolutions:
            if not self._validate_resolution(res):
                self.error_label.setText("Game resolutions must be XDIMxYDIM,DEPTH per line.")
                return

        palette_extensions = self.palette_extensions.text().strip()
        if not palette_extensions:
            self.error_label.setText("Palette extensions must contain at least one entry.")
            return

        save_extension = self.save_extension.text().strip()
        if not save_extension:
            self.error_label.setText("Save extension is required.")
            return

        poll_rate_text = self.emulator_poll_rate.text().strip()
        try:
            poll_rate = int(poll_rate_text)
        except ValueError:
            self.error_label.setText("Emulator poll rate must be an integer.")
            return
        if poll_rate < 0:
            self.error_label.setText("Emulator poll rate must be 0 or higher.")
            return

        start_res = self.emulator_start_res.text().strip()
        if not self._validate_resolution(start_res):
            self.error_label.setText("Emulator start resolution must be XDIMxYDIM,DEPTH.")
            return

        exec_path = self.exec_file_path.text().strip()
        grom_path = self.grom_file_path.text().strip()
        log_file = self.log_file_path.text().strip()
        roms_folder = self.roms_folder_path.text().strip()
        isolate_background = self.isolate_background.text().strip() or "#000000"

        self.error_label.setText("")
        new_settings = dict(self._settings)
        new_settings["palette_dir"] = self.palette_dir.text().strip()
        new_settings["palette_extensions"] = palette_extensions
        new_settings["color_save_format"] = self.color_save_format.currentText()
        new_settings["save_extension"] = save_extension
        new_settings["start_dock_state"] = self.start_dock_state.currentText()
        new_settings["emulator_poll_rate"] = poll_rate
        new_settings["emulator_start_res"] = start_res
        new_settings["exec_file_path"] = exec_path
        new_settings["grom_file_path"] = grom_path
        new_settings["log_file"] = log_file
        new_settings["roms_folder"] = roms_folder
        new_settings["color_labels"] = labels
        new_settings["game_resolutions"] = resolutions
        new_settings["isolate_background"] = isolate_background

        self._settings = new_settings
        save_settings(new_settings)
        self._on_change(new_settings)

    def _open_settings_file(self):
        """Open the settings JSON file in the default editor."""
        import os
        import subprocess
        from .settings import get_config_path
        
        settings_path = get_config_path()
        if settings_path.exists():
            if os.name == 'nt':
                os.startfile(str(settings_path))
            elif os.name == 'posix':
                subprocess.run(['open' if os.uname().sysname == 'Darwin' else 'xdg-open', str(settings_path)])

    @staticmethod
    def _validate_resolution(value: str) -> bool:
        if not value or "," not in value:
            return False
        dims_part, depth_part = value.split(",", 1)
        if "x" not in dims_part:
            return False
        x_part, y_part = dims_part.split("x", 1)
        try:
            x_val = int(x_part)
            y_val = int(y_part)
            depth_val = int(depth_part)
        except ValueError:
            return False
        return x_val > 0 and y_val > 0 and depth_val > 0


class PaletteList(QListWidget):
    def __init__(self, on_files_dropped):
        super().__init__()
        self._on_files_dropped = on_files_dropped
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self._on_files_dropped(files)
        event.acceptProposedAction()


class CollapsibleSection(QWidget):
    def __init__(self, title: str, content: QWidget):
        super().__init__()
        self.toggle = QToolButton()
        self.toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle.setArrowType(Qt.DownArrow)
        self.toggle.setText(title)
        self.toggle.setCheckable(True)
        self.toggle.setChecked(True)
        self.toggle.setStyleSheet("QToolButton { font-weight: 600; }")

        self.content = content
        self.content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toggle)
        layout.addWidget(self.content)

        self.toggle.toggled.connect(self._on_toggled)

    def _on_toggled(self, checked: bool) -> None:
        self.content.setVisible(checked)
        self.toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)


class ElideLabel(QLabel):
    def __init__(self, text: str = ""):
        super().__init__(text)
        self._full_text = text

    def setText(self, text: str) -> None:  # type: ignore[override]
        self._full_text = text
        self._update_elide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elide()

    def _update_elide(self) -> None:
        metrics = self.fontMetrics()
        elided = metrics.elidedText(self._full_text, Qt.ElideRight, self.width())
        super().setText(elided)


class GameDialog(QMainWindow):
    def __init__(self, session: GameSession, main_window: "MainWindow", resolution: str = "640x480,8"):
        super().__init__(main_window)
        self.session = session
        self.main_window = main_window
        self.resolution = resolution
        self.setWindowTitle(f"Game Session {session.session_id}")
        
        # Parse resolution for dialog sizing
        width, height = 640, 480
        try:
            if "," in resolution:
                dims = resolution.split(",")[0]
                if "x" in dims:
                    w, h = dims.split("x")
                    width, height = int(w), int(h)
        except (ValueError, IndexError):
            pass
        
        # Size dialog to fit the game resolution plus UI elements
        # Menu bar (~23px), status label (~20px), margins (12px), spacing (6px)
        dialog_width = width + 12
        dialog_height = height + 61
        
        self.setMinimumSize(dialog_width, dialog_height)
        self.setMaximumSize(dialog_width, dialog_height)
        self.resize(dialog_width, dialog_height)

        self.process = QProcess(self)
        self.process.started.connect(self._on_process_started)
        self.process.finished.connect(self._on_process_finished)
        self.process.readyReadStandardOutput.connect(self._on_process_stdout)
        self.process.readyReadStandardError.connect(self._on_process_stderr)

        self._embed_timer = QTimer(self)
        self._embed_timer.setInterval(250)
        self._embed_timer.timeout.connect(self._try_embed_window)
        self._embedded = False
        self._rom_title: str | None = None
        self._embedded_window_hwnd: int | None = None
        self._pending_rom_path: str | None = None

        game_menu = QMenu("Game", self)
        reference_menu = QMenu("Reference", self)
        self.menuBar().setVisible(False)

        menu_toolbar = QToolBar()
        menu_toolbar.setMovable(False)
        menu_toolbar.setFloatable(False)

        game_menu_button = QToolButton()
        game_menu_button.setText("Game")
        game_menu_button.setPopupMode(QToolButton.InstantPopup)
        game_menu_button.setMenu(game_menu)
        game_menu_button.setStyleSheet("QToolButton::menu-indicator { image: none; }")

        reference_menu_button = QToolButton()
        reference_menu_button.setText("Reference")
        reference_menu_button.setPopupMode(QToolButton.InstantPopup)
        reference_menu_button.setMenu(reference_menu)
        reference_menu_button.setStyleSheet("QToolButton::menu-indicator { image: none; }")

        menu_container = QWidget()
        menu_layout = QHBoxLayout(menu_container)
        menu_layout.setContentsMargins(6, 0, 6, 0)
        menu_layout.setSpacing(6)
        menu_layout.addWidget(game_menu_button, alignment=Qt.AlignVCenter)
        menu_layout.addWidget(reference_menu_button, alignment=Qt.AlignVCenter)
        
        # Add slider to menu bar for split position (right of Reference Palette)
        self.ref_split_slider = QSlider(Qt.Horizontal)
        self.ref_split_slider.setMinimum(0)
        self.ref_split_slider.setMaximum(159)
        self.ref_split_slider.setValue(80)
        self.ref_split_slider.setFixedWidth(120)
        self.ref_split_slider.setEnabled(False)
        self.ref_split_slider.valueChanged.connect(self._on_split_value_changed)

        self.ref_split_slider_container = QWidget()
        slider_layout = QHBoxLayout(self.ref_split_slider_container)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(0)
        slider_layout.addWidget(self.ref_split_slider, alignment=Qt.AlignVCenter)
        menu_layout.addWidget(self.ref_split_slider_container, alignment=Qt.AlignVCenter)
        menu_layout.addStretch(1)

        self.session_id_value = f"{session.session_id:02d}"
        self.session_id_label = QLabel(self.session_id_value)
        self.session_id_label.setFixedWidth(36)
        self.session_id_label.setAlignment(Qt.AlignCenter)
        self.session_id_label.setToolTip("Session Id")
        self.session_id_label.mousePressEvent = self._on_session_id_clicked
        menu_layout.addWidget(self.session_id_label, alignment=Qt.AlignVCenter)

        menu_toolbar.addWidget(menu_container)

        self.addToolBar(Qt.TopToolBarArea, menu_toolbar)

        QTimer.singleShot(0, lambda: self._update_reference_controls(enabled=False))

        load_action = QAction("Load Game", self)
        quit_action = QAction("Quit Game", self)
        reset_action = QAction("Reset Game", self)
        self.pause_action = QAction("Pause Game", self)
        screenshot_action = QAction("Screenshot", self)

        load_action.triggered.connect(self._load_game)
        quit_action.triggered.connect(lambda: self._send_command("QUIT"))
        reset_action.triggered.connect(lambda: self._send_command("RESET"))
        self.pause_action.triggered.connect(lambda: self._send_command("PAUSE"))
        screenshot_action.triggered.connect(lambda: self._send_command("SCREENSHOT"))

        for action in (load_action, quit_action, reset_action, self.pause_action, screenshot_action):
            game_menu.addAction(action)

        self.ref_palette_combo = QComboBox()
        self.ref_palette_combo.addItem("<none>")
        for name, _ in self.main_window._get_palette_options():
            self.ref_palette_combo.addItem(name)

        self.ref_split_mode = QComboBox()
        self.ref_split_mode.addItems(["No Split", "Vertical", "Horizontal"])

        self.ref_flip_btn = QPushButton("Flip Palettes")
        self._ref_flip_negative = False

        self.ref_palette_combo.currentTextChanged.connect(self._on_ref_palette_changed)
        self.ref_split_mode.currentTextChanged.connect(self._on_split_mode_changed)
        self.ref_flip_btn.clicked.connect(self._on_flip_clicked)

        reference_widget = QWidget()
        reference_layout = QVBoxLayout(reference_widget)
        reference_layout.setContentsMargins(8, 6, 8, 6)
        reference_layout.setSpacing(6)
        reference_layout.addWidget(QLabel("Palette"))
        reference_layout.addWidget(self.ref_palette_combo)
        reference_layout.addWidget(QLabel("Split Mode"))
        reference_layout.addWidget(self.ref_split_mode)
        reference_layout.addWidget(self.ref_flip_btn)

        reference_action = QWidgetAction(self)
        reference_action.setDefaultWidget(reference_widget)
        reference_menu.addAction(reference_action)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #b00020;")
        self._status_base_text = "Emulator not running."
        self._update_status_focus()

        # Container for embedded window
        self.video_container = QWidget()
        self.video_container.setStyleSheet("background-color: black;")
        
        # Use scroll area to clip the larger container to the selected resolution
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.video_container)
        self.scroll_area.setWidgetResizable(False)  # Don't resize the widget
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFixedSize(width, height)
        self.scroll_area.setStyleSheet("border: none;")
        
        # Disable mouse wheel scrolling
        self.scroll_area.wheelEvent = lambda event: event.ignore()

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(6, 6, 6, 6)
        central_layout.setSpacing(6)
        central_layout.addWidget(self.scroll_area)
        central_layout.addWidget(self.status_label)
        self.setCentralWidget(central)

        self._update_reference_controls(enabled=False)

    def _load_game(self) -> None:
        start_dir = self.main_window.settings.get("roms_folder", "")
        rom_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ROM",
            start_dir,
            "ROM Files (*.bin *.int *.rom);;All Files (*.*)",
        )
        if not rom_path:
            return
        if self.process.state() != QProcess.NotRunning:
            self._pending_rom_path = rom_path
            self._send_command("QUIT")
            self._stop_emulator()
            self._set_status_base("Waiting for emulator to quit...")
            return
        self._launch_emulator(rom_path)

    def _sync_pause_action(self) -> None:
        if not hasattr(self, "pause_action"):
            return
        if self.session.emulator_paused:
            self.pause_action.setText("Resume")
        else:
            self.pause_action.setText("Pause Game")

    def _launch_emulator(self, rom_path: str) -> None:
        exe_path = self.main_window._get_emulator_path()
        if exe_path is None:
            QMessageBox.warning(self, "Launch", "jzintv_pal executable not found.")
            self.main_window._log_message("Launch failed: jzintv_pal executable not found.")
            return
        exec_path = os.path.normpath(self.main_window.settings.get("exec_file_path", ".\\exec.bin"))
        grom_path = os.path.normpath(self.main_window.settings.get("grom_file_path", ".\\grom.bin"))
        display_size = self._current_display_size()
        rom_path = os.path.normpath(rom_path)
        try:
            self._rom_title = Path(rom_path).stem
        except Exception:
            self._rom_title = None
        if not exec_path or not Path(exec_path).exists():
            self.main_window._log_message(f"Launch failed: exec.bin not found at {exec_path}")
            QMessageBox.warning(self, "Launch", "Exec file path is missing or invalid.")
            return
        if not grom_path or not Path(grom_path).exists():
            self.main_window._log_message(f"Launch failed: grom.bin not found at {grom_path}")
            QMessageBox.warning(self, "Launch", "GROM file path is missing or invalid.")
            return
        self.main_window._log_message(
            f"Launching emulator: exe={exe_path} exec={exec_path} grom={grom_path} shm={self.session.map_name} rom={rom_path}"
        )
        cmd_line = (
            f"\"{exe_path}\" --shm-name=\"{self.session.map_name}\" "
            f"--execimg=\"{exec_path}\" --gromimg=\"{grom_path}\" "
            f"--displaysize=\"{display_size}\" \"{rom_path}\""
        )
        self.main_window._log_message(f"Command line: {cmd_line}")
        self._stop_emulator()
        self._set_status_base("Launching emulator...")
        self.process.setProgram(str(exe_path))
        self.process.setArguments(
            [
                f"--shm-name={self.session.map_name}",
                f"--execimg={exec_path}",
                f"--gromimg={grom_path}",
                f"--displaysize={display_size}",
                rom_path,
            ]
        )
        self.process.start()

    def _current_display_size(self) -> str:
        # Double the resolution so jzintv renders at higher quality
        # Dialog will be sized to show only the selected resolution portion
        width, height, depth = 640, 480, 8
        try:
            if "," in self.resolution:
                dims, depth_str = self.resolution.split(",", 1)
                if "x" in dims:
                    w, h = dims.split("x")
                    width, height = int(w), int(h)
                depth = int(depth_str)
        except (ValueError, IndexError):
            pass
        
        return f"{width * 2}x{height * 2},{depth}"

    def _stop_emulator(self) -> None:
        if self.process.state() != QProcess.NotRunning:
            self._send_command("QUIT")
            self.process.terminate()
            self.process.waitForFinished(2000)
        self._embedded = False
        self._embed_timer.stop()
        self._embedded_window_hwnd = None
        self._set_status_base("Emulator not running.")

    def _on_process_started(self) -> None:
        self._set_status_base("Emulator running. Embedding window...")
        self._embed_timer.start()

    def _on_process_finished(self) -> None:
        exit_code = self.process.exitCode()
        exit_status = self.process.exitStatus()
        self.main_window._log_message(f"Emulator exited: code={exit_code} status={exit_status}")
        self._set_status_base("Emulator not running.")
        self._embed_timer.stop()
        if self._pending_rom_path:
            rom_path = self._pending_rom_path
            self._pending_rom_path = None
            self._launch_emulator(rom_path)

    def _on_process_stdout(self) -> None:
        try:
            data = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace").rstrip()
        except Exception:
            return
        if data:
            for line in data.splitlines():
                self.main_window._log_message(f"[stdout] {line}")

    def _on_process_stderr(self) -> None:
        try:
            data = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace").rstrip()
        except Exception:
            return
        if data:
            for line in data.splitlines():
                self.main_window._log_message(f"[stderr] {line}")

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._focus_emulator_window()
        self._update_status_focus()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._update_status_focus()

    def event(self, event):
        if event.type() == QEvent.WindowActivate:
            self._focus_emulator_window()
            self._update_status_focus()
        elif event.type() == QEvent.WindowDeactivate:
            self._update_status_focus()
        return super().event(event)

    def _set_status_base(self, text: str) -> None:
        self._status_base_text = text
        self._update_status_focus()

    def _update_status_focus(self) -> None:
        if self.isActiveWindow():
            suffix = " Input Ready"
            color = "#1b5e20"
        else:
            suffix = " Input Not Ready"
            color = "#b00020"
        self.status_label.setText(f"{self._status_base_text}{suffix}")
        self.status_label.setStyleSheet(f"color: {color};")

    def _focus_emulator_window(self) -> None:
        if not self._embedded_window_hwnd or os.name != "nt":
            return
        try:
            import ctypes
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.SetForegroundWindow(self._embedded_window_hwnd)
            user32.SetActiveWindow(self._embedded_window_hwnd)
            user32.SetFocus(self._embedded_window_hwnd)
        except Exception:
            return

    def _on_session_id_clicked(self, event) -> None:
        current_value = self.session_id_value
        text, ok = QInputDialog.getText(
            self,
            "Session Id",
            "Enter Session Id (up to 3 chars):",
            text=current_value,
        )
        if ok:
            new_value = (text or "")[:3]
            if not new_value:
                new_value = f"{self.session.session_id:02d}"
            self.session_id_value = new_value
            self.session_id_label.setText(new_value)
            self.main_window._update_traffic_lights()

    def _try_embed_window(self) -> None:
        if self._embedded:
            return
        if os.name != "nt":
            self._set_status_base("Embedding only supported on Windows for now.")
            self._embed_timer.stop()
            return
        pid = self.process.processId()
        if pid == 0:
            return
        handle = self._find_window_for_pid(pid, self._rom_title)
        if handle is None:
            return
        
        # Parse resolution to get doubled size for embedding
        width, height = 640, 480
        try:
            if "," in self.resolution:
                dims = self.resolution.split(",")[0]
                if "x" in dims:
                    w, h = dims.split("x")
                    width, height = int(w), int(h)
        except (ValueError, IndexError):
            pass
        
        # Set video_container to doubled size BEFORE embedding
        doubled_width = width * 2
        doubled_height = height * 2
        self.video_container.setFixedSize(doubled_width, doubled_height)
        
        try:
            import ctypes
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            
            # Get the video container's window handle
            container_hwnd = int(self.video_container.winId())
            
            # Set the emulator window as a child of the container
            GWL_STYLE = -16
            WS_CHILD = 0x40000000
            WS_VISIBLE = 0x10000000
            
            # Remove window decorations and make it a child window
            current_style = user32.GetWindowLongW(handle, GWL_STYLE)
            new_style = (current_style | WS_CHILD | WS_VISIBLE) & ~0x00C00000  # Remove WS_CAPTION
            user32.SetWindowLongW(handle, GWL_STYLE, new_style)
            
            # Set parent window
            user32.SetParent(handle, container_hwnd)
            
            # Size the window to fill the doubled container
            SWP_NOZORDER = 0x0004
            user32.SetWindowPos(
                handle, 0,
                0, 0, doubled_width, doubled_height,
                SWP_NOZORDER
            )

            # Give focus to the embedded window
            try:
                user32.SetForegroundWindow(handle)
                user32.SetActiveWindow(handle)
                user32.SetFocus(handle)
            except Exception:
                pass
            
            self._embedded_window_hwnd = handle
            self._embedded = True
            self._embed_timer.stop()
            self._set_status_base("Emulator running.")
            self.main_window._log_message(f"Embedded emulator window at {doubled_width}x{doubled_height}")
            
        except Exception as e:
            self.main_window._log_message(f"Failed to embed window: {e}")
            self._embed_timer.stop()


    def _find_window_for_pid(self, pid: int, title_hint: str | None) -> int | None:
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

            handles: List[int] = []
            titled_handles: List[int] = []

            def get_title(hwnd) -> str:
                length = user32.GetWindowTextLengthW(hwnd)
                if length == 0:
                    return ""
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                return buffer.value

            def callback(hwnd, lparam):
                if not user32.IsWindowVisible(hwnd):
                    return True
                pid_out = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_out))
                if pid_out.value == pid:
                    handles.append(hwnd)
                    title = get_title(hwnd)
                    if title:
                        self.main_window._log_message(f"Found window for pid {pid}: {title}")
                    return False
                if title_hint:
                    title = get_title(hwnd)
                    if title and title_hint.lower() in title.lower():
                        titled_handles.append(hwnd)
                        self.main_window._log_message(f"Found window by title '{title_hint}': {title}")
                return True

            user32.EnumWindows(enum_proc(callback), 0)
            if handles:
                return handles[0]
            if titled_handles:
                return titled_handles[0]
            return None
        except Exception:
            return None


    def _send_command(self, command: str) -> None:
        try:
            self.session.memory_map.set_command(command)
        except Exception:
            return


    def _on_ref_palette_changed(self, value: str) -> None:
        if value == "<none>":
            self.session.memory_map.set_ref_palette_start("")
            self._update_reference_controls(enabled=False)
            return
        palette_path = self.main_window._get_palette_path(value)
        if palette_path is None:
            return
        parsed = parse_palette_file(palette_path)
        if not parsed.valid:
            QMessageBox.warning(self, "Reference Palette", parsed.error or "Invalid palette file")
            return
        self.session.memory_map.write_ref_palette(self.main_window._colors_to_map_values(parsed.colors))
        self._update_reference_controls(enabled=True)
        self._apply_ref_split()

    def _on_split_mode_changed(self, value: str) -> None:
        self._apply_ref_split()

    def _on_split_value_changed(self, value: int) -> None:
        self._apply_ref_split()

    def _on_flip_clicked(self) -> None:
        self._ref_flip_negative = not self._ref_flip_negative
        self._apply_ref_split()

    def _apply_ref_split(self) -> None:
        if self.ref_palette_combo.currentText() == "<none>":
            return
        mode = self.ref_split_mode.currentText()
        if mode == "No Split":
            self.ref_split_slider.setEnabled(False)
            self.ref_split_slider.setRange(0, 159)
            self.ref_split_slider.setValue(0)
            self.session.memory_map.set_ref_palette_start("V:0")
            return

        if mode == "Vertical":
            self.ref_split_slider.setEnabled(True)
            self.ref_split_slider.setRange(0, 159)
            if self.ref_split_slider.value() == 0:
                self.ref_split_slider.setValue(80)
            orientation = "V"
        else:
            self.ref_split_slider.setEnabled(True)
            self.ref_split_slider.setRange(0, 191)
            if self.ref_split_slider.value() == 0:
                self.ref_split_slider.setValue(96)
            orientation = "H"

        line_value = self.ref_split_slider.value()
        if self._ref_flip_negative:
            line_value = -line_value
        self.session.memory_map.set_ref_palette_start(f"{orientation}:{line_value}")

    def _update_reference_controls(self, enabled: bool) -> None:
        self.ref_split_mode.setEnabled(enabled)
        self.ref_split_slider.setEnabled(enabled and self.ref_split_mode.currentText() != "No Split")
        self.ref_flip_btn.setEnabled(enabled)

    def closeEvent(self, event):
        self._stop_emulator()
        self.main_window._remove_game_session(self.session)
        super().closeEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IntelliPal")
        self.resize(520, 800)

        self._dock_width = 520
        
        self._early_logs = []

        self.settings = load_settings(log_callback=self._early_log)
        self.base_dir = Path(__file__).resolve().parents[1]
        self.default_palette_path = self.base_dir / "resources" / "NTSC_Color_Palette.cfg"

        self.palette_states: Dict[str, PaletteState] = {}
        self.current_palette_id: str | None = None

        self.palette_list = PaletteList(self._import_palette_files)
        self.palette_list.currentItemChanged.connect(self._on_palette_selected)

        self.open_folder_btn = QToolButton()
        self.rename_btn = QToolButton()
        self.settings_btn = QToolButton()
        self.new_session_btn = QToolButton()

        self.open_folder_btn.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.rename_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.settings_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogContentsView))
        self.new_session_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

        self.open_folder_btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.rename_btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.settings_btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.new_session_btn.setToolButtonStyle(Qt.ToolButtonIconOnly)

        self.open_folder_btn.setToolTip("Open palette folder")
        self.rename_btn.setToolTip("Rename selected palette")
        self.settings_btn.setToolTip("Open settings dialog")
        self.new_session_btn.setToolTip("New game session")

        self.resolution_combo = QComboBox()
        resolutions = self.settings.get("game_resolutions", [])
        for res in resolutions:
            self.resolution_combo.addItem(res)
        # Default to 640x480,8
        default_idx = self.resolution_combo.findText("640x480,8")
        if default_idx >= 0:
            self.resolution_combo.setCurrentIndex(default_idx)
        self.resolution_combo.setToolTip("Game session resolution")

        self.open_folder_btn.clicked.connect(self._open_palette_folder)
        self.rename_btn.clicked.connect(self._rename_palette)
        self.settings_btn.clicked.connect(self._open_settings)
        self.new_session_btn.clicked.connect(self._create_game_session)

        self.dock_left_btn = QToolButton()
        self.dock_right_btn = QToolButton()
        self.dock_left_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowLeft))
        self.dock_right_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowRight))
        self.dock_left_btn.setToolTip("Dock left")
        self.dock_right_btn.setToolTip("Dock right")
        self.dock_left_btn.clicked.connect(self._dock_left)
        self.dock_right_btn.clicked.connect(self._dock_right)

        self.left_panel_toggle = QToolButton()
        self.left_panel_toggle.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.left_panel_toggle.setArrowType(Qt.LeftArrow)
        self.left_panel_toggle.setToolTip("Collapse palette panel")
        self.left_panel_toggle.setCheckable(True)
        self.left_panel_toggle.setChecked(False)
        self.left_panel_toggle.toggled.connect(self._toggle_left_panel)

        self.game_sessions: List[GameSession] = []
        self._game_session_counter = 0
        self._session_poll_timer = QTimer(self)
        self._session_poll_timer.setInterval(200)
        self._session_poll_timer.timeout.connect(self._poll_game_sessions)
        self._session_poll_timer.start()

        self.file_name_label = ElideLabel("No palette selected")
        self.pending_label = QLabel("Pending changes")
        self.pending_label.setStyleSheet("color: #b00020;")
        self.pending_label.setMinimumHeight(self.pending_label.sizeHint().height())
        self.pending_label.setText("")
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #b00020;")

        self.save_btn = QToolButton()
        self.save_as_btn = QToolButton()
        self.reset_btn = QToolButton()
        self.open_file_btn = QToolButton()
        self.rename_file_btn = QToolButton()

        self.save_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.save_as_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.reset_btn.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.open_file_btn.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.rename_file_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))

        for btn in (self.save_btn, self.save_as_btn, self.reset_btn, self.open_file_btn, self.rename_file_btn):
            btn.setToolButtonStyle(Qt.ToolButtonIconOnly)

        self.save_btn.setToolTip("Save changes")
        self.save_as_btn.setToolTip("Save palette as new file")
        self.reset_btn.setToolTip("Reset to on-disk values")
        self.open_file_btn.setToolTip("Open palette file in default editor")
        self.rename_file_btn.setToolTip("Rename selected palette")

        self.save_btn.clicked.connect(self._save_palette)
        self.save_as_btn.clicked.connect(self._save_as_palette)
        self.reset_btn.clicked.connect(self._reset_palette)
        self.open_file_btn.clicked.connect(self._open_palette_file)
        self.rename_file_btn.clicked.connect(self._rename_palette)

        file_controls = QHBoxLayout()
        file_controls.setSpacing(2)
        file_controls.setContentsMargins(0, 0, 0, 0)
        file_controls.addWidget(self.save_btn)
        file_controls.addWidget(self.save_as_btn)
        file_controls.addWidget(self.reset_btn)
        file_controls.addWidget(self.open_file_btn)
        file_controls.addWidget(self.rename_file_btn)
        file_controls.addStretch()

        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addLayout(file_controls)
        header_layout.addWidget(self.file_name_label)
        header_layout.addWidget(self.pending_label)
        header_layout.addWidget(self.status_label)

        header_widget = QWidget()
        header_widget.setLayout(header_layout)

        selected_label = QLabel("Selected Palette")
        palettes_label = QLabel("Palettes")
        self._style_section_label(selected_label)
        self._style_section_label(palettes_label)

        palette_header = QHBoxLayout()
        palette_header.setSpacing(2)
        palette_header.setContentsMargins(0, 0, 0, 0)
        palette_header.addWidget(palettes_label)
        palette_header.addStretch()
        palette_header.addWidget(self.open_folder_btn)

        selected_content = QWidget()
        selected_layout = QVBoxLayout(selected_content)
        selected_layout.setSpacing(2)
        selected_layout.setContentsMargins(0, 0, 0, 0)
        selected_layout.addWidget(header_widget)

        left_panel_content = QWidget()
        left_panel_layout = QVBoxLayout(left_panel_content)
        left_panel_layout.setSpacing(4)
        left_panel_layout.setContentsMargins(0, 0, 0, 0)
        left_panel_layout.addWidget(selected_label)
        left_panel_layout.addWidget(header_widget)
        left_panel_layout.addLayout(palette_header)
        left_panel_layout.addWidget(self.palette_list, 1)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(4)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(left_panel_content)
        self.left_panel_widget = QWidget()
        self.left_panel_widget.setLayout(left_layout)

        self.controls_container = QWidget()
        self.controls_layout = QVBoxLayout(self.controls_container)
        self.controls_layout.setAlignment(Qt.AlignTop)
        self.controls_layout.setSpacing(1)
        self.controls_layout.setContentsMargins(0, 0, 0, 0)

        self.color_controls: List[ColorControl] = []
        self._build_color_controls(self.settings.get("color_labels", DEFAULT_LABELS))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.controls_container)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(scroll)
        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(2)
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.addWidget(self.left_panel_toggle)
        top_bar.addWidget(self.settings_btn)
        top_bar.addWidget(self.new_session_btn)
        top_bar.addWidget(self.resolution_combo)
        self.traffic_lighting_checkbox = QCheckBox("CTL")
        self.traffic_lighting_checkbox.setChecked(True)
        self.traffic_lighting_checkbox.setToolTip("Toggle color traffic lighting indicators")
        self.traffic_lighting_checkbox.stateChanged.connect(self._on_toggle_traffic_lighting)
        top_bar.addWidget(self.traffic_lighting_checkbox)
        top_bar.addStretch()
        top_bar.addWidget(self.dock_left_btn)
        top_bar.addWidget(self.dock_right_btn)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.left_panel_widget)
        splitter.addWidget(right_widget)
        splitter.setCollapsible(0, True)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 600])

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setSpacing(2)
        root_layout.setContentsMargins(2, 2, 2, 2)
        root_layout.addLayout(top_bar)
        root_layout.addWidget(splitter)
        self.setCentralWidget(root)

        self._load_palette_list()
        QTimer.singleShot(0, self._resize_to_fit_colors)
        QTimer.singleShot(0, self._apply_start_dock_state)
        QTimer.singleShot(0, self._apply_session_settings)
        QTimer.singleShot(0, self._update_game_session_availability)
        QTimer.singleShot(0, self._log_settings_location)
        QTimer.singleShot(0, self._on_toggle_traffic_lighting)

    def _early_log(self, message: str) -> None:
        """Collect log messages before logging is fully configured."""
        self._early_logs.append(message)
    
    def _log_settings_location(self) -> None:
        from .settings import get_config_path
        # Flush early logs first
        for msg in self._early_logs:
            self._log_message(msg)
        self._early_logs.clear()
        # Then log the settings path
        settings_path = get_config_path()
        self._log_message(f"Settings file: {settings_path}")

    def _dock_left(self) -> None:
        self._dock_to_side(left=True)

    def _dock_right(self) -> None:
        self._dock_to_side(left=False)

    def _dock_to_side(self, left: bool) -> None:
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        frame = self.frameGeometry()
        geo = self.geometry()
        margin_left = geo.left() - frame.left()
        margin_top = geo.top() - frame.top()
        margin_right = frame.right() - geo.right()
        margin_bottom = frame.bottom() - geo.bottom()
        adjusted = available.adjusted(margin_left, margin_top, -margin_right, -margin_bottom)
        width = min(self._dock_width, adjusted.width())
        height = max(0, adjusted.height())
        x = adjusted.x() if left else adjusted.x() + adjusted.width() - width
        self.setGeometry(x, adjusted.y(), width, height)

    def _create_game_session(self) -> None:
        if not self._game_sessions_enabled():
            QMessageBox.warning(self, "Game Session", "Exec/GROM paths are not configured.")
            return
        start_dir = self.settings.get("roms_folder", "")
        rom_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ROM",
            start_dir,
            "ROM Files (*.bin *.int *.rom);;All Files (*.*)",
        )
        if not rom_path:
            return
        
        # Get selected resolution
        selected_resolution = self.resolution_combo.currentText()
        if not selected_resolution:
            selected_resolution = "640x480,8"
        
        self._log_message("Creating new game session.")
        self._game_session_counter += 1
        session_id = self._game_session_counter
        map_name = f"IntelliPalSession-{session_id}"
        memory_map = SharedMemoryMap(map_name)
        try:
            memory_map.open()
        except Exception as exc:
            self._log_message(f"Failed to open shared memory map: {exc}")
            QMessageBox.warning(self, "Game Session", "Failed to open shared memory map.")
            return
        memory_map.set_polling_rate(int(self.settings.get("emulator_poll_rate", 10)))
        palette = self._current_palette_colors()
        if palette is not None:
            memory_map.write_palette(self._colors_to_map_values(palette))
        session = GameSession(
            session_id=session_id,
            map_name=map_name,
            memory_map=memory_map,
            displayed_colors=[0] * 16,
            emulator_paused=False,
        )
        self.game_sessions.append(session)
        try:
            dialog = GameDialog(session, self, selected_resolution)
            session.dialog = dialog
            dialog.show()
            self._log_message(f"Game dialog shown for session {session_id}.")
            dialog._launch_emulator(rom_path)
            self._update_traffic_lights()
        except Exception as exc:
            self._log_message(f"Failed to create game dialog: {exc}")
            QMessageBox.warning(self, "Game Session", "Failed to open game dialog.")
            self._remove_game_session(session)
            return
        self.status_label.setText(f"Created game session {session_id}")

    def _current_palette_colors(self) -> List[ColorTuple] | None:
        state = self._current_state()
        if not state or state.invalid or len(state.colors) != 16:
            return None
        return state.colors

    def _colors_to_map_values(self, colors: List[ColorTuple]) -> List[int]:
        return [(r << 16) | (g << 8) | b for r, g, b in colors]

    def _push_palette_to_sessions(self, colors: List[ColorTuple]) -> None:
        values = self._colors_to_map_values(colors)
        for session in self.game_sessions:
            session.memory_map.write_palette(values)

    def _poll_game_sessions(self) -> None:
        for session in self.game_sessions:
            try:
                session.displayed_colors = session.memory_map.read_displayed_colors()
                session.emulator_paused = session.memory_map.read_emulator_paused()
                if session.dialog is not None:
                    session.dialog._sync_pause_action()
            except Exception:
                continue
        if self.traffic_lighting_checkbox.isChecked():
            self._update_traffic_lights()

    def _update_traffic_lights(self) -> None:
        if not self.traffic_lighting_checkbox.isChecked():
            for control in self.color_controls:
                control.set_traffic_lights_visible(False)
            return
        for control in self.color_controls:
            control.set_traffic_lights_visible(True)
        sessions = self.game_sessions[:6]
        focused_session_id: int | None = None
        for session in sessions:
            if session.dialog is not None and session.dialog.isActiveWindow():
                focused_session_id = session.session_id
                break

        for color_index, control in enumerate(self.color_controls):
            session_labels: list[tuple[str, bool]] = []
            focus_active = False
            for session in sessions:
                label_text = f"{session.session_id:02d}"
                if session.dialog is not None:
                    text_value = session.dialog.session_id_value.strip()
                    if text_value:
                        label_text = text_value[:3]
                running = (
                    session.dialog is not None
                    and session.dialog.process.state() != QProcess.NotRunning
                )
                used = running and color_index < len(session.displayed_colors) and session.displayed_colors[color_index] == 1
                session_labels.append((label_text, used))

                if focused_session_id == session.session_id and used:
                    focus_active = True

            control.update_traffic_lights(session_labels, focus_active)

    def _on_toggle_traffic_lighting(self) -> None:
        self._update_traffic_lights()

    def _apply_start_dock_state(self) -> None:
        state = self.settings.get("start_dock_state", "Left")
        if state == "Left":
            self._dock_to_side(left=True)
        elif state == "Right":
            self._dock_to_side(left=False)

    def _apply_session_settings(self) -> None:
        poll_rate = int(self.settings.get("emulator_poll_rate", 10))
        for session in self.game_sessions:
            session.memory_map.set_polling_rate(poll_rate)

    def _log_message(self, message: str) -> None:
        log_path = self.settings.get("log_file", "")
        if not log_path:
            return
        try:
            path = Path(log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(message + "\n")
        except Exception:
            return

    def _get_emulator_path(self) -> Path | None:
        exe_path = self.base_dir / "resources" / "jzintv_pal.exe"
        return exe_path if exe_path.exists() else None

    def _game_sessions_enabled(self) -> bool:
        exec_value = self.settings.get("exec_file_path", ".\\exec.bin")
        grom_value = self.settings.get("grom_file_path", ".\\grom.bin")
        if not exec_value or not grom_value:
            return False
        exec_path = Path(exec_value)
        grom_path = Path(grom_value)
        return exec_path.exists() and grom_path.exists()

    def _update_game_session_availability(self) -> None:
        enabled = self._game_sessions_enabled()
        self.new_session_btn.setEnabled(enabled)
        self.new_session_btn.setVisible(enabled)

    def _get_palette_options(self) -> List[Tuple[str, Path]]:
        options: List[Tuple[str, Path]] = []
        for palette_id, state in self.palette_states.items():
            if state.invalid or state.path is None:
                continue
            options.append((state.name, state.path))
        return options

    def _get_palette_path(self, name: str) -> Path | None:
        for _, state in self.palette_states.items():
            if state.name == name and state.path is not None and not state.invalid:
                return state.path
        return None

    def _remove_game_session(self, session: GameSession) -> None:
        if session in self.game_sessions:
            self.game_sessions.remove(session)
        session.memory_map.close()
        self._update_traffic_lights()

    def _toggle_left_panel(self, collapsed: bool) -> None:
        self.left_panel_widget.setVisible(not collapsed)
        self.left_panel_toggle.setArrowType(Qt.RightArrow if collapsed else Qt.LeftArrow)
        self.left_panel_toggle.setToolTip(
            "Expand palette panel" if collapsed else "Collapse palette panel"
        )

    def _build_color_controls(self, labels: List[str]) -> None:
        for control in self.color_controls:
            control.setParent(None)
        self.color_controls = []

        for index, label in enumerate(labels):
            control = ColorControl(label, index, (0, 0, 0))
            control.colorChanged.connect(self._on_color_changed)
            control.resetRequested.connect(self._on_color_reset)
            control.saveRequested.connect(self._on_color_save)
            self.controls_layout.addWidget(control)
            self.color_controls.append(control)

        self.controls_layout.addStretch()

    def _palette_dir(self) -> Path:
        path = Path(self.settings.get("palette_dir", "./Palettes"))
        if not path.is_absolute():
            path = (self.base_dir / path).resolve()
        return path

    def _palette_extensions(self) -> List[str]:
        raw = self.settings.get("palette_extensions", ".cfg|.txt")
        return [ext.strip().lower() for ext in raw.split("|") if ext.strip()]

    def _load_palette_list(self):
        self.palette_list.blockSignals(True)
        self.palette_list.clear()

        self.palette_states = {}
        self.current_palette_id = None

        default_state = self._load_palette_state("Default", self.default_palette_path, read_only=True)
        default_item = QListWidgetItem("Default")
        default_item.setData(Qt.UserRole, "Default")
        default_item.setToolTip("Default palette")
        self.palette_list.addItem(default_item)
        self.palette_states["Default"] = default_state

        palette_dir = self._palette_dir()
        extensions = self._palette_extensions()
        if palette_dir.exists():
            for file in sorted(palette_dir.iterdir()):
                if not file.is_file():
                    continue
                if file.suffix.lower() not in extensions:
                    continue

                palette_id = str(file)
                state = self._load_palette_state(file.name, file)
                item = QListWidgetItem(file.name)
                item.setData(Qt.UserRole, palette_id)
                if state.invalid:
                    item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                    item.setToolTip("Invalid palette file layout")
                self.palette_list.addItem(item)
                self.palette_states[palette_id] = state

        self.palette_list.blockSignals(False)
        self.palette_list.setCurrentRow(0)

    def _load_palette_state(self, name: str, path: Path, read_only: bool = False) -> PaletteState:
        parsed = parse_palette_file(path)
        if not parsed.valid:
            return PaletteState(name=name, path=path, colors=[], base_colors=[], dirty_colors=[], dirty=False, invalid=True)
        return PaletteState(
            name=name,
            path=path,
            colors=parsed.colors[:],
            base_colors=parsed.colors[:],
            dirty_colors=[False] * len(parsed.colors),
            dirty=False,
        )

    def _on_palette_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        if previous:
            prev_id = previous.data(Qt.UserRole)
            self._save_current_state(prev_id)

        if current is None:
            return

        palette_id = current.data(Qt.UserRole)
        state = self.palette_states.get(palette_id)
        if state is None:
            return

        self.current_palette_id = palette_id
        self._apply_palette_state(state)

    def _save_current_state(self, palette_id: str | None):
        if not palette_id:
            return
        state = self.palette_states.get(palette_id)
        if not state or state.invalid:
            return
        state.colors = [control.color() for control in self.color_controls]
        state.dirty_colors = [
            color != base_color for color, base_color in zip(state.colors, state.base_colors)
        ]
        state.dirty = any(state.dirty_colors)
        self._update_palette_indicator(palette_id, state)

    def _apply_palette_state(self, state: PaletteState):
        self.status_label.setText("" if not state.invalid else "Invalid palette file layout")
        for control in self.color_controls:
            control.setEnabled(not state.invalid)

        if state.invalid:
            self.file_name_label.setText(state.name)
            self._set_title(state.name)
            self.pending_label.setText("")
            self.save_btn.setEnabled(False)
            self.reset_btn.setEnabled(False)
            self.open_file_btn.setEnabled(True)
            self.save_as_btn.setEnabled(True)
            for control in self.color_controls:
                control.set_pending(False)
                control.set_actions_enabled(reset_enabled=False, save_enabled=False)
            return

        self.file_name_label.setText(state.name)
        self._set_title(state.name)
        self.pending_label.setText("Pending changes" if state.dirty else "")

        is_default = state.name == "Default"
        for index, (control, color) in enumerate(zip(self.color_controls, state.colors)):
            control.set_color(color, emit=False)
            pending = state.dirty_colors[index] if index < len(state.dirty_colors) else False
            control.set_pending(pending)
            control.set_actions_enabled(reset_enabled=pending, save_enabled=pending and not is_default)

        self.save_btn.setEnabled(state.dirty and not is_default)
        self.reset_btn.setEnabled(True)
        self.save_as_btn.setEnabled(True)
        self.open_file_btn.setEnabled(True)
        self._push_palette_to_sessions(state.colors)

    def _on_color_changed(self, index: int, color: ColorTuple):
        palette_id = self.current_palette_id
        if not palette_id:
            return
        state = self.palette_states.get(palette_id)
        if not state or state.invalid:
            return
        if index >= len(state.colors):
            return
        state.colors[index] = color
        state.dirty_colors[index] = color != state.base_colors[index]
        state.dirty = any(state.dirty_colors)

        self.color_controls[index].set_pending(state.dirty_colors[index])
        self.color_controls[index].set_actions_enabled(
            reset_enabled=state.dirty_colors[index],
            save_enabled=state.dirty_colors[index] and state.name != "Default",
        )

        self.pending_label.setText("Pending changes" if state.dirty else "")
        self.save_btn.setEnabled(state.dirty and state.name != "Default")
        self._update_palette_indicator(palette_id, state)
        self._push_palette_to_sessions(state.colors)

    def _on_color_reset(self, index: int):
        state = self._current_state()
        if not state or not state.path or state.invalid:
            return

        parsed = parse_palette_file(state.path)
        if not parsed.valid:
            QMessageBox.warning(self, "Reset", parsed.error or "Invalid palette file layout")
            return
        if index >= len(parsed.colors):
            return

        state.colors[index] = parsed.colors[index]
        state.base_colors[index] = parsed.colors[index]
        state.dirty_colors[index] = False
        state.dirty = any(state.dirty_colors)

        control = self.color_controls[index]
        control.set_color(state.colors[index], emit=False)
        control.set_pending(False)
        control.set_actions_enabled(reset_enabled=False, save_enabled=False)

        self.pending_label.setText("Pending changes" if state.dirty else "")
        self.save_btn.setEnabled(state.dirty and state.name != "Default")
        self._update_palette_indicator(self.current_palette_id, state)
        self._push_palette_to_sessions(state.colors)

    def _on_color_save(self, index: int):
        state = self._current_state()
        if not state or not state.path or state.invalid or state.name == "Default":
            return
        if index >= len(state.colors) or not state.dirty_colors[index]:
            return
        try:
            update_palette_color(
                state.path,
                index,
                state.colors[index],
                self.settings.get("color_save_format", "#rrggbb"),
            )
        except Exception as exc:
            QMessageBox.warning(self, "Save", str(exc))
            return

        state.base_colors[index] = state.colors[index]
        state.dirty_colors[index] = False
        state.dirty = any(state.dirty_colors)

        control = self.color_controls[index]
        control.set_pending(False)
        control.set_actions_enabled(reset_enabled=False, save_enabled=False)

        self.pending_label.setText("Pending changes" if state.dirty else "")
        self.save_btn.setEnabled(state.dirty and state.name != "Default")
        self._update_palette_indicator(self.current_palette_id, state)

    def _update_palette_indicator(self, palette_id: str, state: PaletteState):
        for index in range(self.palette_list.count()):
            item = self.palette_list.item(index)
            if item.data(Qt.UserRole) != palette_id:
                continue
            if state.dirty:
                item.setIcon(self._dirty_icon())
                item.setToolTip("Pending changes")
            else:
                item.setIcon(QIcon())
                if palette_id == "Default":
                    item.setToolTip("Default palette")
                else:
                    item.setToolTip("")
            break

    def _dirty_icon(self) -> QIcon:
        pixmap = QPixmap(10, 10)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(Qt.red)
        painter.setPen(Qt.red)
        painter.drawEllipse(2, 2, 6, 6)
        painter.end()
        return QIcon(pixmap)

    def _open_palette_folder(self):
        palette_dir = self._palette_dir()
        palette_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(palette_dir)))

    def _open_palette_file(self):
        state = self._current_state()
        if not state or not state.path:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(state.path)))

    def _rename_palette(self):
        state = self._current_state()
        if not state or state.name == "Default" or not state.path:
            QMessageBox.information(self, "Rename", "Default palette cannot be renamed.")
            return

        new_name, ok = QInputDialog.getText(self, "Rename Palette", "New name:")
        if not ok or not new_name.strip():
            return

        new_name = new_name.strip()
        if Path(new_name).suffix == "":
            new_name += self.settings.get("save_extension", ".txt")

        new_path = state.path.parent / new_name
        if new_path.exists():
            QMessageBox.warning(self, "Rename", "A file with that name already exists.")
            return

        state.path.rename(new_path)
        self._load_palette_list()

    def _set_title(self, palette_name: str | None) -> None:
        if palette_name:
            self.setWindowTitle(f"IntelliPal — {palette_name}")
        else:
            self.setWindowTitle("IntelliPal")

    def _resize_to_fit_colors(self) -> None:
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return
        available_height = screen.availableGeometry().height()

        controls_height = self.controls_container.sizeHint().height()
        left_height = self.left_panel_widget.sizeHint().height()
        content_height = max(controls_height, left_height)

        chrome_height = self.height() - self.centralWidget().height()
        desired_height = content_height + chrome_height + 8

        safe_height = max(0, available_height - 20)
        target_height = min(desired_height, safe_height)
        self.resize(self.width(), target_height)


    def _style_section_label(self, label: QLabel) -> None:
        palette = self.palette()
        border = palette.color(QPalette.Mid).name()
        bg_color = palette.color(QPalette.AlternateBase)
        if bg_color.lightness() > 160:
            bg = bg_color.darker(110).name()
            text = "#000000"
        else:
            bg = bg_color.lighter(130).name()
            text = palette.color(QPalette.WindowText).name()

        label.setStyleSheet(
            f"font-weight: 600; padding: 4px 6px; background-color: {bg}; color: {text}; border: 1px solid {border};"
        )

    def _save_palette(self):
        state = self._current_state()
        if not state or state.name == "Default" or not state.path:
            return
        try:
            update_palette_file(state.path, state.colors, self.settings.get("color_save_format", "#rrggbb"))
        except Exception as exc:
            QMessageBox.warning(self, "Save", str(exc))
            return

        state.base_colors = state.colors[:]
        state.dirty_colors = [False] * len(state.colors)
        state.dirty = False
        self.pending_label.setText("")
        self.save_btn.setEnabled(False)
        for control in self.color_controls:
            control.set_pending(False)
            control.set_actions_enabled(reset_enabled=False, save_enabled=False)
        self._update_palette_indicator(self.current_palette_id, state)

    def _save_as_palette(self):
        state = self._current_state()
        if not state:
            return

        base_name, ok = QInputDialog.getText(self, "Save As", "New palette name:")
        if not ok or not base_name.strip():
            return

        save_extension = self.settings.get("save_extension", ".txt")
        base_name = Path(base_name.strip()).stem
        new_path = self._palette_dir() / f"{base_name}{save_extension}"
        if new_path.exists():
            QMessageBox.warning(self, "Save As", "A file with that name already exists.")
            return

        self._palette_dir().mkdir(parents=True, exist_ok=True)
        write_palette_file(
            new_path,
            state.colors,
            self.settings.get("color_save_format", "#rrggbb"),
            self.settings.get("color_labels", DEFAULT_LABELS),
        )

        state.base_colors = state.colors[:]
        state.dirty_colors = [False] * len(state.colors)
        state.dirty = False
        self.pending_label.setText("")
        self.save_btn.setEnabled(False)
        for control in self.color_controls:
            control.set_pending(False)
            control.set_actions_enabled(reset_enabled=False, save_enabled=False)
        self._update_palette_indicator(self.current_palette_id, state)
        self._load_palette_list()

    def _reset_palette(self):
        state = self._current_state()
        if not state or not state.path:
            return

        parsed = parse_palette_file(state.path)
        if not parsed.valid:
            QMessageBox.warning(self, "Reset", parsed.error or "Invalid palette file layout")
            return

        state.colors = parsed.colors[:]
        state.base_colors = parsed.colors[:]
        state.dirty_colors = [False] * len(state.colors)
        state.dirty = False
        self._apply_palette_state(state)
        self._update_palette_indicator(self.current_palette_id, state)

    def _current_state(self) -> PaletteState | None:
        if not self.current_palette_id:
            return None
        return self.palette_states.get(self.current_palette_id)

    def _import_palette_files(self, files: List[str]):
        palette_dir = self._palette_dir()
        palette_dir.mkdir(parents=True, exist_ok=True)
        extensions = self._palette_extensions()

        for file_path in files:
            path = Path(file_path)
            if path.suffix.lower() not in extensions:
                continue
            destination = palette_dir / path.name
            if destination.exists():
                QMessageBox.warning(self, "Import", f"File already exists: {path.name}")
                continue
            destination.write_bytes(path.read_bytes())

        self._load_palette_list()

    def _open_settings(self):
        def on_change(new_settings):
            self.settings = new_settings
            labels = self.settings.get("color_labels", DEFAULT_LABELS)
            self._build_color_controls(labels)
            self._load_palette_list()
            self._apply_session_settings()
            self._update_game_session_availability()

        dialog = SettingsDialog(self.settings, on_change)
        dialog.exec()

    def closeEvent(self, event):
        for session in list(self.game_sessions):
            if session.dialog is not None:
                session.dialog.close()
            session.memory_map.close()
        self.game_sessions.clear()
        super().closeEvent(event)


def create_app() -> QApplication:
    app = QApplication([])
    window = MainWindow()
    log_path = window.settings.get("log_file", "")
    if log_path:
        try:
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)
            Path(log_path).write_text("", encoding="utf-8")
        except Exception:
            pass
    window.show()
    app.window = window
    return app
