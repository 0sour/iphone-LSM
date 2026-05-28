# iPhone 虚拟定位模拟器

类似爱思助手的 iPhone 虚拟定位工具，提供**图形界面**和**命令行**两种使用方式。通过 USB 连接 iPhone，使用 Apple DVT 协议修改手机 GPS 坐标。

## 功能概览

| 功能 | GUI | 命令行 | 说明 |
|------|:---:|:------:|------|
| 静态定位 | ✓ | ✓ | 将 GPS 固定到指定坐标 |
| 轨迹模拟 | ✓ | ✓ | 沿路径移动，模拟步行/骑行/驾车 |
| 循环轨迹 | ✓ | ✓ | 到达终点后自动折返，无限循环 |
| 保持位置 | ✓ | ✓ | 完成后不恢复真实 GPS |
| GPX 轨迹生成 | ✓ | ✓ | 自定义起终点生成轨迹文件 |
| 预设坐标点 | ✓ | | 一键切换到常用地点 |
| 设备信息 | ✓ | ✓ | 查看已连接 iPhone 的详细信息 |
| 进度显示 | ✓ | | 轨迹模拟实时进度条和预计时间 |
| 坐标串输入 | ✓ | ✓ | 直接输入 lat,lng 坐标串 |

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

## 图形界面使用 (推荐)

启动 GUI：

```bash
python gui.py
```

或双击 `launcher.bat` 选择 `[0] 图形界面`。

### 界面说明

GUI 包含三个功能标签页：

**① 静态定位** — 设置固定 GPS 位置

- 输入经纬度，点击「设置位置」
- 内置常用坐标一键切换：北京天安门、上海外滩、广州塔、深圳华强北、成都春熙路、纽约时代广场
- 点击「恢复真实 GPS」停止虚拟定位

**② 轨迹模拟** — 沿路径移动

- 选择 GPX 轨迹文件（内置三条预设轨迹：天安门、外滩、圆形循环）
- 或手动输入坐标串，格式：`lat,lng|lat,lng|lat,lng`
- 可配置移动模式（步行/骑行/驾车/跑步）、速度、更新间隔
- 支持「循环」和「完成后保持位置」
- 底部显示实时进度条和预计剩余时间

**③ 生成 GPX** — 快速生成直线轨迹文件

- 输入起终点坐标和航点数，生成 GPX 文件供轨迹模拟使用

### 连接流程

1. 启动 GUI 后会自动启动 tunneld 服务
2. 看到「检测到设备，点击连接」后点击「连接」
3. 连接成功后显示设备名称和 iOS 版本
4. 即可开始使用各项功能

## 命令行使用

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
| `walking` | 1.4 m/s (5 km/h) | 模拟步行、微信运动 |
| `running` | 3.3 m/s (12 km/h) | 模拟跑步 |
| `cycling` | 4.2 m/s (15 km/h) | 模拟骑行 |
| `driving` | 11.1 m/s (40 km/h) | 模拟驾车 |

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
2. iPhone 是否**解锁**并弹出了「信任此电脑」
3. Windows 任务管理器 > 服务 > **Apple Mobile Device Service** 是否在运行
4. 尝试换个 USB 口或重启 iPhone

**Q: 提示 "DVT 服务启动失败"？**

确认 iPhone 上已开启开发者模式：**设置 > 隐私与安全性 > 开发者模式 > 开启并重启手机**。iOS 16+ 需要手动开启。

**Q: 虚拟定位对哪些 App 生效？**

系统级模拟，对所有 App 生效（微信、钉钉、美团、滴滴、游戏等），和 Xcode 模拟定位效果一致。

**Q: 如何获取某个地点的坐标？**

打开 [百度地图拾取坐标](https://api.map.baidu.com/lbsapi/getpoint/)，在地图上点击目标位置即可复制经纬度。

**Q: 拔线后 GPS 会恢复吗？**

会。USB 断开或脚本退出时，iPhone 默认恢复真实 GPS。如果想保持虚拟位置，使用 `--keep-location` 参数或 GUI 中勾选「完成后保持位置」。

## 文件说明

| 文件 | 用途 |
|------|------|
| `gui.py` | 图形化界面（推荐使用） |
| `iphone_location_sim.py` | 核心脚本：定位、轨迹模拟、GPX 生成 |
| `trajectory_tools.py` | 辅助工具：曲线/随机/通勤路线生成 |
| `setup_check.py` | 一键安装依赖 + 设备连接检测 |
| `launcher.bat` | Windows 交互菜单启动器 |
| `examples/` | 示例 GPX 轨迹文件 |
