# 海南免税香水工具站 · 本地运行 + OSS 报告分享指南

> **前提说明**：你**没有云服务器**，只有阿里云 OSS（存储桶）。因此本应用**在本地 Windows 运行**，
> 深度竞品分析 HTML 报告通过 OSS 上传，生成可随时打开 / 分享的链接。
> Streamlit 必须有个能跑 Python 的环境，OSS 只是存储、跑不了应用，所以无法公网常驻访问。

---

## 一、本地运行（已在你电脑就绪）

1. 进入项目目录 `perfume-tools-main`
2. 双击 `启动项目.bat`（或在命令行运行 `python -m streamlit run app.py`）
3. 浏览器自动打开 `http://localhost:8501`
4. 左侧菜单 → **Sell Out** → **竞品价格监控** → 第三个 Tab **「🔍 深度竞品分析」**即可看到报告

> 报告文件已随代码放在 `reports/海南免税香水竞品分析.html`
> （已修复原来硬编码的 Windows 绝对路径，本地直接可读，不依赖 OSS）。

---

## 二、把深度竞品分析报告上传到 OSS（拿分享链接）

前提：已在 `.streamlit/secrets.toml` 配置 `OSS_ACCESS_KEY` / `OSS_SECRET_KEY`
（应用读取知识库 xlsx 也用这对凭证，配好即可复用）。

### 方式 A —— 一键脚本（推荐）
```bash
cd perfume-tools-main
python upload_report_to_oss.py            # 默认「公开读」，打印可分享链接
python upload_report_to_oss.py --private  # 仅自己看，生成 7 天有效签名链接
```
脚本会打印一个 OSS 链接，浏览器打开即可看报告，也能直接发给同事。

### 方式 B —— 控制台手动上传（无需脚本）
1. 登录阿里云 OSS 控制台 → Bucket `maximinus-flies`
2. 进入 / 新建 `reports/` 目录，上传 `reports/海南免税香水竞品分析.html`
3. 该文件 → 设置 ACL 为「公共读」→ 复制文件 URL（中文名会自动编码）

---

## 三、更新报告

报告内容有变动时，重新生成 HTML 覆盖 `reports/` 下文件，再跑一次
`python upload_report_to_oss.py` 即可覆盖 OSS 上的旧版本。

---

## 四、注意事项

- 上传到 OSS 的是「竞品分析报告 HTML」，**不含你的原始销售数据**。
- 若设为「公开读」，链接**任何人可访问**——请勿在报告里放机密信息；只想自己看请用 `--private`。
- 应用其它数据（知识库 xlsx）走 `utils/oss_helper.py` 的**私有 OSS** 通道，密钥不外泄。
- 若以后买了云服务器想公网部署，再单独找我出服务器方案（原 `start_server.sh` 已删除）。
