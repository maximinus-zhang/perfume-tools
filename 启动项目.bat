@echo off
chcp 65001 >nul
title 海南免税系统 - 推送+启动
color 0A

cd /d "C:\Users\Maximinuszhang\Desktop\项目"

echo.
echo =======================================
echo    🌴 一键推送代码 + 启动系统
echo =======================================
echo.

:: 推送到 GitHub（自动处理冲突）
git add -A
git commit -m "自动更新 %date% %time%"

:: 先拉取远程内容，再推送
git pull origin main --allow-unrelated-histories --no-edit
git push


:: === 第二步：启动本地应用 ===
echo.
echo 🚀 正在启动本地 Streamlit...
if not exist "venv\Scripts\activate.bat" (
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
streamlit run app.py

pause
