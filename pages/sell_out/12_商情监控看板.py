# -*- coding: utf-8 -*-
"""
海南免税 商情监控看板（门店级代理估算） v1.6
============================================
定位: 在「零售商 — 门店」维度展示海南离岛免税商情。

⚠️ 核心合规要求（来自 MAX）:
  1. 门店级销售/客流全部为【代理估算值】，必须带「估算」角标，禁止误判为实测。
  2. 各零售商均为合作方（COOPERATION_ALL = 合作），尽量列详细。
  3. 估算方法透明可追溯（每条记录带 method 字段，看板内可展开查看）。

v1.6 新增（2026-07-22）：
  - 💎 战略洞察（管理层 1 页纸速读）：30 秒看懂三大机会/风险/资源投放
  - 📈 增长归因分解：18.8% 增长拆到客流/件单价/客单价三端
  - 🎯 客单×客流 战略矩阵（BCG 2x2）：每家门店定位到 4 象限
  - ⚖️ Top vs Bottom 诊断：头部 3 vs 尾部 3 多维度对比
  - 💼 单店盈亏模型：用户可调成本参数，输出盈亏差距
  - 🚀 情景模拟：乐观/基准/悲观三档，输出各维度销售
  - 🛡️ 风险评分卡：4 维度综合评分 + 雷达 + 优先级

防御性设计: 模块导入/计算失败只影响本页，弹友好提示，不连累 app.py 导航整站。
"""

import streamlit as st
from datetime import datetime

st.set_page_config(page_title="免税商情看板", page_icon="📊", layout="wide")

# ============================================================
# 防御性导入（任何失败只影响本页）
# ============================================================
try:
    from utils.hainan_2026_data import HA_DF_2026, SOURCE_NOTE
    from utils.hainan_retailers import (
        RETAILERS, iter_stores, store_count, COOPERATION_ALL,
    )
    from utils.hainan_estimator import (
        estimate_store_sales, estimate_by_retailer,
        ESTIMATE_BADGE, ESTIMATE_DISCLAIMER, RETAILER_SHARE,
    )
    from utils.news_analyzer import (
        fetch_news_cached, analyze_news_for_context, render_insight_markdown,
    )
    _IMPORT_OK = True
    _IMPORT_ERR = ""
except Exception as _e:  # 非裸 except，明确捕获
    _IMPORT_OK = False
    _IMPORT_ERR = str(_e)

st.title("📊 海南免税商情监控看板")
st.caption("零售商 / 门店维度 · 门店级为代理估算 · v1.6")

if not _IMPORT_OK:
    st.error(
        f"⚠️ 数据模块加载失败，本页无法显示（不影响其他页面）：{_IMPORT_ERR}\n"
        f"请检查 utils/hainan_estimator.py、hainan_retailers.py、hainan_2026_data.py 是否存在。"
    )
    st.stop()


# ============================================================
# 新闻自动分析（防御性：失败不影响主看板）
# ============================================================
try:
    _news_data = fetch_news_cached()
    _all_news = []
    for k in ["airport_news", "duty_free_news", "li_island_news", "policy_news", "travel_news"]:
        items = _news_data.get(k, [])
        for item in items:
            if isinstance(item, (tuple, list)):
                if len(item) >= 2:
                    _all_news.append((item[0], item[1]))
                else:
                    _all_news.append((str(item[0]), ""))
            else:
                _all_news.append((str(item), ""))
except Exception as _ne:
    _all_news = []
    st.caption(f"📰 新闻加载失败，自动备注暂不可用：{_ne}")


def show_insight(context, max_bullets=3):
    """在模块下方渲染新闻自动分析备注（基于官方 H1 指标做量化交叉验证）。"""
    try:
        if not _all_news:
            return
        bullets = analyze_news_for_context(
            _all_news, context, max_bullets=max_bullets, metrics=HAINAN_METRICS
        )
        st.markdown(render_insight_markdown(bullets))
    except Exception as e:
        st.caption(f"🤖 新闻备注生成失败：{e}")


# ============================================================
# 小工具：角标 + 估算强提醒
# ============================================================
def est_badge():
    """返回「估算」角标 HTML（门店级数值一律带它）。"""
    return (
        f'<span style="background:#d97706;color:#fff;padding:1px 8px;'
        f'border-radius:10px;font-size:12px;font-weight:600;">{ESTIMATE_BADGE}</span>'
    )


# ============================================================
# 顶部：全省官方大盘（这些是实测，非估算）
# ============================================================
ytd = HA_DF_2026["ytd"]
HAINAN_METRICS = {
    "h1_amount": float(ytd["amount_2026"]),
    "h1_pax": float(ytd["pax_2026"]),
    "h1_pieces": float(ytd["pieces_2026"]),
    "h1_months": 6,
    "amt_yoy": float(ytd["amt_yoy"]),
    "pax_yoy": float(ytd["pax_yoy"]),
    "pc_yoy": float(ytd["pc_yoy"]),
}
st.subheader("📌 全省大盘（官方口径 · 海口海关）")
c1, c2, c3 = st.columns(3)
c1.metric("H1 销售额", f"{ytd['amount_2026']} 亿", f"{ytd['amt_yoy']}% YoY",
          help=f"官方来源：{ytd['source']}")
c2.metric("H1 客流", f"{ytd['pax_2026']} 万人次", f"{ytd['pax_yoy']}% YoY",
          help="官方·海口海关")
c3.metric("H1 件数", f"{ytd['pieces_2026']} 万件", f"{ytd['pc_yoy']}% YoY",
          help="官方·海口海关")

# 门店级估算强提醒（MAX 重点要求）
st.warning(ESTIMATE_DISCLAIMER, icon="⚠️")
show_insight("hainan_overview", max_bullets=3)


# ============================================================
# 锚点调整（可选）：默认取官方 199.2 亿；改动按比例重算，仍为估算
# ============================================================
with st.expander("🔧 调整估算锚点（可选）", expanded=False):
    st.markdown(
        "门店级估算 = 锚点全省总量 × 零售商占比 × 门店权重。默认锚点取海口海关官方 "
        f"**{ytd['amount_2026']} 亿 / {ytd['pax_2026']} 万人次**。改动后按比例重算，"
        "**结果仍全部为估算值**，请勿当作实测。"
    )
    col_a, col_b = st.columns(2)
    h1_total = col_a.number_input(
        "H1 全省销售额（亿元）", value=float(ytd["amount_2026"]),
        min_value=1.0, step=1.0, key="h1_total",
        help="下限 1 亿：设为 0 会让所有门店估算归零，导致分层/集中度等分析无法计算",
    )
    h1_pax = col_b.number_input(
        "H1 全省客流（万人次）", value=float(ytd["pax_2026"]),
        min_value=1.0, step=1.0, key="h1_pax",
        help="下限 1 万人次：设为 0 同样会让估算失效",
    )

stores = estimate_store_sales(h1_total=h1_total, h1_pax=h1_pax)
retailers_est = estimate_by_retailer(h1_total=h1_total)


# ============================================================
# 📊 深度分析：基于门店估算的辅助业务判断（v1.5 新增）
# ============================================================
st.markdown("---")
st.subheader("📊 深度分析（基于门店估算 · 辅助业务判断）")
st.caption(
    "本节以「门店级为代理估算」为前提，从 6 个业务视角回答："
    "**哪家店是核心？哪类门店最赚钱？哪里有风险？下一步该投什么？** "
    "所有结论仍需结合合作方实际口径校准。"
)

import pandas as pd
import numpy as np

# ---------- 数据准备 ----------
df = pd.DataFrame(stores)
df["客单价(元/人)"] = np.where(
    df["pax_h1_est"] > 0,
    (df["sales_h1_est"] * 10000 / df["pax_h1_est"]).round(0),
    np.nan,
)
total_sales = float(df["sales_h1_est"].sum())
total_pax = float(df["pax_h1_est"].sum())
overall_aov = (total_sales * 10000 / total_pax) if total_pax else 0
median_aov = float(df["客单价(元/人)"].median())

# 排序 / 累计占比
df_sorted = df.sort_values("sales_h1_est", ascending=False).reset_index(drop=True)
df_sorted["累计销售(亿)"] = df_sorted["sales_h1_est"].cumsum().round(2)
df_sorted["累计占比%"] = (df_sorted["累计销售(亿)"] / total_sales * 100).round(1)
p80_count = int((df_sorted["累计占比%"] < 80).sum() + 1)
p80_pct_stores = p80_count / len(df_sorted) * 100

# 零售商集中度
retailer_sales = df.groupby("retailer")["sales_h1_est"].sum().sort_values(ascending=False)
shares = retailer_sales / total_sales * 100
hhi = float((shares ** 2).sum())
top1_share = float(shares.iloc[0])

# 城市聚合
city_df = df.groupby("city").agg(
    销售额=("sales_h1_est", "sum"),
    客流=("pax_h1_est", "sum"),
    店数=("store", "count"),
).reset_index()
city_df["占比%"] = (city_df["销售额"] / total_sales * 100).round(1)
city_df["客单价(元/人)"] = np.where(
    city_df["客流"] > 0,
    (city_df["销售额"] * 10000 / city_df["客流"]).round(0),
    np.nan,
)
city_df = city_df.sort_values("销售额", ascending=False).reset_index(drop=True)

# 业态聚合
type_df = df.groupby("type").agg(
    销售额=("sales_h1_est", "sum"),
    客流=("pax_h1_est", "sum"),
    店数=("store", "count"),
).reset_index()
type_df["占比%"] = (type_df["销售额"] / total_sales * 100).round(1)
type_df = type_df.sort_values("销售额", ascending=False).reset_index(drop=True)

# 异常门店（客单价偏离中位数）
df["客单vs中位%"] = np.where(
    df["客单价(元/人)"].isna(), np.nan,
    (df["客单价(元/人)"] / median_aov * 100).round(0),
)
high_aov = df[(df["客单价(元/人)"].notna()) & (df["客单价(元/人)"] > median_aov * 1.5)]
low_aov = df[(df["客单价(元/人)"].notna()) & (df["客单价(元/人)"] < median_aov * 0.5)]

# 线上渗透
online_pct = float(type_df[type_df["type"].str.contains("线上", na=False)]["占比%"].sum())

