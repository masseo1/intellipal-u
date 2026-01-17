from __future__ import annotations

from typing import Tuple

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QColorDialog,
    QGroupBox,
    QStyle,
    QMenu,
)

ColorTuple = Tuple[int, int, int]


def clamp_channel(value: int) -> int:
    return max(0, min(255, int(value)))


def color_to_tuple(color: QColor) -> ColorTuple:
    return (color.red(), color.green(), color.blue())


def tuple_to_color(color: ColorTuple) -> QColor:
    return QColor(color[0], color[1], color[2])


class ColorPickerDialog(QColorDialog):
    applied = Signal(QColor)

    def __init__(self, initial: QColor, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Pick Color")
        self.setOption(QColorDialog.DontUseNativeDialog, True)
        self.setOption(QColorDialog.NoButtons, True)
        self.setCurrentColor(initial)

        self.apply_btn = QPushButton("Apply")
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Cancel")

        self.apply_btn.clicked.connect(self._apply)
        self.ok_btn.clicked.connect(self._accept)
        self.cancel_btn.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self.apply_btn)
        buttons.addWidget(self.ok_btn)
        buttons.addWidget(self.cancel_btn)

        layout = self.layout()
        if layout is not None:
            layout.addLayout(buttons)

    def _apply(self):
        self.applied.emit(self.currentColor())

    def _accept(self):
        self.applied.emit(self.currentColor())
        self.accept()


class ColorControl(QWidget):
    colorChanged = Signal(int, tuple)
    resetRequested = Signal(int)
    saveRequested = Signal(int)
    isolateRequested = Signal(int)

    def __init__(self, label: str, index: int, initial: ColorTuple):
        super().__init__()
        self._updating = False
        self._color = initial
        self._label = label
        self._index = index
        self._pending = False

        self.group = QGroupBox()
        self.group.setCheckable(False)

        self.preview = QPushButton()
        self.preview.setFixedSize(40, 20)
        self.preview.setToolTip("Open color picker")
        self._preview_disabled = False
        self._preview_disabled_style = "border: 1px solid #9e9e9e; background-color: #e0e0e0;"

        self._traffic_labels: list[QLabel] = []
        self._traffic_active_style = (
            "QLabel { color: #1b5e20; background: #c8e6c9; border: 1px solid #81c784; "
            "border-radius: 3px; font-weight: 600; padding: 0 2px; }"
        )
        self._traffic_muted_style = (
            "QLabel { color: #9e9e9e; background: transparent; border: none; "
            "font-weight: 400; padding: 0 2px; }"
        )

        self.actions_btn = QToolButton()
        self.actions_btn.setText("Actions")
        self.actions_btn.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMenuButton))
        self.actions_btn.setToolTip("Actions for this color")
        self.actions_btn.setPopupMode(QToolButton.InstantPopup)

        actions_menu = QMenu(self.actions_btn)
        self.reset_action = actions_menu.addAction(
            self.style().standardIcon(QStyle.SP_BrowserReload),
            "Reset",
        )
        self.save_action = actions_menu.addAction(
            self.style().standardIcon(QStyle.SP_DialogSaveButton),
            "Save",
        )
        self.isolate_action = actions_menu.addAction(
            self.style().standardIcon(QStyle.SP_MessageBoxInformation),
            "Isolate",
        )
        self.actions_btn.setMenu(actions_menu)

        self.traffic_container = QWidget()
        traffic_layout = QHBoxLayout(self.traffic_container)
        traffic_layout.setContentsMargins(0, 0, 0, 0)
        traffic_layout.setSpacing(2)
        self.traffic_container.setFixedHeight(16)
        self.traffic_container.setMaximumWidth(170)
        self.traffic_container.setVisible(True)

        for _ in range(6):
            label_widget = QLabel("")
            label_widget.setAlignment(Qt.AlignCenter)
            label_widget.setFixedSize(24, 14)
            label_widget.setStyleSheet(self._traffic_muted_style)
            label_widget.setVisible(False)
            traffic_layout.addWidget(label_widget)
            self._traffic_labels.append(label_widget)

        row = QHBoxLayout()
        row.setSpacing(2)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.preview)
        row.addWidget(self.actions_btn)
        row.addWidget(self.traffic_container)
        row.addStretch()

        layout = QVBoxLayout(self.group)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(row)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.group)

        self.preview.clicked.connect(self._on_pick)
        self.reset_action.triggered.connect(lambda: self.resetRequested.emit(self._index))
        self.save_action.triggered.connect(lambda: self.saveRequested.emit(self._index))
        self.isolate_action.triggered.connect(lambda: self.isolateRequested.emit(self._index))

        self.set_color(initial, emit=False)

    def _update_preview(self) -> None:
        color = tuple_to_color(self._color)
        if self._preview_disabled:
            self.preview.setStyleSheet(self._preview_disabled_style)
            return
        self.preview.setStyleSheet(
            f"border: 1px solid #444; background-color: {color.name().upper()};"
        )

    def _update_title(self) -> None:
        r, g, b = self._color
        hex_value = f"#{r:02X}{g:02X}{b:02X}"
        indicator = "" if not self._pending else "* "
        self.group.setTitle(f"{indicator}{self._label} ({hex_value}-R{r},G{g},B{b})")

    def set_color(self, color: ColorTuple, emit: bool = True) -> None:
        self._updating = True
        self._color = (clamp_channel(color[0]), clamp_channel(color[1]), clamp_channel(color[2]))
        self._update_preview()
        self._update_title()
        self._updating = False
        if emit:
            self.colorChanged.emit(self._index, self._color)

    def color(self) -> ColorTuple:
        return self._color

    def set_pending(self, pending: bool) -> None:
        self._pending = pending
        self._update_title()

    def set_actions_enabled(self, reset_enabled: bool, save_enabled: bool) -> None:
        self.reset_action.setEnabled(reset_enabled)
        self.save_action.setEnabled(save_enabled)

    def set_actions_icon(self, icon: QIcon, size: int = 16) -> None:
        if not icon.isNull():
            self.actions_btn.setIcon(icon)
            self.actions_btn.setIconSize(QSize(size, size))

    def set_isolation_state(self, isolation_active: bool, is_isolated: bool) -> None:
        if isolation_active and is_isolated:
            self.isolate_action.setText("Clear")
        else:
            self.isolate_action.setText("Isolate")

        preview_enabled = not isolation_active or is_isolated
        self._preview_disabled = not preview_enabled
        self.preview.setEnabled(preview_enabled)
        self._update_preview()

    def update_traffic_lights(self, session_labels: list[tuple[str, bool]], focus_active: bool) -> None:
        for idx, label_widget in enumerate(self._traffic_labels):
            if idx >= len(session_labels):
                label_widget.setVisible(False)
                continue
            text, active = session_labels[idx]
            label_widget.setText(text)
            label_widget.setStyleSheet(self._traffic_active_style if active else self._traffic_muted_style)
            label_widget.setVisible(True)

        _ = focus_active

    def set_traffic_lights_visible(self, visible: bool) -> None:
        self.traffic_container.setVisible(visible)
        if not visible:
            for label_widget in self._traffic_labels:
                label_widget.setVisible(False)

    def _on_pick(self) -> None:
        dialog = ColorPickerDialog(tuple_to_color(self._color), self)
        dialog.applied.connect(lambda color: self.set_color(color_to_tuple(color)))
        dialog.exec()
