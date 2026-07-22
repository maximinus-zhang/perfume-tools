# -*- coding: utf-8 -*-
"""
海南免税 商情监控看板（门店级代理估算） v1.5
============================================
定位: 在「零售商 — 门店」维度展示海南离岛免税商情。

⚠️ 核心合规要求（来自 MAX）:
  1. 门店级销售/客流全部为【代理估算值】，必须带「估算」角标，禁止误判为实测。
  2. 各零售商均为合作方（COOPERATION_ALL = 合作），尽量列详细。
  3. 估算方法透明可追溯（每条记录带 method 字段，看板内可展开查看）。

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
st.caption("零售商 / 门店维度 · 门店级为代理估算 · v1.5")

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
        step=1.0, key="h1_total",
    )
    h1_pax = col_b.number_input(
        "H1 全省客流（万人次）", value=float(ytd["pax_2026"]),
        step=1.0, key="h1_pax",
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

# 分层（按销售降序的 33/33/34 分位）
df_sorted["tier"] = pd.qcut(
    df_sorted["sales_h1_est"], q=[0, 0.34, 0.67, 1.0],
    labels=["C 尾段", "B 中段", "A 头部"],
)
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

# ---------- 多维分析（Tabs）----------
_tabs = st.tabs([
    "🏆 80/20 与分层",
    "🏙️ 城市结构",
    "🏬 业态结构",
    "🏢 集中度",
    "🚨 异常门店",
    "📅 成熟度",
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

    _a_n = int(tier_summary[tier_summary["tier"] == "A 头部"]["店数"].iloc[0])
    _a_s = float(tier_summary[tier_summary["tier"] == "A 头部"]["销售占比%"].iloc[0])
    _c_n = int(tier_summary[tier_summary["tier"] == "C 尾段"]["店数"].iloc[0])
    _c_s = float(tier_summary[tier_summary["tier"] == "C 尾段"]["销售占比%"].iloc[0])
    st.info(
        f"💡 **解读**：A 头部 {_a_n} 家承担 {_a_s:.1f}% 销售，C 尾段 {_c_n} 家仅贡献 {_c_s:.1f}%。"
        f"长尾门店需逐家评估：继续投入（品牌曝光/客群补充）vs 整改/退出。",
        icon="💡",
    )

with _tabs[1]:
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

with _tabs[2]:
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

with _tabs[3]:
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

with _tabs[4]:
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
    _ad["预警"] = np.where(
        _ad["客单价(元/人)"].isna(), "—",
        np.where(_ad["客单价(元/人)"] > median_aov * 1.5, "🟠 高端异常",
                 np.where(_ad["客单价(元/人)"] < median_aov * 0.5, "🔴 低端异常", "✅ 正常")),
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

with _tabs[5]:
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

# 2) 80/20 长尾
_tc_share = float(tier_summary[tier_summary["tier"] == "C 尾段"]["销售占比%"].iloc[0])
_tc_count = int(tier_summary[tier_summary["tier"] == "C 尾段"]["店数"].iloc[0])
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