# 成熟度
_store_open = {s["name"]: s.get("opened") for r in RETAILERS for s in r.get("stores", [])}
df["开业年"] = df["store"].map(_store_open).astype(str)


def _year_bucket(y):
    # 防御：opened 可能缺失 → map 出 None/NaN；先统一转字符串再判断
    try:
        y = str(y).strip()
    except (TypeError, ValueError):
        return "未披露"
    if y in ("nan", "None", "", "—"):
        return "未披露"
    return y.split("-")[0]


df["开业年组"] = df["开业年"].apply(_year_bucket)
mat_df = df.groupby("开业年组").agg(
    店数=("store", "count"),
    销售额=("sales_h1_est", "sum"),
    客流=("pax_h1_est", "sum"),
).reset_index()
mat_df["店均销售(亿)"] = (mat_df["销售额"] / mat_df["店数"]).round(2)
mat_df = mat_df.sort_values("开业年组", ascending=False).reset_index(drop=True)

# 分层（按销售降序的 33/33/34 分位）；防御：销售全相同时(锚点过小)qcut 会报错
try:
    df_sorted["tier"] = pd.qcut(
        df_sorted["sales_h1_est"], q=[0, 0.34, 0.67, 1.0],
        labels=["C 尾段", "B 中段", "A 头部"], duplicates="drop",
    )
except (ValueError, IndexError):
    # 退化情况：所有门店估算相同 → 统一归入中段，避免崩溃
    df_sorted["tier"] = "B 中段"
tier_summary = df_sorted.groupby("tier", observed=False).agg(
    店数=("store", "count"),
    销售额=("sales_h1_est", "sum"),
    客流=("pax_h1_est", "sum"),
).reset_index()
tier_summary["销售占比%"] = (tier_summary["销售额"] / total_sales * 100).round(1)
tier_summary["店均销售(亿)"] = (tier_summary["销售额"] / tier_summary["店数"]).round(2)
tier_summary["店均客流(万)"] = (tier_summary["客流"] / tier_summary["店数"]).round(1)
tier_summary["销售额"] = tier_summary["销售额"].round(2)
tier_summary["客流"] = tier_summary["客流"].round(1)

def _tier_val(tier_name, col, default=0.0):
    """安全取某 tier 的字段值；退化情况(如锚点=0 导致只有单一档)下返回 default。"""
    _sub = tier_summary[tier_summary["tier"] == tier_name]
    if len(_sub) == 0:
        return default
    return float(_sub[col].iloc[0])

# C 尾段指标（提前定义，供后续「关键发现 / 战略洞察 / 风险评分卡」复用）
_tc_share = _tier_val("C 尾段", "销售占比%", 0.0)
_tc_count = int(_tier_val("C 尾段", "店数", 0))

# ---------- 关键发现（自动提炼）----------
st.markdown("##### 🎯 关键发现（自动从数据提炼）")
_findings = []

if p80_pct_stores < 30:
    _findings.append(("🔴",
        f"**头部高度集中**：仅 {p80_count} 家门店（{p80_pct_stores:.0f}%）"
        f"贡献 80% 销售，剩余 {len(df_sorted) - p80_count} 家仅分 20%，长尾生存压力较大"))
elif p80_pct_stores < 50:
    _findings.append(("🟡",
        f"**头部较集中**：{p80_count} 家门店（{p80_pct_stores:.0f}%）"
        f"贡献 80% 销售，结构合理但仍可优化"))
else:
    _findings.append(("🟢",
        f"**集中度合理**：{p80_count} 家门店（{p80_pct_stores:.0f}%）"
        f"贡献 80% 销售，长尾门店各有价值"))

if hhi >= 5000:
    _hhi_lbl, _hhi_emoji = "极高（垄断风险）", "🔴"
elif hhi >= 2500:
    _hhi_lbl, _hhi_emoji = "高度集中", "🟠"
elif hhi >= 1500:
    _hhi_lbl, _hhi_emoji = "中度集中", "🟡"
else:
    _hhi_lbl, _hhi_emoji = "竞争性", "🟢"
_findings.append((_hhi_emoji,
    f"**零售商 HHI = {hhi:.0f}**（{_hhi_lbl}），中免独占 {top1_share:.1f}%；"
    f"Top 3 累计 {shares.head(3).sum():.1f}%"))

_top_city = city_df.iloc[0]
_city_emoji = "🟢" if _top_city["占比%"] < 50 else ("🟡" if _top_city["占比%"] < 70 else "🔴")
_findings.append((_city_emoji,
    f"**{_top_city['city']}** 为核心市场：销售额 {_top_city['销售额']:.1f} 亿"
    f"（占 {_top_city['占比%']:.1f}%），店均 {_top_city['销售额'] / _top_city['店数']:.1f} 亿"))

if online_pct > 0:
    _onl_emoji = "🟡" if online_pct < 30 else "🟢"
    _findings.append((_onl_emoji,
        f"**线上渗透率 {online_pct:.1f}%**；封关后线上品类扩容"
        f"（茶叶/乐器/数码等）值得跟踪"))

if len(high_aov) > 0 or len(low_aov) > 0:
    _h_str = "、".join(high_aov["store"].tolist()[:3]) if len(high_aov) else "无"
    _l_str = "、".join(low_aov["store"].tolist()[:3]) if len(low_aov) else "无"
    _findings.append(("🟠",
        f"**客单异常**：{len(high_aov)} 家高于中位数 1.5×（{_h_str}），"
        f"{len(low_aov)} 家低于 50%（{_l_str}），需逐一诊断"))

for _em, _tx in _findings:
    st.markdown(f"- {_em} {_tx}")

# ============================================================
# 💎 战略洞察（管理层 1 页纸速读）v1.6 新增
# ============================================================
# 设计目标：用 30 秒回答三个业务问题——
#   1) 钱从哪里来？（结构）
#   2) 风险在哪里？（集中度+异常+长尾）
#   3) 下一步投什么？（按 ROI 排序的行动建议）
# 全部由数据自动生成，结论与下方 Tabs/建议保持一致。
# ============================================================
st.markdown("---")
st.markdown("##### 💎 战略洞察（管理层 1 页纸速读）")
st.caption(
    "⏱️ **30 秒速读**：用 3 句话回答业务三大问题。结论由下方全部 Tabs 自动汇总，"
    "如需深挖请展开对应 Tab。"
)

# 计算客单价 YoY (用乘法分解：amt_yoy = (1+pax_yoy)*(1+aov_yoy)-1)
amt_yoy = HAINAN_METRICS["amt_yoy"]
pax_yoy = HAINAN_METRICS["pax_yoy"]
pc_yoy = HAINAN_METRICS["pc_yoy"]
aov_yoy = ((1 + amt_yoy / 100) / (1 + pax_yoy / 100) - 1) * 100

# ---- 三大机会 (按潜在影响排序) ----
_opps = []
_a_n = int(_tier_val("A 头部", "店数", 0))
_a_s = _tier_val("A 头部", "销售占比%", 0.0)
_opps.append(
    f"🏆 **头部样板可复制**：A 头部 {_a_n} 家门店以 {p80_pct_stores:.0f}% 门店数贡献 {_a_s:.1f}% 销售；"
    f"成功要素（选址/品类/客群）需复盘，若下沉到 B 段可拉动大盘 +5-8%"
)
_opps.append(
    f"💎 **客单价提升空间**：增长 {amt_yoy:+.1f}% 中，客单价仅贡献 {aov_yoy:+.1f}%、"
    f"客流贡献 {pax_yoy:+.1f}%。对标韩国免税（客单价 1500-2000 元），"
    f"当前估算 {overall_aov:,.0f} 元仍有 20-30% 提升空间"
)
if online_pct > 0:
    if online_pct < 30:
        _opps.append(
            f"💻 **线上渗透待加强**：当前仅 {online_pct:.1f}%（cdf 中免海南官方商城为主），"
            f"封关后品类扩容（茶叶/乐器/数码）为新增长点"
        )
    else:
        _opps.append(
            f"💻 **线上已较成熟**（{online_pct:.1f}%）：重点是提升复购率与客单价，"
            f"而非继续铺用户"
        )

# ---- 三大风险 (按紧迫度排序) ----
_risks = []
if hhi >= 5000:
    _risks.append(
        f"🔴 **极高集中度**：中免独占 {top1_share:.1f}%、HHI={hhi:.0f}，"
        f"任何政策/经营/口碑风险将直接冲击大盘"
    )
elif hhi >= 2500:
    _risks.append(
        f"🟠 **高集中度**：中免 {top1_share:.1f}%、HHI={hhi:.0f}，"
        f"建议推动二线零售商占比从 {shares.iloc[2:].sum():.1f}% 提升至 15%+"
    )
elif hhi >= 1500:
    _risks.append(
        f"🟡 **中度集中**：HHI={hhi:.0f}，中免仍为主导，"
        f"持续观察王府井/海控实际经营"
    )
else:
    _risks.append(f"🟢 集中度合理（HHI={hhi:.0f}）")

if _tc_count >= 2 and _tc_share < 15:
    _risks.append(
        f"🟠 **长尾效率低**：C 尾段 {_tc_count} 家仅贡献 {_tc_share:.1f}%，"
        f"可能存在资源稀释（人员/库存/营销摊销）"
    )

if len(high_aov) + len(low_aov) >= 2:
    _risks.append(
        f"🟡 **客单异常**：{len(high_aov) + len(low_aov)} 家门店客单偏离中位数 ±50%，"
        f"需排除「估算偏差」后再下定论"
    )

# 数据校准风险（始终提示）
_risks.append(
    f"⚪ **数据校准**：当前为 RETAILER_SHARE 代理假设；"
    f"王府井 Q1=1.39 亿 vs 当前 H1 估算 5.98 亿存 1 倍偏差，"
    f"建议尽快与各合作方核对实际口径"
)

# ---- 渲染 2 列 ----
_co1, _co2 = st.columns(2)
with _co1:
    st.markdown("**🟢 三大机会（按潜在影响排序）**")
    for _o in _opps:
        st.markdown(f"- {_o}")
