#!/usr/bin/env python3
"""
iPhone 虚拟定位 / Virtual Location Simulator
类似爱思助手虚拟定位功能，支持轨迹模拟

Dependencies:
    pip install pymobiledevice3

Requirements:
    - iPhone connected via USB
    - Developer Mode enabled on iPhone (Settings > Privacy > Developer Mode)
    - iTunes / Apple Mobile Device Support installed (Windows)
"""

import argparse
import asyncio
import inspect
import math
import sys
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Fix Windows GBK encoding for emoji in device names
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ---------- coordinate utilities ----------

@dataclass
class Coordinate:
    lat: float
    lng: float

    def __str__(self) -> str:
        return f"{self.lat:.6f}, {self.lng:.6f}"


def haversine_distance(a: Coordinate, b: Coordinate) -> float:
    """返回两点间距离（米）"""
    R = 6371000.0
    dlat = math.radians(b.lat - a.lat)
    dlng = math.radians(b.lng - a.lng)
    sin_dlat = math.sin(dlat / 2)
    sin_dlng = math.sin(dlng / 2)
    a_ = sin_dlat ** 2 + math.cos(math.radians(a.lat)) * math.cos(math.radians(b.lat)) * sin_dlng ** 2
    return R * 2 * math.atan2(math.sqrt(a_), math.sqrt(1 - a_))


def bearing(a: Coordinate, b: Coordinate) -> float:
    """返回从 a 到 b 的方位角（度）"""
    dlat = math.radians(b.lat - a.lat)
    dlng = math.radians(b.lng - a.lng)
    y = math.sin(dlng) * math.cos(math.radians(b.lat))
    x = math.cos(math.radians(a.lat)) * math.sin(math.radians(b.lat)) - \
        math.sin(math.radians(a.lat)) * math.cos(math.radians(b.lat)) * math.cos(dlng)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def interpolate(a: Coordinate, b: Coordinate, fraction: float) -> Coordinate:
    """线性插值两点之间的坐标"""
    return Coordinate(
        lat=a.lat + (b.lat - a.lat) * fraction,
        lng=a.lng + (b.lng - a.lng) * fraction,
    )


# ---------- GPX parser ----------

def parse_gpx(filepath: str) -> List[Coordinate]:
    """解析 GPX 文件，提取航点 / 轨迹点"""
    import xml.etree.ElementTree as ET

    ns = {"gpx": "http://www.topografix.com/GPX/1/1"}
    tree = ET.parse(filepath)
    root = tree.getroot()

    points: List[Coordinate] = []

    # <wpt lat="..." lon="...">
    for wpt in root.findall(".//gpx:wpt", ns):
        points.append(Coordinate(lat=float(wpt.attrib["lat"]), lng=float(wpt.attrib["lon"])))

    # <trkpt lat="..." lon="...">
    for trkpt in root.findall(".//gpx:trkpt", ns):
        points.append(Coordinate(lat=float(trkpt.attrib["lat"]), lng=float(trkpt.attrib["lon"])))

    # <rtept lat="..." lon="...">
    for rtept in root.findall(".//gpx:rtept", ns):
        points.append(Coordinate(lat=float(rtept.attrib["lat"]), lng=float(rtept.attrib["lon"])))

    return points


# ---------- trajectory generator ----------

@dataclass
class TrajectoryConfig:
    mode: str = "walking"       # walking | cycling | driving | custom
    speed_ms: Optional[float] = None   # 自定义速度 (m/s)，覆盖 mode
    update_interval: float = 1.0       # 位置更新间隔（秒）
    loop: bool = False                 # 是否循环


SPEED_PRESETS = {
    "walking": 1.4,    # 5 km/h
    "cycling": 4.2,    # 15 km/h
    "driving": 11.1,   # 40 km/h
    "running": 3.3,    # 12 km/h
}


def generate_path_points(waypoints: List[Coordinate], step_distance: float = 5.0) -> List[Coordinate]:
    """
    在相邻航点之间按固定步长插值，生成完整路径点列表。
    step_distance: 相邻插值点之间的最大距离（米）
    """
    if len(waypoints) < 2:
        return waypoints

    result: List[Coordinate] = [waypoints[0]]
    for i in range(len(waypoints) - 1):
        a, b = waypoints[i], waypoints[i + 1]
        dist = haversine_distance(a, b)
        if dist <= step_distance:
            result.append(b)
            continue
        steps = int(dist / step_distance)
        for j in range(1, steps + 1):
            result.append(interpolate(a, b, j / steps))
        if steps * step_distance < dist:
            result.append(b)
    return result


# ---------- device connector ----------

