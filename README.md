# iPhone 虚拟定位模拟器

类似爱思助手的 iPhone 虚拟定位工具，支持静态定位和轨迹模拟。通过 USB 连接 iPhone，使用 Apple DVT 协议修改手机 GPS 坐标。

## 前置条件

| 条件 | 说明 |
|------|------|
| iPhone 通过 **USB 数据线** 连接电脑 | 不支持 WiFi 连接 |
| iPhone 已**解锁**并点击**信任此电脑** | 首次连接时会弹出 |
| iPhone 开启**开发者模式** | 设置 > 隐私与安全性 > 开发者模式 |
| Windows 安装 **iTunes**（提供 USB 驱动） | [苹果官网下载](https://www.apple.com/itunes/) |
| **Python 3.8+** | 脚本运行环境 |

## 安装

```bash
# 方式一：自动安装并检测
python setup_check.py

# 方式二：手动安装
pip install pymobiledevice3
```

安装完成后，连接 iPhone 并确保已解锁信任，运行 `python iphone_location_sim.py info` 验证连接。

## 使用教程

### 一、静态定位（固定位置）

将 iPhone GPS 固定到指定坐标，适用于打卡、定位签到等场景。

```bash
# 格式：python iphone_location_sim.py set <纬度> <经度>
python iphone_location_sim.py set 39.9042 116.4074    # 北京天安门
python iphone_location_sim.py set 31.2304 121.4737    # 上海外滩
python iphone_location_sim.py set 22.5431 114.0579    # 深圳市民中心
```

执行后手机 GPS 会立即变成指定坐标，**按 Ctrl+C 或关闭窗口会自动恢复真实 GPS**。

### 二、轨迹模拟（沿路径移动）

模拟手机沿着一条路线移动，适用于跑步打卡、微信运动、游戏定位等场景。

#### 2.1 使用 GPX 轨迹文件

项目内置了示例轨迹：

```bash
# 白天安门广场步行（约 1.5 公里）
python iphone_location_sim.py track --gpx examples/beijing_tiananmen.gpx --mode walking

# 上海外滩骑车
python iphone_location_sim.py track --gpx examples/shanghai_bund.gpx --mode cycling

# 圆形循环轨迹（适合持续模拟在某区域活动）
python iphone_location_sim.py track --gpx examples/circle_loop.gpx --mode cycling --loop
```

#### 2.2 使用坐标串

```bash
# 用 | 分隔多个坐标点，工具会自动插值生成平滑路径
python iphone_location_sim.py track --points "39.90,116.40|39.91,116.41|39.92,116.42" --mode driving
```

#### 2.3 移动模式说明

| 模式 | 速度 | 适用场景 |
|------|------|----------|
| `walking` | 5 km/h (1.4 m/s) | 模拟步行、微信运动 |
| `running` | 12 km/h (3.3 m/s) | 模拟跑步 |
| `cycling` | 15 km/h (4.2 m/s) | 模拟骑行 |
| `driving` | 40 km/h (11.1 m/s) | 模拟驾车 |

#### 2.4 自定义速度

```bash
# 以 20 m/s (72 km/h) 的速度移动
python iphone_location_sim.py track --gpx my_route.gpx --speed 20
```

#### 2.5 循环与保持

```bash
# 循环折返（走到终点后原路返回，无限重复）
python iphone_location_sim.py track --gpx route.gpx --loop

# 到达终点后保持虚拟位置（不在关机/断连后自动恢复 GPS）
python iphone_location_sim.py track --gpx route.gpx --keep-location
```

### 三、生成轨迹文件

#### 3.1 快速生成直线轨迹

```bash
# 从 A 到 B 生成 30 个均匀分布的航点
python iphone_location_sim.py generate --from "39.90,116.40" --to "39.95,116.45" --num-points 30 -o my_route.gpx
```

#### 3.2 生成弯曲道路轨迹

模拟真实道路的弯曲效果：

```bash
python trajectory_tools.py curved --from "39.90,116.40" --to "39.95,116.45" --curve 0.5 --num 40 -o curved_route.gpx
```

`--curve` 控制弯曲程度：0 = 直线，越大越弯曲，建议 0.2 ~ 0.6。

#### 3.3 生成随机游走轨迹

模拟某人在一个区域内随意走动：

```bash
# 以某坐标为中心，在 500 米半径内随机游走 300 步
python trajectory_tools.py random-walk --center "39.9042,116.4074" --steps 300 --radius 500 -o random_walk.gpx
```

#### 3.4 生成通勤路线

模拟上下班路线，带自然的路径偏移：

```bash
python trajectory_tools.py commute --home "39.90,116.40" --work "39.95,116.45" --segments 8 -o commute.gpx
```

### 四、停止虚拟定位

```bash
python iphone_location_sim.py stop
```

执行后 iPhone 立即恢复真实 GPS。或者直接拔掉 USB 线也会自动恢复。

### 五、自定义 GPX 文件格式

你也可以自己编辑 GPX 文件，格式如下：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="your-name"
     xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>我的路线</name>
    <trkseg>
      <trkpt lat="39.904200" lon="116.397407"></trkpt>
      <trkpt lat="39.908000" lon="116.399200"></trkpt>
      <trkpt lat="39.912000" lon="116.401500"></trkpt>
      <!-- 更多航点... -->
    </trkseg>
  </trk>
</gpx>
```

坐标查询推荐使用 [百度拾取坐标系统](https://api.map.baidu.com/lbsapi/getpoint/) 或高德地图。

## 常见问题

**Q: 连接失败 / 找不到设备？**

确认以下几点：
1. 数据线是否为 **MFi 认证线**（杂牌线可能只支持充电不支持数据）
2. iPhone 是否**解锁**并弹出了"信任此电脑"
3. Windows 任务管理器 > 服务 > **Apple Mobile Device Service** 是否在运行
4. 尝试换个 USB 口或重启 iPhone

**Q: 提示 "DVT 服务启动失败"？**

确认 iPhone 上已开启开发者模式：**设置 > 隐私与安全性 > 开发者模式 > 开启并重启手机**。iOS 16+ 需要手动开启。

**Q: 虚拟定位对哪些 App 生效？**

系统级模拟，对所有 App 生效（微信、钉钉、美团、滴滴、游戏等），和 Xcode 模拟定位效果一致。

**Q: 如何获取某个地点的坐标？**

打开 [百度地图拾取坐标](https://api.map.baidu.com/lbsapi/getpoint/)，在地图上点击目标位置即可复制经纬度。

**Q: 拔线后 GPS 会恢复吗？**

会。USB 断开或脚本退出时，iPhone 默认恢复真实 GPS。如果想保持虚拟位置，使用 `--keep-location` 参数。

## 文件说明

| 文件 | 用途 |
|------|------|
| `iphone_location_sim.py` | 主脚本：定位、轨迹模拟 |
| `trajectory_tools.py` | 辅助工具：曲线/随机/通勤路线生成 |
| `setup_check.py` | 一键安装依赖 + 设备连接检测 |
| `launcher.bat` | Windows 交互菜单启动器 |
| `examples/` | 示例 GPX 轨迹文件 |