with _co2:
    st.markdown("**🔴 三大风险（按紧迫度排序）**")
    for _r in _risks[:3]:  # 三大风险
        st.markdown(f"- {_r}")

# ---- 资源投放建议（按 ROI 排序）----
st.markdown("**🎯 资源投放建议（按 ROI 排序）**")
_inv = []
if hhi >= 2500:
    _inv.append(
        f"1️⃣ **【最高优先】降低单点依赖**：与王府井/海控核对实际 Q2 销售，"
        f"校准 RETAILER_SHARE；推动 2-3 家二线零售商占比从 {shares.iloc[2:].sum():.1f}% 提至 15%+，"
        f"3 年内 HHI 降至 2500 以下"
    )
if _a_n >= 2:
    _inv.append(
        f"2️⃣ **【高优先】复制头部 {_a_n} 家成功要素**：识别其品类组合、客群结构、营销动作，"
        f"形成可复制的「样板手册」"
    )
if online_pct < 30 and online_pct > 0:
    _inv.append(
        f"3️⃣ **【中优先】加大线上投入**：当前渗透 {online_pct:.1f}%，"
        f"对接 cdf 海南线上团队评估 SKU 深度与价格力，"
        f"承接封关后品类扩容红利"
    )
if _tc_count >= 2 and _tc_share < 15:
    _inv.append(
        f"4️⃣ **【中优先】整改长尾 {_tc_count} 家**：18 个月未达标的门店启动「关停/合并/转型」评估，"
        f"避免资源持续稀释"
    )
_inv.append(
    "5️⃣ **【长期】建立数据共享机制**：与合作方签订月度对账协议，"
    "用实测替代代理假设，从根上解决数据偏差"
)
for _i in _inv:
    st.markdown(f"- {_i}")

# ---- 信心水平提示 ----
_conf = (
    f"📊 **信心水平**：本节结论建立在 12 家门店代理估算上，"
    f"其中 {p80_count} 家头部贡献 80% 销售、信心较高；"
    f"长尾 {len(df_sorted) - p80_count} 家及客单异常门店结论置信度较低，"
    f"需以实际口径校准后再下最终决策"
)
st.caption(_conf)


# ============================================================
# 📈 增长归因分解（18.8% 增长来自哪里？）v1.6 新增
# ============================================================
# 经典归因：销售额 = 客流量 × 客单价 × 件单价
# 把 18.8% 增长拆到三端，识别核心驱动
# ============================================================
st.markdown("---")
st.markdown("##### 📈 增长归因分解（增长由谁驱动？）")
st.caption(
    "经典乘法分解：**销售额 = 客流量 × 客单价 × 件单价**。"
    f"把 H1 销售 YoY ({amt_yoy:+.1f}%) 拆到三端，识别核心驱动。"
)

# 件单价 YoY = (1+amt_yoy)/(1+pc_yoy) - 1  → 注意：件是件数不是"单件"概念
# 严格地说件数 = 客流 × 件/人，所以件数 YoY = 客流 YoY × 件/人 YoY
# 件/人 YoY = (1+pc_yoy)/(1+pax_yoy) - 1
pieces_per_pax_yoy = ((1 + pc_yoy / 100) / (1 + pax_yoy / 100) - 1) * 100 if pax_yoy > -100 else 0

# 用对数加法分解（更准确）: ln(1+r_total) ≈ ln(1+r1) + ln(1+r2) + ln(1+r3)
import math
def _ln_pct(p):
    return math.log(1 + p / 100) if (1 + p / 100) > 0 else 0

_ln_amt = _ln_pct(amt_yoy)
_ln_pax = _ln_pct(pax_yoy)
_ln_aov = _ln_pct(aov_yoy)
_ln_ppp = _ln_pct(pieces_per_pax_yoy)
# 客单价 = 件/人 × 件单价, 所以 aov_yoy ≈ ppp_yoy + unit_price_yoy
# unit_price_yoy = aov_yoy - ppp_yoy (log 减法)
unit_price_yoy = aov_yoy - pieces_per_pax_yoy

# 4 列 metric
_g1, _g2, _g3, _g4 = st.columns(4)
_g1.metric("H1 销售 YoY", f"{amt_yoy:+.1f}%", help="官方·海口海关")
_g2.metric("H1 客流 YoY", f"{pax_yoy:+.1f}%", help="官方·海口海关")
_g3.metric("H1 件数 YoY", f"{pc_yoy:+.1f}%", help="件数 = 客流 × 件/人")
_g4.metric("H1 客单 YoY（推算）", f"{aov_yoy:+.1f}%", help="= (1+amt)/(1+pax)-1")

# 拆解表
_decomp = pd.DataFrame({
    "驱动维度": ["客流量", "件/人", "件单价", "客单价(综合)", "合计"],
    "YoY 增速%": [pax_yoy, pieces_per_pax_yoy, unit_price_yoy, aov_yoy, amt_yoy],
    "对总增长贡献%": [
        _ln_pax / _ln_amt * 100 if _ln_amt else 0,
        _ln_ppp / _ln_amt * 100 if _ln_amt else 0,
        (aov_yoy - pieces_per_pax_yoy) / amt_yoy * 100 if amt_yoy else 0,
        _ln_aov / _ln_amt * 100 if _ln_amt else 0,
        100.0,
    ],
    "驱动类型": ["拉新驱动", "连带驱动", "升级驱动", "—", "—"],
})
_decomp["YoY 增速%"] = _decomp["YoY 增速%"].round(1)
_decomp["对总增长贡献%"] = _decomp["对总增长贡献%"].round(1)
st.dataframe(_decomp, hide_index=True, width='stretch')

# 解读
if aov_yoy < pax_yoy / 2:
    _driver = (
        f"**极度依赖拉新**：增长几乎全靠客流（{pax_yoy:+.1f}%），"
        f"客单价仅 {aov_yoy:+.1f}%。需关注新客质量与复购率，"
        f"避免「拉新-流失」恶性循环"
    )
elif aov_yoy < pax_yoy:
    _driver = (
        f"**增长均衡偏拉新**：客流 {pax_yoy:+.1f}% + 客单 {aov_yoy:+.1f}% 双轮驱动，"
        f"但仍以拉新为主。客单价提升仍有空间"
    )
else:
    _driver = (
        f"**升级驱动**：客单价 {aov_yoy:+.1f}% > 客流 {pax_yoy:+.1f}%，"
        f"品类升级与高端化路径已见效，可继续加码"
    )
st.info(
    f"💡 **解读**：{_driver}。\n\n"
    f"- **件/人 YoY {pieces_per_pax_yoy:+.1f}%**：反映连带率（每位顾客买几件），"
    f"正数表示顾客买更多，负数表示聚焦爆品\n"
    f"- **件单价 YoY {unit_price_yoy:+.1f}%**：反映产品结构升级，"
    f"正数表示单件价格更高，品类向高端迁移",
    icon="💡",
)


_tabs = st.tabs([
    "🏆 80/20 与分层",
    "🎯 客单×客流矩阵",      # v1.6 新增：BCG 风格 2x2 战略矩阵
    "🏙️ 城市结构",
    "🏬 业态结构",
    "🏢 集中度",
    "⚖️ Top vs Bottom",      # v1.6 新增：头部尾部对比诊断
    "🚨 异常门店",
    "📅 成熟度",
    "💼 单店盈亏模型",        # v1.6 新增：单店模型评估
    "🚀 情景模拟",            # v1.6 新增：乐观/基准/悲观
    "🛡️ 风险评分卡",          # v1.6 新增：综合风险评分
])

with _tabs[0]:
    st.markdown("#### 帕累托分析 · 门店分层")
    st.caption("按销售估算降序排列，识别「少数关键门店」与「长尾门店」。")
    _c1, _c2 = st.columns([3, 2])
    with _c1:
        st.markdown("**📊 门店销售排序**")
        st.bar_chart(df_sorted.set_index("store")["sales_h1_est"])
    with _c2:
        st.markdown("**🏆 分层结果（按销售分位 33/33/34）**")
        st.dataframe(tier_summary, hide_index=True, width='stretch')

    with st.expander("📋 累计占比明细（帕累托）", expanded=False):
        _pp = df_sorted[["store", "retailer", "city", "sales_h1_est",
                          "累计销售(亿)", "累计占比%"]].copy()
        _pp.columns = ["门店", "零售商", "城市", "销售(亿)", "累计销售(亿)", "累计占比%"]
        _pp["销售(亿)"] = _pp["销售(亿)"].round(2)
        st.dataframe(_pp, hide_index=True, width='stretch')

    _a_n = int(_tier_val("A 头部", "店数", 0))
    _a_s = _tier_val("A 头部", "销售占比%", 0.0)
    _c_n = int(_tier_val("C 尾段", "店数", 0))
    _c_s = _tier_val("C 尾段", "销售占比%", 0.0)
    st.info(
        f"💡 **解读**：A 头部 {_a_n} 家承担 {_a_s:.1f}% 销售，C 尾段 {_c_n} 家仅贡献 {_c_s:.1f}%。"
        f"长尾门店需逐家评估：继续投入（品牌曝光/客群补充）vs 整改/退出。",
        icon="💡",
    )

with _tabs[2]:
    st.markdown("#### 城市结构")
    st.caption("按城市聚合，识别核心市场与潜力市场。")
    _cs = city_df.copy()
    _cs["店均销售(亿)"] = (_cs["销售额"] / _cs["店数"]).round(2)
    _cs["销售额"] = _cs["销售额"].round(2)
    _cs["客流"] = _cs["客流"].round(1)
    _cs["客单价(元/人)"] = _cs["客单价(元/人)"].astype("Int64")
    st.dataframe(_cs, hide_index=True, width='stretch')
    st.bar_chart(city_df.set_index("city")["销售额"])

    _top3_share = float(city_df.head(3)["占比%"].sum())
    st.info(
        f"💡 **解读**：{city_df.iloc[0]['city']} / {city_df.iloc[1]['city'] if len(city_df) > 1 else '—'} "
        f"为绝对主力，Top 3 城市累计占 {_top3_share:.1f}%。"
        f"主市场若遇政策/天气/竞品冲击，对大盘影响显著；"
        f"建议每季度跟踪琼海/万宁等潜力城市的开店节奏。",
        icon="💡",
    )

