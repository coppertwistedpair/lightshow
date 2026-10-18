import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QComboBox,
    QColorDialog, QMessageBox,
    QGroupBox, QDialog, QLineEdit, QDialogButtonBox, QCheckBox, QSpinBox, QSlider,
)
from PyQt6.QtCore import Qt, QEvent, QMimeData, QTimer
from PyQt6.QtGui import QColor, QFont, QDrag
import serial.tools.list_ports
from core.animations import HOLIDAY_PRESETS


class ColorSwatch(QPushButton):
    """A colored square button that opens a color picker when clicked."""

    def __init__(self, color=(255, 0, 0), parent=None):
        super().__init__(parent)
        self.setFixedSize(52, 52)
        self.set_color(color)
        self.clicked.connect(self._pick_color)

    def set_color(self, color):
        r, g, b = color[0], color[1], color[2]
        self.color = (r, g, b, 0, 0, 0)
        self.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); border: 2px solid #888; border-radius: 4px;"
        )

    def _pick_color(self):
        r, g, b = self.color[0], self.color[1], self.color[2]
        picked = QColorDialog.getColor(
            QColor(r, g, b), self.window(), "Pick a Color",
            QColorDialog.ColorDialogOption.DontUseNativeDialog
        )
        if picked.isValid():
            self.set_color((picked.red(), picked.green(), picked.blue()))


_CHANNEL_SWATCH_PROPS = {
    'W':  {'label': 'W',  'bg': '#ffffff', 'fg': '#000000', 'color': (0, 0, 0, 0, 255, 0)},
    'A':  {'label': 'A',  'bg': '#ff8800', 'fg': '#000000', 'color': (0, 0, 0, 255, 0, 0)},
    'UV': {'label': 'UV', 'bg': '#6600cc', 'fg': '#ffffff', 'color': (0, 0, 0, 0, 0, 255)},
}


class ChannelSwatch(QPushButton):
    """A fixed swatch representing a dedicated LED channel (W, A, or UV)."""

    def __init__(self, channel, parent=None):
        super().__init__(parent)
        props = _CHANNEL_SWATCH_PROPS[channel]
        self.color = props['color']
        self.setFixedSize(52, 52)
        self.setText(props['label'])
        self.setStyleSheet(
            f"background-color: {props['bg']}; color: {props['fg']}; "
            f"border: 2px solid #888; border-radius: 4px; font-weight: bold; font-size: 16px;"
        )


class SwatchContainer(QWidget):
    """Wraps a color or channel swatch with an X button overlay and drag-to-reorder support."""

    def __init__(self, swatch, parent=None):
        super().__init__(parent)
        self.swatch = swatch
        self._drag_start = None
        self.setFixedSize(58, 64)

        swatch.setParent(self)
        swatch.setFixedSize(52, 52)
        swatch.move(0, 12)
        swatch.installEventFilter(self)

        self._x_btn = QPushButton("×", self)
        self._x_btn.setFixedSize(18, 18)
        self._x_btn.move(40, 0)
        self._x_btn.setStyleSheet(
            "QPushButton { background: #cc3333; color: white; border-radius: 9px; "
            "font-size: 13px; font-weight: bold; border: none; }"
            "QPushButton:hover { background: #ff4444; }"
        )
        self._x_btn.raise_()

    @property
    def color(self):
        return self.swatch.color

    def set_removable(self, removable):
        self._x_btn.setVisible(removable)

    def eventFilter(self, obj, event):
        if obj is self.swatch:
            if event.type() == QEvent.Type.MouseButtonPress:
                self._drag_start = event.position().toPoint()
            elif event.type() == QEvent.Type.MouseMove:
                if (event.buttons() & Qt.MouseButton.LeftButton) and self._drag_start:
                    if (event.position().toPoint() - self._drag_start).manhattanLength() >= 10:
                        self._drag_start = None
                        drag = QDrag(self)
                        mime = QMimeData()
                        mime.setText(str(id(self)))
                        drag.setMimeData(mime)
                        drag.setPixmap(self.grab())
                        drag.setHotSpot(event.position().toPoint())
                        drag.exec(Qt.DropAction.MoveAction)
                        return True
        return False


