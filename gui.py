#!/usr/bin/env python3
"""
iPhone 虚拟定位 - 图形化界面
GUI wrapper for iphone_location_sim.py
"""

import asyncio
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Fix Windows GBK encoding for device names with emoji
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ---- async helpers ----

class AsyncLoop:
    """Persistent asyncio event loop running in a background thread.
    Keeps DTX channels alive across GUI operations."""

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coro):
        """Submit a coroutine to the persistent loop and return its result."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=30)

    def stop(self):
        self._loop.call_soon_threadsafe(self._loop.stop)

# Global async loop shared by the entire app
_async = AsyncLoop()


# ---- tunneld management ----

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
        # Wait for it to start
        import time
        for _ in range(10):
            time.sleep(0.5)
            if _is_tunneld_running():
                return
    except Exception:
        pass


async def _get_rsd_provider():
    """Get a RemoteServiceDiscovery provider for the first connected device."""
    from pymobiledevice3.tunneld.api import get_tunneld_devices
    devices = await get_tunneld_devices(TUNNELD_ADDRESS)
    if not devices:
        raise Exception("未发现设备。请确保 iPhone 已通过 USB 连接并解锁。")
    return devices[0]


# ---- Main App ----

class App(ttk.Frame):
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self._conn = None  # (service_provider, location_service)
        self._tracking = False
        self._stop_event = threading.Event()
        self._track_thread = None

        # Build UI first, then start tunneld
        self._build_ui()
        self._ensure_tunneld()
        self._refresh_device_list()

        # Cleanup
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _ensure_tunneld(self):
        self._set_status("正在启动 tunneld ...")
        try:
            _start_tunneld()
        except Exception as e:
            self._set_status(f"tunneld 启动失败: {e}")
            return
        self._set_status("就绪")

    # ==== connection ====

    def _connect(self):
        self._set_status("正在连接 iPhone ...")
        btn = self._connect_btn
        btn["state"] = "disabled"
        try:
            conn = _async.run(self._connect_async())
        except Exception as e:
            messagebox.showerror("连接失败", str(e))
        else:
            self._conn = conn
            provider = conn[0]
            info = provider.all_values
            name = info.get("DeviceName", "?")
            ios = info.get("ProductVersion", "?")
            self._device_label["text"] = f"{name}  (iOS {ios})"
            self._device_label["foreground"] = "#2e7d32"
            self._set_status(f"已连接: {name}")
            self._update_buttons()
        finally:
            btn["state"] = "normal"

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
            self._device_label["text"] = "tunneld 未运行"
            self._device_label["foreground"] = "#999"
            return
        try:
            from pymobiledevice3.tunneld.api import get_tunneld_devices
            devices = _async.run(get_tunneld_devices(TUNNELD_ADDRESS))
        except Exception:
            devices = []
        if devices:
            names = []
            for d in devices:
                names.append(getattr(d, "udid", str(d)))
            self._device_label["text"] = "检测到设备，点击连接"
            self._device_label["foreground"] = "#1565c0"
        else:
            self._device_label["text"] = "未检测到设备"
            self._device_label["foreground"] = "#999"

    # ==== actions ====

    def _set_location(self):
        if not self._conn:
            messagebox.showwarning("未连接", "请先连接 iPhone")
            return
        try:
            lat = float(self._lat_var.get().strip())
            lng = float(self._lng_var.get().strip())
        except ValueError:
            messagebox.showwarning("输入错误", "经纬度必须是数字")
            return
        try:
            _async.run(self._conn[1].set(lat, lng))
            self._set_status(f"已设置虚拟位置: {lat:.6f}, {lng:.6f}")
        except Exception as e:
            messagebox.showerror("设置失败", str(e))

    def _stop_location(self):
        if not self._conn:
            return
        try:
            _async.run(self._conn[1].clear())
            self._set_status("已恢复真实 GPS")
        except Exception as e:
            messagebox.showerror("停止失败", str(e))

    def _start_track(self):
        if not self._conn:
            messagebox.showwarning("未连接", "请先连接 iPhone")
            return
        if self._tracking:
            return

        gpx_path = self._gpx_var.get().strip()
        points_str = self._points_var.get().strip()

        waypoints = []
        if gpx_path:
            from iphone_location_sim import parse_gpx
            waypoints = parse_gpx(gpx_path)
            if not waypoints:
                messagebox.showerror("GPX 错误", "GPX 文件中未找到航点")
                return
        elif points_str:
            from iphone_location_sim import Coordinate
            for p in points_str.split("|"):
                lat_s, lng_s = p.strip().split(",")
                waypoints.append(Coordinate(lat=float(lat_s.strip()), lng=float(lng_s.strip())))
        else:
            messagebox.showwarning("缺少输入", "请选择 GPX 文件或输入坐标串")
            return

        if len(waypoints) < 2:
            messagebox.showerror("航点不足", "轨迹模式至少需要 2 个航点")
            return

        mode = self._mode_var.get()
        speed_str = self._speed_var.get().strip()
        speed = float(speed_str) if speed_str else None
        interval = float(self._interval_var.get().strip() or "1.0")
        loop = self._loop_var.get()
        keep = self._keep_var.get()

        from iphone_location_sim import (
            SPEED_PRESETS,
            TrajectoryConfig,
            generate_path_points,
            haversine_distance,
        )

        effective_speed = speed if speed is not None else SPEED_PRESETS.get(mode, 1.4)
        config = TrajectoryConfig(mode=mode, speed_ms=effective_speed, update_interval=interval, loop=loop)
        path = generate_path_points(waypoints, step_distance=effective_speed * interval)

        total_dist = sum(haversine_distance(path[i], path[i + 1]) for i in range(len(path) - 1))
        eta = total_dist / effective_speed if effective_speed > 0 else 0

        self._progress["maximum"] = len(path)
        self._progress["value"] = 0
        self._eta_label["text"] = f"总距离: {total_dist:.0f}m  预计: {eta:.0f}s"
        self._tracking = True
        self._stop_event.clear()
        self._update_buttons()

        loc = self._conn[1]

        def _run():
            import time as _time
            current_path = list(path)
            try:
                while not self._stop_event.is_set():
                    for i, pt in enumerate(current_path):
                        if self._stop_event.is_set():
                            break
                        _async.run(loc.set(pt.lat, pt.lng))
                        self.root.after(0, lambda idx=i: self._track_progress(idx))
                        _time.sleep(interval)
                    if not loop:
                        break
                    current_path = list(reversed(current_path))
            except Exception as e:
                self.root.after(0, lambda: self._set_status(f"轨迹错误: {e}"))
            finally:
                self._tracking = False
                if keep:
                    self.root.after(0, lambda: self._set_status("轨迹完成，位置保持在终点"))
                else:
                    try:
                        _async.run(loc.clear())
                    except Exception:
                        pass
                    self.root.after(0, lambda: self._set_status("轨迹完成，已恢复真实 GPS"))
                self.root.after(0, self._update_buttons)

        self._track_thread = threading.Thread(target=_run, daemon=True)
        self._track_thread.start()

    def _track_progress(self, idx):
        self._progress["value"] = idx + 1
        pct = (idx + 1) / self._progress["maximum"] * 100
        self._set_status(f"轨迹模拟中... {pct:.0f}%")

    def _stop_track(self):
        self._stop_event.set()
        if self._track_thread and self._track_thread.is_alive():
            self._track_thread.join(timeout=2)
        self._tracking = False
        self._update_buttons()

    def _pick_gpx(self):
        path = filedialog.askopenfilename(
            title="选择 GPX 文件",
            filetypes=[("GPX files", "*.gpx"), ("All files", "*.*")],
        )
        if path:
            self._gpx_var.set(path)

    def _generate_gpx(self):
        from_str = self._gen_from_var.get().strip()
        to_str = self._gen_to_var.get().strip()
        try:
            from_lat, from_lng = map(float, from_str.split(","))
            to_lat, to_lng = map(float, to_str.split(","))
        except ValueError:
            messagebox.showwarning("输入错误", "坐标格式: lat,lng (数字)")
            return
        try:
            num = int(self._gen_num_var.get().strip() or "20")
        except ValueError:
            num = 20

        output = filedialog.asksaveasfilename(
            title="保存 GPX",
            defaultextension=".gpx",
            filetypes=[("GPX files", "*.gpx")],
        )
        if not output:
            return

        from iphone_location_sim import Coordinate, interpolate
        pts = [interpolate(Coordinate(from_lat, from_lng), Coordinate(to_lat, to_lng), i / (num - 1)) for i in range(num)]
        content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<gpx version="1.1" creator="iphone-location-sim-gui"\n'
            '     xmlns="http://www.topografix.com/GPX/1/1">\n'
            '  <trk><name>Generated Track</name><trkseg>\n'
        )
        for pt in pts:
            content += f'      <trkpt lat="{pt.lat:.6f}" lon="{pt.lng:.6f}"></trkpt>\n'
        content += '    </trkseg></trk>\n</gpx>\n'

        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
        self._set_status(f"GPX 已保存: {output}")
        messagebox.showinfo("完成", f"已生成 {num} 个航点\n{output}")

    def _show_info(self):
        if not self._conn:
            messagebox.showwarning("未连接", "请先连接 iPhone")
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
        messagebox.showinfo("设备信息", "\n".join(lines))

    # ==== UI helpers ====

    def _set_status(self, text):
        self._status_var.set(text)

    def _update_buttons(self):
        connected = self._conn is not None
        tracking = self._tracking
        self._set_btn["state"] = "normal" if connected else "disabled"
        self._stop_btn["state"] = "normal" if connected else "disabled"
        self._track_btn["state"] = "normal" if connected and not tracking else "disabled"
        self._abort_btn["state"] = "normal" if tracking else "disabled"
        self._info_btn["state"] = "normal" if connected else "disabled"

    def _on_close(self):
        self.root.destroy()

    # ==== build UI ====

    def _build_ui(self):
        self.root.title("iPhone 虚拟定位")
        self.root.geometry("620x620")
        self.root.resizable(True, True)
        self.root.configure(bg="#f0f0f0")
        self.pack(fill="both", expand=True, padx=12, pady=12)

        style = ttk.Style()
        style.theme_use("clam")

        # ---- Device bar ----
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 8))

        ttk.Label(bar, text="设备:", font=("", 10, "bold")).pack(side="left")
        self._device_label = ttk.Label(bar, text="检测中...", foreground="#999", font=("", 10))
        self._device_label.pack(side="left", padx=(6, 12))

        self._connect_btn = ttk.Button(bar, text="连接", command=self._connect, width=6)
        self._connect_btn.pack(side="left", padx=2)
        ttk.Button(bar, text="刷新", command=self._refresh_device_list, width=6).pack(side="left", padx=2)
        self._info_btn = ttk.Button(bar, text="设备信息", command=self._show_info, width=8)
        self._info_btn.pack(side="left", padx=2)
        self._info_btn["state"] = "disabled"

        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=4)

        # ---- Notebook ----
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, pady=(4, 0))

        # == Tab 1: Static location ==
        tab1 = ttk.Frame(nb, padding=16)
        nb.add(tab1, text="静态定位")

        f1 = ttk.Frame(tab1)
        f1.pack(fill="x")
        ttk.Label(f1, text="纬度 (lat):", font=("", 10)).grid(row=0, column=0, sticky="e", padx=(0, 8), pady=6)
        self._lat_var = tk.StringVar(value="39.9042")
        ttk.Entry(f1, textvariable=self._lat_var, width=22, font=("", 11)).grid(row=0, column=1, pady=6)

        ttk.Label(f1, text="经度 (lng):", font=("", 10)).grid(row=1, column=0, sticky="e", padx=(0, 8), pady=6)
        self._lng_var = tk.StringVar(value="116.4074")
        ttk.Entry(f1, textvariable=self._lng_var, width=22, font=("", 11)).grid(row=1, column=1, pady=6)

        btn_row1 = ttk.Frame(tab1)
        btn_row1.pack(fill="x", pady=(12, 0))
        self._set_btn = ttk.Button(btn_row1, text="设置位置", command=self._set_location)
        self._set_btn.pack(side="left", padx=(0, 8))
        self._stop_btn = ttk.Button(btn_row1, text="恢复真实 GPS", command=self._stop_location)
        self._stop_btn.pack(side="left")
        self._set_btn["state"] = "disabled"
        self._stop_btn["state"] = "disabled"

        ttk.Label(tab1, text="\n常用坐标:", font=("", 9, "bold")).pack(anchor="w")
        presets_frame = ttk.Frame(tab1)
        presets_frame.pack(fill="x")
        presets = [
            ("北京天安门", "39.9042, 116.4074"),
            ("上海外滩", "31.2304, 121.4737"),
            ("广州塔", "23.1065, 113.3245"),
            ("深圳华强北", "22.5431, 114.0824"),
            ("成都春熙路", "30.6598, 104.0805"),
            ("纽约时代广场", "40.7580, -73.9855"),
        ]
        for i, (name, coord) in enumerate(presets):
            ttk.Button(
                presets_frame, text=name,
                command=lambda c=coord: self._set_preset(c),
            ).grid(row=i // 3, column=i % 3, padx=2, pady=2, sticky="ew")

        # == Tab 2: Track ==
        tab2 = ttk.Frame(nb, padding=16)
        nb.add(tab2, text="轨迹模拟")

        # GPX picker
        gpx_frame = ttk.Frame(tab2)
        gpx_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(gpx_frame, text="GPX 文件:", font=("", 10)).pack(side="left")
        self._gpx_var = tk.StringVar()
        ttk.Entry(gpx_frame, textvariable=self._gpx_var, width=36).pack(side="left", padx=6)
        ttk.Button(gpx_frame, text="浏览...", command=self._pick_gpx).pack(side="left")

        ttk.Label(tab2, text="或直接输入坐标串 (lat,lng|lat,lng):", font=("", 9)).pack(anchor="w")
        self._points_var = tk.StringVar()
        ttk.Entry(tab2, textvariable=self._points_var, width=60).pack(fill="x", pady=(2, 12))

        # Options
        opts = ttk.Frame(tab2)
        opts.pack(fill="x")

        ttk.Label(opts, text="模式:").grid(row=0, column=0, sticky="e", padx=(0, 6), pady=4)
        self._mode_var = tk.StringVar(value="walking")
        mode_cb = ttk.Combobox(opts, textvariable=self._mode_var, values=["walking", "cycling", "driving", "running"], state="readonly", width=10)
        mode_cb.grid(row=0, column=1, sticky="w", pady=4)

        ttk.Label(opts, text="速度 (m/s, 留空用预设):").grid(row=0, column=2, sticky="e", padx=(16, 6), pady=4)
        self._speed_var = tk.StringVar()
        ttk.Entry(opts, textvariable=self._speed_var, width=8).grid(row=0, column=3, sticky="w", pady=4)

        ttk.Label(opts, text="间隔 (秒):").grid(row=1, column=0, sticky="e", padx=(0, 6), pady=4)
        self._interval_var = tk.StringVar(value="1.0")
        ttk.Entry(opts, textvariable=self._interval_var, width=8).grid(row=1, column=1, sticky="w", pady=4)

        self._loop_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="循环", variable=self._loop_var).grid(row=1, column=2, padx=(16, 6), pady=4)
        self._keep_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="完成后保持位置", variable=self._keep_var).grid(row=1, column=3, padx=6, pady=4)

        # Preset GPX buttons
        presets2 = ttk.Frame(tab2)
        presets2.pack(fill="x", pady=(12, 8))
        ttk.Label(presets2, text="预设轨迹:", font=("", 9)).pack(side="left", padx=(0, 8))
        examples_dir = os.path.join(os.path.dirname(__file__), "examples")
        preset_gpx = [
            ("天安门", "beijing_tiananmen.gpx"),
            ("外滩", "shanghai_bund.gpx"),
            ("圆形循环", "circle_loop.gpx"),
        ]
        for name, fname in preset_gpx:
            full = os.path.join(examples_dir, fname)
            ttk.Button(presets2, text=name, command=lambda p=full: self._gpx_var.set(p)).pack(side="left", padx=2)

        # Progress & controls
        self._progress = ttk.Progressbar(tab2, mode="determinate", length=560)
        self._progress.pack(fill="x", pady=(12, 2))

        self._eta_label = ttk.Label(tab2, text="", font=("", 9))
        self._eta_label.pack(anchor="w")

        ctrl_frame = ttk.Frame(tab2)
        ctrl_frame.pack(fill="x", pady=(10, 0))
        self._track_btn = ttk.Button(ctrl_frame, text="开始轨迹", command=self._start_track)
        self._track_btn.pack(side="left", padx=(0, 8))
        self._abort_btn = ttk.Button(ctrl_frame, text="停止轨迹", command=self._stop_track)
        self._abort_btn.pack(side="left")
        self._track_btn["state"] = "disabled"
        self._abort_btn["state"] = "disabled"

        # == Tab 3: GPX Generator ==
        tab3 = ttk.Frame(nb, padding=16)
        nb.add(tab3, text="生成 GPX")

        f3 = ttk.Frame(tab3)
        f3.pack(fill="x")
        ttk.Label(f3, text="起点 (lat,lng):", font=("", 10)).grid(row=0, column=0, sticky="e", padx=(0, 8), pady=6)
        self._gen_from_var = tk.StringVar(value="39.9042, 116.4074")
        ttk.Entry(f3, textvariable=self._gen_from_var, width=30, font=("", 10)).grid(row=0, column=1, pady=6)

        ttk.Label(f3, text="终点 (lat,lng):", font=("", 10)).grid(row=1, column=0, sticky="e", padx=(0, 8), pady=6)
        self._gen_to_var = tk.StringVar(value="39.9142, 116.4174")
        ttk.Entry(f3, textvariable=self._gen_to_var, width=30, font=("", 10)).grid(row=1, column=1, pady=6)

        ttk.Label(f3, text="航点数:", font=("", 10)).grid(row=2, column=0, sticky="e", padx=(0, 8), pady=6)
        self._gen_num_var = tk.StringVar(value="20")
        ttk.Entry(f3, textvariable=self._gen_num_var, width=10).grid(row=2, column=1, sticky="w", pady=6)

        ttk.Button(tab3, text="生成并保存 GPX...", command=self._generate_gpx).pack(pady=(16, 0))

        # ---- Status bar ----
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=(8, 4))
        self._status_var = tk.StringVar(value="正在启动 tunneld ...")
        ttk.Label(self, textvariable=self._status_var, font=("", 9), foreground="#555").pack(anchor="w")

    def _set_preset(self, coord_str):
        lat_s, lng_s = coord_str.split(",")
        self._lat_var.set(lat_s.strip())
        self._lng_var.set(lng_s.strip())
        self._set_location()


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