with _tabs[3]:
    st.markdown("#### 业态结构")
    st.caption("按业态（离岛免税城 / 离岛免税店 / 机场免税店 / 线上）聚合，识别高价值渠道。")
    _ts = type_df.copy()
    _ts["店均销售(亿)"] = (_ts["销售额"] / _ts["店数"]).round(2)
    _ts["客单价(元/人)"] = np.where(
        _ts["客流"] > 0,
        (_ts["销售额"] * 10000 / _ts["客流"]).round(0),
        np.nan,
    )
    _ts["销售额"] = _ts["销售额"].round(2)
    _ts["客流"] = _ts["客流"].round(1)
    st.dataframe(_ts, hide_index=True, width='stretch')
    st.bar_chart(type_df.set_index("type")["销售额"])

    _fl = type_df.iloc[0]
    _air = type_df[type_df["type"].str.contains("机场", na=False)]
    _air_n = int(_air["店数"].sum()) if len(_air) else 0
    _air_s = float(_air["销售额"].sum()) if len(_air) else 0
    st.info(
        f"💡 **解读**：{_fl['type']} 是体量担当（{_fl['销售额']:.1f} 亿，店均 "
        f"{_fl['销售额'] / _fl['店数']:.1f} 亿）；"
        f"机场免税店 {_air_n} 家合计 {_air_s:.1f} 亿，**虽规模较小但服务出入境即时客群**，"
        f"是品牌曝光与新客获取的关键节点；"
        f"线上渠道在封关后享受品类扩容红利，建议持续跟踪其客单价与复购率。",
        icon="💡",
    )

with _tabs[4]:
    st.markdown("#### 零售商集中度 · HHI")
    st.caption(
        "**HHI（赫芬达尔-赫希曼指数）** = 各零售商占比平方之和 × 10000。"
        ">5000 极高集中（垄断风险）｜2500-5000 高度集中｜1500-2500 中度集中｜<1500 竞争性"
    )
    _sd = shares.reset_index()
    _sd.columns = ["零售商", "占比%"]
    _sd["销售(亿)"] = _sd["零售商"].map(lambda x: round(retailer_sales[x], 2))
    _sd["累计占比%"] = _sd["占比%"].cumsum().round(1)
    _sd["占比%"] = _sd["占比%"].round(1)
    st.dataframe(_sd, hide_index=True, width='stretch')
    st.bar_chart(_sd.set_index("零售商")["占比%"])

    _m1, _m2, _m3 = st.columns(3)
    _m1.metric("HHI 指数", f"{hhi:.0f}")
    _m2.metric("Top 1 占比", f"{top1_share:.1f}%")
    _m3.metric("Top 3 累计", f"{shares.head(3).sum():.1f}%")

    if hhi >= 5000:
        _risk = "🔴 **极高集中度**：中免一家独大，竞争对手合计不足 10%。任何政策/经营/口碑风险都将直接冲击大盘"
    elif hhi >= 2500:
        _risk = "🟠 **高度集中**：中免占绝对主导，建议持续观察竞争格局变化（王府井实际口径、海控扩张等）"
    elif hhi >= 1500:
        _risk = "🟡 **中度集中**：格局相对合理，但仍以中免为锚"
    else:
        _risk = "🟢 集中度合理"
    st.warning(_risk)

with _tabs[6]:
    st.markdown("#### 异常门店预警")
    st.caption(
        f"客单价中位数 = **{median_aov:,.0f} 元/人**。"
        f"**超过 1.5× = 🟠 高端异常**，**不足 50% = 🔴 低端异常**。"
    )
    _ad = df[["retailer", "store", "city", "type", "sales_h1_est",
               "pax_h1_est", "客单价(元/人)", "客单vs中位%"]].copy()
    _ad["销售(亿)"] = _ad["sales_h1_est"].round(2)
    _ad["客流(万)"] = _ad["pax_h1_est"].round(1)
    _ad["客单价(元/人)"] = _ad["客单价(元/人)"].astype("Int64")
    _ad["客单vs中位%"] = _ad["客单vs中位%"].astype("Int64")
    # 防御：中位数为 NA(如锚点=0 导致客单价全空)时，直接用「—」标注，避免 Int64 NA 比较报错
    if pd.isna(median_aov) or _ad["客单价(元/人)"].notna().sum() == 0:
        _ad["预警"] = "—"
    else:
        _aov_cmp = _ad["客单价(元/人)"].astype("float64")  # 转 float，<NA>→NaN，比较不再 ambiguous
        _ad["预警"] = np.where(
            _aov_cmp.isna(), "—",
            np.where(_aov_cmp > median_aov * 1.5, "🟠 高端异常",
                     np.where(_aov_cmp < median_aov * 0.5, "🔴 低端异常", "✅ 正常")),
        )
    _ad = _ad.sort_values("客单价(元/人)", ascending=False, na_position="last")
    _ad = _ad[["retailer", "store", "city", "type", "销售(亿)", "客流(万)",
                "客单价(元/人)", "客单vs中位%", "预警"]]
    _ad.columns = ["零售商", "门店", "城市", "业态", "销售(亿)", "客流(万)",
                    "客单价(元/人)", "vs中位数%", "预警"]
    st.dataframe(_ad, hide_index=True, width='stretch')

    if len(high_aov) > 0:
        st.markdown("**🟠 高端异常门店**（客单 > 1.5× 中位数）")
        st.markdown("- 可能原因：① 客群结构差异（境外/商务/高端）；② 高客单品类集中（腕表/珠宝/重奢）；"
                    "③ 数据口径差异")
        st.markdown("- **建议**：作奢侈品牌重点投放样板，验证「高端化」路径是否可复制")
    if len(low_aov) > 0:
        st.markdown("**🔴 低端异常门店**（客单 < 50% 中位数）")
        st.markdown("- 可能原因：① 客群偏中端（家庭/学生）；② 价格带覆盖不全；"
                    "③ 体验/服务短板；④ 估算口径偏差")
        st.markdown("- **建议**：抽样 1-2 家做产品组合 + 客群调研；"
                    "若是估算偏差则需校准 `RETAILER_SHARE`")

with _tabs[7]:
    st.markdown("#### 门店成熟度诊断")
    st.caption("按开业年份分组，观察新店爬坡与老店健康度。")
    _ms = mat_df.copy()
    _ms["店均销售(亿)"] = _ms["店均销售(亿)"].round(2)
    _ms["销售额"] = _ms["销售额"].round(2)
    _ms["客流"] = _ms["客流"].round(1)
    st.dataframe(_ms, hide_index=True, width='stretch')

    _with_year = mat_df[~mat_df["开业年组"].isin(["未披露", "nan"])]
    if len(_with_year) >= 2:
        st.bar_chart(_with_year.set_index("开业年组")["店均销售(亿)"])
        _newest = _with_year.iloc[0]
        _oldest = _with_year.iloc[-1]
        st.info(
            f"💡 **解读**：{_newest['开业年组']} 年开业门店（{int(_newest['店数'])} 家）"
            f"店均销售 {_newest['店均销售(亿)']:.2f} 亿；"
            f"{_oldest['开业年组']} 年开业门店（{int(_oldest['店数'])} 家）"
            f"店均销售 {_oldest['店均销售(亿)']:.2f} 亿。"
            f"若新店能在 2-3 年内追平老店，说明模型可复制；反之需复盘选址/招商/运营。",
            icon="💡",
        )
    else:
        st.caption("⚠️ 开业年数据较少，成熟度对比仅供参考。")

# ============================================================
# Tab 2 (v1.6)：客单价 × 客流量 战略矩阵（BCG 风格 2x2）
# ============================================================
with _tabs[1]:
    st.markdown("#### 客单价 × 客流量 战略矩阵")
    st.caption(
        "经典 BCG 矩阵：横轴=客流量（中位数切分）、纵轴=客单价（中位数切分）。"
        "每家门店自动定位到 4 象限，配套战略动作。"
    )

    # 准备矩阵数据
    _matrix_df = df[["retailer", "store", "city", "type",
                      "sales_h1_est", "pax_h1_est", "客单价(元/人)"]].copy()
    _matrix_df = _matrix_df.dropna(subset=["客单价(元/人)", "pax_h1_est"])
    _median_pax = float(_matrix_df["pax_h1_est"].median())
    _median_aov_local = float(_matrix_df["客单价(元/人)"].median())

    # 象限定位
    _matrix_df["客流象限"] = np.where(_matrix_df["pax_h1_est"] >= _median_pax, "高客流", "低客流")
    _matrix_df["客单象限"] = np.where(_matrix_df["客单价(元/人)"] >= _median_aov_local, "高客单", "低客单")
    _matrix_df["象限"] = _matrix_df["客流象限"] + " × " + _matrix_df["客单象限"]

    # 4 象限标签
    _qmap = {
        "高客流 × 高客单": ("🌟 明星门店", "重点维护：保地位、防下滑"),
        "高客流 × 低客单": ("💰 现金牛", "提客单：推套装/升级/连带"),
        "低客流 × 高客单": ("💎 利润门店", "引客流：营销/活动/曝光"),
        "低客流 × 低客单": ("⚠️ 问题门店", "整改/退出：18 个月未达标即淘汰"),
    }
    _matrix_df["定位"] = _matrix_df["象限"].map(lambda x: _qmap[x][0])
    _matrix_df["建议动作"] = _matrix_df["象限"].map(lambda x: _qmap[x][1])

    # 4 列展示每个象限的门店
    _mq1, _mq2 = st.columns(2)
    _mq3, _mq4 = st.columns(2)
    _quad_cols = [_mq1, _mq2, _mq3, _mq4]
    _quad_keys = list(_qmap.keys())

    for _qc, _qk in zip(_quad_cols, _quad_keys):
        _qdf = _matrix_df[_matrix_df["象限"] == _qk]
        _lbl, _act = _qmap[_qk]
        with _qc:
            _q_sales = _qdf["sales_h1_est"].sum()
            _q_pct = _q_sales / total_sales * 100 if total_sales else 0
            st.metric(
                _lbl,
                f"{len(_qdf)} 家 · {_q_sales:.1f} 亿 ({_q_pct:.1f}%)",
            )
            st.caption(f"💡 {_act}")
            if len(_qdf) > 0:
                for _, _r in _qdf.iterrows():
                    st.caption(
                        f"  • **{_r['store']}** — "
                        f"客单 {_r['客单价(元/人)']:,.0f} 元 / 客流 {_r['pax_h1_est']:.0f} 万"
                    )
            else:
                st.caption("  （暂无门店）")

    # 散点图（气泡大小=销售额）
    st.markdown("**📊 散点图（横=客流，纵=客单，气泡=销售额）**")
    _chart = _matrix_df.copy()
    _chart["销售额(亿)"] = _chart["sales_h1_est"]
    _chart["客流(万)"] = _chart["pax_h1_est"]
    _chart["客单价(元/人)"] = _chart["客单价(元/人)"].astype(float)
    # streamlit 原生 scatter 不支持 size，简化用 bar 替代
    _chart_sort = _chart.sort_values("客单价(元/人)", ascending=False)
    st.bar_chart(
        _chart_sort.set_index("store")[["客单价(元/人)", "客流(万)"]],
        height=320,
    )
    st.caption(
        f"参考线：客流中位数 = {_median_pax:.0f} 万 / 客单中位数 = {_median_aov_local:,.0f} 元"
    )

    # 详细表
    with st.expander("📋 完整矩阵明细（含建议动作）", expanded=False):
        _show = _matrix_df[["retailer", "store", "city", "sales_h1_est",
                              "pax_h1_est", "客单价(元/人)", "定位", "建议动作"]].copy()
        _show["sales_h1_est"] = _show["sales_h1_est"].round(2)
        _show["pax_h1_est"] = _show["pax_h1_est"].round(1)
        _show["客单价(元/人)"] = _show["客单价(元/人)"].astype("Int64")
        _show.columns = ["零售商", "门店", "城市", "销售(亿)", "客流(万)",
                          "客单价(元/人)", "定位", "建议动作"]
        st.dataframe(_show, hide_index=True, width='stretch')

    st.info(
        f"💡 **战略总览**：\n"
        f"- 🌟 明星门店 = 重点维护对象，资源优先供给；\n"
        f"- 💰 现金牛 = 大流量低客单，是**提客单**最容易见效的样本；\n"
        f"- 💎 利润门店 = 高端定位但客流不足，**营销/活动**拉客流；\n"
        f"- ⚠️ 问题门店 = 双重劣势，**18 个月未达标即启动退出评估**。",
        icon="💡",
    )


