# -*- coding: utf-8 -*-
"""
竞品价格监控 · 采集编排器 v1.0
================================
run_monitor()  : 跑一轮全量抓取（所有零售商 × 所有 SKU），限速 / 重试 / 合规拦截，
                 结果双写本地 CSV 与 OSS（OSS 不可用则静默降级到本地）。
load_latest()  : 读最近一次快照（看板默认展示）。
load_history() : 读某 SKU 的历史价格（画趋势线 / 算降价）。
to_dataframe() : 转 pandas，供看板作图。

部署说明
--------
目标运行环境 = 阿里云轻量应用服务器（MAX 计划迁移处）。
  · 需安装：pip install playwright && playwright install chromium
  · 定时：crontab -e 加 `0 9 * * * cd /app && python -m utils.price_monitor.fetcher`
  · Streamlit 页面「立即抓取一次」按钮同样调用 run_monitor()。
"""

import os
import csv
import time
from datetime import datetime

from utils.price_monitor.config import (
    RETAILERS_MONITOR, PERFUME_SKUS, ALL_MONITOR_SKUS, GUARDRAILS, snapshot_date,
)
from utils.price_monitor.models import PriceRecord, CSV_COLUMNS, now_iso
from utils.price_monitor.adapters import ADAPTER_REGISTRY
from utils.price_monitor.adapters.base import random_ua

LOCAL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "price_monitor")
)


# ============================================================
# 主流程
# ============================================================
def run_monitor(retailers=None, skus=None, headless=None, persist=True):
    """跑一轮全量抓取，返回 list[PriceRecord]。

    引擎分发
    --------
    · 仅当存在 engine=="playwright" 的适配器时才启动浏览器（如海旅）。
    · 纯 HTTP 适配器（ENGINE=="api"，如中免）无需浏览器，直接发请求，
      甚至可在 Streamlit Cloud 免费额度等无 chromium 的环境跑。
    """
    retailers = retailers or RETAILERS_MONITOR
    skus = skus or ALL_MONITOR_SKUS
    g = GUARDRAILS
    if headless is None:
        headless = g["headless"]

    # 是否需要浏览器：存在任一非 None 且 ENGINE=="playwright" 的适配器
    need_browser = any(
        (ADAPTER_REGISTRY.get(r["id"]) is not None)
        and ADAPTER_REGISTRY.get(r["id"]).ENGINE == "playwright"
        for r in retailers
    )

    records = []

    def _collect(page):
        """单家循环；page 对纯 HTTP 适配器为 None 也无妨。"""
        for r in retailers:
            rid = r["id"]
            adapter_cls = ADAPTER_REGISTRY.get(rid)

            # 适配器尚未实现（如 #9 阶段遗留的海控/中服）→ 标 verify_pending，不阻塞其他家
            if adapter_cls is None:
                for sku in skus:
                    rec = PriceRecord(
                        retailer_id=rid, retailer_name=r["name"], sku_id=sku["id"],
                        brand=sku["brand"], name_cn=sku["name_cn"], name_en=sku["name_en"],
                        size_ml=sku["size_ml"], status="verify_pending",
                        note="适配器待 #10 实现（先验证是否公开）",
                        source=f"{r['name']}官网", category=sku.get("category", "香水"),
                    )
                    rec.captured_at = now_iso()
                    records.append(rec)
                continue

            adapter = adapter_cls(r, g, source_label=f"{r['name']}官网公开标价")
            for sku in skus:
                rec = _run_with_retry(adapter, sku, page, g)
                records.append(rec)
                time.sleep(g["min_interval_seconds"])  # 限速

    if need_browser:
        # 懒加载 Playwright（仅在真正需要浏览器时要求已安装 chromium）
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            ctx = browser.new_context(user_agent=random_ua())
            page = ctx.new_page()
            _collect(page)
            browser.close()
    else:
        # 全部是纯 HTTP 适配器（如只跑中免）→ 根本不碰浏览器
        _collect(None)

    if persist:
        save_snapshot(records)
    return records


def _run_with_retry(adapter, sku, page, g):
    """单次抓取失败按 max_retries 重试；非 error 状态立即返回。"""
    last = None
    for attempt in range(g["max_retries"]):
        try:
            rec = adapter.run(sku, page)
        except Exception as e:
            rec = adapter._blank_record(sku)
            rec.status = "error"
            rec.note = f"{type(e).__name__}: {e}"
            rec.captured_at = now_iso()
        if rec.status != "error":
            return rec
        last = rec
        time.sleep(2 * (attempt + 1))
    return last


