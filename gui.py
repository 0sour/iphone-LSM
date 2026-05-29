#!/usr/bin/env python3
"""
iPhone 虚拟定位 - 图形化界面 (Win11 Fluent Design)
GUI wrapper for iphone_location_sim.py
"""

import asyncio
import os
import subprocess
import sys
import threading
from functools import partial

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

# Fix Windows GBK encoding for device names with emoji
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# async helpers
# ---------------------------------------------------------------------------


class AsyncLoop:
    """Persistent asyncio event loop running in a background thread."""

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=30)

    def stop(self):
        self._loop.call_soon_threadsafe(self._loop.stop)


_async = AsyncLoop()

# ---------------------------------------------------------------------------
# tunneld management
# ---------------------------------------------------------------------------

TUNNELD_ADDRESS = ("127.0.0.1", 49151)
_tunneld_process = None


def _is_tunneld_running():
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect(TUNNELD_ADDRESS)
        s.close()
        return True
    except Exception:
        return False


def _start_tunneld():
    global _tunneld_process
    if _is_tunneld_running():
        return
    try:
        _tunneld_process = subprocess.Popen(
            [sys.executable, "-m", "pymobiledevice3", "remote", "tunneld"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        import time

        for _ in range(10):
            time.sleep(0.5)
            if _is_tunneld_running():
                return
    except Exception:
        pass


async def _get_rsd_provider():
    from pymobiledevice3.tunneld.api import get_tunneld_devices

    devices = await get_tunneld_devices(TUNNELD_ADDRESS)
    if not devices:
        raise Exception("未发现设备。请确保 iPhone 已通过 USB 连接并解锁。")
    return devices[0]


# ---------------------------------------------------------------------------
# Win11 QSS Stylesheet
# ---------------------------------------------------------------------------

WIN11_QSS = """
/* ---- Global ---- */
QMainWindow {
    background-color: #f3f3f3;
}

QWidget {
    font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 13px;
    color: #1a1a1a;
}

/* ---- Cards ---- */
QFrame#card {
    background-color: #fcfcfc;
    border: 1px solid #e8e8e8;
    border-radius: 8px;
}

/* ---- Labels ---- */
QLabel#title {
    font-size: 15px;
    font-weight: 600;
    color: #1a1a1a;
}

QLabel#subtitle {
    font-size: 12px;
    color: #616161;
}

QLabel#device-label {
    font-size: 13px;
    color: #999999;
}

QLabel#device-label-connected {
    font-size: 13px;
    color: #107c10;
    font-weight: 600;
}

QLabel#device-label-detected {
    font-size: 13px;
    color: #0078d4;
}

QLabel#section-label {
    font-size: 12px;
    font-weight: 600;
    color: #616161;
    padding-top: 4px;
}

QLabel#eta-label {
    font-size: 12px;
    color: #616161;
}

/* ---- PushButton (default) ---- */
QPushButton {
    background-color: #fcfcfc;
    color: #1a1a1a;
    border: 1px solid #cfcfcf;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #f0f0f0;
    border-color: #b0b0b0;
}

QPushButton:pressed {
    background-color: #e0e0e0;
    border-color: #999999;
}

QPushButton:disabled {
    background-color: #f5f5f5;
    color: #b0b0b0;
    border-color: #e0e0e0;
}

/* ---- PushButton (primary / accent) ---- */
QPushButton#primary {
    background-color: #0078d4;
    color: #ffffff;
    border: none;
    padding: 8px 20px;
    font-weight: 600;
}

QPushButton#primary:hover {
    background-color: #106ebe;
}

QPushButton#primary:pressed {
    background-color: #005a9e;
}

QPushButton#primary:disabled {
    background-color: #c0c0c0;
    color: #e8e8e8;
}

/* ---- PushButton (danger) ---- */
QPushButton#danger {
    background-color: #fcfcfc;
    color: #d13438;
    border: 1px solid #d13438;
}

QPushButton#danger:hover {
    background-color: #fde7e9;
}

QPushButton#danger:pressed {
    background-color: #f9c9cb;
}

QPushButton#danger:disabled {
    color: #e0a0a2;
    border-color: #e0a0a2;
}

/* ---- PushButton (small / ghost) ---- */
QPushButton#small {
    background-color: transparent;
    border: 1px solid #cfcfcf;
    padding: 4px 10px;
    font-size: 12px;
    border-radius: 4px;
}

QPushButton#small:hover {
    background-color: #f0f0f0;
}

/* ---- LineEdit ---- */
QLineEdit {
    border: 1px solid #cfcfcf;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 13px;
    background-color: #fcfcfc;
    selection-background-color: #0078d4;
    selection-color: #ffffff;
}

QLineEdit:focus {
    border-color: #0078d4;
    background-color: #ffffff;
}

QLineEdit:disabled {
    background-color: #f5f5f5;
    color: #a0a0a0;
}

/* ---- ComboBox ---- */
QComboBox {
    border: 1px solid #cfcfcf;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 13px;
    background-color: #fcfcfc;
    min-width: 80px;
}

QComboBox:hover {
    border-color: #b0b0b0;
}

QComboBox:focus {
    border-color: #0078d4;
}

QComboBox::drop-down {
    border: none;
    width: 26px;
}

QComboBox::down-arrow {
    image: none;
    border: none;
}

QComboBox QAbstractItemView {
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    padding: 4px;
    selection-background-color: #e8f3fc;
    selection-color: #1a1a1a;
    outline: none;
}

/* ---- CheckBox ---- */
QCheckBox {
    font-size: 13px;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1.5px solid #8a8a8a;
    border-radius: 4px;
    background-color: #fcfcfc;
}

QCheckBox::indicator:hover {
    border-color: #0078d4;
}

QCheckBox::indicator:checked {
    background-color: #0078d4;
    border-color: #0078d4;
}

QCheckBox::indicator:checked:hover {
    background-color: #106ebe;
    border-color: #106ebe;
}

QCheckBox:disabled {
    color: #a0a0a0;
}

QCheckBox::indicator:disabled {
    border-color: #d0d0d0;
    background-color: #f0f0f0;
}

/* ---- TabWidget ---- */
QTabWidget::pane {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background-color: #fcfcfc;
    top: -1px;
}

QTabBar::tab {
    background-color: transparent;
    color: #616161;
    border: none;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 500;
    border-bottom: 2px solid transparent;
    margin-right: 2px;
}

QTabBar::tab:selected {
    color: #0078d4;
    border-bottom: 2px solid #0078d4;
}

QTabBar::tab:hover:!selected {
    color: #1a1a1a;
    border-bottom: 2px solid #e0e0e0;
}

/* ---- ProgressBar ---- */
QProgressBar {
    border: none;
    border-radius: 3px;
    background-color: #e8e8e8;
    height: 6px;
    text-align: center;
    font-size: 0px;
}

QProgressBar::chunk {
    background-color: #0078d4;
    border-radius: 3px;
}

/* ---- Separator ---- */
QFrame#separator {
    background-color: #e0e0e0;
    max-height: 1px;
    border: none;
}

/* ---- StatusBar ---- */
QStatusBar {
    background-color: transparent;
    color: #616161;
    font-size: 12px;
    border: none;
}
"""

# ---------------------------------------------------------------------------
# Leaflet map HTML (loaded in QWebEngineView)
# ---------------------------------------------------------------------------

MAP_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  *{margin:0;padding:0}
  html,body,#map{width:100%;height:100%}
</style>
</head>
<body>
<div id="map"></div>
<script>
var map = L.map('map', {attributionControl: false}).setView([39.9042, 116.4074], 14);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19}).addTo(map);
var marker = null;
var pathLine = null;
function setMarker(lat, lng) {
    if (marker) { marker.setLatLng([lat, lng]); }
    else { marker = L.marker([lat, lng]).addTo(map); }
    map.panTo([lat, lng]);
}
function clearMarker() {
    if (marker) { map.removeLayer(marker); marker = null; }
}
function drawPath(latLngs) {
    clearPath();
    pathLine = L.polyline(latLngs, {color: '#0078d4', weight: 3, opacity: 0.8}).addTo(map);
    if (latLngs.length > 0) { map.fitBounds(pathLine.getBounds().pad(0.1)); }
}
function clearPath() {
    if (pathLine) { map.removeLayer(pathLine); pathLine = null; }
}
</script>
</body>
</html>"""

# ---------------------------------------------------------------------------
# Track worker – runs the trajectory loop in a background thread
# ---------------------------------------------------------------------------


class TrackSignals(QThread):
    """Signals bridge for track progress updates from bg thread → Qt main thread."""
    progress = Signal(int, float, float)
    finished = Signal(str)
    error = Signal(str)


class TrackWorker:
    """Runs the track loop on a daemon thread (not QThread, to keep our async pattern)."""

    def __init__(self, app):
        self._app = app
        self._stop = threading.Event()

    def run(self, path, interval, loop, keep):
        import time as _time

        app = self._app
        loc = app._conn[1]
        current_path = list(path)

        try:
            while not self._stop.is_set():
                for i, pt in enumerate(current_path):
                    if self._stop.is_set():
                        break
                    _async.run(loc.set(pt.lat, pt.lng))
                    app._sig.progress.emit(i, pt.lat, pt.lng)
                    _time.sleep(interval)
                if not loop:
                    break
                current_path = list(reversed(current_path))
        except Exception as e:
            app._sig.error.emit(str(e))
        finally:
            app._tracking = False
            if keep:
                app._sig.finished.emit("轨迹完成，位置保持在终点")
            else:
                try:
                    _async.run(loc.clear())
                except Exception:
                    pass
                app._sig.finished.emit("轨迹完成，已恢复真实 GPS")


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self._conn = None
        self._tracking = False
        self._track_thread = None
        self._track_worker = None
        self._map_ready = False
        self._track_keep = False
        self._last_lat = None
        self._last_lng = None
        self._last_track_waypoints = []
        self._sig = TrackSignals(self)

        self._setup_ui()
        self._apply_style()

        # Wire track signals
        self._sig.progress.connect(self._on_track_progress)
        self._sig.finished.connect(self._on_track_finished)
        self._sig.error.connect(self._on_track_error)

        # Start tunneld & refresh
        self._ensure_tunneld()
        self._refresh_device_list()

    # ------------------------------------------------------------------
    # Style
    # ------------------------------------------------------------------

    def _apply_style(self):
        self.setStyleSheet(WIN11_QSS)

    # ------------------------------------------------------------------
    # Map panel
    # ------------------------------------------------------------------

    def _build_map_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 20, 0)
        layout.setSpacing(6)

        self._map_view = QWebEngineView()
        self._map_view.setHtml(MAP_HTML, QUrl("https://unpkg.com"))
        self._map_view.loadFinished.connect(self._on_map_loaded)
        layout.addWidget(self._map_view, 1)

        self._map_coord_label = QLabel("")
        self._map_coord_label.setObjectName("eta-label")
        self._map_coord_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._map_coord_label)

        return panel

    def _on_map_loaded(self, ok):
        if ok:
            self._map_ready = True

    def _update_map_marker(self, lat, lng):
        self._last_lat = lat
        self._last_lng = lng
        if not HAS_WEBENGINE or not self._map_ready:
            return
        self._map_view.page().runJavaScript(f"setMarker({lat}, {lng})")
        self._map_coord_label.setText(f"{lat:.6f}, {lng:.6f}")

    def _clear_map_marker(self):
        if not HAS_WEBENGINE or not self._map_ready:
            return
        self._map_view.page().runJavaScript("clearMarker()")
        self._map_view.page().runJavaScript("clearPath()")
        self._map_coord_label.setText("")

    def _draw_map_path(self, waypoints):
        """Draw waypoints as a polyline on the map."""
        if not HAS_WEBENGINE or not self._map_ready:
            return
        import json

        coords = [[wp.lat, wp.lng] for wp in waypoints]
        self._map_view.page().runJavaScript(f"drawPath({json.dumps(coords)})")

    def _clear_map_path(self):
        if not HAS_WEBENGINE or not self._map_ready:
            return
        self._map_view.page().runJavaScript("clearPath()")

    def _on_tab_changed(self, index):
        """Switch map view: tab 0 = marker only, tab 1 = track path + marker."""
        if not HAS_WEBENGINE or not self._map_ready:
            return
        if index == 0:
            # Static-location tab: show current position, hide path
            self._map_view.page().runJavaScript("clearPath()")
            if self._last_lat is not None:
                self._update_map_marker(self._last_lat, self._last_lng)
        elif index == 1:
            # Track tab: show GPX path + current position
            if self._last_track_waypoints:
                self._draw_map_path(self._last_track_waypoints)
            if self._last_lat is not None:
                self._update_map_marker(self._last_lat, self._last_lng)

    def _preview_gpx(self, path):
        """Set GPX path and preview its track on the map."""
        self._gpx_input.setText(path)
        if not HAS_WEBENGINE or not self._map_ready:
            return
        try:
            from iphone_location_sim import parse_gpx

            waypoints = parse_gpx(path)
            if waypoints:
                self._last_track_waypoints = waypoints
                self._draw_map_path(waypoints)
                self._update_map_marker(waypoints[0].lat, waypoints[0].lng)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        self.setWindowTitle("iPhone 虚拟定位")
        self.resize(1100, 680)
        self.setMinimumSize(900, 560)

        # App icon
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        # ---- Left panel: controls ----
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(20, 16, 12, 12)
        left_layout.setSpacing(0)

        self._build_device_bar(left_layout)

        sep = QFrame(objectName="separator")
        left_layout.addWidget(sep)
        left_layout.addSpacing(12)

        self._tabs = QTabWidget()
        left_layout.addWidget(self._tabs, 1)

        self._build_tab_static()
        self._build_tab_track()
        self._build_tab_generator()
        self._build_tab_about()

        self._tabs.currentChanged.connect(self._on_tab_changed)

        splitter.addWidget(left)

        # ---- Right panel: map ----
        if HAS_WEBENGINE:
            right = self._build_map_panel()
            splitter.addWidget(right)
            splitter.setSizes([580, 500])
        else:
            splitter.setSizes([680, 0])

        # ---- Status bar ----
        self._status_bar = QStatusBar()
        self._status_bar.showMessage("正在启动 tunneld ...")
        self.setStatusBar(self._status_bar)

    # ------------------------------------------------------------------
    # Device bar
    # ------------------------------------------------------------------

    def _build_device_bar(self, parent):
        bar = QHBoxLayout()
        bar.setSpacing(8)
        bar.setContentsMargins(0, 0, 0, 8)

        lbl = QLabel("设备")
        lbl.setFont(QFont(lbl.font().family(), -1, QFont.Bold))
        bar.addWidget(lbl)

        self._device_label = QLabel("检测中...")
        self._device_label.setObjectName("device-label")
        bar.addWidget(self._device_label)

        bar.addStretch()

        self._connect_btn = QPushButton("连接")
        self._connect_btn.setObjectName("primary")
        self._connect_btn.setFixedWidth(72)
        self._connect_btn.clicked.connect(self._connect)
        bar.addWidget(self._connect_btn)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setFixedWidth(72)
        refresh_btn.clicked.connect(self._refresh_device_list)
        bar.addWidget(refresh_btn)

        self._info_btn = QPushButton("设备信息")
        self._info_btn.clicked.connect(self._show_info)
        self._info_btn.setEnabled(False)
        bar.addWidget(self._info_btn)

        parent.addLayout(bar)

    # ------------------------------------------------------------------
    # Tab 1 — Static location
    # ------------------------------------------------------------------

    def _build_tab_static(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # --- Coordinate inputs ---
        card = QFrame(objectName="card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(10)

        header = QLabel("目标坐标")
        header.setObjectName("title")
        card_layout.addWidget(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        grid.addWidget(QLabel("纬度 (lat):"), 0, 0, Qt.AlignRight)
        self._lat_input = QLineEdit("39.9042")
        self._lat_input.setMinimumWidth(200)
        grid.addWidget(self._lat_input, 0, 1)

        grid.addWidget(QLabel("经度 (lng):"), 1, 0, Qt.AlignRight)
        self._lng_input = QLineEdit("116.4074")
        grid.addWidget(self._lng_input, 1, 1)

        card_layout.addLayout(grid)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._set_btn = QPushButton("设置位置")
        self._set_btn.setObjectName("primary")
        self._set_btn.clicked.connect(self._set_location)
        self._set_btn.setEnabled(False)
        btn_row.addWidget(self._set_btn)

        self._stop_btn = QPushButton("恢复真实 GPS")
        self._stop_btn.setObjectName("danger")
        self._stop_btn.clicked.connect(self._stop_location)
        self._stop_btn.setEnabled(False)
        btn_row.addWidget(self._stop_btn)

        btn_row.addStretch()
        card_layout.addLayout(btn_row)

        layout.addWidget(card)

        # --- Presets ---
        layout.addSpacing(4)
        presets_label = QLabel("常用坐标")
        presets_label.setObjectName("section-label")
        layout.addWidget(presets_label)

        presets_grid = QGridLayout()
        presets_grid.setSpacing(6)

        presets = [
            ("北京天安门", "39.9042, 116.4074"),
            ("上海外滩", "31.2304, 121.4737"),
            ("广州塔", "23.1065, 113.3245"),
            ("深圳华强北", "22.5431, 114.0824"),
            ("成都春熙路", "30.6598, 104.0805"),
            ("纽约时代广场", "40.7580, -73.9855"),
        ]

        for i, (name, coord) in enumerate(presets):
            btn = QPushButton(name)
            btn.setObjectName("small")
            btn.clicked.connect(partial(self._set_preset, coord))
            presets_grid.addWidget(btn, i // 3, i % 3)

        layout.addLayout(presets_grid)
        layout.addStretch()
        self._tabs.addTab(tab, "静态定位")

    # ------------------------------------------------------------------
    # Tab 2 — Track simulation
    # ------------------------------------------------------------------

    def _build_tab_track(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # --- GPX input ---
        card1 = QFrame(objectName="card")
        card1_layout = QVBoxLayout(card1)
        card1_layout.setContentsMargins(20, 16, 20, 16)
        card1_layout.setSpacing(10)

        header = QLabel("轨迹输入")
        header.setObjectName("title")
        card1_layout.addWidget(header)

        gpx_row = QHBoxLayout()
        gpx_row.setSpacing(8)
        gpx_row.addWidget(QLabel("GPX 文件:"))
        self._gpx_input = QLineEdit()
        self._gpx_input.setPlaceholderText("选择 GPX 文件...")
        gpx_row.addWidget(self._gpx_input, 1)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._pick_gpx)
        gpx_row.addWidget(browse_btn)
        card1_layout.addLayout(gpx_row)

        card1_layout.addWidget(QLabel("或直接输入坐标串 (lat,lng|lat,lng):"))
        self._points_input = QLineEdit()
        self._points_input.setPlaceholderText("39.90,116.40|39.91,116.41")
        card1_layout.addWidget(self._points_input)

        layout.addWidget(card1)

        # --- Options ---
        card2 = QFrame(objectName="card")
        card2_layout = QVBoxLayout(card2)
        card2_layout.setContentsMargins(20, 16, 20, 16)
        card2_layout.setSpacing(10)

        header2 = QLabel("模拟参数")
        header2.setObjectName("title")
        card2_layout.addWidget(header2)

        opts = QGridLayout()
        opts.setHorizontalSpacing(16)
        opts.setVerticalSpacing(10)

        opts.addWidget(QLabel("模式:"), 0, 0, Qt.AlignRight)
        self._mode_cb = QComboBox()
        self._mode_cb.addItems(["walking", "cycling", "driving", "running"])
        self._mode_cb.setCurrentText("walking")
        self._mode_cb.setFixedWidth(110)
        opts.addWidget(self._mode_cb, 0, 1)

        opts.addWidget(QLabel("速度 (m/s):"), 0, 2, Qt.AlignRight)
        self._speed_input = QLineEdit()
        self._speed_input.setPlaceholderText("留空 = 预设")
        self._speed_input.setFixedWidth(90)
        opts.addWidget(self._speed_input, 0, 3)

        opts.addWidget(QLabel("间隔 (秒):"), 1, 0, Qt.AlignRight)
        self._interval_input = QLineEdit("1.0")
        self._interval_input.setFixedWidth(90)
        opts.addWidget(self._interval_input, 1, 1)

        self._loop_cb = QCheckBox("循环")
        opts.addWidget(self._loop_cb, 1, 2)

        self._keep_cb = QCheckBox("完成后保持位置")
        opts.addWidget(self._keep_cb, 1, 3)

        card2_layout.addLayout(opts)
        layout.addWidget(card2)

        # --- Preset GPX buttons ---
        presets_row = QHBoxLayout()
        presets_row.setSpacing(8)
        presets_row.addWidget(QLabel("预设轨迹:"))
        examples_dir = os.path.join(os.path.dirname(__file__), "examples")
        preset_gpx = [
            ("天安门", "beijing_tiananmen.gpx"),
            ("外滩", "shanghai_bund.gpx"),
            ("圆形循环", "circle_loop.gpx"),
        ]
        for name, fname in preset_gpx:
            full = os.path.join(examples_dir, fname)
            btn = QPushButton(name)
            btn.setObjectName("small")
            btn.clicked.connect(partial(self._preview_gpx, full))
            presets_row.addWidget(btn)
        presets_row.addStretch()
        layout.addLayout(presets_row)

        # --- Progress ---
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(6)
        layout.addWidget(self._progress_bar)

        self._eta_label = QLabel("")
        self._eta_label.setObjectName("eta-label")
        layout.addWidget(self._eta_label)

        # --- Control buttons ---
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        self._track_btn = QPushButton("开始轨迹")
        self._track_btn.setObjectName("primary")
        self._track_btn.clicked.connect(self._start_track)
        self._track_btn.setEnabled(False)
        ctrl_row.addWidget(self._track_btn)

        self._abort_btn = QPushButton("停止轨迹")
        self._abort_btn.setObjectName("danger")
        self._abort_btn.clicked.connect(self._stop_track)
        self._abort_btn.setEnabled(False)
        ctrl_row.addWidget(self._abort_btn)

        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        layout.addStretch()
        self._tabs.addTab(tab, "轨迹模拟")

    # ------------------------------------------------------------------
    # Tab 3 — GPX Generator
    # ------------------------------------------------------------------

    def _build_tab_generator(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        card = QFrame(objectName="card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(10)

        header = QLabel("GPX 生成器")
        header.setObjectName("title")
        card_layout.addWidget(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        grid.addWidget(QLabel("起点 (lat,lng):"), 0, 0, Qt.AlignRight)
        self._gen_from_input = QLineEdit("39.9042, 116.4074")
        self._gen_from_input.setMinimumWidth(220)
        grid.addWidget(self._gen_from_input, 0, 1)

        grid.addWidget(QLabel("终点 (lat,lng):"), 1, 0, Qt.AlignRight)
        self._gen_to_input = QLineEdit("39.9142, 116.4174")
        grid.addWidget(self._gen_to_input, 1, 1)

        grid.addWidget(QLabel("航点数:"), 2, 0, Qt.AlignRight)
        self._gen_num_input = QLineEdit("20")
        self._gen_num_input.setFixedWidth(80)
        grid.addWidget(self._gen_num_input, 2, 1, Qt.AlignLeft)

        card_layout.addLayout(grid)

        gen_btn = QPushButton("生成并保存 GPX...")
        gen_btn.setObjectName("primary")
        gen_btn.clicked.connect(self._generate_gpx)
        gen_btn.setFixedWidth(180)
        card_layout.addWidget(gen_btn, 0, Qt.AlignLeft)

        layout.addWidget(card)
        layout.addStretch()
        self._tabs.addTab(tab, "生成 GPX")

    # ------------------------------------------------------------------
    # Tab 4 — About
    # ------------------------------------------------------------------

    def _build_tab_about(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        card = QFrame(objectName="card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 28, 32, 28)
        card_layout.setSpacing(10)
        card_layout.setAlignment(Qt.AlignCenter)

        # App icon
        self._app_icon_label = QLabel()
        self._app_icon_label.setFixedSize(80, 80)
        self._app_icon_label.setAlignment(Qt.AlignCenter)
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(
                80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            from PySide6.QtGui import QBitmap

            mask = QBitmap(pixmap.size())
            mask.clear()
            p = QPainter(mask)
            p.setBrush(Qt.color1)
            p.setPen(Qt.NoPen)
            p.setRenderHint(QPainter.Antialiasing)
            p.drawEllipse(pixmap.rect())
            p.end()
            pixmap.setMask(mask)
            self._app_icon_label.setPixmap(pixmap)
        card_layout.addWidget(self._app_icon_label, 0, Qt.AlignCenter)

        # App name
        title = QLabel("iPhone 虚拟定位模拟器")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        # Description
        desc = QLabel(
            "通过 USB 连接 iPhone，使用 Apple DVT 协议修改手机 GPS 坐标\n"
            "GUI: PySide6 + Win11 Fluent Design + Leaflet 地图"
        )
        desc.setObjectName("subtitle")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

        # Features
        sep = QFrame(objectName="separator")
        sep.setFixedWidth(360)
        card_layout.addWidget(sep, 0, Qt.AlignCenter)

        features = QLabel(
            "静态定位  ·  轨迹模拟  ·  GPX 生成\n"
            "实时地图  ·  轨迹预览  ·  循环折返\n"
            "坐标串输入  ·  预设位置  ·  设备信息"
        )
        features.setObjectName("subtitle")
        features.setAlignment(Qt.AlignCenter)
        features.setWordWrap(True)
        card_layout.addWidget(features)

        # ---- GitHub section ----
        sep2 = QFrame(objectName="separator")
        sep2.setFixedWidth(200)
        card_layout.addWidget(sep2, 0, Qt.AlignCenter)

        gh_row = QHBoxLayout()
        gh_row.setSpacing(10)
        gh_row.setContentsMargins(0, 0, 0, 0)

        self._avatar_label = QLabel()
        self._avatar_label.setFixedSize(36, 36)
        self._avatar_label.setAlignment(Qt.AlignCenter)
        gh_row.addWidget(self._avatar_label)

        gh_text = QVBoxLayout()
        gh_text.setSpacing(2)
        gh_name = QLabel("sour")
        gh_name.setStyleSheet("font-weight: 600; font-size: 13px; color: #1a1a1a; border: none;")
        gh_text.addWidget(gh_name)
        gh_link = QLabel(
            '<a href="https://github.com/0sour/iphone-LSM" '
            'style="color:#0078d4; text-decoration:none; font-size:12px;">'
            'github.com/0sour/iphone-LSM</a>'
        )
        gh_link.setOpenExternalLinks(True)
        gh_text.addWidget(gh_link)

        gh_row.addLayout(gh_text)
        gh_row.addStretch()

        gh_wrapper = QWidget()
        gh_wrapper.setLayout(gh_row)
        gh_wrapper.setFixedWidth(280)
        card_layout.addWidget(gh_wrapper, 0, Qt.AlignCenter)

        layout.addWidget(card)
        layout.addStretch()
        self._tabs.addTab(tab, "关于")

        # Load avatar from GitHub
        self._load_avatar()

    def _load_avatar(self):
        import urllib.request

        def _fetch():
            try:
                data = urllib.request.urlopen(
                    "https://github.com/0sour.png", timeout=8
                ).read()
                pixmap = QPixmap()
                pixmap.loadFromData(data)
                pixmap = pixmap.scaled(
                    36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                # Circular mask
                from PySide6.QtGui import QBitmap

                mask = QBitmap(pixmap.size())
                mask.clear()
                p = QPainter(mask)
                p.setBrush(Qt.color1)
                p.setPen(Qt.NoPen)
                p.setRenderHint(QPainter.Antialiasing)
                p.drawEllipse(pixmap.rect())
                p.end()
                pixmap.setMask(mask)
                self._avatar_label.setPixmap(pixmap)
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()

    # ------------------------------------------------------------------
    # Tunneld
    # ------------------------------------------------------------------

    def _ensure_tunneld(self):
        self._set_status("正在启动 tunneld ...")
        try:
            _start_tunneld()
        except Exception as e:
            self._set_status(f"tunneld 启动失败: {e}")
            return
        self._set_status("就绪")

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _connect(self):
        self._set_status("正在连接 iPhone ...")
        self._connect_btn.setEnabled(False)
        try:
            conn = _async.run(self._connect_async())
        except Exception as e:
            QMessageBox.critical(self, "连接失败", str(e))
        else:
            self._conn = conn
            provider = conn[0]
            info = provider.all_values
            name = info.get("DeviceName", "?")
            ios = info.get("ProductVersion", "?")
            self._device_label.setText(f"{name}  (iOS {ios})")
            self._device_label.setObjectName("device-label-connected")
            self._device_label.style().unpolish(self._device_label)
            self._device_label.style().polish(self._device_label)
            self._set_status(f"已连接: {name}")
            self._update_buttons()
        finally:
            self._connect_btn.setEnabled(True)

    async def _connect_async(self):
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

        provider = await _get_rsd_provider()
        await provider.connect()
        dvt = DvtProvider(provider)
        await dvt.connect()
        loc = LocationSimulation(dvt)
        await loc.connect()
        return (provider, loc)

    def _refresh_device_list(self):
        if not _is_tunneld_running():
            self._device_label.setText("tunneld 未运行")
            self._device_label.setObjectName("device-label")
            self._device_label.style().unpolish(self._device_label)
            self._device_label.style().polish(self._device_label)
            return
        try:
            from pymobiledevice3.tunneld.api import get_tunneld_devices

            devices = _async.run(get_tunneld_devices(TUNNELD_ADDRESS))
        except Exception:
            devices = []
        if devices:
            self._device_label.setText("检测到设备，点击连接")
            self._device_label.setObjectName("device-label-detected")
        else:
            self._device_label.setText("未检测到设备")
            self._device_label.setObjectName("device-label")
        self._device_label.style().unpolish(self._device_label)
        self._device_label.style().polish(self._device_label)

    # ------------------------------------------------------------------
    # Actions — static location
    # ------------------------------------------------------------------

    def _set_location(self):
        if not self._conn:
            QMessageBox.warning(self, "未连接", "请先连接 iPhone")
            return
        try:
            lat = float(self._lat_input.text().strip())
            lng = float(self._lng_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "输入错误", "经纬度必须是数字")
            return
        try:
            _async.run(self._conn[1].set(lat, lng))
            self._set_status(f"已设置虚拟位置: {lat:.6f}, {lng:.6f}")
            self._update_map_marker(lat, lng)
        except Exception as e:
            QMessageBox.critical(self, "设置失败", str(e))

    def _stop_location(self):
        if not self._conn:
            return
        try:
            _async.run(self._conn[1].clear())
            self._set_status("已恢复真实 GPS")
            self._clear_map_marker()
        except Exception as e:
            QMessageBox.critical(self, "停止失败", str(e))

    def _set_preset(self, coord_str):
        lat_s, lng_s = coord_str.split(",")
        self._lat_input.setText(lat_s.strip())
        self._lng_input.setText(lng_s.strip())
        self._set_location()

    # ------------------------------------------------------------------
    # Actions — track
    # ------------------------------------------------------------------

    def _start_track(self):
        if not self._conn:
            QMessageBox.warning(self, "未连接", "请先连接 iPhone")
            return
        if self._tracking:
            return

        gpx_path = self._gpx_input.text().strip()
        points_str = self._points_input.text().strip()

        waypoints = []
        if gpx_path:
            from iphone_location_sim import parse_gpx

            waypoints = parse_gpx(gpx_path)
            if not waypoints:
                QMessageBox.critical(self, "GPX 错误", "GPX 文件中未找到航点")
                return
        elif points_str:
            from iphone_location_sim import Coordinate

            for p in points_str.split("|"):
                lat_s, lng_s = p.strip().split(",")
                waypoints.append(Coordinate(lat=float(lat_s.strip()), lng=float(lng_s.strip())))
        else:
            QMessageBox.warning(self, "缺少输入", "请选择 GPX 文件或输入坐标串")
            return

        if len(waypoints) < 2:
            QMessageBox.critical(self, "航点不足", "轨迹模式至少需要 2 个航点")
            return

        mode = self._mode_cb.currentText()
        speed_str = self._speed_input.text().strip()
        speed = float(speed_str) if speed_str else None
        interval = float(self._interval_input.text().strip() or "1.0")
        loop = self._loop_cb.isChecked()
        keep = self._keep_cb.isChecked()

        from iphone_location_sim import (
            SPEED_PRESETS,
            generate_path_points,
            haversine_distance,
        )

        effective_speed = speed if speed is not None else SPEED_PRESETS.get(mode, 1.4)
        path = generate_path_points(waypoints, step_distance=effective_speed * interval)

        self._last_track_waypoints = waypoints
        self._draw_map_path(waypoints)

        total_dist = sum(
            haversine_distance(path[i], path[i + 1]) for i in range(len(path) - 1)
        )
        eta = total_dist / effective_speed if effective_speed > 0 else 0

        self._progress_bar.setMaximum(len(path))
        self._progress_bar.setValue(0)
        self._eta_label.setText(f"总距离: {total_dist:.0f}m    预计: {eta:.0f}s")

        self._track_keep = keep
        self._tracking = True
        self._update_buttons()

        self._update_map_marker(path[0].lat, path[0].lng)

        self._track_worker = TrackWorker(self)
        self._track_thread = threading.Thread(
            target=self._track_worker.run,
            args=(path, interval, loop, keep),
            daemon=True,
        )
        self._track_thread.start()

    def _stop_track(self):
        if self._track_worker:
            self._track_worker._stop.set()
        if self._track_thread and self._track_thread.is_alive():
            self._track_thread.join(timeout=2)
        self._tracking = False
        self._update_buttons()

    def _on_track_progress(self, idx, lat, lng):
        self._progress_bar.setValue(idx + 1)
        pct = (idx + 1) / self._progress_bar.maximum() * 100
        self._set_status(f"轨迹模拟中... {pct:.0f}%")
        self._update_map_marker(lat, lng)

    def _on_track_finished(self, msg):
        self._set_status(msg)
        if not self._track_keep:
            self._clear_map_marker()
        self._update_buttons()

    def _on_track_error(self, msg):
        self._set_status(f"轨迹错误: {msg}")
        self._update_buttons()

    # ------------------------------------------------------------------
    # File dialogs
    # ------------------------------------------------------------------

    def _pick_gpx(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 GPX 文件", "", "GPX files (*.gpx);;All files (*.*)"
        )
        if path:
            self._preview_gpx(path)

    def _generate_gpx(self):
        from_str = self._gen_from_input.text().strip()
        to_str = self._gen_to_input.text().strip()
        try:
            from_lat, from_lng = map(float, from_str.split(","))
            to_lat, to_lng = map(float, to_str.split(","))
        except ValueError:
            QMessageBox.warning(self, "输入错误", "坐标格式: lat,lng (数字)")
            return
        try:
            num = int(self._gen_num_input.text().strip() or "20")
        except ValueError:
            num = 20

        output, _ = QFileDialog.getSaveFileName(
            self, "保存 GPX", "", "GPX files (*.gpx)"
        )
        if not output:
            return

        from iphone_location_sim import Coordinate, interpolate

        pts = [
            interpolate(
                Coordinate(from_lat, from_lng),
                Coordinate(to_lat, to_lng),
                i / (num - 1),
            )
            for i in range(num)
        ]
        content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<gpx version="1.1" creator="iphone-location-sim-gui"\n'
            '     xmlns="http://www.topografix.com/GPX/1/1">\n'
            '  <trk><name>Generated Track</name><trkseg>\n'
        )
        for pt in pts:
            content += f'      <trkpt lat="{pt.lat:.6f}" lon="{pt.lng:.6f}"></trkpt>\n'
        content += "    </trkseg></trk>\n</gpx>\n"

        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
        self._set_status(f"GPX 已保存: {output}")
        QMessageBox.information(self, "完成", f"已生成 {num} 个航点\n{output}")

    # ------------------------------------------------------------------
    # Device info
    # ------------------------------------------------------------------

    def _show_info(self):
        if not self._conn:
            QMessageBox.warning(self, "未连接", "请先连接 iPhone")
            return
        info = self._conn[0].all_values
        lines = [
            f"设备名称: {info.get('DeviceName', '?')}",
            f"型号:     {info.get('ProductType', '?')}",
            f"iOS:      {info.get('ProductVersion', '?')}",
            f"序列号:   {info.get('SerialNumber', '?')}",
            f"UDID:     {info.get('UniqueDeviceID', '?')}",
            f"WiFi MAC: {info.get('WiFiAddress', '?')}",
            f"蓝牙 MAC: {info.get('BluetoothAddress', '?')}",
        ]
        QMessageBox.information(self, "设备信息", "\n".join(lines))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, text):
        self._status_bar.showMessage(text)

    def _update_buttons(self):
        connected = self._conn is not None
        tracking = self._tracking
        self._set_btn.setEnabled(connected)
        self._stop_btn.setEnabled(connected)
        self._track_btn.setEnabled(connected and not tracking)
        self._abort_btn.setEnabled(tracking)
        self._info_btn.setEnabled(connected)

    def closeEvent(self, event):
        self._stop_track()
        super().closeEvent(event)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("iPhone 虚拟定位")

    # Base font
    font = app.font()
    font.setFamilies(["Segoe UI Variable", "Segoe UI", "Microsoft YaHei UI"])
    font.setPointSize(10)
    app.setFont(font)

    window = App()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