# ============================================================
# Tab 6 (v1.6)：Top vs Bottom 诊断（头部 vs 尾部对比）
# ============================================================
with _tabs[5]:
    st.markdown("#### Top 3 vs Bottom 3 诊断")
    st.caption("头部 3 家 vs 尾部 3 家：多维度对比，识别「头部为什么强」「尾部为什么弱」。")

    # 排序
    _tb = df[["retailer", "store", "city", "type", "sales_h1_est",
                "pax_h1_est", "客单价(元/人)"]].copy()
    _tb = _tb.dropna(subset=["sales_h1_est"]).sort_values("sales_h1_est", ascending=False)
    _top3 = _tb.head(3).copy()
    _bot3 = _tb.tail(3).copy()
    _top3["组别"] = "🟢 Top 3"
    _bot3["组别"] = "🔴 Bottom 3"
    _tb_compare = pd.concat([_top3, _bot3], ignore_index=True)

    # 关键指标对比
    _tk1, _tk2, _tk3, _tk4 = st.columns(4)
    _top3_sales_avg = _top3["sales_h1_est"].mean()
    _bot3_sales_avg = _bot3["sales_h1_est"].mean()
    _top3_pax_avg = _top3["pax_h1_est"].mean()
    _bot3_pax_avg = _bot3["pax_h1_est"].mean()
    _top3_aov = _top3["客单价(元/人)"].mean()
    _bot3_aov = _bot3["客单价(元/人)"].mean()
    _tk1.metric("Top 3 店均销售", f"{_top3_sales_avg:.1f} 亿",
                  f"{(_top3_sales_avg / _bot3_sales_avg - 1) * 100:+.0f}% vs 尾")
    _tk2.metric("Top 3 店均客流", f"{_top3_pax_avg:.0f} 万",
                  f"{(_top3_pax_avg / _bot3_pax_avg - 1) * 100:+.0f}% vs 尾")
    _tk3.metric("Top 3 客单价", f"{_top3_aov:,.0f} 元",
                  f"{(_top3_aov / _bot3_aov - 1) * 100:+.0f}% vs 尾")
    _tk4.metric("销售差距倍数", f"{_top3_sales_avg / _bot3_sales_avg:.1f}×", "")

    st.dataframe(_tb_compare, hide_index=True, width='stretch')

    # 维度对比表（结构性差异）
    st.markdown("**🔍 结构性差异（Top vs Bottom 在 城市/业态/零售商 的分布）**")
    _diff_rows = []
    for _dim, _col in [("城市", "city"), ("业态", "type"), ("零售商", "retailer")]:
        _top_dist = _top3[_col].value_counts().to_dict()
        _bot_dist = _bot3[_col].value_counts().to_dict()
        _all_keys = set(_top_dist) | set(_bot_dist)
        for _k in _all_keys:
            _diff_rows.append({
                "维度": _dim,
                "类别": _k,
                "Top 3 出现次数": _top_dist.get(_k, 0),
                "Bottom 3 出现次数": _bot_dist.get(_k, 0),
            })
    _diff_df = pd.DataFrame(_diff_rows)
    st.dataframe(_diff_df, hide_index=True, width='stretch')

    # 解读
    _top_cities = ", ".join(_top3["city"].unique()[:3])
    _bot_cities = ", ".join(_bot3["city"].unique()[:3])
    st.info(
        f"💡 **诊断**：\n"
        f"- Top 3 主要位于：**{_top_cities}**；Bottom 3 主要位于：**{_bot_cities}**\n"
        f"- 销售差距 **{_top3_sales_avg / _bot3_sales_avg:.1f}×** 主要来自"
        f"客流（{_top3_pax_avg / _bot3_pax_avg:.1f}×）+ 客单（{_top3_aov / _bot3_aov:.1f}×）\n"
        f"- 若 Bottom 3 客单显著偏低：客群匹配度/产品组合问题；"
        f"若客流显著偏低：选址/曝光问题\n"
        f"- **建议**：Top 3 形成「样板手册」（品类组合/营销动作/客群结构），"
        f"下沉到 Bottom 3 整改",
        icon="💡",
    )


# ============================================================
# Tab 9 (v1.6)：单店盈亏模型（粗略估算）
# ============================================================
with _tabs[8]:
    st.markdown("#### 单店盈亏模型（基于假设成本结构）")
    st.caption(
        "**仅供战略参考，非财务核算**。参数可调：调整下方数字即可看各门店盈亏变化。"
    )

    # 假设参数（用户可调）
    _sp1, _sp2, _sp3 = st.columns(3)
    _fc_monthly = _sp1.number_input(
        "月固定成本（万元）", value=120, step=10,
        help="租金 + 人员 + 装修摊销 + 行政等，假设单店 H1 平均",
        key="fc_monthly",
    )
    _vc_rate = _sp2.number_input(
        "变动成本率%", value=12, step=1,
        help="商品成本 + 营销摊销等占销售的比例",
        key="vc_rate",
    ) / 100
    _tm_rate = _sp3.number_input(
        "目标利润率%", value=8, step=1,
        help="希望门店达到的最低利润率",
        key="tm_rate",
    ) / 100

    # 盈亏平衡 H1 销售（半年）= 月固定成本 × 6 / (1 - 变动成本率 - 目标利润率)
    _denom = 1 - _vc_rate - _tm_rate
    if _denom > 0:
        _be_h1_wan = _fc_monthly * 6 / _denom
        _be_h1_yi = _be_h1_wan / 10000
    else:
        _be_h1_yi = float("inf")
        st.error("⚠️ 变动成本率 + 目标利润率 ≥ 100%，参数不合理")

    _bm1, _bm2, _bm3, _bm4 = st.columns(4)
    _bm1.metric("H1 盈亏平衡销售", f"{_be_h1_yi:.2f} 亿")
    _bm2.metric("盈亏平衡客单（按平均客流）",
                  f"{_be_h1_yi * 10000 / (total_pax / len(df)) * len(df) / total_pax:,.0f} 元"
                  if total_pax else "—",
                  help="假设客流与 H1 估算相同，需达到的平均客单价")
    _bm3.metric("H1 估算销售（总）", f"{total_sales:.1f} 亿")
    _bm4.metric("达标门店占比", f"{(df['sales_h1_est'] >= _be_h1_yi).sum() / len(df) * 100:.0f}%"
                  if _be_h1_yi < float("inf") else "—")

    # 各门店盈亏状态
    _store_be = df[["retailer", "store", "city", "type", "sales_h1_est"]].copy()
    _store_be["盈亏平衡(亿)"] = round(_be_h1_yi, 2)
    _store_be["差距(亿)"] = (_store_be["sales_h1_est"] - _be_h1_yi).round(2)
    _store_be["状态"] = np.where(
        _store_be["sales_h1_est"] >= _be_h1_yi * 1.3, "🟢 盈利良好",
        np.where(_store_be["sales_h1_est"] >= _be_h1_yi, "🟡 盈亏边缘",
        np.where(_store_be["sales_h1_est"] >= _be_h1_yi * 0.5, "🟠 需关注",
        "🔴 亏损"))
    )
    _store_be["销售(亿)"] = _store_be["sales_h1_est"].round(2)
    _store_be = _store_be[["retailer", "store", "city", "type",
                            "销售(亿)", "盈亏平衡(亿)", "差距(亿)", "状态"]]
    _store_be.columns = ["零售商", "门店", "城市", "业态",
                          "销售(亿)", "盈亏平衡(亿)", "差距(亿)", "状态"]
    st.dataframe(_store_be, hide_index=True, width='stretch')

    # 解读
    if _be_h1_yi < float("inf"):
        _loss_n = int((df["sales_h1_est"] < _be_h1_yi).sum())
        _warn_n = int(((df["sales_h1_est"] >= _be_h1_yi) &
                        (df["sales_h1_est"] < _be_h1_yi * 1.3)).sum())
        st.info(
            f"💡 **解读**：当前假设下，🔴 亏损 {_loss_n} 家、🟠 需关注 {int((df['sales_h1_est'] < _be_h1_yi * 0.5).sum())} 家、"
            f"🟡 盈亏边缘 {_warn_n} 家。\n\n"
            f"**行动建议**：\n"
            f"- 🔴 亏损店：18 个月内未扭亏即启动「关停/合并/转型」评估；\n"
            f"- 🟠 需关注店：抽样 1-2 家做产品组合 + 客群调研，识别拖累原因；\n"
            f"- 🟡 盈亏边缘店：若 H2 旺季无法提升 30%，转评估对象；\n"
            f"- 🟢 盈利良好店：作为样板，研究其单店模型作为新店参考。",
            icon="💡",
        )
    st.caption(
        "⚠️ **说明**：参数为行业典型值估算，非各店真实成本。"
        "建议与财务核对实际单店成本结构后调整参数。"
    )


