# -*- coding: utf-8 -*-
"""临时：验证看板数据层（修复 per-run 历史后）。
1) load_latest() 应返回 30 条、全部有价
2) 抽样 SKU 的 load_history() 应 >= 2 个历史点（两轮抓取）
3) 复刻看板 _price_drop 逻辑：真实数据无降价 -> 空；注入 +10% 上一轮价 -> 触发
"""
from utils.price_monitor.fetcher import load_latest, load_history

THRESH = 0.05

def price_drop(current, prev):
    pmap = {r.sku_id: r for r in prev if r.price is not None}
    out = {}
    for r in current:
        if r.price is None:
            continue
        p = pmap.get(r.sku_id)
        if p and p.price and p.price > 0:
            d = (p.price - r.price) / p.price
            if d >= THRESH:
                out[r.sku_id] = (d, r.price, p.price)
    return out

print("=== load_latest ===")
cur = load_latest()
print(f"records={len(cur)} priced={sum(1 for r in cur if r.price is not None)} "
      f"retailers={sorted({r.retailer_name for r in cur})}")

print("\n=== load_history (sample SKUs) ===")
samples = ["chanel_coco", "dior_miss", "tomford_tobacco", "bvlgari_pourhomme"]
for sid in samples:
    h = load_history(sid)
    print(f"{sid}: history_points={len(h)} "
          f"times={[x.captured_at[:16] for x in h]} "
          f"prices={[x.price for x in h]}")

# 构造 prev_run：取每个 sku 历史倒数第二条（看板逻辑）
hist_all = []
sku_ids = sorted({r.sku_id for r in cur})
for sid in sku_ids:
    hist_all.extend(load_history(sid))
hist_all.sort(key=lambda x: x.captured_at)
prev_map = {}
for r in hist_all:
    prev_map.setdefault(r.sku_id, []).append(r)
prev_run = [v[-2] for v in prev_map.values() if len(v) >= 2]
print(f"\nprev_run count (skus with >=2 history points) = {len(prev_run)}")

print("\n=== _price_drop on REAL data ===")
drops = price_drop(cur, prev_run)
print(f"real drops (>=5%) = {len(drops)}  -> {drops}")

print("\n=== _price_drop with SYNTHETIC +10% previous price ===")
# 复制 prev_run，但把价格抬高 10%，模拟一次真实降价
import copy
syn_prev = []
for r in prev_run:
    rr = copy.copy(r)
    if rr.price:
        rr.price = round(rr.price * 1.10, 2)
    syn_prev.append(rr)
drops2 = price_drop(cur, syn_prev)
print(f"synthetic drops = {len(drops2)}")
for sid, (d, nowp, wasp) in list(drops2.items())[:5]:
    print(f"  {sid}: ¥{wasp} -> ¥{nowp} (down {d*100:.1f}%)")
print("\nVERIFY_DONE")
