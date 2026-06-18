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

:: === 第一步：自动推送 GitHub ===
echo 🔄 正在检查 Git 变更...
git add -A
git status --short

set /p confirm="是否推送以上变更到 GitHub？(Y/N): "
if /i "%confirm%"=="Y" (
    echo 📤 正在提交...
    git commit -m "自动更新 %date% %time%"
    echo 📤 正在推送...
    git push
    if errorlevel 1 (
        echo ⚠️ 推送失败，请检查网络或 Git 配置
    ) else (
        echo ✅ 推送成功！Streamlit Cloud 将自动部署
    )
) else (
    echo ⏭️ 跳过推送
)

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
