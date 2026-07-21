@echo off
:: ====== 单实例锁：防止双击时 Windows 重复打开两个窗口 ======
set LOCK_FILE=%TEMP%\perfume_tools_push_lock.tmp
if exist "%LOCK_FILE%" (
    echo [INFO] 已经在运行中，本实例自动退出。
    exit /B 0
)
echo locked > "%LOCK_FILE%"
:: ================================================================

chcp 65001 >nul
title Perfume Supply Chain - Push & Start
color 0A

cd /d "C:\Users\Maximinuszhang\Desktop\PYTHON\perfume-tools-main"

echo.
echo =======================================
echo    Push to GitHub + Start Local App
echo =======================================
echo.

echo Step 1: Pushing to GitHub
git add -A
git commit -m "auto update %date% %time%"

:: 拉取远程内容，避免冲突
git pull origin main --allow-unrelated-histories --no-edit

:: 推送到远程 main 分支
git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo [OK] GitHub push success!
) else (
    echo [WARN] GitHub push failed
)
echo.

echo Step 2: Starting local Streamlit...
python -m pip install --upgrade -r requirements.txt
echo 应用启动后请在浏览器打开: http://localhost:8501
python -m streamlit run app.py

:: 清理锁文件
del "%LOCK_FILE%" 2>nul

pause
