#!/usr/bin/env python3
"""
一键安装脚本
pip install pymobiledevice3 + 验证 iPhone 连接状态
"""

import asyncio
import subprocess
import sys


def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


async def main():
    print("=" * 50)
    print("  iPhone 虚拟定位 - 环境安装与检测")
    print("=" * 50)
    print()

    # 1. Install dependency
    print("[1/4] 安装 pymobiledevice3 ...")
    result = run([sys.executable, "-m", "pip", "install", "pymobiledevice3", "--upgrade"])
    if result.returncode != 0:
        print(f"安装失败:\n{result.stderr}")
        print("\n请手动运行: pip install pymobiledevice3")
    else:
        print("  pymobiledevice3 安装成功[OK]")
    print()

    # 2. Check if iTunes/USB driver is available
    print("[2/4] 检查 USB 驱动 ...")
    try:
        result = run([sys.executable, "-c", "from pymobiledevice3.usbmux import select_device; select_device()"])
        if result.returncode == 0:
            print("  USB 驱动正常[OK]")
        else:
            print(f"  警告: USB 驱动可能未安装")
            print(f"  请在 Windows 上安装 iTunes 以获取 Apple Mobile Device Support 驱动")
            print(f"  下载: https://www.apple.com/itunes/")
    except Exception:
        pass
    print()

    # 3. Check connected devices
    print("[3/4] 检测 iPhone 连接 ...")
    try:
        from pymobiledevice3.usbmux import list_devices
        devices = await list_devices()
        if devices:
            for d in devices:
                serial = d.serial if hasattr(d, 'serial') else str(d)
                print(f"  发现设备: {serial}")
            print("  iPhone 已连接[OK]")
        else:
            print("  未发现已连接的 iPhone")
            print("  请确认:")
            print("    1. iPhone 已通过 USB 连接到电脑")
            print('    2. iPhone 已解锁并点击"信任此电脑"')
    except Exception as e:
        print(f"  检测失败: {e}")
    print()

    # 4. Check Developer Mode
    print("[4/4] 开发者模式提醒 ...")
    print("  请确保 iPhone 上已开启开发者模式:")
    print("  设置 > 隐私与安全性 > 开发者模式 > 开启")
    print()
    print("=" * 50)
    print("安装检测完成！")
    print()
    print("用法示例:")
    print("  python iphone_location_sim.py set 39.9042 116.4074")
    print("  python iphone_location_sim.py track --gpx examples/beijing_tiananmen.gpx")
    print("  python iphone_location_sim.py stop")
    print()
    print("或双击 launcher.bat 使用交互菜单。")


if __name__ == "__main__":
    asyncio.run(main())