class SwatchRow(QWidget):
    """Horizontal row of SwatchContainers supporting drag-to-reorder."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self._containers = []

    def add_swatch(self, swatch):
        container = SwatchContainer(swatch, self)
        container._x_btn.clicked.connect(lambda: self._remove(container))
        self._layout.addWidget(container)
        self._containers.append(container)
        self._update_x_buttons()

    def _remove(self, container):
        if len(self._containers) <= 1:
            return
        self._containers.remove(container)
        self._layout.removeWidget(container)
        container.setParent(None)
        container.deleteLater()
        self._update_x_buttons()

    def _update_x_buttons(self):
        removable = len(self._containers) > 1
        for c in self._containers:
            c.set_removable(removable)

    def colors(self):
        return [c.color for c in self._containers]

    def clear(self):
        for c in list(self._containers):
            self._layout.removeWidget(c)
            c.setParent(None)
            c.deleteLater()
        self._containers.clear()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        try:
            target_id = int(event.mimeData().text())
        except (ValueError, AttributeError):
            return
        dragged = next((c for c in self._containers if id(c) == target_id), None)
        if dragged is None:
            return

        drop_x = event.position().toPoint().x()
        old_idx = self._containers.index(dragged)
        insert_idx = len(self._containers)
        for i, c in enumerate(self._containers):
            if drop_x < c.x() + c.width() // 2:
                insert_idx = i
                break

        if insert_idx == old_idx:
            event.acceptProposedAction()
            return

        self._containers.pop(old_idx)
        self._layout.removeWidget(dragged)
        if insert_idx > old_idx:
            insert_idx -= 1
        self._containers.insert(insert_idx, dragged)
        self._layout.insertWidget(insert_idx, dragged)
        event.acceptProposedAction()


class NameDialog(QDialog):
    """Simple dialog asking the user to type a name."""

    def __init__(self, prompt, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Name")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(prompt))
        self.edit = QLineEdit()
        layout.addWidget(self.edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_name(self):
        return self.edit.text().strip()


class MainWindow(QMainWindow):
    def __init__(self, dmx_output, fixture_manager, cycle_mode,
                 rainbow_mode, strobe_mode, candle_mode, police_mode, fireworks_mode):
        super().__init__()
        self.dmx = dmx_output
        self.fixtures = fixture_manager
        self.cycle_mode = cycle_mode
        self.rainbow_mode = rainbow_mode
        self.strobe_mode = strobe_mode
        self.candle_mode = candle_mode
        self.police_mode = police_mode
        self.fireworks_mode = fireworks_mode
        self._all_modes = (cycle_mode, rainbow_mode, strobe_mode, candle_mode, police_mode, fireworks_mode)

        self.setWindowTitle("Lightshow")
        self.setMinimumSize(820, 560)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setSpacing(12)
        root.setContentsMargins(12, 12, 12, 12)

        root.addWidget(self._build_fixture_panel(), stretch=1)
        root.addWidget(self._build_control_panel(), stretch=2)

        self._refresh_fixture_list()

        # Notice if the interface drops out (e.g. USB unplugged) while connected
        self._conn_timer = QTimer(self)
        self._conn_timer.timeout.connect(self._check_connection)
        self._conn_timer.start(500)

    # ── Fixture list ──────────────────────────────────────────────────────────

    def _build_fixture_panel(self):
        group = QGroupBox("Fixtures")
        layout = QVBoxLayout(group)

        self.fixture_list = QListWidget()
        layout.addWidget(self.fixture_list)

        add_btn = QPushButton("+ Add Fixture")
        add_btn.clicked.connect(self._add_fixture)
        layout.addWidget(add_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_fixture)
        layout.addWidget(remove_btn)

        return group

    def _refresh_fixture_list(self):
        self.fixture_list.clear()
        for f in self.fixtures.fixtures:
            end = f.start_address + 5
            self.fixture_list.addItem(f"{f.name}  —  ch {f.start_address}–{end}")

    def _add_fixture(self):
        dlg = NameDialog("Give this light a name (e.g. 'Stage Left'):", self)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.get_name():
            return
        try:
            fixture = self.fixtures.add_fixture(dlg.get_name())
            QMessageBox.information(
                self, "Light Added",
                f"'{fixture.name}' added.\n\n"
                f"On the light itself, set the DMX start address to:  {fixture.start_address}\n\n"
                f"(Uses channels {fixture.start_address} – {fixture.start_address + 5})"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        self._refresh_fixture_list()

    def _remove_fixture(self):
        row = self.fixture_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Nothing Selected", "Click a fixture in the list first.")
            return
        name = self.fixtures.fixtures[row].name
        confirm = QMessageBox.question(
            self, "Remove Fixture", f"Remove '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.fixtures.remove_fixture(row)
            self._refresh_fixture_list()

    # ── Control panel ─────────────────────────────────────────────────────────

    def _build_control_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.addWidget(self._build_connection_group())
        layout.addWidget(self._build_cycle_group())
        layout.addWidget(self._build_animations_group())
        layout.addStretch()
        return widget

    def _build_connection_group(self):
        group = QGroupBox("DMX Interface  (Enttec Pro)")
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel("COM Port:"))

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(110)
        layout.addWidget(self.port_combo)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_ports)
        layout.addWidget(refresh_btn)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setCheckable(True)
        self.connect_btn.clicked.connect(self._toggle_connect)
        layout.addWidget(self.connect_btn)

        self.status_label = QLabel("● Disconnected")
        self.status_label.setStyleSheet("color: #cc3333; font-weight: bold;")
        layout.addWidget(self.status_label)

        layout.addStretch()
        self._refresh_ports()
        return group

    def _refresh_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self.port_combo.addItem(p.device)
        if not ports:
            self.port_combo.addItem("(none found)")

    def _toggle_connect(self, checked):
        if checked:
            port = self.port_combo.currentText()
            if port.startswith("("):
                self.connect_btn.setChecked(False)
                QMessageBox.warning(
                    self, "No COM Port",
                    "No COM port found.\n\nMake sure your Enttec Pro is plugged in, "
                    "then click Refresh."
                )
                return
            try:
                self.dmx.connect(port)
                self.connect_btn.setText("Disconnect")
                self.status_label.setText(f"● Connected  ({port})")
                self.status_label.setStyleSheet("color: #22aa44; font-weight: bold;")
            except Exception as e:
                self.connect_btn.setChecked(False)
                QMessageBox.critical(self, "Connection Failed", str(e))
        else:
            self._stop_all()
            self.dmx.disconnect()
            self.connect_btn.setText("Connect")
            self.status_label.setText("● Disconnected")
            self.status_label.setStyleSheet("color: #cc3333; font-weight: bold;")

    def _build_cycle_group(self):
        group = QGroupBox("Color Cycle Mode")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # --- Color swatches + plus button ---
        swatch_outer = QHBoxLayout()
        swatch_outer.setSpacing(8)

        self.swatch_row = SwatchRow()
        swatch_outer.addWidget(self.swatch_row)

        add_btn = QPushButton("+")
        add_btn.setFixedSize(40, 64)
        add_btn.setStyleSheet("font-size: 22px; font-weight: bold;")
        add_btn.clicked.connect(lambda: self.swatch_row.add_swatch(ColorSwatch()))
        swatch_outer.addWidget(add_btn)
        swatch_outer.addStretch()
        layout.addLayout(swatch_outer)

        # --- LED channel buttons ---
        led_row = QHBoxLayout()
        led_row.setSpacing(6)
        led_row.addWidget(QLabel("Add LED channel:"))
        for ch in ('W', 'A', 'UV'):
            btn = QPushButton(ch)
            btn.setFixedWidth(46)
            btn.clicked.connect(lambda _=False, c=ch: self.swatch_row.add_swatch(ChannelSwatch(c)))
            led_row.addWidget(btn)
        led_row.addStretch()
        layout.addLayout(led_row)

        # --- Chase mode toggle ---
        chase_row = QHBoxLayout()
        self.chase_check = QCheckBox("Chase mode  (each light gets its own color, they rotate)")
        self.chase_check.stateChanged.connect(self._on_chase_changed)
        chase_row.addWidget(self.chase_check)
        chase_row.addStretch()
        layout.addLayout(chase_row)

        # --- Fade / Hold time ---
        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("Fade:"))
        self.fade_spin = QSpinBox()
        self.fade_spin.setRange(0, 60)
        self.fade_spin.setValue(3)
        self.fade_spin.setSuffix("s")
        self.fade_spin.setFixedWidth(64)
        self.fade_spin.valueChanged.connect(lambda v: self.cycle_mode.set_fade_time(float(v)))
        time_row.addWidget(self.fade_spin)

        time_row.addSpacing(20)
        time_row.addWidget(QLabel("Hold:"))
        self.hold_spin = QSpinBox()
        self.hold_spin.setRange(0, 60)
        self.hold_spin.setValue(0)
        self.hold_spin.setSuffix("s")
        self.hold_spin.setFixedWidth(64)
        self.hold_spin.valueChanged.connect(lambda v: self.cycle_mode.set_hold_time(float(v)))
        time_row.addWidget(self.hold_spin)
        time_row.addStretch()
        layout.addLayout(time_row)

        # --- GO button ---
        self.go_btn = QPushButton("GO")
        self.go_btn.setCheckable(True)
        self.go_btn.setFixedHeight(64)
        f = QFont()
        f.setPointSize(20)
        f.setBold(True)
        self.go_btn.setFont(f)
        self.go_btn.setStyleSheet(
            "QPushButton { background-color: #2a7a2a; color: white; border-radius: 6px; }"
            "QPushButton:checked { background-color: #aa2222; }"
        )
        self.go_btn.clicked.connect(self._toggle_go)
        layout.addWidget(self.go_btn)

        # Default colors
        self.swatch_row.add_swatch(ColorSwatch((220, 0, 255)))
        self.swatch_row.add_swatch(ColorSwatch((0, 140, 255)))

        return group

    def _build_animations_group(self):
        group = QGroupBox("Animations & Presets")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # --- Live animation buttons ---
        anim_row = QHBoxLayout()
        anim_row.setSpacing(6)
        anim_btns = [
            ('Rainbow',   self._start_rainbow),
            ('Strobe',    self._start_strobe),
            ('Candle',    self._start_candle),
            ('Police',    self._start_police),
            ('Fireworks', self._start_fireworks),
        ]
        for label, fn in anim_btns:
            btn = QPushButton(label)
            btn.setFixedHeight(36)
            btn.clicked.connect(fn)
            anim_row.addWidget(btn)

        stop_btn = QPushButton('STOP')
        stop_btn.setFixedHeight(36)
        stop_btn.setStyleSheet("background-color: #992222; color: white; font-weight: bold;")
        stop_btn.clicked.connect(self._stop_all)
        anim_row.addWidget(stop_btn)
        anim_row.addStretch()
        layout.addLayout(anim_row)

        # --- Speed slider (shared by Rainbow / Strobe / Police) ---
        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Speed:"))
        self.anim_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.anim_speed_slider.setRange(1, 20)
        self.anim_speed_slider.setValue(8)
        speed_row.addWidget(self.anim_speed_slider)
        self.anim_speed_label = QLabel("8")
        self.anim_speed_label.setFixedWidth(24)
        self.anim_speed_slider.valueChanged.connect(
            lambda v: self.anim_speed_label.setText(str(v))
        )
        speed_row.addWidget(self.anim_speed_label)
        layout.addLayout(speed_row)

        # --- Holiday macros ---
        layout.addWidget(QLabel("Holiday Macros:"))
        row1 = QHBoxLayout()
        row2 = QHBoxLayout()
        for i, (name, colors, fade, hold) in enumerate(HOLIDAY_PRESETS):
            btn = QPushButton(name)
            btn.clicked.connect(
                lambda _=False, c=colors, f=fade, h=hold: self._load_holiday(c, f, h)
            )
            (row1 if i < 4 else row2).addWidget(btn)
        row1.addStretch()
        row2.addStretch()
        layout.addLayout(row1)
        layout.addLayout(row2)

        return group

    def _stop_all(self):
        for mode in self._all_modes:
            mode.stop()
        self.go_btn.setChecked(False)
        self.go_btn.setText("GO")

    def _start_rainbow(self):
        self._stop_all()
        speed = self.anim_speed_slider.value()
        self.rainbow_mode.set_cycle_seconds(21 - speed)  # 1→20s, 20→1s
        self.rainbow_mode.start()

    def _start_strobe(self):
        self._stop_all()
        self.strobe_mode.set_rate(float(self.anim_speed_slider.value()))
        self.strobe_mode.start()

    def _start_candle(self):
        self._stop_all()
        self.candle_mode.start()

    def _start_police(self):
        self._stop_all()
        self.police_mode.set_rate(self.anim_speed_slider.value() * 0.75)
        self.police_mode.start()

    def _start_fireworks(self):
        self._stop_all()
        self.fireworks_mode.start()

    def _load_holiday(self, colors, fade, hold):
        self._stop_all()
        if colors is None:  # New Year → fireworks
            self.fireworks_mode.start()
            return
        self.swatch_row.clear()
        for color in colors:
            self.swatch_row.add_swatch(ColorSwatch(color))
        self.fade_spin.setValue(fade)
        self.hold_spin.setValue(hold)
        self.cycle_mode.set_colors(colors)
        self.cycle_mode.set_fade_time(float(fade))
        self.cycle_mode.set_hold_time(float(hold))
        self.cycle_mode.start()

    def _on_chase_changed(self, state):
        self.cycle_mode.set_chase_mode(state == Qt.CheckState.Checked.value)

    def _toggle_go(self, checked):
        if checked:
            if not self.dmx.is_connected():
                self.go_btn.setChecked(False)
                QMessageBox.warning(
                    self, "Not Connected",
                    "Connect to your Enttec Pro first, then press GO."
                )
                return
            if not self.fixtures.fixtures:
                self.go_btn.setChecked(False)
                QMessageBox.warning(
                    self, "No Fixtures",
                    "Add at least one fixture before starting the show."
                )
                return
            for mode in self._all_modes:
                if mode is not self.cycle_mode:
                    mode.stop()
            self.cycle_mode.set_colors(self.swatch_row.colors())
            self.cycle_mode.set_fade_time(float(self.fade_spin.value()))
            self.cycle_mode.set_hold_time(float(self.hold_spin.value()))
            self.cycle_mode.start()
            self.go_btn.setText("STOP")
        else:
            self._stop_show()

    def _check_connection(self):
        if self.connect_btn.isChecked() and not self.dmx.is_connected():
            self._stop_all()
            self.dmx.disconnect()
            self.connect_btn.setChecked(False)
            self.connect_btn.setText("Connect")
            self.status_label.setText("● Connection lost")
            self.status_label.setStyleSheet("color: #cc3333; font-weight: bold;")
            QMessageBox.warning(
                self, "DMX Connection Lost",
                "Lost contact with the Enttec Pro.\n\n"
                "Check the USB cable, click Refresh, then Connect again."
            )

    def _stop_show(self):
        self.cycle_mode.stop()
        self.go_btn.setText("GO")
        self.go_btn.setChecked(False)

    def closeEvent(self, event):
        self._stop_all()
        self.dmx.disconnect()
        event.accept()
