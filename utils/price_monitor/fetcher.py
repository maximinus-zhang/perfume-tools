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

from utils.price_monitor.config import (
    RETAILERS_MONITOR, PERFUME_SKUS, GUARDRAILS, snapshot_date,
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
    """跑一轮全量抓取，返回 list[PriceRecord]。"""
    retailers = retailers or RETAILERS_MONITOR
    skus = skus or PERFUME_SKUS
    g = GUARDRAILS
    if headless is None:
        headless = g["headless"]

    # 懒加载 Playwright（仅在真正抓取时要求已安装 chromium）
    from playwright.sync_api import sync_playwright

    records = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(user_agent=random_ua())
        page = ctx.new_page()

        for r in retailers:
            rid = r["id"]
            adapter_cls = ADAPTER_REGISTRY.get(rid)

            # 适配器尚未实现（如 #9 阶段的海控/中服）→ 标记 verify_pending，不阻塞其他家
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

        browser.close()

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
    """把一轮结果写成当日快照 + latest.csv，并尝试上传 OSS。返回本地路径。"""
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

    _upload_oss(day_path, f"price_monitor/snapshots/{date}.csv")
    _upload_oss(latest_path, "price_monitor/latest.csv")
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
    """读某 SKU 的全部历史价格（跨每日快照文件），按时间升序。
    返回 list[PriceRecord]（status=='ok' 的才有 price）。"""
    _ensure_dir()
    hist = []
    for fn in sorted(os.listdir(LOCAL_DIR)):
        if not fn.endswith(".csv") or fn == "latest.csv":
            continue
        with open(os.path.join(LOCAL_DIR, fn), "r", encoding="utf-8-sig") as f:
            for d in csv.DictReader(f):
                if d["sku_id"] != sku_id:
                    continue
                if retailer_id and d["retailer_id"] != retailer_id:
                    continue
                hist.append(PriceRecord.from_dict(d))
    hist.sort(key=lambda r: r.captured_at)
    return hist


def to_dataframe(records) -> "pd.DataFrame":
    import pandas as pd
    return pd.DataFrame([r.to_dict() for r in records])
