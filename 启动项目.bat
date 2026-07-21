@echo off
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
if not exist "venv\Scripts\activate.bat" python -m venv venv
call venv\Scripts\activate.bat
pip install --upgrade -r requirements.txt --quiet

echo 应用启动后请在浏览器打开: http://localhost:8501
streamlit run app.py

pause
