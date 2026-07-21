@echo off
chcp 65001 >nul
title "Perfume Supply Chain - Push and Start"
color 0A

cd /d "C:\Users\Maximinuszhang\Desktop\PYTHON\perfume-tools-main"

:: 关闭残留的旧 Streamlit 进程（8501~8503），避免双开导致出现两个页面 / 两个窗口
echo 正在清理可能残留的旧 Streamlit 进程...
for %%p in (8501 8502 8503) do (
  for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%%p" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
)
timeout /t 1 >nul

echo.
echo ======================================
echo    Push to GitHub + Start Local App
echo ======================================
echo.

echo Step 1: Pushing to GitHub
git add -A
git commit -m "auto update %date% %time%"
git pull origin main --allow-unrelated-histories --no-edit
git push -u origin main
if %ERRORLEVEL% EQU 0 (echo [OK] GitHub push success!) else (echo [WARN] GitHub push failed)
echo.

echo Step 2: Starting local Streamlit...
python -m pip install --upgrade -r requirements.txt
echo 应用启动后请访问: http://localhost:8501
python -m streamlit run app.py --server.port 8501

pause