# ============================================================
# Tab 10 (v1.6)：情景模拟（乐观 / 基准 / 悲观）
# ============================================================
with _tabs[9]:
    st.markdown("#### 情景模拟（乐观 / 基准 / 悲观）")
    st.caption(
        "调整三档情景的全省销售变化，查看各零售商/城市/业态在不同情景下的表现，"
        "辅助 H2 备货与资源规划。"
    )

    # 三档情景滑块
    _sc1, _sc2, _sc3 = st.columns(3)
    _opt_pct = _sc1.slider("🟢 乐观情景 YoY %", -30, 30, 10, key="opt_pct") / 100
    _base_pct = _sc2.slider("🟡 基准情景 YoY %", -30, 30, 0, key="base_pct") / 100
    _pess_pct = _sc3.slider("🔴 悲观情景 YoY %", -30, 30, -10, key="pess_pct") / 100

    _scenarios = {
        "🟢 乐观": 1 + _opt_pct,
        "🟡 基准": 1 + _base_pct,
        "🔴 悲观": 1 + _pess_pct,
    }

    # 全省总量
    _st1, _st2, _st3 = st.columns(3)
    _st1.metric("🟢 乐观情景 H1 销售", f"{total_sales * (1 + _opt_pct):.1f} 亿")
    _st2.metric("🟡 基准情景 H1 销售", f"{total_sales * (1 + _base_pct):.1f} 亿")
    _st3.metric("🔴 悲观情景 H1 销售", f"{total_sales * (1 + _pess_pct):.1f} 亿")

    # 零售商维度
    st.markdown("**🏢 零售商维度（按当前代理占比分摊）**")
    _scen_r = retailer_sales.reset_index()
    _scen_r.columns = ["零售商", "基准销售(亿)"]
    for _sn, _f in _scenarios.items():
        _scen_r[f"{_sn}"] = (_scen_r["基准销售(亿)"] * _f).round(2)
    _scen_r["基准销售(亿)"] = _scen_r["基准销售(亿)"].round(2)
    st.dataframe(_scen_r, hide_index=True, width='stretch')

    # 城市维度
    st.markdown("**🏙️ 城市维度**")
    _scen_c = city_df[["city", "销售额"]].copy()
    _scen_c.columns = ["城市", "基准销售(亿)"]
    for _sn, _f in _scenarios.items():
        _scen_c[f"{_sn}"] = (_scen_c["基准销售(亿)"] * _f).round(2)
    _scen_c["基准销售(亿)"] = _scen_c["基准销售(亿)"].round(2)
    st.dataframe(_scen_c, hide_index=True, width='stretch')

    # 业态维度
    st.markdown("**🏬 业态维度**")
    _scen_t = type_df[["type", "销售额"]].copy()
    _scen_t.columns = ["业态", "基准销售(亿)"]
    for _sn, _f in _scenarios.items():
        _scen_t[f"{_sn}"] = (_scen_t["基准销售(亿)"] * _f).round(2)
    _scen_t["基准销售(亿)"] = _scen_t["基准销售(亿)"].round(2)
    st.dataframe(_scen_t, hide_index=True, width='stretch')

    # 解读
    _delta_opt_pess = (_opt_pct - _pess_pct) * 100
    _total_opt = total_sales * (1 + _opt_pct)
    _total_pess = total_sales * (1 + _pess_pct)
    st.info(
        f"💡 **解读**：乐观 ↔ 悲观 全省差额 **{_delta_opt_pess:.0f}%**（{abs(_total_opt - _total_pess):.1f} 亿）。\n\n"
        f"- **主力零售商承压最大**：中免独占 {top1_share:.1f}%，"
        f"情景下行的 {_total_pess * top1_share / 100:.1f} 亿（vs 基准 {total_sales * top1_share / 100:.1f} 亿）"
        f"将主要由中免承担；\n"
        f"- **二线零售商机会**：悲观情景下中免压力更大，"
        f"王府井/海控若能保持份额相对稳定，**实际占比反而上升**；\n"
        f"- **H2 备货建议**：按悲观情景作为下限，乐观情景作为目标上限，"
        f"中位线 = 基准情景。",
        icon="💡",
    )


# ============================================================
# Tab 11 (v1.6)：风险评分卡（综合风险评估）
# ============================================================
with _tabs[10]:
    st.markdown("#### 风险评分卡（综合风险评估）")
    st.caption(
        "从 4 个维度量化风险：集中度 / 头部门店 / 长尾 / 数据校准。"
        "每维度 0-100 分，分数越高 = 风险越大。"
    )

    # 计算 4 个维度风险分
    # 1) 集中度风险 (基于 HHI)
    if hhi >= 5000:
        _r_conc = 90
    elif hhi >= 2500:
        _r_conc = 70
    elif hhi >= 1500:
        _r_conc = 50
    else:
        _r_conc = 25

    # 2) 头部门店风险 (Top 1 门店占比)
    _top1_store = df_sorted.iloc[0]
    _top1_store_pct = _top1_store["sales_h1_est"] / total_sales * 100
    if _top1_store_pct >= 25:
        _r_top1 = 80
    elif _top1_store_pct >= 18:
        _r_top1 = 60
    elif _top1_store_pct >= 10:
        _r_top1 = 40
    else:
        _r_top1 = 20

    # 3) 长尾风险 (C 尾段门店占比)
    if _tc_count >= 4 and _tc_share < 15:
        _r_tail = 75
    elif _tc_count >= 2 and _tc_share < 20:
        _r_tail = 55
    elif _tc_count >= 1:
        _r_tail = 30
    else:
        _r_tail = 10

    # 4) 数据校准风险 (王府井 Q1 偏差 + 客单异常数量)
    _wj_q1_actual = 1.39
    _wj_h1_est = total_sales * RETAILER_SHARE.get("wangfujing", 0.03)
    _wj_bias_ratio = abs(_wj_h1_est - _wj_q1_actual * 2) / (_wj_q1_actual * 2) * 100 \
        if _wj_q1_actual else 0
    if _wj_bias_ratio >= 80:
        _r_data = 85
    elif _wj_bias_ratio >= 50:
        _r_data = 65
    elif _wj_bias_ratio >= 30:
        _r_data = 45
    else:
        _r_data = 25

    # 综合风险 = 4 项加权
    _r_total = round(_r_conc * 0.35 + _r_top1 * 0.20 + _r_tail * 0.20 + _r_data * 0.25, 0)
    if _r_total >= 75:
        _r_lbl, _r_emoji = "🔴 高风险", "🔴"
    elif _r_total >= 55:
        _r_lbl, _r_emoji = "🟠 中高风险", "🟠"
    elif _r_total >= 40:
        _r_lbl, _r_emoji = "🟡 中等风险", "🟡"
    else:
        _r_lbl, _r_emoji = "🟢 低风险", "🟢"

    # 顶部综合分数
    _rt1, _rt2, _rt3 = st.columns(3)
    _rt1.metric("综合风险评分", f"{_r_total:.0f} / 100", _r_lbl)
    _rt2.metric("最高风险维度", max(
        [("集中度", _r_conc), ("头部门店", _r_top1),
         ("长尾", _r_tail), ("数据校准", _r_data)],
        key=lambda x: x[1]
    )[0])
    _rt3.metric("最低风险维度", min(
        [("集中度", _r_conc), ("头部门店", _r_top1),
         ("长尾", _r_tail), ("数据校准", _r_data)],
        key=lambda x: x[1]
    )[0])

    # 4 维度详细评分
    st.markdown("**📊 4 维度风险评分**")
    _risk_df = pd.DataFrame({
        "维度": ["🏢 集中度", "🏪 头部门店", "📉 长尾", "📋 数据校准"],
        "评分 (0-100)": [_r_conc, _r_top1, _r_tail, _r_data],
        "权重": ["35%", "20%", "20%", "25%"],
        "依据": [
            f"HHI = {hhi:.0f}",
            f"Top 1 门店 {_top1_store['store']} 占比 {_top1_store_pct:.1f}%",
            f"C 尾段 {_tc_count} 家贡献 {_tc_share:.1f}%",
            f"王府井 H1 估算 {(_wj_h1_est):.2f} 亿 vs 实际 Q1×2 = {_wj_q1_actual * 2:.2f} 亿（偏差 {_wj_bias_ratio:.0f}%）",
        ],
    })
    st.dataframe(_risk_df, hide_index=True, width='stretch')

    # 雷达图替代（用 bar 展示）
    st.markdown("**📊 风险雷达（条形可视化）**")
    _risk_chart = _risk_df.set_index("维度")["评分 (0-100)"]
    st.bar_chart(_risk_chart, height=250)
    st.caption("分数越高 = 风险越大；建议优先处理评分 ≥ 60 的维度。")

    # 行动优先级
    st.markdown("**🎯 风险处理优先级**")
    _risk_items = [
        ("🏢 集中度", _r_conc),
        ("🏪 头部门店", _r_top1),
        ("📉 长尾", _r_tail),
        ("📋 数据校准", _r_data),
    ]
    _risk_items.sort(key=lambda x: -x[1])
    for _i, (_rn, _rs) in enumerate(_risk_items, 1):
        if _rs >= 70:
            _pri = "🔴 高"
            _act = "立即处理"
        elif _rs >= 50:
            _pri = "🟠 中"
            _act = "本月内处理"
        elif _rs >= 30:
            _pri = "🟡 低"
            _act = "季度内处理"
        else:
            _pri = "🟢 极低"
            _act = "保持监测"
        st.markdown(
            f"- **{_i}. {_rn}（{_rs:.0f} 分）** → "
            f"优先级：{_pri} | 行动：{_act}"
        )

    st.caption(
        "⚠️ **数据局限**：本评分基于代理估算 + 已知王府井偏差，"
        "为相对参考。校准 RETAILER_SHARE 后建议重算。"
    )


