# 海南免税香水工具站 · 阿里云轻量应用服务器部署指南

## 一、前提
- 你已有阿里云**轻量应用服务器**实例（推荐 2核4G / Alibaba Cloud Linux 3 或 Ubuntu 22.04）。
- 本项目已推送到 GitHub：`git@github.com:maximinus-zhang/perfume-tools.git`
- 「深度竞品分析」Tab 的报告已随代码放在 `reports/海南免税香水竞品分析.html`
  （已修复原来硬编码的 Windows 绝对路径，改用相对路径 + 环境变量兜底，部署不会找不到文件）。

## 二、服务器端一次性操作
1. **放端口**：控制台 → 防火墙/安全组 → 放行 **TCP 8501** 入方向（来源 `0.0.0.0/0`，或限定你的办公 IP）。
2. **SSH 登录**服务器。
3. **装基础依赖**：
   - Alibaba Cloud Linux / CentOS：`sudo yum install -y git python3 python3-pip`
   - Ubuntu：`sudo apt update && sudo apt install -y git python3 python3-venv python3-pip`
4. **拉代码**（二选一）：
   - 方式 A（推荐）：把服务器的 SSH 公钥加到 GitHub **Deploy Key**，然后
     `git clone git@github.com:maximinus-zhang/perfume-tools.git`
   - 方式 B：本机已 `git push`，服务器用 HTTPS 克隆 / 或之后 `git pull`。
5. **启动**：`cd perfume-tools && bash start_server.sh`
6. 浏览器访问 `http://<公网IP>:8501`。

## 三、后续更新代码
本机改完 → `git push`；服务器执行：
```bash
cd perfume-tools
git pull
bash start_server.sh
```
（脚本会重建 venv 依赖并重启；旧进程用 `pkill -f "streamlit run"` 清掉即可。）

## 四、可选增强
- **实时抓取（Tab1/Tab2）用到 Playwright**：服务器需先装浏览器内核
  `venv/bin/playwright install --with-deps chromium`（需 root + 联网）。
- **域名 + HTTPS**：在 8501 前加 Nginx 反代，申请免费证书（Let's Encrypt）。
- **持久化**：用 systemd 托管，避免 SSH 断开后进程退出（示例见下）。

## 五、systemd 单元示例（可选，推荐生产用）
`/etc/systemd/system/perfume.service`：
```ini
[Unit]
Description=Perfume Tools Streamlit
After=network.target

[Service]
WorkingDirectory=/root/perfume-tools
ExecStart=/root/perfume-tools/venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```
启用：
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now perfume
# 查看状态 / 日志
sudo systemctl status perfume
journalctl -u perfume -f
```

## 六、常见坑
- **8501 打不开** → 先查安全组是否放行；再查 `streamlit.log`。
- **深度分析 Tab 空白/报错** → 确认 `reports/海南免税香水竞品分析.html` 已随 `git pull` 下来
  （可用 `ls reports/` 验证；也支持环境变量 `DEEP_ANALYSIS_HTML` 强制指定绝对路径）。
- **内存不足** → 轻量 2核2G 跑 Streamlit + Playwright 偏紧，建议 ≥4G。
- **GitHub 克隆要密码** → 改用 Deploy Key（服务器公钥）或 Personal Access Token（HTTPS）。