TUNNELD_ADDRESS = ("127.0.0.1", 49151)


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
    if _is_tunneld_running():
        return
    import subprocess
    subprocess.Popen(
        [sys.executable, "-m", "pymobiledevice3", "remote", "tunneld"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    for _ in range(20):
        time.sleep(0.5)
        if _is_tunneld_running():
            return
    sys.exit("无法启动 tunneld。请手动运行: python -m pymobiledevice3 remote tunneld")


async def _get_rsd_provider():
    from pymobiledevice3.tunneld.api import get_tunneld_devices
    devices = await get_tunneld_devices(TUNNELD_ADDRESS)
    if not devices:
        sys.exit("未发现设备。请确保 iPhone 已通过 USB 连接并解锁。")
    return devices[0]


async def connect_device() -> Tuple:
    """连接 iPhone 并返回 (service_provider, location_service)"""
    try:
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
    except ImportError:
        sys.exit(
            "请先安装 pymobiledevice3:\n"
            "  pip install pymobiledevice3\n\n"
            "Windows 用户还需要安装 iTunes (提供 Apple Mobile Device USB 驱动):\n"
            "  https://www.apple.com/itunes/"
        )

    print("正在启动 tunneld ...")
    _start_tunneld()

    print("正在连接 iPhone ...")
    try:
        provider = await _get_rsd_provider()
        await provider.connect()
    except Exception as e:
        sys.exit(f"连接失败: {e}\n请确保:\n  1. iPhone 已通过 USB 连接到电脑\n  2. iPhone 已解锁\n  3. 已信任此电脑")

    device_info = provider.all_values
    print(f"已连接: {device_info.get('DeviceName', 'Unknown')} "
          f"(iOS {device_info.get('ProductVersion', '?')}, "
          f"{device_info.get('HardwareModel', '?')})")

    try:
        dvt = DvtProvider(provider)
        await dvt.connect()
        location_service = LocationSimulation(dvt)
        await location_service.connect()
    except Exception as e:
        sys.exit(f"DVT 服务启动失败: {e}\n请确保 iPhone 上已开启开发者模式 (设置 > 隐私与安全性 > 开发者模式)")

    return provider, location_service


# ---------- commands ----------

async def cmd_set(args):
    """设置静态虚拟位置"""
    _, loc = await connect_device()
    coord = Coordinate(lat=args.lat, lng=args.lng)
    print(f"设置虚拟位置: {coord}")
    await loc.set(coord.lat, coord.lng)
    print("位置已更新。按 Ctrl+C 停止虚拟定位（位置将恢复真实 GPS）。")


async def cmd_stop(args):
    """停止虚拟定位，恢复真实 GPS"""
    _, loc = await connect_device()
    print("正在停止虚拟定位 ...")
    await loc.clear()
    print("已恢复真实 GPS。")


async def cmd_track(args):
    """模拟轨迹"""
    # 解析航点
    waypoints: List[Coordinate] = []
    if args.gpx:
        waypoints = parse_gpx(args.gpx)
        if not waypoints:
            sys.exit(f"GPX 文件中未找到航点: {args.gpx}")
        print(f"从 GPX 加载了 {len(waypoints)} 个航点")
    elif args.points:
        for p in args.points.split("|"):
            lat_str, lng_str = p.strip().split(",")
            waypoints.append(Coordinate(lat=float(lat_str.strip()), lng=float(lng_str.strip())))
        print(f"加载了 {len(waypoints)} 个航点")

    if len(waypoints) < 2:
        sys.exit("轨迹模式至少需要 2 个航点。")

    # 速度
    speed = SPEED_PRESETS.get(args.mode, 1.4) if args.speed is None else args.speed
    config = TrajectoryConfig(
        mode=args.mode,
        speed_ms=speed,
        update_interval=args.interval,
        loop=args.loop,
    )

    # 生成路径
    path = generate_path_points(waypoints, step_distance=speed * config.update_interval)
    print(f"生成轨迹路径: {len(path)} 个插值点")

    # 计算距离和时间
    total_dist = sum(
        haversine_distance(path[i], path[i + 1]) for i in range(len(path) - 1)
    )
    eta_seconds = total_dist / speed
    print(f"总距离: {total_dist:.0f} m  |  速度: {speed:.1f} m/s ({args.mode})  |  预计用时: {eta_seconds:.0f}s")
    print()

    # 连接设备
    _, loc = await connect_device()
    print()

    # 模拟轨迹
    try:
        while True:
            for i, pt in enumerate(path):
                await loc.set(pt.lat, pt.lng)
                progress = (i + 1) / len(path) * 100
                dist_done = sum(
                    haversine_distance(path[j], path[j + 1]) for j in range(i)
                )
                remaining = eta_seconds - (dist_done / speed) if speed > 0 else 0

                bar_len = 30
                filled = int(bar_len * (i + 1) / len(path))
                bar = "█" * filled + "░" * (bar_len - filled)

                sys.stdout.write(
                    f"\r[{bar}] {progress:5.1f}%  |  {pt}  |  剩余 {remaining:5.0f}s  "
                )
                sys.stdout.flush()
                time.sleep(config.update_interval)

            if not config.loop:
                break
            path = list(reversed(path))  # 折返
            print("\n--- 折返 ---")

    except KeyboardInterrupt:
        print("\n\n轨迹模拟已中断。")
        if args.keep_location:
            print("虚拟位置保持当前坐标。执行 stop 命令恢复真实 GPS。")
        else:
            print("正在恢复真实 GPS ...")
            await loc.clear()
            print("已恢复真实 GPS。")
        return

    print("\n轨迹模拟完成。")
    if args.keep_location:
        print("虚拟位置保持在终点。执行 stop 命令恢复真实 GPS。")
    else:
        print("正在恢复真实 GPS ...")
        loc.clear()
        print("已恢复真实 GPS。")


def cmd_generate(args):
    """生成 GPX 轨迹文件"""
    from_str = args.from_
    to_str = args.to
    from_lat, from_lng = map(float, from_str.split(","))
    to_lat, to_lng = map(float, to_str.split(","))

    start = Coordinate(lat=float(from_lat), lng=float(from_lng))
    end = Coordinate(lat=float(to_lat), lng=float(to_lng))
    num = args.num_points

    pts = [interpolate(start, end, i / (num - 1)) for i in range(num)]

    gpx_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="iphone-location-sim"
     xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Generated Track</name>
    <trkseg>
'''
    for pt in pts:
        gpx_content += f'      <trkpt lat="{pt.lat:.6f}" lon="{pt.lng:.6f}"></trkpt>\n'
    gpx_content += '    </trkseg>\n  </trk>\n</gpx>\n'

    out_file = args.output or f"track_{start.lat:.4f}_{start.lng:.4f}_to_{end.lat:.4f}_{end.lng:.4f}.gpx"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(gpx_content)
    print(f"GPX 已保存: {out_file} ({num} 个航点)")


async def cmd_info(args):
    """显示设备信息"""
    print("正在启动 tunneld ...")
    _start_tunneld()

    try:
        provider = await _get_rsd_provider()
        await provider.connect()
    except Exception:
        sys.exit("未找到已连接的 iPhone。请确认:\n  1. iPhone 已通过 USB 连接\n  2. iPhone 已解锁并信任此电脑")

    info = provider.all_values
    print("=" * 50)
    print(f"  设备名称: {info.get('DeviceName', '?')}")
    print(f"  型号:     {info.get('ProductType', '?')}")
    print(f"  iOS:      {info.get('ProductVersion', '?')}")
    print(f"  序列号:   {info.get('SerialNumber', '?')}")
    print(f"  UDID:     {info.get('UniqueDeviceID', '?')}")
    print(f"  WiFi MAC: {info.get('WiFiAddress', '?')}")
    print(f"  蓝牙 MAC: {info.get('BluetoothAddress', '?')}")
    print("=" * 50)


# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(
        description="iPhone 虚拟定位 / Virtual Location Simulator — 类似爱思助手虚拟定位功能",
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    # set
    p_set = sub.add_parser("set", help="设置静态虚拟位置")
    p_set.add_argument("lat", type=float, help="纬度 (latitude)")
    p_set.add_argument("lng", type=float, help="经度 (longitude)")
    p_set.set_defaults(func=cmd_set)

    # stop
    p_stop = sub.add_parser("stop", help="停止虚拟定位，恢复真实 GPS")
    p_stop.set_defaults(func=cmd_stop)

    # track
    p_track = sub.add_parser("track", help="模拟轨迹移动")
    p_track.add_argument("--gpx", help="GPX 轨迹文件路径")
    p_track.add_argument("--points", help='坐标串，用 | 分隔，如 "39.9,116.4|39.91,116.41"')
    p_track.add_argument("--mode", default="walking", choices=["walking", "cycling", "driving", "running"],
                         help="移动模式 (默认: walking)")
    p_track.add_argument("--speed", type=float, help="自定义速度 (m/s)，覆盖 mode 预设")
    p_track.add_argument("--interval", type=float, default=1.0, help="位置更新间隔 秒 (默认: 1.0)")
    p_track.add_argument("--loop", action="store_true", help="循环轨迹")
    p_track.add_argument("--keep-location", action="store_true", help="完成后保持虚拟位置")
    p_track.set_defaults(func=cmd_track)

    # generate
    p_gen = sub.add_parser("generate", help="生成 GPX 轨迹文件")
    p_gen.add_argument("--from", dest="from_", required=True, help='起点坐标 "lat,lng"')
    p_gen.add_argument("--to", required=True, help='终点坐标 "lat,lng"')
    p_gen.add_argument("--num-points", type=int, default=20, help="航点数 (默认: 20)")
    p_gen.add_argument("--output", "-o", help="输出文件路径")
    p_gen.set_defaults(func=cmd_generate)

    # info
    p_info = sub.add_parser("info", help="显示已连接 iPhone 的设备信息")
    p_info.set_defaults(func=cmd_info)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if inspect.iscoroutinefunction(args.func):
        asyncio.run(args.func(args))
    else:
        args.func(args)


if __name__ == "__main__":
    main()