# ---------- 综合行动建议 ----------
st.markdown("---")
st.subheader("🎯 综合行动建议")

_recs = []

# 1) 集中度风险
if hhi >= 2500:
    _recs.append({
        "icon": "🔴", "title": "降低中免单点依赖",
        "priority": "高",
        "body": (
            f"中免独占 **{top1_share:.1f}%** 市场（H1 估算 {top1_share * total_sales / 100:.1f} 亿），"
            f"HHI 处于高度集中区间。\n\n"
            f"**建议动作**：\n"
            f"1. **优先核对实际口径**：与王府井/海控等合作方核对实际 Q1/Q2 销售，"
            f"用真实数据校准 `RETAILER_SHARE`（当前 3% / 3% 等占比为代理假设，"
            f"王府井已有 Q1=1.39 亿实测值待用）；\n"
            f"2. **推动二线零售商扩张**：推动 2-3 家二线零售商占比从 "
            f"{shares.iloc[2:].sum():.1f}% 提升至 15%+，3 年内将 HHI 降至 2500 以下；\n"
            f"3. **建立数据共享机制**：与合作方签订月度对账协议，"
            f"用实测替代季度估算，从根上解决代理假设偏差。"
        ),
    })
else:
    _recs.append({
        "icon": "🟢", "title": "竞争格局相对健康",
        "priority": "中",
        "body": (
            f"HHI = {hhi:.0f}，处于合理区间。"
            f"建议继续维护各合作方关系，**通过数据校准让占比从代理假设转为实测口径**，"
            f"为后续合作策略提供更可靠的判断依据。"
        ),
    })

# 2) 80/20 长尾（_tc_share / _tc_count 已在数据准备段定义）
if _tc_share < 15 and _tc_count >= 2:
    _recs.append({
        "icon": "🟠", "title": "长尾门店战略复盘",
        "priority": "中",
        "body": (
            f"C 尾段 **{_tc_count} 家门店**仅贡献 **{_tc_share:.1f}%** 销售，"
            f"存在资源稀释风险。\n\n"
            f"**建议动作**：\n"
            f"1. **评估单店模型**：单店是否已实现盈亏平衡？"
            f"若 18 个月内未达标，启动「关停/合并/转型」评估；\n"
            f"2. **深度调研 1-2 家**：识别拖累原因（选址/产品/营销/客群），"
            f"形成可复用的避坑清单；\n"
            f"3. **明确爬坡 KPI**：新店开业 12 个月内销售/客流/客单的达标线，"
            f"不达标即触发整改而非观望。"
        ),
    })

# 3) 城市集中
_top_city_share = float(city_df.iloc[0]["占比%"])
if _top_city_share > 50:
    _recs.append({
        "icon": "🟡", "title": f"主市场 {city_df.iloc[0]['city']} 集中度风险",
        "priority": "中",
        "body": (
            f"{city_df.iloc[0]['city']} 单一市场贡献 **{_top_city_share:.1f}%**。\n\n"
            f"**建议动作**：\n"
            f"1. 关注主市场已开新店的爬坡（单店模型是否可持续）；\n"
            f"2. 跟踪非主力城市（万宁/琼海）的开店节奏与政策红利"
            f"（封关后离岛免税扩容到更多港口的可能性）；\n"
            f"3. 主市场已较饱和，**增量空间有限**，应转向「客单提升 + 复购率」，"
            f"而非继续拉新开店。"
        ),
    })

# 4) 线上渗透
if 0 < online_pct < 30:
    _recs.append({
        "icon": "🟡", "title": "线上渗透待加强",
        "priority": "中",
        "body": (
            f"线上渠道仅 **{online_pct:.1f}%**，渗透偏低。"
            f"封关后线上品类扩容（茶叶/乐器/数码）为新增长点。\n\n"
            f"**建议动作**：\n"
            f"1. **对接线上团队**：与中免/海控线上团队对接，"
            f"评估 SKU 覆盖深度与价格竞争力；\n"
            f"2. **新渠道尝试**：直播/短视频等线上引流，承接线下客流外的增量；\n"
            f"3. **监测客单差异**：若线上客单明显低于线下，"
            f"需排查是否折扣过度或客群结构差异。"
        ),
    })

# 5) 客单异常
if len(high_aov) + len(low_aov) > 0:
    _recs.append({
        "icon": "🟠", "title": "客单异常门店诊断",
        "priority": "中",
        "body": (
            f"共 **{len(high_aov) + len(low_aov)} 家门店**客单价偏离中位数 ±50%。\n\n"
            f"**建议动作**：\n"
            f"1. **高端异常 {len(high_aov)} 家**：验证是定位差异还是产品组合优势；"
            f"如属后者，抽取成功要素复制到其他门店；\n"
            f"2. **低端异常 {len(low_aov)} 家**：检查产品组合（是否过于低端）、"
            f"客群匹配、体验/服务短板；\n"
            f"3. **同步排查估算偏差**：若 `RETAILER_SHARE` 不准，"
            f"客单估算会系统性偏低/偏高，需先校准再下结论。"
        ),
    })

# 6) 增长归因（v1.6 新增）—— 拉新 vs 升级
try:
    if aov_yoy < pax_yoy / 2:
        _recs.append({
            "icon": "🟡", "title": "增长过度依赖拉新，客单价提升空间大",
            "priority": "中",
            "body": (
                f"H1 增长 {amt_yoy:+.1f}% 中，**客单仅贡献 {aov_yoy:+.1f}%、客流贡献 {pax_yoy:+.1f}%**，"
                f"过度依赖拉新驱动。\n\n"
                f"**建议动作**：\n"
                f"1. **客单价提升专项**：参考 BCG 矩阵中的 💰 现金牛门店，"
                f"推套装/连带/升级推荐，目标 H2 客单 YoY 提至 {pax_yoy:+.1f}% 以上；\n"
                f"2. **新客质量评估**：抽样新客 200 人做复购率调研，"
                f"若 3 个月复购率 < 30%，需调整拉新渠道（可能为获客做促销过度）；\n"
                f"3. **监控连带率**：件/人 YoY 是连带率指标，正向表示顾客买更多，"
                f"需保持正向（当前估算 {pieces_per_pax_yoy:+.1f}%）。"
            ),
        })
    elif aov_yoy < pax_yoy:
        _recs.append({
            "icon": "🟢", "title": "增长均衡（偏拉新），可适度向升级倾斜",
            "priority": "中",
            "body": (
                f"H1 增长 {amt_yoy:+.1f}% = 客流 {pax_yoy:+.1f}% + 客单 {aov_yoy:+.1f}%，"
                f"双轮驱动但仍偏拉新。\n\n"
                f"**建议动作**：\n"
                f"1. 维持拉新节奏，但**逐步加大高端化投入**（参考 BCG 矩阵中 💎 利润门店的复制）；\n"
                f"2. 季度跟踪客单 YoY，若从 {aov_yoy:+.1f}% 提升至 +{pax_yoy:+.1f}% 以上，"
                f"说明升级路径生效。"
            ),
        })
    else:
        _recs.append({
            "icon": "🟢", "title": "升级驱动增长，路径已见效",
            "priority": "低",
            "body": (
                f"H1 增长 {amt_yoy:+.1f}% 中客单 {aov_yoy:+.1f}% > 客流 {pax_yoy:+.1f}%，"
                f"品类升级与高端化路径已见效。\n\n"
                f"**建议动作**：\n"
                f"1. **继续加码高端 SKU 引进**（腕表/重奢/小众香等），"
                f"复制头部 {len(high_aov)} 家高端异常门店的成功要素；\n"
                f"2. **注意客流萎缩风险**：若客流持续下滑，需评估是否过度聚焦高端而忽略中端。"
            ),
        })
except NameError:
    pass  # 战略洞察模块可能未执行

# 7) BCG 矩阵 4 象限（v1.6 新增）—— 分类施策
try:
    _matrix_df_rec = df[["store", "sales_h1_est", "pax_h1_est", "客单价(元/人)"]].copy()
    _matrix_df_rec = _matrix_df_rec.dropna(subset=["客单价(元/人)", "pax_h1_est"])
    _median_pax_rec = float(_matrix_df_rec["pax_h1_est"].median())
    _median_aov_rec = float(_matrix_df_rec["客单价(元/人)"].median())
    _matrix_df_rec["象限"] = np.where(
        _matrix_df_rec["pax_h1_est"] >= _median_pax_rec, "高客流", "低客流"
    ) + " × " + np.where(
        _matrix_df_rec["客单价(元/人)"] >= _median_aov_rec, "高客单", "低客单"
    )
    _q_count = _matrix_df_rec["象限"].value_counts().to_dict()
    _problem_n = _q_count.get("低客流 × 低客单", 0)
    _cashcow_n = _q_count.get("高客流 × 低客单", 0)
    _star_n = _q_count.get("高客流 × 高客单", 0)
    _profit_n = _q_count.get("低客流 × 高客单", 0)

    if _problem_n >= 2 or _cashcow_n >= 2:
        _recs.append({
            "icon": "🎯", "title": f"BCG 象限分类施策：🌟{_star_n} / 💰{_cashcow_n} / 💎{_profit_n} / ⚠️{_problem_n}",
            "priority": "中",
            "body": (
                f"4 象限门店分布：**🌟 明星 {_star_n} 家 / 💰 现金牛 {_cashcow_n} 家 / "
                f"💎 利润 {_profit_n} 家 / ⚠️ 问题 {_problem_n} 家**。\n\n"
                f"**分类施策建议**：\n"
                f"1. **🌟 明星门店**：资源优先供给，保地位、复制成功要素到其他门店；\n"
                f"2. **💰 现金牛（{_cashcow_n} 家）**：推套装/连带/升级推荐，**客单提升 ROI 最高**；\n"
                f"3. **💎 利润门店（{_profit_n} 家）**：营销/活动拉客流，避免定位与曝光脱节；\n"
                f"4. **⚠️ 问题门店（{_problem_n} 家）**：18 个月未达标即启动「关停/合并/转型」评估。"
            ),
        })
