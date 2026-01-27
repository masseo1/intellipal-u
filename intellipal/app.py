from __future__ import annotations

from dataclasses import dataclass
import os
import sys
import shlex
import time
from pathlib import Path
from typing import Dict, List, Tuple

from PySide6.QtCore import Qt, QTimer, QProcess, QEvent, QSize
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap, QPainter, QPalette, QGuiApplication, QAction, QWindow, QColor
from PySide6.QtSvg import QSvgRenderer
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
from .settings import load_settings, save_settings, DEFAULT_LABELS, SCREENSHOT_RES_OPTIONS
from .memory_map import SharedMemoryMap
from .widgets import ColorControl
try:
    from ._build import BUILD_ID
except Exception:
    BUILD_ID = "DEV"

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
    last_heartbeat: int = 0
    last_heartbeat_time: float = 0.0
    is_unresponsive: bool = False
    dialog: "GameDialog | None" = None


class SettingsDialog(QDialog):
    def __init__(self, settings: Dict, on_change):
        super().__init__()
        # Set dialog icon to project settings SVG if present
        try:
            base_dir = Path(__file__).resolve().parents[1]
            svg_path = base_dir / "resources" / "settings.svg"
            if svg_path.exists():
                try:
                    renderer = QSvgRenderer(str(svg_path))
                    pix = QPixmap(QSize(24, 24))
                    pix.fill(Qt.transparent)
                    painter = QPainter(pix)
                    renderer.render(painter)
                    painter.end()
                    self.setWindowIcon(QIcon(pix))
                except Exception:
                    self.setWindowIcon(QIcon(str(svg_path)))
        except Exception:
            pass
        self.setWindowTitle(f"Settings - Build {BUILD_ID}")
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

        self.screenshot_path = QLineEdit(self._settings.get("screenshot_path", "./Screenshots"))
        screenshot_browse_btn = QToolButton()
        screenshot_browse_btn.setText("...")
        screenshot_browse_btn.clicked.connect(self._browse_screenshot_path)

        screenshot_path_row = QHBoxLayout()
        screenshot_path_row.addWidget(self.screenshot_path)
        screenshot_path_row.addWidget(screenshot_browse_btn)
        screenshot_path_widget = QWidget()
        screenshot_path_widget.setLayout(screenshot_path_row)

        self.palette_extensions = QLineEdit(self._settings["palette_extensions"])
        self.color_save_format = QComboBox()
        self.color_save_format.addItems(["#rrggbb", "R G B", "RRR GGG BBB"])
        self.color_save_format.setCurrentText(self._settings["color_save_format"])
        self.save_extension = QLineEdit(self._settings["save_extension"])

        self.start_dock_state = QComboBox()
        self.start_dock_state.addItems(["Left", "Right", "None"])
        self.start_dock_state.setCurrentText(self._settings.get("start_dock_state", "Left"))

        self.emulator_poll_rate = QLineEdit(str(self._settings.get("emulator_poll_rate", 10)))
        self.emulator_start_res = QLineEdit(self._settings.get("emulator_start_res", "1024x768,8"))

        self.default_screenshot_res = QComboBox()
        self.default_screenshot_res.addItems(SCREENSHOT_RES_OPTIONS)
        self.default_screenshot_res.setCurrentText(
            self._settings.get("default_screenshot_res", "1x (320x200)")
        )

        self.jzintv_flags = QLineEdit(self._settings.get("jzintv_flags", ""))
        self.jzintv_flags.setPlaceholderText("(optional)")

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
        general_layout.addRow("Screenshot folder", screenshot_path_widget)
        general_layout.addRow("Palette extensions", self.palette_extensions)
        general_layout.addRow("Color save format", self.color_save_format)
        general_layout.addRow("Save extension", self.save_extension)
        general_layout.addRow("Start dock state", self.start_dock_state)
        general_layout.addRow("Color labels (16 lines)", self.color_labels)

        emulator_layout.addRow("Emulator poll rate", self.emulator_poll_rate)
        emulator_layout.addRow("Exec file path", exec_widget)
        emulator_layout.addRow("GROM file path", grom_widget)
        jzintv_flags_label = QLabel("JZINTV Flags")
        jzintv_flags_label.setToolTip("Optional extra flags passed to jzintv_pal.exe when launching a Game Session.")
        emulator_layout.addRow(jzintv_flags_label, self.jzintv_flags)

        session_layout.addRow("ROMs folder", roms_widget)
        session_layout.addRow("Emulator start resolution", self.emulator_start_res)
        session_layout.addRow("Default screenshot resolution", self.default_screenshot_res)
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
        self.screenshot_path.editingFinished.connect(self._apply)
        self.palette_extensions.editingFinished.connect(self._apply)
        self.color_save_format.currentTextChanged.connect(lambda: self._apply())
        self.save_extension.editingFinished.connect(self._apply)
        self.start_dock_state.currentTextChanged.connect(lambda: self._apply())
        self.emulator_poll_rate.editingFinished.connect(self._apply)
        self.emulator_start_res.editingFinished.connect(self._apply)
        self.jzintv_flags.editingFinished.connect(self._apply)
        self.default_screenshot_res.currentTextChanged.connect(lambda: self._apply())
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

    def _browse_screenshot_path(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Screenshot Folder")
        if directory:
            self.screenshot_path.setText(directory)
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
        screenshot_path = self.screenshot_path.text().strip()
        default_screenshot_res = self.default_screenshot_res.currentText()
        jzintv_flags = self.jzintv_flags.text().strip()

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
        new_settings["screenshot_path"] = screenshot_path
        new_settings["default_screenshot_res"] = default_screenshot_res
        new_settings["jzintv_flags"] = jzintv_flags
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
        try:
            icon_path = Path(__file__).resolve().parents[1] / "resources" / "game.svg"
            if icon_path.exists():
                try:
                    renderer = QSvgRenderer(str(icon_path))
                    pix = QPixmap(QSize(24, 24))
                    pix.fill(Qt.transparent)
                    painter = QPainter(pix)
                    renderer.render(painter)
                    painter.end()
                    self.setWindowIcon(QIcon(pix))
                except Exception:
                    self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        
        # Parse resolution for dialog sizing (logical pixels)
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
        self.process.errorOccurred.connect(self._on_process_error)
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
        self.screenshot_menu = QMenu("Screenshot", self)
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

        self.screenshot_menu_button = QToolButton()
        self.screenshot_menu_button.setText("Screenshot")
        self.screenshot_menu_button.setPopupMode(QToolButton.InstantPopup)
        self.screenshot_menu_button.setMenu(self.screenshot_menu)
        self.screenshot_menu_button.setStyleSheet("QToolButton::menu-indicator { image: none; }")

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
        menu_layout.addWidget(self.screenshot_menu_button, alignment=Qt.AlignVCenter)
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
        close_action = QAction("Close", self)
        reset_action = QAction("Reset Game", self)
        self.pause_action = QAction("Pause Game", self)

        load_action.triggered.connect(self._load_game)
        quit_action.triggered.connect(self._quit_game)
        close_action.triggered.connect(self._close_session)
        reset_action.triggered.connect(lambda: self._send_command("RESET"))
        self.pause_action.triggered.connect(lambda: self._send_command("PAUSE"))

        for action in (load_action, quit_action, reset_action, self.pause_action, close_action):
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

        self.screenshot_res_combo = QComboBox()
        self.screenshot_res_combo.addItems(SCREENSHOT_RES_OPTIONS)
        default_screenshot_res = self.main_window.settings.get("default_screenshot_res", "1x (320x200)")
        if default_screenshot_res not in SCREENSHOT_RES_OPTIONS:
            default_screenshot_res = SCREENSHOT_RES_OPTIONS[0]
        self.screenshot_res_combo.setCurrentText(default_screenshot_res)
        self.screenshot_res_combo.currentTextChanged.connect(self._on_screenshot_resolution_changed)

        self.screenshot_prefix_label = QLabel("")
        self.screenshot_prefix_label.setMinimumWidth(140)
        self.screenshot_prefix_label.setToolTip("Screenshot file prefix")

        self.edit_screenshot_prefix_button = QPushButton("Edit Prefix")
        self.edit_screenshot_prefix_button.clicked.connect(self._on_edit_screenshot_prefix)

        self.take_screenshot_button = QPushButton("Take Screenshot")
        self.take_screenshot_button.clicked.connect(lambda: self._send_command("SCREENSHOT"))

        screenshot_widget = QWidget()
        screenshot_layout = QVBoxLayout(screenshot_widget)
        screenshot_layout.setContentsMargins(8, 6, 8, 6)
        screenshot_layout.setSpacing(6)
        screenshot_layout.addWidget(QLabel("Resolution"))
        screenshot_layout.addWidget(self.screenshot_res_combo)
        screenshot_layout.addWidget(QLabel("File Prefix"))
        screenshot_layout.addWidget(self.screenshot_prefix_label)
        screenshot_layout.addWidget(self.edit_screenshot_prefix_button)
        screenshot_layout.addWidget(self.take_screenshot_button)

        screenshot_action = QWidgetAction(self)
        screenshot_action.setDefaultWidget(screenshot_widget)
        self.screenshot_menu.addAction(screenshot_action)

        self._screenshot_menu_open = False
        self.screenshot_menu.aboutToShow.connect(self._on_screenshot_menu_opened)
        self.screenshot_menu.aboutToHide.connect(self._on_screenshot_menu_closed)

        self.ref_status_label = ElideLabel("")
        self.ref_status_label.setToolTip("")
        self.ref_status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.ref_status_label.setVisible(False)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #b00020;")
        self.status_label.setAlignment(Qt.AlignRight)
        self._status_base_text = "Emulator not running."
        self._unresponsive_override = False
        self._update_status_focus()

        # Container for embedded window
        self.video_container = QWidget()
        self.video_container.setStyleSheet("background-color: black;")
        
        # Use scroll area to clip the container to the selected resolution
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
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(6)
        status_row.addWidget(self.ref_status_label)
        status_row.addWidget(self.status_label)
        central_layout.addLayout(status_row)
        self.setCentralWidget(central)

        self._init_screenshot_controls()
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
            if self.session.is_unresponsive:
                self._force_kill_emulator("Load Game")
                self._launch_emulator(rom_path)
                return
            self._pending_rom_path = rom_path
            self._send_command("QUIT")
            self._stop_emulator()
            self._set_status_base("Waiting for emulator to quit...")
            return
        self._launch_emulator(rom_path)

    def _quit_game(self) -> None:
        if self.session.is_unresponsive:
            self._force_kill_emulator("Quit Game")
            return
        self._send_command("QUIT")

    def _close_session(self) -> None:
        if self.session.is_unresponsive:
            self._force_kill_emulator("Close")
        self.close()

    def _sync_pause_action(self) -> None:
        if not hasattr(self, "pause_action"):
            return
        if self.session.emulator_paused:
            self.pause_action.setText("Resume")
        else:
            self.pause_action.setText("Pause Game")

    def _init_screenshot_controls(self) -> None:
        self._screenshot_prefix_updating = False
        default_prefix = self._default_screenshot_prefix(self.session_id_value)
        self._screenshot_prefix_value = default_prefix
        self._update_screenshot_prefix_label()
        try:
            self._write_screenshot_scale(self.screenshot_res_combo.currentText())
            self._write_screenshot_prefix(default_prefix)
        except Exception as exc:
            self._set_screenshot_controls_enabled(False)
            self.main_window._log_message(f"Screenshot controls disabled: {exc}")

    def _set_screenshot_controls_enabled(self, enabled: bool) -> None:
        self.screenshot_menu_button.setEnabled(enabled)
        self.screenshot_res_combo.setEnabled(enabled)
        self.screenshot_prefix_label.setEnabled(enabled)
        self.edit_screenshot_prefix_button.setEnabled(enabled)
        self.take_screenshot_button.setEnabled(enabled)

    def _default_screenshot_prefix(self, session_id_value: str) -> str:
        return f"{session_id_value}_"

    def _screenshot_scale_from_text(self, value: str) -> int:
        try:
            base = value.split("x", 1)[0].strip()
            parsed = int(base)
            return parsed if parsed > 0 else 1
        except Exception:
            return 1

    def _write_screenshot_scale(self, value: str) -> None:
        scale = self._screenshot_scale_from_text(value)
        self.session.memory_map.set_scale_screenshot(scale)

    def _write_screenshot_prefix(self, value: str) -> None:
        self.session.memory_map.set_screenshot_prefix(value)

    def _on_screenshot_resolution_changed(self, value: str) -> None:
        try:
            self._write_screenshot_scale(value)
        except Exception as exc:
            self._set_screenshot_controls_enabled(False)
            self.main_window._log_message(f"Failed to set screenshot scale: {exc}")

    def _update_screenshot_prefix_label(self) -> None:
        self.screenshot_prefix_label.setText(self._screenshot_prefix_value)

    def _on_edit_screenshot_prefix(self) -> None:
        current_value = self._screenshot_prefix_value
        text, ok = QInputDialog.getText(
            self,
            "Screenshot Prefix",
            "Enter screenshot prefix (max 20 chars):",
            text=current_value,
        )
        if not ok:
            return
        new_value = (text or "")[:20]
        self._screenshot_prefix_value = new_value
        self._update_screenshot_prefix_label()
        try:
            self._write_screenshot_prefix(new_value)
        except Exception as exc:
            self._set_screenshot_controls_enabled(False)
            self.main_window._log_message(f"Failed to set screenshot prefix: {exc}")

    def _launch_emulator(self, rom_path: str) -> None:
        exe_path = self.main_window._get_emulator_path()
        if exe_path is None:
            QMessageBox.warning(self, "Launch", "jzintv_pal executable not found.")
            self.main_window._log_message("Launch failed: jzintv_pal executable not found.")
            return
        exec_path = self._exec_path()
        grom_path = self._grom_path()
        display_size = self._current_display_size()
        rom_path = os.path.normpath(rom_path)
        try:
            self._rom_title = Path(rom_path).stem
        except Exception:
            self._rom_title = None
        if not exec_path or not exec_path.exists():
            self.main_window._log_message(f"Launch failed: exec.bin not found at {exec_path}")
            QMessageBox.warning(self, "Launch", "Exec file path is missing or invalid.")
            return
        if not grom_path or not grom_path.exists():
            self.main_window._log_message(f"Launch failed: grom.bin not found at {grom_path}")
            QMessageBox.warning(self, "Launch", "GROM file path is missing or invalid.")
            return
        self.main_window._log_message(
            f"Launching emulator: exe={exe_path} exec={exec_path} grom={grom_path} shm={self.session.map_name} rom={rom_path}"
        )
        jzintv_flags_text = (self.main_window.settings.get("jzintv_flags", "") or "").strip()
        jzintv_flag_args: list[str] = []
        if jzintv_flags_text:
            try:
                jzintv_flag_args = shlex.split(jzintv_flags_text, posix=os.name != "nt")
            except ValueError:
                jzintv_flag_args = [jzintv_flags_text]
        screenshot_dir_arg: str | None = None
        screenshot_path_value = (self.main_window.settings.get("screenshot_path", "") or "").strip()
        if screenshot_path_value:
            target_path = Path(screenshot_path_value)
            if not target_path.is_absolute():
                target_path = (Path.cwd() / target_path).resolve()
            try:
                target_path.mkdir(parents=True, exist_ok=True)
                screenshot_dir_arg = str(target_path)
            except Exception as exc:
                self.main_window._log_message(f"Screenshot path unavailable, using CWD: {exc}")

        cmd_line = (
            f"\"{exe_path}\" --shm-name=\"{self.session.map_name}\" "
            f"--execimg=\"{exec_path}\" --gromimg=\"{grom_path}\" "
            f"--displaysize=\"{display_size}\" "
        )
        if screenshot_dir_arg:
            cmd_line += f"--screenshot-dir=\"{screenshot_dir_arg}\" "
        if jzintv_flags_text:
            cmd_line += f" {jzintv_flags_text} "
        cmd_line += f"\"{rom_path}\""
        self.main_window._log_message(f"Command line: {cmd_line}")
        self._stop_emulator()
        self._set_status_base("Launching emulator...")
        self.process.setProgram(str(exe_path))
        args = [
            f"--shm-name={self.session.map_name}",
            f"--execimg={exec_path}",
            f"--gromimg={grom_path}",
            f"--displaysize={display_size}",
        ]
        if screenshot_dir_arg:
            args.append(f"--screenshot-dir={screenshot_dir_arg}")
        if jzintv_flag_args:
            args.extend(jzintv_flag_args)
        args.append(rom_path)
        self.process.setArguments(args)
        self.process.start()

    def _dpi_scale(self) -> float:
        handle = self.windowHandle()
        if handle is not None:
            screen = handle.screen()
            if screen is not None:
                return float(screen.devicePixelRatio())
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            return float(screen.devicePixelRatio())
        return 1.0

    def _current_display_size(self) -> str:
        # Match jzintv render size to OS DPI scaling to keep visible size consistent
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

        scale = self._dpi_scale()
        scaled_w = max(1, int(round(width * scale)))
        scaled_h = max(1, int(round(height * scale)))
        return f"{scaled_w}x{scaled_h},{depth}"

    def _exec_path(self) -> Path:
        p = Path(self.main_window.settings.get("exec_file_path", "./exec.bin"))
        if not p.is_absolute():
            return (Path.cwd() / p).resolve()
        return p

    def _grom_path(self) -> Path:
        p = Path(self.main_window.settings.get("grom_file_path", "./grom.bin"))
        if not p.is_absolute():
            return (Path.cwd() / p).resolve()
        return p

    def _stop_emulator(self) -> None:
        if self.process.state() != QProcess.NotRunning:
            self._send_command("QUIT")
            self.process.terminate()
            self.process.waitForFinished(2000)
        self._embedded = False
        self._embed_timer.stop()
        self._embedded_window_hwnd = None
        if self.session.is_unresponsive:
            self.session.is_unresponsive = False
            self._set_unresponsive_state(False)
        self._set_status_base("Emulator not running.")

    def _on_process_started(self) -> None:
        self._set_status_base("Emulator running. Embedding window...")
        self._embed_timer.start()

    def _on_process_finished(self) -> None:
        exit_code = self.process.exitCode()
        exit_status = self.process.exitStatus()
        self.main_window._log_message(f"Emulator exited: code={exit_code} status={exit_status}")
        self._set_status_base("Emulator not running.")
        if self.session.is_unresponsive:
            self.session.is_unresponsive = False
            self._set_unresponsive_state(False)
        self.session.last_heartbeat = 0
        self.session.last_heartbeat_time = 0.0
        self._embed_timer.stop()
        if self._pending_rom_path:
            rom_path = self._pending_rom_path
            self._pending_rom_path = None
            self._launch_emulator(rom_path)

    def _force_kill_emulator(self, action: str) -> None:
        if self.process.state() == QProcess.NotRunning:
            return
        self.main_window._log_message(f"Force killing emulator due to unresponsive state ({action}).")
        self.process.kill()
        self.process.waitForFinished(2000)
        self._stop_emulator()

    def _set_unresponsive_state(self, is_unresponsive: bool) -> None:
        self._unresponsive_override = is_unresponsive
        self._update_status_focus()

    def _on_process_error(self, error) -> None:
        flags_text = (self.main_window.settings.get("jzintv_flags", "") or "").strip()
        hint = ""
        if flags_text:
            hint = f"\n\nJZINTV Flags setting may be a cause: {flags_text}"
        self.main_window._log_message(f"Emulator process error: {error}{hint}")
        QMessageBox.warning(
            self,
            "Game Session",
            f"Emulator failed to start or stopped unexpectedly.{hint}",
        )

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
        if getattr(self, "_unresponsive_override", False):
            self.status_label.setText("Emulator unresponsive.")
            self.status_label.setStyleSheet("color: #b00020;")
            return
        if self.isActiveWindow():
            suffix = " Input Ready"
            color = "#1b5e20"
        else:
            suffix = " Input Not Ready"
            color = "#b00020"
        self.status_label.setText(f"{self._status_base_text}{suffix}")
        self.status_label.setStyleSheet(f"color: {color};")

    def _focus_emulator_window(self) -> None:
        if getattr(self, "_screenshot_menu_open", False):
            return
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

    def _on_screenshot_menu_opened(self) -> None:
        self._screenshot_menu_open = True
        self._update_status_focus()

    def _on_screenshot_menu_closed(self) -> None:
        self._screenshot_menu_open = False
        self._focus_emulator_window()
        self._update_status_focus()

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
            self._maybe_update_screenshot_prefix(current_value, new_value)
            self.main_window._update_traffic_lights()

    def _maybe_update_screenshot_prefix(self, old_session_id: str, new_session_id: str) -> None:
        if not hasattr(self, "screenshot_prefix_label"):
            return
        old_default = self._default_screenshot_prefix(old_session_id)
        if getattr(self, "_screenshot_prefix_value", "") != old_default:
            return
        new_default = self._default_screenshot_prefix(new_session_id)
        self._screenshot_prefix_value = new_default
        self._update_screenshot_prefix_label()
        try:
            self._write_screenshot_prefix(new_default)
        except Exception as exc:
            self._set_screenshot_controls_enabled(False)
            self.main_window._log_message(f"Failed to update screenshot prefix: {exc}")

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
            self._update_ref_status_label(None)
            return
        palette_path = self.main_window._get_palette_path(value)
        if palette_path is None:
            return
        parsed = parse_palette_file(palette_path)
        if not parsed.valid:
            QMessageBox.warning(self, "Reference Palette", parsed.error or "Invalid palette file")
            return
        self._update_reference_controls(enabled=True)
        # Always write reference palette on selection so the map is populated
        self._apply_reference_palette()
        self._apply_ref_split()
        self._update_ref_status_label(value)
        if self.main_window._isolation_active():
            self.main_window._apply_isolation_state()

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
        if self._reference_palette_active():
            self._apply_reference_palette()

    def _reference_palette_active(self) -> bool:
        return (
            self.ref_palette_combo.currentText() != "<none>"
            and self.ref_split_mode.currentText() != "No Split"
        )

    def _get_reference_palette_colors(self) -> List[ColorTuple] | None:
        name = self.ref_palette_combo.currentText()
        if name == "<none>":
            return None
        palette_path = self.main_window._get_palette_path(name)
        if palette_path is None:
            return None
        parsed = parse_palette_file(palette_path)
        if not parsed.valid:
            return None
        return parsed.colors

    def _apply_reference_palette(self) -> None:
        colors = self._get_reference_palette_colors()
        if colors is None:
            return
        if self.main_window._isolation_active():
            colors = self.main_window._apply_isolation_to_colors(colors)
        self.session.memory_map.write_ref_palette(self.main_window._colors_to_map_values(colors))

    def _update_ref_status_label(self, name: str | None) -> None:
        if not name or name == "<none>":
            self.ref_status_label.setText("")
            self.ref_status_label.setToolTip("")
            self.ref_status_label.setVisible(False)
            return
        self.ref_status_label.setVisible(True)
        self.ref_status_label.setText(f"Ref:{name}")
        self.ref_status_label.setToolTip(name)

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
        self.setWindowTitle(f"IntelliPal - Build {BUILD_ID}")
        try:
            icon_path = Path(__file__).resolve().parents[1] / "resources" / "icon_snafu.png"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        self.resize(520, 800)

        self._dock_width = 520
        
        self._early_logs = []
        self._isolated_indices: set[int] = set()

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

        # local helper to load SVG icons from resources (render to pixmap)
        def _load_icon(name: str, size: int = 24):
            try:
                svg_path = self.base_dir / "resources" / f"{name}.svg"
                if svg_path.exists():
                    renderer = QSvgRenderer(str(svg_path))
                    pix = QPixmap(QSize(size, size))
                    pix.fill(Qt.transparent)
                    p = QPainter(pix)
                    renderer.render(p)
                    p.end()
                    return QIcon(pix)
            except Exception:
                pass
            return None

        self._load_icon = _load_icon

        # Assign icons from resources when available, otherwise use standard icons
        icon = self._load_icon("view")
        self.open_folder_btn.setIcon(icon or self.style().standardIcon(QStyle.SP_DirOpenIcon))
        icon = self._load_icon("rename")
        self.rename_btn.setIcon(icon or self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        # Use project SVG for settings icon if available
        try:
            svg_path = self.base_dir / "resources" / "settings.svg"
            if svg_path.exists():
                # Render SVG into a QPixmap for reliable display across styles
                try:
                    renderer = QSvgRenderer(str(svg_path))
                    pix = QPixmap(QSize(24, 24))
                    pix.fill(Qt.transparent)
                    painter = QPainter(pix)
                    renderer.render(painter)
                    painter.end()
                    self.settings_btn.setIcon(QIcon(pix))
                    self.settings_btn.setIconSize(QSize(16, 16))
                except Exception:
                    self.settings_btn.setIcon(QIcon(str(svg_path)))
            else:
                self.settings_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogContentsView))
        except Exception:
            self.settings_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogContentsView))
        icon = self._load_icon("game")
        self.new_session_btn.setIcon(icon or self.style().standardIcon(QStyle.SP_MediaPlay))

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
        # Default to emulator_start_res when available
        default_res = (self.settings.get("emulator_start_res", "640x480,8") or "640x480,8").strip()
        default_idx = self.resolution_combo.findText(default_res)
        if default_idx >= 0:
            self.resolution_combo.setCurrentIndex(default_idx)
        elif default_res:
            # If not in list, append and select without reordering existing entries
            self.resolution_combo.addItem(default_res)
            self.resolution_combo.setCurrentIndex(self.resolution_combo.count() - 1)
        self.resolution_combo.setToolTip("Game session resolution")

        self.open_folder_btn.clicked.connect(self._open_palette_folder)
        self.rename_btn.clicked.connect(self._rename_palette)
        self.settings_btn.clicked.connect(self._open_settings)
        self.new_session_btn.clicked.connect(self._create_game_session)

        self.dock_left_btn = QToolButton()
        self.dock_right_btn = QToolButton()
        icon = self._load_icon("dock-left")
        self.dock_left_btn.setIcon(icon or self.style().standardIcon(QStyle.SP_ArrowLeft))
        icon = self._load_icon("dock-right")
        self.dock_right_btn.setIcon(icon or self.style().standardIcon(QStyle.SP_ArrowRight))
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
        self.refresh_btn = QToolButton()

        icon = self._load_icon("save")
        self.save_btn.setIcon(icon or self.style().standardIcon(QStyle.SP_DialogSaveButton))
        icon = self._load_icon("save-as")
        self.save_as_btn.setIcon(icon or self.style().standardIcon(QStyle.SP_DialogSaveButton))
        icon = self._load_icon("reset")
        self.reset_btn.setIcon(icon or self.style().standardIcon(QStyle.SP_BrowserReload))
        self.refresh_btn.setIcon(icon or self.style().standardIcon(QStyle.SP_BrowserReload))
        icon = self._load_icon("view")
        self.open_file_btn.setIcon(icon or self.style().standardIcon(QStyle.SP_DirOpenIcon))
        icon = self._load_icon("rename")
        self.rename_file_btn.setIcon(icon or self.style().standardIcon(QStyle.SP_FileDialogDetailedView))

        for btn in (self.save_btn, self.save_as_btn, self.reset_btn, self.open_file_btn, self.rename_file_btn, self.refresh_btn):
            btn.setToolButtonStyle(Qt.ToolButtonIconOnly)

        self.save_btn.setToolTip("Save changes")
        self.save_as_btn.setToolTip("Save palette as new file")
        self.reset_btn.setToolTip("Reset to on-disk values")
        self.open_file_btn.setToolTip("Open palette file in default editor")
        self.rename_file_btn.setToolTip("Rename selected palette")
        self.refresh_btn.setToolTip("Refresh palette list")

        self.save_btn.clicked.connect(self._save_palette)
        self.save_as_btn.clicked.connect(self._save_as_palette)
        self.reset_btn.clicked.connect(self._reset_palette)
        self.open_file_btn.clicked.connect(self._open_palette_file)
        self.rename_file_btn.clicked.connect(self._rename_palette)
        self.refresh_btn.clicked.connect(self._refresh_palette_list)

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
        palette_header.addWidget(self.refresh_btn)
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
            if self._isolated_indices:
                isolated_colors = self._apply_isolation_to_colors(palette)
                memory_map.write_palette(self._colors_to_map_values(isolated_colors))
            else:
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

    def _isolation_active(self) -> bool:
        return bool(self._isolated_indices)

    def _get_isolate_background_color(self) -> ColorTuple:
        value = self.settings.get("isolate_background", "#000000")
        color = QColor(value)
        if not color.isValid():
            color = QColor("#000000")
        return (color.red(), color.green(), color.blue())

    def _apply_isolation_to_colors(self, colors: List[ColorTuple]) -> List[ColorTuple]:
        if not self._isolated_indices:
            return colors
        background = self._get_isolate_background_color()
        return [colors[i] if i in self._isolated_indices else background for i in range(16)]

    def _write_main_palette_to_sessions(self, colors: List[ColorTuple]) -> None:
        values = self._colors_to_map_values(colors)
        for session in self.game_sessions:
            session.memory_map.write_palette(values)

    def _write_reference_palette_for_sessions(self) -> None:
        for session in self.game_sessions:
            if session.dialog is None:
                continue
            if session.dialog._reference_palette_active():
                session.dialog._apply_reference_palette()

    def _push_palette_to_sessions(self, colors: List[ColorTuple]) -> None:
        if self._isolated_indices:
            isolated_colors = self._apply_isolation_to_colors(colors)
            self._write_main_palette_to_sessions(isolated_colors)
            return
        self._write_main_palette_to_sessions(colors)

    def _sync_isolation_controls(self) -> None:
        isolation_active = self._isolation_active()
        for idx, control in enumerate(self.color_controls):
            control.set_isolation_state(isolation_active, idx in self._isolated_indices)

    def _apply_isolation_state(self) -> None:
        state = self._current_state()
        if not state or state.invalid or len(state.colors) != 16:
            self._sync_isolation_controls()
            return
        if self._isolated_indices:
            isolated_colors = self._apply_isolation_to_colors(state.colors)
            self._write_main_palette_to_sessions(isolated_colors)
        else:
            self._write_main_palette_to_sessions(state.colors)
        self._write_reference_palette_for_sessions()
        self._sync_isolation_controls()

    def _on_color_isolate(self, index: int) -> None:
        if index in self._isolated_indices:
            self._isolated_indices.clear()
        else:
            self._isolated_indices.add(index)
        self._apply_isolation_state()

    def _poll_game_sessions(self) -> None:
        for session in self.game_sessions:
            try:
                session.displayed_colors = session.memory_map.read_displayed_colors()
                session.emulator_paused = session.memory_map.read_emulator_paused()
                self._update_session_heartbeat(session)
                if session.dialog is not None:
                    session.dialog._sync_pause_action()
            except Exception:
                continue
        if self.traffic_lighting_checkbox.isChecked():
            self._update_traffic_lights()

    def _update_session_heartbeat(self, session: GameSession) -> None:
        if session.dialog is None:
            return
        if session.dialog.process.state() == QProcess.NotRunning:
            if session.is_unresponsive:
                session.is_unresponsive = False
                session.dialog._set_unresponsive_state(False)
            session.last_heartbeat_time = 0.0
            return
        try:
            heartbeat = session.memory_map.read_heartbeat()
        except Exception:
            heartbeat = None
        now = time.monotonic()
        if heartbeat is not None and heartbeat != session.last_heartbeat:
            session.last_heartbeat = heartbeat
            session.last_heartbeat_time = now
            if session.is_unresponsive:
                session.is_unresponsive = False
                session.dialog._set_unresponsive_state(False)
            return
        if session.last_heartbeat_time == 0.0:
            session.last_heartbeat_time = now
            return
        if now - session.last_heartbeat_time > 6.0:
            if not session.is_unresponsive:
                session.is_unresponsive = True
                session.dialog._set_unresponsive_state(True)

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
        # Search order:
        # 1. Current working directory (allows jzintv_pal.exe beside intellipal.exe/runtime)
        # 2. Frozen executable's directory (when bundled with PyInstaller / single-exe)
        # 3. The packaged resources folder (existing behavior)
        candidates = [
            Path.cwd() / "jzintv_pal.exe",
        ]
        try:
            candidates.append(Path(sys.executable).parent / "jzintv_pal.exe")
        except Exception:
            pass
        candidates.append(self.base_dir / "resources" / "jzintv_pal.exe")

        for p in candidates:
            if p.exists():
                return p
        return None

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
            control.isolateRequested.connect(self._on_color_isolate)
            if hasattr(self, "_load_icon"):
                icon = self._load_icon("menu")
                if icon is not None:
                    control.set_actions_icon(icon, size=14)
            self.controls_layout.addWidget(control)
            self.color_controls.append(control)

        self.controls_layout.addStretch()
        self._sync_isolation_controls()

    def _palette_dir(self) -> Path:
        # Resolve palette directory exactly as specified in settings.
        # If the path is relative, resolve it against the current working directory.
        # Do not fall back to packaged resources; obey user settings.
        path = Path(self.settings.get("palette_dir", "./palettes"))
        if not path.is_absolute():
            return (Path.cwd() / path).resolve()
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
            self._sync_isolation_controls()
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
        self._sync_isolation_controls()

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

        new_name, ok = QInputDialog.getText(
            self,
            "Rename Palette",
            "New name:",
            text=state.name,
        )
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

        default_extension = self.settings.get("save_extension", ".txt")
        base_name, ok = QInputDialog.getText(
            self,
            "Save As",
            f"New palette name (default {default_extension}):",
        )
        if not ok or not base_name.strip():
            return

        save_extension = default_extension
        valid_extensions = self._palette_extensions()
        base_name = base_name.strip()
        provided_ext = Path(base_name).suffix
        if provided_ext and provided_ext.lower() in valid_extensions:
            filename = Path(base_name).name
        else:
            filename = f"{Path(base_name).stem}{save_extension}"
        new_path = self._palette_dir() / filename
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

    def _refresh_palette_list(self) -> None:
        self._save_current_state(self.current_palette_id)
        dirty_states = [state for state in self.palette_states.values() if state.dirty]
        if dirty_states:
            prompt = QMessageBox(self)
            prompt.setWindowTitle("Refresh Palettes")
            prompt.setText("You have unsaved palette changes.")
            save_btn = prompt.addButton("Save Changes", QMessageBox.AcceptRole)
            discard_btn = prompt.addButton("Discard Changes", QMessageBox.ButtonRole.DestructiveRole)
            cancel_btn = prompt.addButton("Cancel", QMessageBox.RejectRole)
            prompt.setDefaultButton(save_btn)
            prompt.exec()
            clicked = prompt.clickedButton()
            if clicked == cancel_btn:
                return
            if clicked == save_btn:
                if not self._save_all_dirty_palettes():
                    return

        self._load_palette_list()
        self._refresh_reference_palettes()

    def _save_all_dirty_palettes(self) -> bool:
        for palette_id, state in self.palette_states.items():
            if not state.dirty or state.invalid or not state.path:
                continue
            if state.name == "Default":
                continue
            try:
                update_palette_file(state.path, state.colors, self.settings.get("color_save_format", "#rrggbb"))
            except Exception as exc:
                QMessageBox.warning(self, "Save", str(exc))
                return False
            state.base_colors = state.colors[:]
            state.dirty_colors = [False] * len(state.colors)
            state.dirty = False
            self._update_palette_indicator(palette_id, state)
        self.pending_label.setText("")
        self.save_btn.setEnabled(False)
        return True

    def _refresh_reference_palettes(self) -> None:
        options = [name for name, _ in self._get_palette_options()]
        for session in self.game_sessions:
            dialog = session.dialog
            if dialog is None:
                continue
            current = dialog.ref_palette_combo.currentText()
            dialog.ref_palette_combo.blockSignals(True)
            dialog.ref_palette_combo.clear()
            dialog.ref_palette_combo.addItem("<none>")
            for name in options:
                dialog.ref_palette_combo.addItem(name)
            dialog.ref_palette_combo.blockSignals(False)
            if current in options:
                dialog.ref_palette_combo.setCurrentText(current)
                dialog._on_ref_palette_changed(current)
            else:
                dialog.ref_palette_combo.setCurrentText("<none>")
                dialog._on_ref_palette_changed("<none>")

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
            if self._isolation_active():
                self._apply_isolation_state()

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
    try:
        icon_path = Path(__file__).resolve().parents[1] / "resources" / "icon_snafu.png"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
    except Exception:
        pass
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
