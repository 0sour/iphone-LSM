@echo off
:: ============================================
::  iPhone Virtual Location Simulator
::  类似爱思助手虚拟定位工具
:: ============================================

echo.
echo ============================================
echo   iPhone 虚拟定位 / Virtual Location Sim
echo ============================================
echo.
echo   [0] 图形界面 (推荐)
echo   [1] 静态定位 - 设置固定位置
echo   [2] 轨迹模拟 - 沿路径移动
echo   [3] 停止定位 - 恢复真实GPS
echo   [4] 生成GPX轨迹文件
echo   [5] 查看设备信息
echo   [Q] 退出
echo.
set /p choice="请选择 (0-5/Q): "

if "%choice%"=="0" goto gui
if "%choice%"=="1" goto static
if "%choice%"=="2" goto track
if "%choice%"=="3" goto stop
if "%choice%"=="4" goto generate
if "%choice%"=="5" goto info
if /I "%choice%"=="Q" exit /b
goto end

:gui
python gui.py
goto end

:static
echo.
set /p lat="纬度 (lat): "
set /p lng="经度 (lng): "
python iphone_location_sim.py set %lat% %lng%
goto end

:track
echo.
echo   [a] 预设 - 北京天安门
echo   [b] 预设 - 上海外滩
echo   [c] 预设 - 圆形循环轨迹
echo   [d] 自定义 GPX 文件
echo   [e] 输入坐标串
echo.
set /p tchoice="选择: "

if "%tchoice%"=="a" set gpx=examples\beijing_tiananmen.gpx
if "%tchoice%"=="b" set gpx=examples\shanghai_bund.gpx
if "%tchoice%"=="c" set gpx=examples\circle_loop.gpx

if "%tchoice%"=="d" (
    set /p gpx="GPX 文件路径: "
)
if "%tchoice%"=="e" (
    set /p pts="坐标串 (lat,lng|lat,lng): "
    python iphone_location_sim.py track --points "%pts%" --mode walking
    goto end
)

if "%tchoice%"=="a" python iphone_location_sim.py track --gpx "%gpx%" --mode walking
if "%tchoice%"=="b" python iphone_location_sim.py track --gpx "%gpx%" --mode walking
if "%tchoice%"=="c" python iphone_location_sim.py track --gpx "%gpx%" --mode cycling --loop
if "%tchoice%"=="d" python iphone_location_sim.py track --gpx "%gpx%" --mode walking
goto end

:stop
python iphone_location_sim.py stop
goto end

:generate
echo.
set /p from_="起点坐标 (lat,lng): "
set /p to_="终点坐标 (lat,lng): "
set /p num_="航点数 (默认20): "
if "%num_%"=="" set num_=20
python iphone_location_sim.py generate --from "%from_%" --to "%to_%" --num-points %num_%
goto end

:info
python iphone_location_sim.py info
goto end

:end
pause