except (NameError, Exception):
    pass

# 8) 单店盈亏（v1.6 新增）—— 财务可行性
try:
    # 用默认参数估算（与 Tab 中默认值一致）
    _fc_default = 120  # 万元/月
    _vc_default = 0.12
    _tm_default = 0.08
    _denom_default = 1 - _vc_default - _tm_default
    if _denom_default > 0:
        _be_default_yi = _fc_default * 6 / _denom_default / 10000
        _loss_n_default = int((df["sales_h1_est"] < _be_default_yi).sum())
        if _loss_n_default >= 2:
            _recs.append({
                "icon": "💼", "title": f"单店模型：默认假设下 {_loss_n_default} 家门店可能亏损",
                "priority": "中",
                "body": (
                    f"用行业典型成本（固定 120万/月 + 变动 12% + 目标利润 8%）估算，"
                    f"**H1 盈亏平衡销售约 {_be_default_yi:.2f} 亿**，"
                    f"当前有 **{_loss_n_default} 家门店** 估算销售低于此线。\n\n"
                    f"**建议动作**：\n"
                    f"1. **【短期】与财务核对实际成本**：行业默认值仅为参考，"
                    f"实际单店成本（租金/人工/装修摊销）差异大，需用真实数据校验；\n"
                    f"2. **【中期】对亏损店做 18 个月整改**：若仍未达平衡线，"
                    f"启动关停/合并/转型评估；\n"
                    f"3. **【长期】建立单店模型库**：每家门店建独立成本档案，"
                    f"作为新店选址与老店关停的决策依据。"
                ),
            })
except (NameError, Exception):
    pass

# 9) 风险评分卡（v1.6 新增）—— 综合风险处理
try:
    if _r_total >= 70:
        _risk_emoji = "🔴"
        _risk_lbl = "高风险"
    elif _r_total >= 55:
        _risk_emoji = "🟠"
        _risk_lbl = "中高风险"
    elif _r_total >= 40:
        _risk_emoji = "🟡"
        _risk_lbl = "中等风险"
    else:
        _risk_emoji = "🟢"
        _risk_lbl = "低风险"

    # 找最高风险维度
    _risk_dim_list = [
        ("集中度", _r_conc, "与王府井/海控核对实际 Q1/Q2，校准 RETAILER_SHARE；推动二线零售商扩张"),
        ("头部门店", _r_top1, f"对 Top 1 门店 {_top1_store['store']} 建风险预案（客流/口碑/政策监控）"),
        ("长尾", _r_tail, "对 C 尾段门店启动整改/退出评估，停止资源稀释"),
        ("数据校准", _r_data, "与合作方签订月度对账协议，从根上解决代理假设偏差"),
    ]
    _risk_dim_list.sort(key=lambda x: -x[1])
    _top_risk = _risk_dim_list[0]

    _recs.append({
        "icon": _risk_emoji, "title": f"综合风险评分 {_r_total:.0f}/100（{_risk_lbl}）",
        "priority": "高" if _r_total >= 70 else ("中" if _r_total >= 55 else "低"),
        "body": (
            f"4 维度风险：集中度 **{_r_conc:.0f}** / 头部门店 **{_r_top1:.0f}** / "
            f"长尾 **{_r_tail:.0f}** / 数据校准 **{_r_data:.0f}**。\n\n"
            f"**最高风险维度：{_top_risk[0]}（{_top_risk[1]:.0f} 分）**\n\n"
            f"**优先处理动作**：\n{_top_risk[2]}\n\n"
            f"**完整优先级（见风险评分卡 Tab）**：\n"
            + "\n".join([f"- {rn}（{rs:.0f} 分）" for rn, rs, _ in _risk_dim_list])
        ),
    })
except (NameError, Exception):
    pass

# 渲染建议
for _r in _recs:
    with st.expander(f"{_r['icon']} {_r['title']}　[优先级：{_r['priority']}]", expanded=False):
        st.markdown(_r["body"])

if not _recs:
    st.success("✅ 各项指标均在合理区间，建议保持当前节奏，重点关注数据校准。")

# 数据局限提醒
st.caption(
    "⚠️ **数据局限**：以上分析均建立在 `RETAILER_SHARE` 代理占比 + 门店权重分摊的估算上，"
    "**不能直接对外披露或用于财务核算**。建议每季度与各合作方核对实际销售后更新 `RETAILER_SHARE`，"
    "再做趋势对比与决策依据。"
)


# ============================================================
# 视图一：按零售商汇总（估算）
# ============================================================
st.subheader("🏢 各零售商 H1 销售估算（全部为估算）")
import pandas as pd

r_rows = []
for r in retailers_est:
    r_rows.append({
        "零售商": r["retailer"],
        "上市代码": r["ticker"] or "—",
        "合作": r["cooperation"],
        "估算占比": f"{r['share_est']:.0%}",
        "H1销售估算(亿)": r["sales_h1_est"],
        "门店数": r["stores"],
        "口径": ESTIMATE_BADGE,
    })
r_df = pd.DataFrame(r_rows)
st.dataframe(r_df, width='stretch', hide_index=True)
st.caption("说明：占比为代理假设（RETAILER_SHARE），非逐店实测；数值随上方锚点联动。")
show_insight("retailer_overview", max_bullets=3)


# ============================================================
# 视图二：门店级明细（估算 + 分摊方法可追溯）
# ============================================================
st.subheader("🏪 门店级销售 / 客流估算（全部为估算，附分摊方法）")

s_rows = []
for s in stores:
    s_rows.append({
        "零售商": s["retailer"],
        "门店": s["store"],
        "城市": s.get("city"),
        "业态": s.get("type"),
        "销售估算(亿)": s["sales_h1_est"],
        "客流估算(万)": s["pax_h1_est"],
        "口径": ESTIMATE_BADGE,
        "分摊方法": s["method"],
    })
s_df = pd.DataFrame(s_rows)
# 门店级数值加角标（用 markdown 渲染，口径列已标注）
st.dataframe(s_df, width='stretch', hide_index=True)
st.markdown(
    f"以上 {len(s_df)} 条门店级记录，每一条的「口径」列均为 {est_badge()}，"
    f"「分摊方法」列可追溯计算来源；**请勿当作各店实测值**。",
    unsafe_allow_html=True,
)
show_insight("store_overview", max_bullets=3)

# 下载 CSV（便于交接给同事，且字段已带 is_estimate / source）
csv_df = pd.DataFrame([{
    "retailer": x["retailer"], "store": x["store"], "city": x.get("city"),
    "type": x.get("type"), "sales_h1_est": x["sales_h1_est"],
    "pax_h1_est": x["pax_h1_est"], "is_estimate": x["is_estimate"],
    "source": x["source"], "method": x["method"],
} for x in stores])
st.download_button(
    "⬇️ 下载门店估算 CSV（含 is_estimate 标记）",
    csv_df.to_csv(index=False).encode("utf-8-sig"),
    file_name="hainan_store_estimate.csv", mime="text/csv",
)


# ============================================================
# 视图三：门店销售估算柱状图
# ============================================================
st.subheader("📈 门店 H1 销售估算对比（全部为估算）")
chart_df = pd.DataFrame(stores)
chart_df = chart_df.set_index("store")["sales_h1_est"].sort_values()
st.bar_chart(chart_df)
st.caption("柱越高代表按权重分摊出的体量越大；仅为估算分布，非实测排名。")
show_insight("store_overview", max_bullets=2)


# ============================================================
# 视图四：零售商 / 门店主数据（尽量详细，合作方全列出）
# ============================================================
with st.expander("📋 零售商 / 门店主数据（合作方全清单）", expanded=False):
    st.markdown(f"合作状态口径：**{COOPERATION_ALL}**（各零售商均与 MAX 团队合作）。")
    for r in RETAILERS:
        st.markdown(f"### {r['name']}")
        meta = (
            f"- 上市代码：{r.get('ticker') or '非上市'}\n"
            f"- 合作：{r.get('cooperation')}\n"
            f"- 数据来源：{r.get('data_source')}\n"
            f"- 备注：{r.get('note')}\n"
        )
        if r.get("hainan_q1_2026_rev") is not None:
            meta += f"- 公开 Q1 海南营收：{r['hainan_q1_2026_rev']} 亿\n"
        st.markdown(meta)
        for s in r.get("stores", []):
            st.markdown(
                f"  - **{s['name']}**（{s.get('city')} / {s.get('type')}）"
                f" 权重 {s.get('weight'):.0%} — {s.get('note')}"
            )
show_insight("retailer_overview", max_bullets=3)


# ============================================================
# 数据校准提示（重要，需 MAX / 合作方核对）
# ============================================================
st.info(
    "📌 **数据校准提示**：王府井 Q1 公开营收仅 1.39 亿，但按当前 RETAILER_SHARE 3% "
    "推算 H1 约 5.98 亿，与 Q1 量级不匹配，占比可能偏高约 1 倍。"
    "建议以合作方实际口径校准 RETAILER_SHARE 后再对外使用门店估算。其余未上市零售商"
    "无公开逐季数据，占比为代理假设，同样建议合作方复核。",
    icon="ℹ️",
)


# ============================================================
# 页脚：来源说明
# ============================================================
st.divider()
st.markdown("### 📚 数据来源与口径")
st.markdown(f"- **官方**：{'; '.join(SOURCE_NOTE.get('official', []))}")
st.markdown(f"- **估算**：{'; '.join(SOURCE_NOTE.get('estimated', []))}")
st.markdown(f"- **抓取**：{'; '.join(SOURCE_NOTE.get('scraped', []))}")
st.caption(
    f"看板生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} · "
    f"门店级数值全部为代理估算（is_estimate=True）"
)
