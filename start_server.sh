#!/usr/bin/env bash
# ============================================================
# 海南免税香水工具站 · 阿里云轻量应用服务器 启动脚本（Linux）
# 用法： bash start_server.sh
# 说明：建/复用 venv，装依赖，无头模式后台启动 Streamlit（端口 8501）
# ============================================================
set -e
cd "$(dirname "$0")"

echo "==> 准备 Python 虚拟环境"
if [ ! -d venv ]; then
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "==> 启动 Streamlit（端口 8501, 绑定 0.0.0.0, 无头模式）"
nohup streamlit run app.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --browser.gatherUsageStats false \
  > streamlit.log 2>&1 &

echo "==> 已后台启动，PID $!"
echo "    日志: tail -f streamlit.log"
echo "    访问: http://<服务器公网IP>:8501"
