# -*- coding: utf-8 -*-
"""临时：连续跑两轮中免 CDF 抓取，生成两次独立的 runs/ 历史点（仅供验证看板趋势/降价对比）。"""
import time
from utils.price_monitor.fetcher import run_monitor
from utils.price_monitor.config import RETAILERS_MONITOR

cdfg = [r for r in RETAILERS_MONITOR if r["id"] == "cdfg"]

print("=== RUN 1 start ===", flush=True)
run_monitor(retailers=cdfg, headless=True, persist=True)
print("=== RUN 1 done ===", flush=True)
time.sleep(3)
print("=== RUN 2 start ===", flush=True)
run_monitor(retailers=cdfg, headless=True, persist=True)
print("=== RUN 2 done ===", flush=True)
print("=== ALL DONE ===", flush=True)
