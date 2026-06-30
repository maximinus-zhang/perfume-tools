@echo off
chcp 65001 >nul
title 香水工具 - 一键修复 + 启动

cd /d "C:\Users\Maximinuszhang\Desktop\PYTHON\perfume-tools-main"

echo ========== 1. 安装核心依赖 ==========
pip install streamlit pandas openpyxl numpy pyarrow xlsxwriter
if %errorlevel% neq 0 (
    echo [注意] 部分核心包安装失败，请检查网络
    pause
)

echo ========== 2. 开放防火墙端口 8501 ==========
netsh advfirewall firewall show rule name="Streamlit 8501" >nul 2>&1
if %errorlevel% equ 0 (
    echo 防火墙规则已存在，跳过。
) else (
    netsh advfirewall firewall add rule name="Streamlit 8501" dir=in action=allow protocol=TCP localport=8501
    echo 防火墙规则已创建。
)

echo ========== 3. 启动 Streamlit ==========
echo 应用将在浏览器中打开...
start "" "http://localhost:8501"
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
pause