# ============================================================
# 持久化（本地 CSV + OSS 双写）
# ============================================================
def _ensure_dir():
    os.makedirs(LOCAL_DIR, exist_ok=True)


def save_snapshot(records, date=None):
    """把一轮结果写成当日快照 + latest.csv + 每轮独立文件（runs/），并尝试上传 OSS。

    历史建模
    --------
    · latest.csv      : 当前轮（看板默认展示）。
    · YYYY-MM-DD.csv  : 当日最后一次抓取（人读用，可留底）。
    · runs/YYYY-MM-DDTHHMMSS.csv : 每一轮独立一份，永不覆盖 —— 监控趋势 /
      降价对比依赖跨「多次抓取」的历史点，同一天多次跑也要保留。
    """
    date = date or snapshot_date()
    _ensure_dir()
    rows = [r.to_dict() for r in records]

    day_path = os.path.join(LOCAL_DIR, f"{date}.csv")
    latest_path = os.path.join(LOCAL_DIR, "latest.csv")
    for path in (day_path, latest_path):
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            w.writeheader()
            w.writerows(rows)

    # 每轮独立历史点：用真实抓取时刻命名，多次跑不互相覆盖
    runs_dir = os.path.join(LOCAL_DIR, "runs")
    os.makedirs(runs_dir, exist_ok=True)
    run_id = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    run_path = os.path.join(runs_dir, f"{run_id}.csv")
    with open(run_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        w.writerows(rows)

    _upload_oss(day_path, f"price_monitor/snapshots/{date}.csv")
    _upload_oss(latest_path, "price_monitor/latest.csv")
    _upload_oss(run_path, f"price_monitor/runs/{run_id}.csv")
    return day_path


def _upload_oss(local_path, oss_key):
    """OSS 上传（可选）：无凭证 / 不可用时静默降级到本地。"""
    try:
        from utils.oss_helper import upload_to_oss
        upload_to_oss(local_path, oss_key)
    except Exception as e:
        print(f"[price_monitor] OSS 上传跳过（无凭证或不可用）: {e}")


# ============================================================
# 读取（看板用）
# ============================================================
def load_latest() -> list:
    """读最近一次快照的 PriceRecord 列表；不存在返回空。"""
    latest_path = os.path.join(LOCAL_DIR, "latest.csv")
    if not os.path.exists(latest_path):
        return []
    with open(latest_path, "r", encoding="utf-8-sig") as f:
        return [PriceRecord.from_dict(d) for d in csv.DictReader(f)]


def load_history(sku_id, retailer_id=None) -> list:
    """读某 SKU 的全部历史价格（跨每日快照 + 每轮独立文件 runs/），按时间升序。
    返回 list[PriceRecord]（status=='ok' 的才有 price）。

    去重：同一轮抓取的记录可能同时出现在「当日快照」和「runs/ 独立文件」中，
    用 (captured_at, sku_id, retailer_id) 去重，避免重复计数。
    """
    _ensure_dir()
    hist = []
    files = []
    # 每日快照（兼容旧数据，且人读用）
    for fn in sorted(os.listdir(LOCAL_DIR)):
        if fn.endswith(".csv") and fn != "latest.csv":
            files.append(os.path.join(LOCAL_DIR, fn))
    # 每轮独立文件（新：趋势 / 降价对比的主数据源）
    runs_dir = os.path.join(LOCAL_DIR, "runs")
    if os.path.isdir(runs_dir):
        for fn in sorted(os.listdir(runs_dir)):
            if fn.endswith(".csv"):
                files.append(os.path.join(runs_dir, fn))

    seen = set()
    for path in files:
        with open(path, "r", encoding="utf-8-sig") as f:
            for d in csv.DictReader(f):
                if d["sku_id"] != sku_id:
                    continue
                if retailer_id and d["retailer_id"] != retailer_id:
                    continue
                key = (d.get("captured_at"), d["sku_id"], d["retailer_id"])
                if key in seen:
                    continue
                seen.add(key)
                hist.append(PriceRecord.from_dict(d))
    hist.sort(key=lambda r: r.captured_at)
    return hist


def to_dataframe(records) -> "pd.DataFrame":
    import pandas as pd
    return pd.DataFrame([r.to_dict() for r in records])
