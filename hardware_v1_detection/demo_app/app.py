"""PyQt realtime demo app for Hardware V1 gait detection."""

from __future__ import annotations

import math
import sys
import time
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import pyqtgraph as pg
    import serial
    from serial.tools import list_ports
    from PyQt5 import QtCore, QtWidgets
except ImportError as exc:  # pragma: no cover - GUI dependency guard
    raise SystemExit(
        "Missing GUI dependency. Install gait_medical_system/requirements.txt "
        "or pip install pyserial PyQt5 pyqtgraph."
    ) from exc

from hardware_v1_detection.pc_receiver.protocol import (
    BMI_SENSOR_NAMES,
    FrameParser,
    NodeDebugFrame,
    SampleFrame,
    SENSOR_NAMES,
    scale_sensor,
)
from hardware_v1_detection.pc_receiver.pipeline import DerivedSample, RealtimePipeline
from hardware_v1_detection.pc_receiver.session import SessionWriter, load_gyro_bias

from theme import (
    EVENT_COLORS,
    JOINT_COLORS,
    PALETTE,
    ZONE_COLORS,
    apply_pyqtgraph_theme,
    qss,
    style_plot,
)


class CaptureWorker(QtCore.QThread):
    frame_received = QtCore.pyqtSignal(object)
    node_frame_received = QtCore.pyqtSignal(object)
    status_changed = QtCore.pyqtSignal(str)
    finished_session = QtCore.pyqtSignal(str)

    def __init__(
        self, port: str, baud: int, output_dir: str, calibration_path: str | None
    ):
        super().__init__()
        self.port = port
        self.baud = baud
        self.output_dir = output_dir
        self.calibration_path = calibration_path
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:  # pragma: no cover - hardware/GUI integration
        parser = FrameParser()
        writer = SessionWriter(self.output_dir, load_gyro_bias(self.calibration_path))
        try:
            with serial.Serial(self.port, self.baud, timeout=0.1) as ser:
                self.status_changed.emit(f"connected {self.port}")
                while self._running:
                    chunk = ser.read(4096)
                    if not chunk:
                        continue
                    for frame in parser.feed(chunk):
                        if isinstance(frame, SampleFrame):
                            writer.append_frame(frame)
                            self.frame_received.emit(frame)
                        elif isinstance(frame, NodeDebugFrame):
                            writer.append_node_frame(frame)
                            self.node_frame_received.emit(frame)
                    stats = writer.stats
                    self.status_changed.emit(
                        f"{stats.mcu_frame_rate_hz:.1f}Hz | frames {stats.frames} | "
                        f"drop {stats.dropped_frames} | crc {parser.stats.crc_errors}"
                    )
        except Exception as exc:
            self.status_changed.emit(f"error: {exc}")
        finally:
            session_dir = writer.close(parser)
            self.finished_session.emit(str(session_dir))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Hardware V1 Gait Detection Demo")
        self.resize(1200, 820)
        self.worker: CaptureWorker | None = None
        self.last_frame: SampleFrame | None = None
        self.calibration: dict = {}
        self.pipeline = RealtimePipeline()
        self.buffers = {
            name: {
                "t": deque(maxlen=1000),
                "acc": deque(maxlen=1000),
                "gyro": deque(maxlen=1000),
                "mag": deque(maxlen=1000),
            }
            for name in SENSOR_NAMES
        }
        self.joint_buffers = {
            name: {"t": deque(maxlen=1600), "value": deque(maxlen=1600)}
            for name in (
                "left_ankle",
                "right_ankle",
                "left_knee",
                "right_knee",
                "left_hip",
                "right_hip",
            )
        }
        self.event_history = deque(maxlen=240)
        self.last_node_debug: NodeDebugFrame | None = None
        self.curves: dict[str, dict[str, pg.PlotDataItem]] = {}
        self.joint_curves: dict[str, pg.PlotDataItem] = {}
        self.event_curves: dict[str, pg.PlotDataItem] = {}
        self.cycle_curves: dict[str, pg.PlotDataItem] = {}
        self._build_ui()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._refresh_plots)
        self.timer.start(50)

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)

        controls = QtWidgets.QHBoxLayout()
        controls.setSpacing(8)
        self.port_combo = QtWidgets.QComboBox()
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.start_button = QtWidgets.QPushButton("Start")
        self.start_button.setObjectName("primary")
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.output_edit = QtWidgets.QLineEdit(str(ROOT / "hardware_v1_sessions"))
        self.calibration_edit = QtWidgets.QLineEdit()
        self.status_label = QtWidgets.QLabel("idle")
        self.status_label.setObjectName("statusBar")

        controls.addWidget(self._field_label("Port"))
        controls.addWidget(self.port_combo)
        controls.addWidget(self.refresh_button)
        controls.addWidget(self._field_label("Output"))
        controls.addWidget(self.output_edit, 1)
        controls.addWidget(self._field_label("Calibration"))
        controls.addWidget(self.calibration_edit, 1)
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        layout.addLayout(controls)
        layout.addWidget(self.status_label)

        self.tabs = QtWidgets.QTabWidget()
        self._build_dashboard_tab()
        self._build_raw_debug_tab()
        layout.addWidget(self.tabs, 1)

        self.setCentralWidget(central)
        self.refresh_button.clicked.connect(self.refresh_ports)
        self.start_button.clicked.connect(self.start_capture)
        self.stop_button.clicked.connect(self.stop_capture)
        self.refresh_ports()

    def _build_dashboard_tab(self) -> None:
        dashboard = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(dashboard)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 3)
        grid.setRowStretch(1, 1)
        grid.setRowStretch(2, 2)

        joint_labels = {
            "left_knee": "left knee",
            "right_knee": "right knee",
            "left_hip": "left hip",
            "right_hip": "right hip",
        }
        self.joint_plot = pg.PlotWidget(title="Joint angles")
        self.joint_plot.addLegend()
        self.joint_plot.setLabel("bottom", "time", units="s")
        self.joint_plot.setLabel("left", "angle", units="deg")
        style_plot(self.joint_plot)
        for name, label in joint_labels.items():
            self.joint_curves[name] = self.joint_plot.plot(
                pen=pg.mkPen(JOINT_COLORS[name], width=2), name=label
            )
        grid.addWidget(self._card(self.joint_plot), 0, 0)

        self.event_plot = pg.PlotWidget(title="Gait event timeline")
        self.event_plot.setLabel("bottom", "time", units="s")
        self.event_plot.setYRange(-0.5, 1.5)
        self.event_plot.getAxis("left").setTicks([[(0, "right"), (1, "left")]])
        style_plot(self.event_plot)
        for key, symbol in (
            ("left_heel_strike", "o"),
            ("left_toe_off", "t"),
            ("right_heel_strike", "o"),
            ("right_toe_off", "t"),
        ):
            self.event_curves[key] = self.event_plot.plot(
                [],
                [],
                pen=None,
                symbol=symbol,
                symbolBrush=EVENT_COLORS[key],
                symbolPen=None,
                symbolSize=11,
            )
        grid.addWidget(self._card(self.event_plot), 1, 0)

        grid.addWidget(self._build_side_panel(), 0, 1, 2, 1)

        cycle_labels = {
            "left_knee": "left knee",
            "right_knee": "right knee",
            "left_hip": "left hip",
            "right_hip": "right hip",
        }
        self.cycle_plot = pg.PlotWidget(title="Gait cycle (heel-strike normalized)")
        self.cycle_plot.addLegend()
        self.cycle_plot.setLabel("bottom", "gait cycle", units="%")
        self.cycle_plot.setLabel("left", "angle", units="deg")
        self.cycle_plot.setXRange(0, 100)
        style_plot(self.cycle_plot)
        for name, label in cycle_labels.items():
            self.cycle_curves[name] = self.cycle_plot.plot(
                pen=pg.mkPen(JOINT_COLORS[name], width=2), name=label
            )
        grid.addWidget(self._card(self.cycle_plot), 2, 0, 1, 2)
        self.tabs.addTab(dashboard, "Dashboard")

    @staticmethod
    def _field_label(text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    def _card(self, inner: QtWidgets.QWidget) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setObjectName("card")
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.addWidget(inner)
        return card

    def _build_side_panel(self) -> QtWidgets.QFrame:
        panel = QtWidgets.QFrame()
        panel.setObjectName("card")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        caption = QtWidgets.QLabel("SYMMETRY INDEX")
        caption.setObjectName("metricCaption")
        caption.setAlignment(QtCore.Qt.AlignCenter)
        self.si_label = QtWidgets.QLabel("--")
        self.si_label.setAlignment(QtCore.Qt.AlignCenter)
        self._style_si_zone("unknown", "--")
        layout.addWidget(caption)
        layout.addWidget(self.si_label)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet(f"color: {PALETTE.border};")
        layout.addWidget(line)

        self.side_label = self._metric_tile(layout, "AFFECTED SIDE", "unknown")
        self.cadence_label = self._metric_tile(layout, "CADENCE", "-- spm")
        self.stance_label = self._metric_tile(layout, "STANCE  L / R", "-- / -- s")
        self.rom_label = self._metric_tile(layout, "KNEE ROM  L / R", "-- / -- deg")
        self.health_label = self._metric_tile(layout, "SENSOR HEALTH", "waiting")
        self.health_label.setWordWrap(True)
        self.c3_temp_label = self._metric_tile(layout, "C3 TEMP", "-- C")
        self.c3_link_label = self._metric_tile(layout, "C3 LINK", "waiting")
        layout.addStretch(1)
        return panel

    def _metric_tile(
        self, layout: QtWidgets.QVBoxLayout, caption: str, value: str
    ) -> QtWidgets.QLabel:
        cap = QtWidgets.QLabel(caption)
        cap.setObjectName("metricCaption")
        val = QtWidgets.QLabel(value)
        val.setObjectName("metricValue")
        layout.addWidget(cap)
        layout.addWidget(val)
        return val

    def _style_si_zone(self, zone: str, text: str) -> None:
        color = ZONE_COLORS.get(zone, ZONE_COLORS["unknown"])
        self.si_label.setText(text)
        self.si_label.setStyleSheet(
            "font-size: 34px; font-weight: 800; padding: 14px; "
            f"border-radius: 10px; background: {color}; color: white;"
        )

    def _build_raw_debug_tab(self) -> None:
        self.raw_tabs = QtWidgets.QTabWidget()
        for name in SENSOR_NAMES:
            plot = pg.PlotWidget(title=name)
            plot.addLegend()
            plot.setLabel("bottom", "time", units="s")
            plot.setLabel("left", "norm")
            style_plot(plot)
            acc_curve = plot.plot(pen=pg.mkPen(PALETTE.right, width=2), name="acc |g|")
            gyro_curve = plot.plot(
                pen=pg.mkPen(PALETTE.left_accent, width=2), name="gyro |dps|"
            )
            mag_curve = plot.plot(
                pen=pg.mkPen(PALETTE.zone_green, width=2), name="mag raw"
            )
            self.curves[name] = {"acc": acc_curve, "gyro": gyro_curve, "mag": mag_curve}
            self.raw_tabs.addTab(self._card(plot), name)
        self.tabs.addTab(self.raw_tabs, "Raw debug")

    def refresh_ports(self) -> None:
        current = self.port_combo.currentText()
        self.port_combo.clear()
        ports = [p.device for p in list_ports.comports()]
        self.port_combo.addItems(ports)
        if current in ports:
            self.port_combo.setCurrentText(current)

    def start_capture(self) -> None:
        port = self.port_combo.currentText()
        if not port:
            self.status_label.setText("select a serial port first")
            return
        self.worker = CaptureWorker(
            port=port,
            baud=921600,
            output_dir=self.output_edit.text(),
            calibration_path=self.calibration_edit.text() or None,
        )
        self.calibration = load_gyro_bias(self.calibration_edit.text() or None)
        self.pipeline = RealtimePipeline(self.calibration)
        self._clear_realtime_buffers()
        self.worker.frame_received.connect(self.on_frame)
        self.worker.node_frame_received.connect(self.on_node_frame)
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.finished_session.connect(
            lambda path: self.status_label.setText(f"saved {path}")
        )
        self.worker.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_capture(self) -> None:
        if self.worker:
            self.worker.stop()
            self.worker.wait(3000)
            self.worker = None
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def on_frame(self, frame: SampleFrame) -> None:
        self.last_frame = frame
        t = frame.ts_us / 1_000_000.0
        for name, imu in zip(BMI_SENSOR_NAMES, frame.bmi):
            self._append_scaled(name, t, scale_sensor(name, imu, self.calibration))
        self._append_scaled(
            "pelvis", t, scale_sensor("pelvis", frame.pelvis, self.calibration)
        )
        self._append_derived(self.pipeline.update(frame))

    def on_node_frame(self, frame: NodeDebugFrame) -> None:
        self.last_node_debug = frame
        temp_c = frame.temp_c
        self.c3_temp_label.setText("-- C" if temp_c is None else f"{temp_c:.1f} C")
        self.c3_link_label.setText(
            f"node {frame.node_id} | age {frame.age_ms} ms | seq {frame.c3_seq}"
        )

    def _append_scaled(self, name: str, t: float, values: dict) -> None:
        acc = math.sqrt(values["ax_g"] ** 2 + values["ay_g"] ** 2 + values["az_g"] ** 2)
        gyro = math.sqrt(
            values["gx_dps"] ** 2 + values["gy_dps"] ** 2 + values["gz_dps"] ** 2
        )
        mag = math.sqrt(
            values.get("mx_raw", 0.0) ** 2
            + values.get("my_raw", 0.0) ** 2
            + values.get("mz_raw", 0.0) ** 2
        )
        buf = self.buffers[name]
        buf["t"].append(t)
        buf["acc"].append(acc)
        buf["gyro"].append(gyro)
        buf["mag"].append(mag)

    def _append_derived(self, sample: DerivedSample) -> None:
        joints = sample.joints.as_dict()
        for name, value in joints.items():
            buf = self.joint_buffers[name]
            buf["t"].append(sample.time_s)
            buf["value"].append(value)
        for event in sample.events:
            self.event_history.append(event)
        self._refresh_metric_labels(sample)

    def _refresh_metric_labels(self, sample: DerivedSample) -> None:
        metrics = sample.metrics
        clinical = sample.clinical
        self._style_si_zone(
            clinical.symmetry_zone, f"{clinical.symmetry_index_pct:.1f}%"
        )
        self.side_label.setText(clinical.affected_side)
        self.cadence_label.setText(f"{metrics.cadence_spm:.1f} spm")
        self.stance_label.setText(
            f"{self._fmt(metrics.left_stance_s)} / {self._fmt(metrics.right_stance_s)} s"
        )
        self.rom_label.setText(
            f"{self._fmt(metrics.left_knee_rom_deg)} / "
            f"{self._fmt(metrics.right_knee_rom_deg)} deg"
        )
        status_names = sample.health.get("status_names") or []
        health = ", ".join(status_names) if status_names else "all sensors reporting"
        self.health_label.setText(health)

    @staticmethod
    def _fmt(value: float | None) -> str:
        return "--" if value is None else f"{value:.2f}"

    def _clear_realtime_buffers(self) -> None:
        for sensor_buffer in self.buffers.values():
            for values in sensor_buffer.values():
                values.clear()
        for joint_buffer in self.joint_buffers.values():
            for values in joint_buffer.values():
                values.clear()
        self.event_history.clear()
        self.last_node_debug = None
        if hasattr(self, "c3_temp_label"):
            self.c3_temp_label.setText("-- C")
            self.c3_link_label.setText("waiting")

    def _refresh_plots(self) -> None:
        self._refresh_dashboard()
        for name, curves in self.curves.items():
            t = list(self.buffers[name]["t"])
            if not t:
                continue
            t0 = t[0]
            x = [v - t0 for v in t]
            curves["acc"].setData(x, list(self.buffers[name]["acc"]))
            curves["gyro"].setData(x, list(self.buffers[name]["gyro"]))
            curves["mag"].setData(x, list(self.buffers[name]["mag"]))

    def _refresh_dashboard(self) -> None:
        for name, curve in self.joint_curves.items():
            t = list(self.joint_buffers[name]["t"])
            if not t:
                continue
            t0 = max(0.0, t[-1] - 8.0)
            x = [v - t0 for v in t if v >= t0]
            y = [
                value
                for time_s, value in zip(
                    self.joint_buffers[name]["t"], self.joint_buffers[name]["value"]
                )
                if time_s >= t0
            ]
            curve.setData(x, y)

        if self.event_history:
            now = self.event_history[-1].time_s
            t0 = max(0.0, now - 8.0)
            grouped = {key: ([], []) for key in self.event_curves}
            for event in self.event_history:
                if event.time_s < t0:
                    continue
                key = f"{event.side}_{event.kind}"
                if key in grouped:
                    grouped[key][0].append(event.time_s - t0)
                    grouped[key][1].append(1 if event.side == "left" else 0)
            for key, curve in self.event_curves.items():
                curve.setData(*grouped[key])

        for name, curve in self.cycle_curves.items():
            self._refresh_cycle_curve(name, curve)

    def _refresh_cycle_curve(self, name: str, curve: pg.PlotDataItem) -> None:
        side = "left" if name.startswith("left") else "right"
        strikes = [
            event.time_s
            for event in self.event_history
            if event.side == side and event.kind == "heel_strike"
        ]
        if len(strikes) < 2:
            curve.setData([], [])
            return
        start, end = strikes[-2], strikes[-1]
        span = end - start
        if span <= 0.0:
            curve.setData([], [])
            return
        x: list[float] = []
        y: list[float] = []
        for time_s, value in zip(
            self.joint_buffers[name]["t"], self.joint_buffers[name]["value"]
        ):
            if start <= time_s <= end:
                x.append((time_s - start) / span * 100.0)
                y.append(value)
        curve.setData(x, y)


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    apply_pyqtgraph_theme()
    app.setStyleSheet(qss())
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
