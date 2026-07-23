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
 3. 第二层：零售商内按各门店 weight 分摊到门店（销售额）。
 4. 客单价差异化（核心修正）：各店客单价不再等于全省均值，而是
    「全省客单价 × 业态系数 × 零售商系数」。
    - 业态：离岛免税城(旗舰/度假客，客单高) > 离岛免税店(基准) > 机场/线上(过境/高频小客单)
    - 零售商：中免(品牌最全/高端) > 王府井/海控 > 海旅/深免/中服(折扣驱动，客单偏低)
 5. 客流：由「销售 ÷ 客单价」反推各店客流，再归一化使全省客流合计 = h1_pax（总量守恒，仅 redistributive）。
    这样各店客单价出现合理差异，而非千篇一律的全省均值。

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

# ============================================================
# 代理假设：各门店客单价相对「全省均价」的修正系数
# 全省均价 = h1_total × 10000 ÷ h1_pax（锚点，约 7,130 元/人）
# 各店客单价 = 全省均价 × 业态系数 × 零售商系数（均为代理假设，已写入 method）
# 取值依据：业态（旗舰度假客 vs 机场过境 vs 线上高频）、零售商定位（高端 vs 折扣）
# ============================================================
STORE_TYPE_AOV_FACTOR = {
    "离岛免税城": 1.30,   # 旗舰/度假客，客单最高
    "离岛免税店": 1.00,   # 基准
    "机场免税店": 0.70,   # 过境客，小客单/冲动型
    "线上免税": 0.75,     # 高频但客单偏低
}
RETAILER_AOV_FACTOR = {
    "cdfg": 1.15,         # 中免：品牌最全、高端定位
    "wangfujing": 0.95,   # 王府井：万宁单体，定位中上
    "hk_global": 0.90,    # 海控全球精品
    "hlt": 0.80,          # 海旅：折扣驱动，客单偏低
    "sz_mian": 0.85,      # 深免
    "zhongfu": 0.85,      # 中服
}

# 看板展示用的强提醒文案
ESTIMATE_BADGE = "估算"
ESTIMATE_DISCLAIMER = (
    "门店级销售/客流为代理估算值（以全省公开总量按零售商占比与门店权重分摊），"
    "客单价再按「业态 × 零售商定位」做差异化代理（非逐店实测）。"
    "仅供趋势参考，请勿用于精确决策。"
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

    # 全省均价（锚点）：销售(亿)×10000 ÷ 客流(万) = 元/人
    base_aov = (h1_total * 10000.0 / h1_pax) if h1_pax else 0.0

    results = []
    for r in RETAILERS:
        share, basis = _retailer_share(r, h1_total)
        r_total = h1_total * share
        stores = r.get("stores", [])
        wsum = sum(_safe(s.get("weight")) for s in stores) or 1.0
        for s in stores:
            w = _safe(s.get("weight")) / wsum
            sales = round(r_total * w, 3)
            # —— 客单价差异化（核心修复：旧版 pax 与 sales 等比，导致客单恒等于全省均值）——
            t_factor = STORE_TYPE_AOV_FACTOR.get(s.get("type"), 1.0)
            r_factor = RETAILER_AOV_FACTOR.get(r["id"], 1.0)
            aov_factor = t_factor * r_factor
            store_aov = base_aov * aov_factor
            # 先按「销售 ÷ 客单价」反推原始客流，循环后统一归一化到全省总量
            pax_raw = (sales * 10000.0 / store_aov) if store_aov else 0.0
            rec = {
                "retailer": r["name"],
                "store": s["name"],
                "city": s.get("city"),
                "type": s.get("type"),
                "sales_h1_est": sales,
                "pax_h1_est": pax_raw,   # 暂存，循环后归一化
                "is_estimate": True,
                "method": (
                    f"{basis} = H1全省{h1_total}亿 × 零售商占比{share:.0%} × 门店权重{w:.0%}；"
                    f"客单价 = 全省{base_aov:,.0f}元 × 业态{t_factor:.2f} × 零售商{r_factor:.2f} "
                    f"= {store_aov:,.0f}元（反推客流，全省归一）"
                ),
                "source": "estimate",
            }
            results.append(rec)

    # —— 客流归一化：保持全省客流合计 = h1_pax（总量守恒），仅 redistributive ——
    # 各店相对客单差异（aov_factor）经此保持完全不变，仅整体水平回锚到全省均值。
    _pax_sum = sum(x["pax_h1_est"] for x in results) or 1.0
    _scale = h1_pax / _pax_sum
    for x in results:
        x["pax_h1_est"] = round(x["pax_h1_est"] * _scale, 2)
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
