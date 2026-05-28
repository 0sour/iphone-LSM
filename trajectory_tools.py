#!/usr/bin/env python3
"""
轨迹生成 & 高级工具集

提供更多轨迹生成方式：
  - 两点间道路状曲线
  - 随机游走模拟
  - 往返通勤路线
  - GPX 格式转换
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Coord:
    lat: float
    lng: float


def haversine(a: Coord, b: Coord) -> float:
    R = 6371000.0
    dlat = math.radians(b.lat - a.lat)
    dlng = math.radians(b.lng - a.lng)
    sdl2 = math.sin(dlat / 2)
    sdlg2 = math.sin(dlng / 2)
    a_ = sdl2 ** 2 + math.cos(math.radians(a.lat)) * math.cos(math.radians(b.lat)) * sdlg2 ** 2
    return R * 2 * math.atan2(math.sqrt(a_), math.sqrt(1 - a_))


def interpolate(a: Coord, b: Coord, t: float) -> Coord:
    return Coord(a.lat + (b.lat - a.lat) * t, a.lng + (b.lng - a.lng) * t)


# ---------- 道路状曲线生成 ----------

def generate_curved_path(
    start: Coord,
    end: Coord,
    num_points: int = 30,
    curvature: float = 0.3,
) -> List[Coord]:
    """
    生成两点间的曲线路径（模拟道路弯曲）。
    curvature: 0 = 直线, 越大越弯曲
    """
    if num_points < 2:
        return [start, end]

    dist = haversine(start, end)
    points: List[Coord] = []

    # 随机产生一个中间控制点偏移
    mid_lat = (start.lat + end.lat) / 2
    mid_lng = (start.lng + end.lng) / 2
    spread = dist * curvature / 111320.0  # 大致转成度数偏移

    # 垂直于路径方向偏移
    dx = end.lng - start.lng
    dy = end.lat - start.lat
    perp_lng = -dy if abs(dx) > 1e-10 else 1.0
    perp_lat = dx if abs(dx) > 1e-10 else 0.0
    perp_len = math.sqrt(perp_lat ** 2 + perp_lng ** 2)
    if perp_len > 0:
        perp_lat /= perp_len
        perp_lng /= perp_len

    ctrl = Coord(
        mid_lat + perp_lat * spread * (random.random() - 0.5) * 2,
        mid_lng + perp_lng * spread * (random.random() - 0.5) * 2,
    )

    # 二次贝塞尔曲线: B(t) = (1-t)^2 * P0 + 2(1-t)t * P1 + t^2 * P2
    for i in range(num_points):
        t = i / (num_points - 1)
        t1 = 1 - t
        lat = t1 * t1 * start.lat + 2 * t1 * t * ctrl.lat + t * t * end.lat
        lng = t1 * t1 * start.lng + 2 * t1 * t * ctrl.lng + t * t * end.lng
        points.append(Coord(lat, lng))

    return points


# ---------- 随机游走 ----------

def generate_random_walk(
    center: Coord,
    steps: int = 100,
    step_length_m: float = 10.0,
    stay_in_radius_m: float = 200.0,
) -> List[Coord]:
    """
    在中心点周围生成随机游走轨迹。
    模拟一个人在区域内随意走动。
    """
    points = [center]
    current = center
    angle = random.uniform(0, 360)

    for _ in range(steps):
        # 随机改变方向（±60°），产生平滑的移动
        angle += random.uniform(-60, 60)
        angle %= 360

        angle_rad = math.radians(angle)

        # 计算新位置（近似）
        dlat = step_length_m / 111320.0 * math.cos(angle_rad)
        dlng = step_length_m / (111320.0 * math.cos(math.radians(current.lat))) * math.sin(angle_rad)
        new_point = Coord(current.lat + dlat, current.lng + dlng)

        # 检查是否在半径范围内
        if haversine(center, new_point) > stay_in_radius_m:
            # 偏转方向，朝中心走
            angle = angle + 180 + random.uniform(-45, 45)
            angle %= 360
            angle_rad = math.radians(angle)
            dlat = step_length_m / 111320.0 * math.cos(angle_rad)
            dlng = step_length_m / (111320.0 * math.cos(math.radians(current.lat))) * math.sin(angle_rad)
            new_point = Coord(current.lat + dlat, current.lng + dlng)

        points.append(new_point)
        current = new_point

    return points


# ---------- 往返通勤路线 ----------

def generate_commute_route(
    home: Coord,
    work: Coord,
    num_segments: int = 5,
    variation: float = 0.0005,
) -> List[Coord]:
    """
    生成多点往返通勤路线。
    在两点之间插入多个有变化的中途点，使路线看起来更自然。
    """
    points = [home]
    for i in range(1, num_segments):
        t = i / num_segments
        pt = interpolate(home, work, t)
        pt.lat += random.uniform(-variation, variation)
        pt.lng += random.uniform(-variation, variation)
        points.append(pt)
    points.append(work)
    return points


# ---------- 带时间戳的轨迹 ----------

def add_timestamps(
    points: List[Coord],
    speed_ms: float = 1.4,
    start_time: Optional[str] = None,
) -> List[dict]:
    """为轨迹点加上时间戳"""
    import datetime

    if start_time:
        t = datetime.datetime.fromisoformat(start_time)
    else:
        t = datetime.datetime.now()

    result = []
    for i, pt in enumerate(points):
        if i > 0:
            dist = haversine(points[i - 1], pt)
            t += datetime.timedelta(seconds=dist / speed_ms)
        result.append({
            "lat": pt.lat,
            "lng": pt.lng,
            "time": t.isoformat(),
        })
    return result


# ---------- GPX 导出 ----------

def export_gpx(points: List[Coord], filepath: str, name: str = "Track") -> str:
    header = f'''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="trajectory-tools"
     xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>{name}</name>
    <trkseg>
'''
    body = ""
    for pt in points:
        body += f'      <trkpt lat="{pt.lat:.6f}" lon="{pt.lng:.6f}"></trkpt>\n'

    footer = '    </trkseg>\n  </trk>\n</gpx>\n'

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header + body + footer)

    return filepath


# ---------- CLI ----------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="轨迹生成 & 高级工具集")
    sub = parser.add_subparsers(dest="cmd")

    # curved
    p_curve = sub.add_parser("curved", help="生成两点间道路状曲线")
    p_curve.add_argument("--from", dest="from_", required=True, help='起点 lat,lng')
    p_curve.add_argument("--to", required=True, help='终点 lat,lng')
    p_curve.add_argument("--num", type=int, default=30, help="点数")
    p_curve.add_argument("--curve", type=float, default=0.3, help="弯曲度")
    p_curve.add_argument("-o", "--output", required=True, help="输出 GPX 文件")

    # random_walk
    p_walk = sub.add_parser("random-walk", help="生成随机游走轨迹")
    p_walk.add_argument("--center", required=True, help='中心坐标 lat,lng')
    p_walk.add_argument("--steps", type=int, default=100, help="步数")
    p_walk.add_argument("--step-len", type=float, default=10.0, help="步长(米)")
    p_walk.add_argument("--radius", type=float, default=200.0, help="活动半径(米)")
    p_walk.add_argument("-o", "--output", required=True, help="输出 GPX 文件")

    # commute
    p_commute = sub.add_parser("commute", help="生成通勤路线")
    p_commute.add_argument("--home", required=True, help='家坐标 lat,lng')
    p_commute.add_argument("--work", required=True, help='公司坐标 lat,lng')
    p_commute.add_argument("--segments", type=int, default=5, help="中途段数")
    p_commute.add_argument("-o", "--output", required=True, help="输出 GPX 文件")

    args = parser.parse_args()

    if args.cmd == "curved":
        lat1, lng1 = map(float, args.from_.split(","))
        lat2, lng2 = map(float, args.to.split(","))
        pts = generate_curved_path(Coord(lat1, lng1), Coord(lat2, lng2), args.num, args.curve)
        export_gpx(pts, args.output, "Curved Path")
        print(f"已生成: {args.output} ({len(pts)} 个航点)")

    elif args.cmd == "random-walk":
        lat, lng = map(float, args.center.split(","))
        pts = generate_random_walk(Coord(lat, lng), args.steps, args.step_len, args.radius)
        export_gpx(pts, args.output, "Random Walk")
        print(f"已生成: {args.output} ({len(pts)} 个航点)")

    elif args.cmd == "commute":
        lat1, lng1 = map(float, args.home.split(","))
        lat2, lng2 = map(float, args.work.split(","))
        pts = generate_commute_route(Coord(lat1, lng1), Coord(lat2, lng2), args.segments)
        export_gpx(pts, args.output, "Commute Route")
        print(f"已生成: {args.output} ({len(pts)} 个航点)")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
