# -*- coding: utf-8 -*-
"""
海南免税 门店级 代理估算 v1.0
========================================
⚠️⚠️⚠️ 重要：本模块所有输出均为【估算值】，禁止当作官方/实测数据使用。
   看板展示时必须带「估算」角标，避免同事/外部误判为实测。

方法（代理分摊，透明可复核）
----------------------------
1. 锚点：公开宏观总量（海南离岛免税 H1 全省销售额，来自 hainan_2026_data.HA_DF_2026）。
2. 第一层：按 RETAILER_SHARE 把总量分摊到各零售商（中免占绝对主导，代理假设）。
3. 第二层：零售商内按各门店 weight 分摊到门店。
4. 客流：用全省 H1 客流量按与各零售商销售额同比例代理分摊（近似）。

所有 assumptions 均为「代理假设」，已写入每条记录的 method 字段，便于复核与调整。
"""

from utils.hainan_2026_data import HA_DF_2026
from utils.hainan_retailers import RETAILERS

# ============================================================
# 代理假设：各零售商在海南离岛免税的营收占比
# 来源：公开报道整理 + 中免/王府井财报口径；非逐店实测，标注 estimate
# （中免海南占全省约九成，其余主体瓜分剩余份额）
# ============================================================
RETAILER_SHARE = {
    "cdfg": 0.90,        # 中国中免（海南）
    "wangfujing": 0.03,   # 王府井免税（已被实际 Q1 口径覆盖，见 _retailer_share）
    "hk_global": 0.03,    # 海控全球精品
    "hlt": 0.02,          # 海旅免税
    "sz_mian": 0.01,      # 深免
    "zhongfu": 0.01,      # 中服免税
}

# 看板展示用的强提醒文案
ESTIMATE_BADGE = "估算"
ESTIMATE_DISCLAIMER = (
    "门店级销售/客流为代理估算值（以全省公开总量按零售商占比与门店权重分摊），"
    "非各店实测，仅供趋势参考，请勿用于精确决策。"
)


def _safe(v, default=0.0):
    """安全取值，避免 None 参与运算（不使用裸 except）。"""
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _retailer_share(r, h1_total):
    """
    取某零售商的 H1 占比（透明可复核），返回 (share, basis):
    - 仅当合作方显式标记 use_actual_q1=True 时，用【实际 Q1 口径】推导：
      占比 = 实际Q1 ÷ 全省Q1（用全省 H1/Q1 季节性把 Q1 外推到 H1 后归一，
      结果等价于 Q1/全省Q1，避免 Q1×2 对大体量零售商外推过头）。
      basis="实际Q1推导"。Q1 为实际披露，H1 为外推，仍标估算。
    - 其余回退到 RETAILER_SHARE 代理占比；basis="代理占比"。
    """
    if r.get("use_actual_q1") and r.get("hainan_q1_2026_rev") is not None:
        q1 = _safe(r["hainan_q1_2026_rev"])
        prov_q1 = _safe(HA_DF_2026["quarter"][0].get("amt26"), 142.1)
        if q1 and prov_q1:
            return q1 / prov_q1, "实际Q1推导"
    return RETAILER_SHARE.get(r["id"], 0.01), "代理占比"


def estimate_store_sales(h1_total=None, h1_pax=None):
    """
    返回门店级销售/客流估算列表。

    每条记录字段：
        retailer     零售商名
        store        门店名
        city         城市
        sales_h1_est 上半年销售额估算（亿元）
        pax_h1_est   上半年客流估算（万人次）
        is_estimate  True（强制）
        method       分摊公式（可追溯）
        source       'estimate'
    参数缺省时自动取 HA_DF_2026 公开口径。
    """
    if h1_total is None:
        h1_total = _safe(HA_DF_2026["ytd"].get("amount_2026"), 199.2)
    if h1_pax is None:
        h1_pax = _safe(HA_DF_2026["ytd"].get("pax_2026"), 279.3)

    results = []
    for r in RETAILERS:
        share, basis = _retailer_share(r, h1_total)
        r_total = h1_total * share
        r_pax = h1_pax * share
        stores = r.get("stores", [])
        wsum = sum(_safe(s.get("weight")) for s in stores) or 1.0
        for s in stores:
            w = _safe(s.get("weight")) / wsum
            rec = {
                "retailer": r["name"],
                "store": s["name"],
                "city": s.get("city"),
                "type": s.get("type"),
                "sales_h1_est": round(r_total * w, 3),
                "pax_h1_est": round(r_pax * w, 2),
                "is_estimate": True,
                "method": (
                    f"{basis} = H1全省{h1_total}亿 × 零售商占比{share:.0%} "
                    f"× 门店权重{w:.0%}（客流同比例分摊）"
                ),
                "source": "estimate",
            }
            results.append(rec)
    return results


def estimate_by_retailer(h1_total=None):
    """
    返回零售商级估算（先聚合成零售商，再标估算）。
    用于看板「按零售商」汇总视图。
    """
    if h1_total is None:
        h1_total = _safe(HA_DF_2026["ytd"].get("amount_2026"), 199.2)
    out = []
    for r in RETAILERS:
        share, basis = _retailer_share(r, h1_total)
        out.append({
            "retailer": r["name"],
            "ticker": r.get("ticker"),
            "cooperation": r.get("cooperation"),
            "share_est": share,
            "sales_h1_est": round(h1_total * share, 3),
            "is_estimate": True,
            "method": f"{basis} = H1全省{h1_total}亿 × 零售商占比{share:.0%}",
            "source": "estimate",
            "stores": len(r.get("stores", [])),
        })
    return out


if __name__ == "__main__":
    # 自检：打印门店级估算，确认标注与数值合理
    rows = estimate_store_sales()
    print(f"门店级估算共 {len(rows)} 条，全部 is_estimate={all(x['is_estimate'] for x in rows)}")
    for x in rows:
        print(f"  {x['retailer']} / {x['store']}: "
              f"销售{x['sales_h1_est']}亿 客流{x['pax_h1_est']}万 | {x['method']}")
