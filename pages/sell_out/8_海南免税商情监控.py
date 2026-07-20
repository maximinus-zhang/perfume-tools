# -*- coding: utf-8 -*-
"""
海南免税商情监控 v9.0（合并版） - Streamlit 可视化仪表盘
✅ 海南离岛免税 2026 官方月度/YTD/政策  ✅ 12大机场双年对比
✅ 机场境外客流（国际航线/免签覆盖/入境游联动）  ✅ 百度新闻实时聚合
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from utils.hainan_scraper import HainanScraper, AIRPORT_DB
from utils.hainan_2026_data import HA_DF_2026, AIRPORT_INTL, SOURCE_NOTE
from utils.customs_parser import build_monthly_from_xlsx, try_cdp_fetch, XLSX_DIR

st.set_page_config(page_title="海南免税商情监控 2026", page_icon="🏝️", layout="wide")

# ============================================================
# 缓存
# ============================================================

@st.cache_data(ttl=86400, show_spinner="🔄 正在爬取最新数据，请稍候...")
def get_scraped_data(force_refresh=False):
    scraper = HainanScraper()
    return scraper.scrape_all()

# ============================================================
# 顶部
# ============================================================

st.title("🏝️ 海南免税商情监控 2026（合并版）")
st.caption("📊 海南离岛免税：海口海关/新华社/央视/海南特区报 ｜ 12大机场：CAAC民航局公报 ｜ 入境游：海南自贸港封关发布会")

col1, col2 = st.columns([3, 1])
with col2:
    st.markdown("**🔄 数据刷新**")
    if st.button("重新解析本地月报", use_container_width=True, key="btn_parse"):
        by_ym, recs = build_monthly_from_xlsx()
        st.session_state["customs_by_ym"] = by_ym
        st.session_state["customs_recs"] = recs
        st.session_state["customs_msg"] = f"已重新解析本地 xlsx/：{len(recs)} 个月报"
        st.rerun()
    if st.button("⬇️ 在线抓取最新(需调试Chrome)", use_container_width=True, key="btn_fetch"):
        ok, msg = try_cdp_fetch()
        by_ym, recs = build_monthly_from_xlsx()
        st.session_state["customs_by_ym"] = by_ym
        st.session_state["customs_recs"] = recs
        st.session_state["customs_msg"] = ("✅ " if ok else "⚠️ ") + msg
        st.rerun()
    if st.button("📰 刷新新闻", use_container_width=True, key="btn_news"):
        st.cache_data.clear()
        st.rerun()

# ---- 海关月报解析结果（session 级，供『重新解析』刷新）----
if "customs_by_ym" not in st.session_state:
    _by, _recs = build_monthly_from_xlsx()
    st.session_state["customs_by_ym"] = _by
    st.session_state["customs_recs"] = _recs
    st.session_state["customs_msg"] = (
        f"已加载本地 xlsx/：{len(_recs)} 个月报（点右上『重新解析本地月报』可刷新）"
    )

data = get_scraped_data()
today = data.get("date", datetime.now().strftime("%Y-%m-%d"))

total_news = sum(len(data.get(k, [])) for k in
                 ["airport_news", "duty_free_news", "li_island_news", "policy_news", "travel_news"])
st.success(f"📅 新闻更新于: {today}  |  共 {total_news} 条新闻")
st.info(f"💰 海关月报：{st.session_state.get('customs_msg', '')}")

# ============================================================
# 安全取值函数
# ============================================================

def safe_info(code, key, default=None):
    info = AIRPORT_DB.get(code, {})
    return info.get(key, default)

def safe_news(data, key):
    items = data.get(key, [])
    result = []
    for item in items:
        if isinstance(item, (tuple, list)):
            if len(item) >= 2:
                result.append((item[0], item[1]))
            else:
                result.append((str(item[0]), ""))
        else:
            result.append((str(item), ""))
    return result

def fmt_growth(val_25, val_24):
    if val_24 and val_24 > 0:
        pct = (val_25 - val_24) / val_24 * 100
        return f"+{pct:.1f}%" if pct > 0 else f"{pct:.1f}%"
    return "N/A"

def badge(src):
    if src in ("官方", "XLSX实时") or "XLSX" in str(src):
        return "🟢 官方/XLSX"
    elif src == "推算":
        return "🟡 推算"
    elif src == "累计进度":
        return "🟠 累计进度"
    return "⚪ 待补"

# ============================================================
# 海关月报解析 → 与硬编码数据合并 / 分析
# ============================================================

def merge_customs_monthly(hardcoded, by_ym):
    """用本地 XLSX 解析值覆盖硬编码月度序列（2026 M1-M5），并标来源。"""
    out = []
    for row in hardcoded:
        m = dict(row)
        label = m.get("m", "")
        mm = re.match(r"(\d+)月", label)
        if mm and "小计" not in label and "合计" not in label:
            rec = by_ym.get((2026, int(mm.group(1))))
            if rec:
                if rec["amt"] is not None:
                    m["amt26"] = rec["amt"]
                if rec["amt_yoy"] is not None:
                    m["yoy"] = round(rec["amt_yoy"], 1)
                if rec["pax"] is not None:
                    m["pax26"] = rec["pax"]
                if rec["pieces"] is not None:
                    m["pieces26"] = rec["pieces"]
                m["src"] = "XLSX实时"
        out.append(m)
    return out


def build_analysis_months(hardcoded, by_ym):
    """构造分析用月度行（含金额/人次/件数/同比，优先 XLSX 真实值）。"""
    rows = []
    for row in hardcoded:
        label = row.get("m", "")
        mm = re.match(r"(\d+)月", label)
        if not mm or "小计" in label or "合计" in label:
            continue
        mo = int(mm.group(1))
        rec = by_ym.get((2026, mo))
        amt26 = rec["amt"] if (rec and rec["amt"] is not None) else row.get("amt26")
        amt25 = row.get("amt25")
        pax26 = rec["pax"] if (rec and rec["pax"] is not None) else row.get("pax26")
        pax25 = row.get("pax25")
        pc26 = rec["pieces"] if (rec and rec["pieces"] is not None) else None
        yoy = rec["amt_yoy"] if (rec and rec["amt_yoy"] is not None) else row.get("yoy")
        src = "XLSX实时" if rec else row.get("src", "官方")
        rows.append({"m": label, "mo": mo, "amt26": amt26, "amt25": amt25,
                     "pax26": pax26, "pax25": pax25, "pieces26": pc26,
                     "yoy": yoy, "src": src})
    return rows

# ============================================================
# 模块一：海南离岛免税商情（2026 官方维度）
# ============================================================

st.markdown("---")
st.subheader("💰 海南离岛免税商情（2026 · 官方口径）")

yd = HA_DF_2026["ytd"]
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("免税购物金额", f"{yd['amount_2026']} 亿",
              delta=f"vs25年 {yd['amount_2025']}亿 · {yd['amt_yoy']:+.1f}%",
              help=f"来源：{yd['source']}")
with c2:
    st.metric("购物人数", f"{yd['pax_2026']} 万",
              delta=f"vs25年 {yd['pax_2025']}万 · {yd['pax_yoy']:+.1f}%")
with c3:
    st.metric("购物件数", f"{yd['pieces_2026']} 万",
              delta=f"vs25年 {yd['pieces_2025']}万 · {yd['pc_yoy']:+.1f}%")
st.caption(f"📌 YTD 口径：{yd['date_label']} ｜ 数据来源：{yd['source']}")

# 季度 + 月度YTD
st.markdown("**📈 季度对比（金额 亿元 · 2026 vs 2025）**")
qd = pd.DataFrame(HA_DF_2026["quarter"])
q_show = qd[["q", "amt26", "amt25", "yoy", "pax26", "pax25", "yoy_pax", "amt_src", "note"]].copy()
q_show.columns = ["季度", "2026金额", "2025金额", "金额同比%", "2026人数", "2025人数", "人数同比%",
                   "数据来源", "说明"]
st.dataframe(q_show, use_container_width=True, hide_index=True)

st.markdown("**📅 月度 YTD 进度（亿元 / 万人次）**")
_merged = merge_customs_monthly(HA_DF_2026["monthly_ytd"], st.session_state["customs_by_ym"])
_mdf = pd.DataFrame(_merged)
# 26 vs 25 月度金额对比图（仅自然月）
_chart = _mdf[_mdf["m"].str.match(r"\d+月")][["m", "amt26", "amt25"]].set_index("m")
st.bar_chart(_chart, color=["#E63946", "#1E90FF"], height=320)
m_show = _mdf.copy()
if "src" in m_show:
    m_show["来源"] = m_show["src"].map(lambda s: badge(s))
m_show = m_show[["m", "amt26", "amt25", "pax26", "pax25", "来源"]]
m_show.columns = ["月份", "2026金额", "2025金额", "2026人数", "2025人数", "来源标注"]
st.dataframe(m_show, use_container_width=True, hide_index=True)
st.caption("💡 1–5月为海关《离岛免税销售情况表》XLSX 真实值（🟢XLSX实时）；6月=H1−Σ1-5 反推；H1/Q1为官方累计口径。点右上『重新解析本地月报』可刷新。")

# 节点专项
st.markdown("**🎪 重要消费节点（2026 · 官方）**")
ed = pd.DataFrame(HA_DF_2026["events_2026"])
ed_show = ed[["name", "period", "amt", "pax", "pieces", "yoy", "src"]].copy()
ed_show.columns = ["节点", "时间", "金额(亿)", "人次(万)", "件数(万)", "金额同比%", "来源"]
st.dataframe(ed_show, use_container_width=True, hide_index=True)

# 政策动销
with st.expander("📜 政策动销（2025-11-01 新政 + 封关）"):
    p = HA_DF_2026["policy"]
    st.markdown(f"- **生效**：{p['effective']}")
    st.markdown(f"- **额度**：{p['quota']}")
    st.markdown(f"- **品类**：{p['categories']}")
    st.markdown(f"- **提货方式**：{p['pickup']}")
    st.markdown(f"- **享惠面扩大**：")
    for e in p["enjoy"]:
        st.markdown(f"  - {e}")
    st.markdown(f"- **限购**：{p['limits']}")
    st.caption(f"来源：{p['source']}")

# 省级入境游（境外游客客流）
st.markdown("**🌍 海南入境游（境外游客客流 · 省级口径）**")
ib = HA_DF_2026["inbound"]
i1, i2, i3, i4 = st.columns(4)
with i1:
    st.metric("进出境旅客", f"{ib['entry_exit_total']} 万", delta=f"{ib['entry_exit_yoy']:+.1f}%")
with i2:
    st.metric("免签入境", f"{ib['visa_free_entry']} 万", delta=f"{ib['visa_free_yoy']:+.1f}%")
with i3:
    st.metric("免签国家", f"{ib['visa_free_countries']} 国")
with i4:
    st.metric("境外航线", f"{ib['intl_routes']} 条 / {ib['route_countries']} 国地")
st.caption(f"📌 {ib['asof']} ｜ 来源：{ib['source']} ｜ {ib['note']}")

# ============================================================
# 模块一·附：月度数据深度分析（海关 XLSX 真实值）
# ============================================================

st.markdown("---")
st.subheader("💡 月度数据深度分析（海关 XLSX 真实值）")

am = build_analysis_months(HA_DF_2026["monthly_ytd"], st.session_state["customs_by_ym"])
amdf = pd.DataFrame(am)

# (1) 26vs25 金额 + 同比走势
c1, c2 = st.columns(2)
with c1:
    st.markdown("**📊 月度免税金额：2026 vs 2025（亿元）**")
    ch = amdf[["m", "amt26", "amt25"]].set_index("m")
    st.bar_chart(ch, color=["#E63946", "#1E90FF"], height=320)
with c2:
    st.markdown("**📉 月度金额同比（%）— Q1冲高→Q2走平**")
    yoy_ch = amdf[["m", "yoy"]].set_index("m")
    st.line_chart(yoy_ch, height=320)

# (2) 客单价 / 件单价 / 人均件数
st.markdown("**🛒 客单价与件单价走势（香化渠道重点关注）**")
asp_rows = []
for _, r in amdf.iterrows():
    if r["pax26"] and r["pieces26"] and r["amt26"]:
        asp = r["amt26"] / r["pax26"] * 10000       # 元/人
        pp = r["amt26"] / r["pieces26"] * 10000     # 元/件
        ppi = r["pieces26"] / r["pax26"]            # 件/人
        asp_rows.append({"月份": r["m"], "客单价(元/人)": round(asp, 0),
                         "件单价(元/件)": round(pp, 0), "人均件数": round(ppi, 2),
                         "金额同比%": r["yoy"]})
aspdf = pd.DataFrame(asp_rows)
if not aspdf.empty:
    st.line_chart(aspdf.set_index("月份")[["客单价(元/人)", "件单价(元/件)"]], height=320)
    st.dataframe(aspdf, use_container_width=True, hide_index=True)
    st.caption("⚠️ 2月/6月缺人次数据，未计入。客单价=金额÷人次；件单价=金额÷件数。")
else:
    st.info("暂无可计算客单价的月份（需同时有人次与件数）")

# (3) 增长贡献 + 全年情景测算
st.markdown("**📈 增长贡献与全年情景测算**")
q = HA_DF_2026["quarter"]
q1 = next(x for x in q if x["q"].startswith("Q1"))
q2 = next(x for x in q if x["q"].startswith("Q2"))
recs = st.session_state.get("customs_recs", [])
full_2025 = None
for rr in recs:
    if rr["year"] == 2025 and rr["month"] == 12 and rr["ytd_amt"]:
        full_2025 = rr["ytd_amt"]
h1_2025 = HA_DF_2026["ytd"]["amount_2025"]
h2_2025 = (full_2025 - h1_2025) if full_2025 else None
h1_2026 = HA_DF_2026["ytd"]["amount_2026"]

proj_rows = []
if h2_2025:
    for g, lbl in [(0.0, "保守 H2同比0%"), (0.05, "中性 H2同比+5%"), (0.10, "乐观 H2同比+10%")]:
        full = h1_2026 + h2_2025 * (1 + g)
        proj_rows.append({"情景": lbl, "H2 2026(亿)": round(h2_2025 * (1 + g), 1),
                          "全年 2026(亿)": round(full, 1),
                          "全年同比%": round((full / full_2025 - 1) * 100, 1) if full_2025 else None})
projdf = pd.DataFrame(proj_rows)
st.markdown(f"- **季度拆解**：Q1 金额 +{q1['yoy']}% → Q2 骤降至 +{q2['yoy']}%（Q2=H1−Q1反推）；"
             f"5月金额同比仅 +0.4% 且件数 −4.9%，增长明显走平。")
if full_2025:
    st.markdown(f"- **2025 全年基数**：{full_2025:.1f} 亿（取自 2025M12 海关累计）；H1 {h1_2025} + H2 {h2_2025:.1f}。")
    st.dataframe(projdf, use_container_width=True, hide_index=True)
    st.caption("📌 情景测算基于『H2 2026 相对 H2 2025 给定增速』，仅作计划参考；实际受新政红利衰减、暑期/国庆旺季及补库节奏影响。")
else:
    st.warning("未解析到 2025M12 累计，无法测算全年情景（请确认 xlsx/ 含 2025M12.xlsx）")

# (4) 香化渠道提示
st.markdown("**🧴 对香化补货 / 计划的提示**")
st.info(
    "① Q2 客单价与件单价双降（Q2 客单价约 5,800–6,000 元/人，较 Q1 的 1月 8,090 / 2月 8,423 元明显回落），"
    "说明 Q2 增长主要靠流量而非客单，且流量亦在放缓。\n"
    "② 下半年同比基数已被新政抬高，H2 大概率仅低个位数增长甚至转负；"
    "补货计划勿按 Q1 斜率外推，建议按『中性情景』(全年约 +12.6%) 做滚动预测并防库存堆积。\n"
    "③ 6月(反推)~15亿为上半年低点，7–8月暑运通常回升，可结合实时月报动态调整。"
)

# ============================================================
# 模块二：12大机场核心指标（2025 vs 2024）
# ============================================================

st.markdown("---")
st.subheader("🛫 全国12大机场核心指标 (2025年 CAAC数据)  —  2025 VS 2024 对比")

airport_keys = list(AIRPORT_DB.keys())

cols = st.columns(6)
for i, code in enumerate(airport_keys[:6]):
    a25 = safe_info(code, "annual_2025", 0)
    a24 = safe_info(code, "annual_2024", 0)
    rank = safe_info(code, "rank", "?")
    growth = safe_info(code, "growth_pct", 0)
    dom = safe_info(code, "domestic_pct", "?")
    intl = safe_info(code, "international_pct", "?")
    with cols[i]:
        st.metric(
            label=f"🛫 {code}",
            value=f"{a25} 万",
            delta=f"+{a25 - a24}万 (+{growth}%)  |  全国第{rank}",
            help=f"2025: {a25}万 | 2024: {a24}万 | 增量: +{a25 - a24}万 | 国内 {dom}% | 国际 {intl}%"
        )

cols = st.columns(6)
for i, code in enumerate(airport_keys[6:]):
    a25 = safe_info(code, "annual_2025", 0)
    a24 = safe_info(code, "annual_2024", 0)
    rank = safe_info(code, "rank", "?")
    growth = safe_info(code, "growth_pct", 0)
    dom = safe_info(code, "domestic_pct", "?")
    intl = safe_info(code, "international_pct", "?")
    with cols[i]:
        st.metric(
            label=f"🛫 {code}",
            value=f"{a25} 万",
            delta=f"+{a25 - a24}万 (+{growth}%)  |  全国第{rank}",
            help=f"2025: {a25}万 | 2024: {a24}万 | 增量: +{a25 - a24}万 | 国内 {dom}% | 国际 {intl}%"
        )

# ============================================================
# 模块三：机场吞吐量对比图（2025 vs 2024）
# ============================================================

st.markdown("---")
st.subheader("📈 机场年吞吐量对比: 2025(蓝) VS 2024(橙)  —  增量百分比")

chart_data = pd.DataFrame({
    "机场": airport_keys,
    "2025年(万人次)": [safe_info(k, "annual_2025", 0) for k in airport_keys],
    "2024年(万人次)": [safe_info(k, "annual_2024", 0) for k in airport_keys],
    "增量(万)": [safe_info(k, "annual_2025", 0) - safe_info(k, "annual_2024", 0) for k in airport_keys],
    "增长率(%)": [safe_info(k, "growth_pct", 0) for k in airport_keys],
})

col1, col2 = st.columns([3, 2])
with col1:
    st.bar_chart(chart_data, x="机场", y=["2025年(万人次)", "2024年(万人次)"],
                 color=["#1E90FF", "#FF8C00"], height=450)

with col2:
    growth_df = chart_data[["机场", "2025年(万人次)", "2024年(万人次)", "增量(万)", "增长率(%)"]].copy()
    growth_df["增长率"] = growth_df["增长率(%)"].apply(lambda x: f"+{x}%" if x > 0 else f"{x}%")
    st.dataframe(
        growth_df.style
            .highlight_max(subset=["增长率(%)"], color="#90EE90")
            .highlight_min(subset=["增长率(%)"], color="#FFB3B3"),
        use_container_width=True, hide_index=True,
        column_config={
            "2025年(万人次)": st.column_config.NumberColumn(format="%.0f"),
            "2024年(万人次)": st.column_config.NumberColumn(format="%.0f"),
            "增量(万)": st.column_config.NumberColumn(format="+%.0f"),
            "增长率(%)": st.column_config.NumberColumn(format="%.1f%%"),
        }
    )

# ============================================================
# 模块四：增长率排名
# ============================================================

st.markdown("---")
st.subheader("📊 增长率排名")

growth_ranked = chart_data.sort_values("增长率(%)", ascending=False).reset_index(drop=True)

col1, col2 = st.columns([2, 3])
with col1:
    st.dataframe(
        growth_ranked[["机场", "增长率(%)"]].style
            .bar(subset=["增长率(%)"], color="#1E90FF"),
        use_container_width=True, hide_index=True
    )
with col2:
    st.bar_chart(growth_ranked, x="机场", y="增长率(%)",
                 color="#1E90FF", height=350)

# ============================================================
# 模块五：月度客流分布（2025 vs 2024）
# ============================================================

st.markdown("---")
st.subheader("📅 月度旅客流量对比: 2025(蓝) VS 2024(橙)")
st.caption("✅ 年总量为 CAAC 官方数据  |  ⚠️ 月度分布为模拟值(基于历史季节规律)，非官方月度数据")

months = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]

selected_airport = st.selectbox("选择机场查看月度对比", airport_keys, index=0)

info = AIRPORT_DB.get(selected_airport, {})
annual_2025 = info.get("annual_2025", 0)
annual_2024 = info.get("annual_2024", 0)
monthly_pct = info.get("monthly_pct", None)
dom_pct = info.get("domestic_pct", 50)
intl_pct = info.get("international_pct", 50)
growth_pct = info.get("growth_pct", 0)
monthly_source = info.get("monthly_source", "模拟值")

if monthly_pct and len(monthly_pct) == 12:
    total_pct = sum(monthly_pct)
    if total_pct > 0:
        m2025 = [round(annual_2025 * p / total_pct, 1) for p in monthly_pct]
        m2024 = [round(annual_2024 * p / total_pct, 1) for p in monthly_pct]
    else:
        m2025 = [round(annual_2025 / 12, 1)] * 12
        m2024 = [round(annual_2024 / 12, 1)] * 12
else:
    m2025 = [round(annual_2025 / 12, 1)] * 12
    m2024 = [round(annual_2024 / 12, 1)] * 12

monthly_df = pd.DataFrame({
    "月份": months,
    "2025(万人次)": m2025,
    "2024(万人次)": m2024,
})

col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    chart_data_month = monthly_df.set_index("月份")
    st.line_chart(chart_data_month, color=["#1E90FF", "#FF8C00"], height=400)

with col2:
    st.metric(f"🛫 {selected_airport} (2025)", f"{annual_2025} 万/年")
    st.metric(f"🛫 {selected_airport} (2024)", f"{annual_2024} 万/年")
    st.metric("📈 同比增长", f"+{growth_pct}%")

with col3:
    st.metric("国内占比", f"{dom_pct}%")
    st.metric("国际占比", f"{intl_pct}%")
    st.metric("月度数据", monthly_source)
    if m2025:
        peak = max(m2025)
        peak_month = months[m2025.index(peak)]
        low = min(m2025)
        low_month = months[m2025.index(low)]
        st.metric(f"📈 旺季 ({peak_month})", f"{peak:.0f} 万")
        st.metric(f"📉 淡季 ({low_month})", f"{low:.0f} 万")

with st.expander("📊 查看月度明细对比数据"):
    monthly_detail = monthly_df.copy()
    monthly_detail["同比增减(万)"] = [m2025[i] - m2024[i] for i in range(12)]
    monthly_detail["同比(%)"] = [
        f"+{((m2025[i]-m2024[i])/m2024[i]*100):.1f}%" if m2024[i] > 0 else "N/A"
        for i in range(12)
    ]
    st.dataframe(monthly_detail, use_container_width=True, hide_index=True)

# ============================================================
# 模块六：航站楼 & 航线总览（含机场境外客流 Tab）
# ============================================================

st.markdown("---")
st.subheader("🏗️ 航站楼 & 航线总览（12大机场 · 含境外客流）")

for code in airport_keys:
    info = AIRPORT_DB.get(code, {})
    annual_25 = info.get("annual_2025", 0)
    annual_24 = info.get("annual_2024", 0)
    rank = info.get("rank", "?")
    growth = info.get("growth_pct", 0)
    terminals = info.get("terminals", {})
    airlines = info.get("major_airlines", [])
    duty_free = info.get("duty_free", {"operator": "暂无", "stores": "暂无", "note": "暂无"})
    code_en = info.get("code_en", code)
    cargo_25 = info.get("cargo_2025", 0)
    mov_25 = info.get("movements_2025", 0)
    intl_pct = info.get("international_pct", 0)
    dom_pct = info.get("domestic_pct", 0)
    intl_info = AIRPORT_INTL.get(code, {})

    airport_news = safe_news(data, "airport_news")
    airport_filtered = [(t, u) for t, u in airport_news if code[:2] in t or code_en in t]

    with st.expander(f"🛫 **{code} ({code_en})** — {annual_25}万/年 (全国第{rank})  |  +{growth}%  |  国际占比 {intl_pct}%"):
        tabs = st.tabs(["🏗️ 航站楼", "✈️ 主力航司", "🛍️ 免税业务",
                        "🌍 境外客流", "📊 双年对比", "📰 最新动态"])

        with tabs[0]:
            if terminals:
                for t_code, t_desc in terminals.items():
                    st.markdown(f"- **{t_code}**: {t_desc}")
            else:
                st.info("暂无航站楼信息")

        with tabs[1]:
            if airlines:
                for airline in airlines:
                    st.markdown(f"- ✈️ {airline}")
            else:
                st.info("暂无主力航司信息")

        with tabs[2]:
            st.markdown(f"- **运营商**: {duty_free.get('operator', '暂无')}")
            st.markdown(f"- **门店**: {duty_free.get('stores', '暂无')}")
            st.markdown(f"- **备注**: {duty_free.get('note', '暂无')}")

        with tabs[3]:
            st.markdown(f"**🌐 国际旅客占比（CAAC官方）**：{intl_pct}%（国内 {dom_pct}%）")
            if intl_info:
                st.markdown(f"_{intl_info.get('intl_pct_note','')}_")
                st.markdown("**✈️ 主要国际/地区航线城市**（公开整理）：")
                for r in intl_info.get("key_intl_routes", []):
                    st.markdown(f"- {r}")
                st.markdown(f"**🛂 免签覆盖**：{intl_info.get('visa_free_cover','')}")
                if intl_info.get("note"):
                    st.caption(intl_info["note"])
            else:
                st.info("暂无境外客流明细")
            if code in ("海口美兰", "三亚凤凰"):
                st.success("🏝️ 该机场为海南离岛免税直接口岸，境外客流经86国免签落地入岛购物（见上方『海南入境游』面板）")

        with tabs[4]:
            st.metric("2025年旅客量", f"{annual_25} 万")
            st.metric("2024年旅客量", f"{annual_24} 万")
            st.metric("同比增长", f"+{growth}%")
            st.metric("货邮吞吐量(2025)", f"{cargo_25} 万吨")
            st.metric("起降架次(2025)", f"{mov_25} 万架次")

        with tabs[5]:
            shown = airport_filtered[:5] if airport_filtered else airport_news[:5]
            if shown:
                for i, (title, url) in enumerate(shown):
                    if url:
                        st.markdown(f"{i+1}. [{title}]({url})")
                    else:
                        st.markdown(f"{i+1}. {title}")
            else:
                st.info("暂无最新动态")

# ============================================================
# 模块七：全国机场对比表
# ============================================================

st.markdown("---")
st.subheader("📋 全国12大机场核心指标对比 — 2025 VS 2024 (CAAC官方数据)")

compare_data = []
for code in airport_keys:
    a25 = safe_info(code, "annual_2025", 0)
    a24 = safe_info(code, "annual_2024", 0)
    dom_pct = safe_info(code, "domestic_pct", 0)
    intl_pct = safe_info(code, "international_pct", 0)
    growth = safe_info(code, "growth_pct", 0)
    rank = safe_info(code, "rank", "?")
    code_en = safe_info(code, "code_en", "")
    cargo_25 = safe_info(code, "cargo_2025", 0)
    mov_25 = safe_info(code, "movements_2025", 0)
    terminals = safe_info(code, "terminals", {})
    airlines = safe_info(code, "major_airlines", [])

    dom = round(a25 * dom_pct / 100, 0)
    intl = round(a25 * intl_pct / 100, 0)
    compare_data.append({
        "机场": code,
        "代码": code_en,
        "2025(万)": a25,
        "2024(万)": a24,
        "增量(万)": a25 - a24,
        "增长(%)": growth,
        "全国排名": rank,
        "货邮(万吨)": cargo_25,
        "起降(万架次)": mov_25,
        "国内(万)": f"{dom:.0f}({dom_pct}%)",
        "国际(万)": f"{intl:.0f}({intl_pct}%)",
        "航站楼数": len(terminals),
        "主力航司数": len(airlines),
    })

compare_df = pd.DataFrame(compare_data)
st.dataframe(
    compare_df.style
        .highlight_max(subset=["2025(万)", "增长(%)"], color="#90EE90")
        .highlight_min(subset=["增长(%)"], color="#FFB3B3"),
    use_container_width=True, hide_index=True,
    column_config={
        "2025(万)": st.column_config.NumberColumn(format="%.0f"),
        "2024(万)": st.column_config.NumberColumn(format="%.0f"),
        "增量(万)": st.column_config.NumberColumn(format="+%.0f"),
        "增长(%)": st.column_config.NumberColumn(format="+.1f%%"),
    }
)

# ============================================================
# 模块八：最新动态
# ============================================================

st.markdown("---")
st.subheader("📰 最新动态 (点击标题打开原文)")

news_tabs = st.tabs(["✈️ 机场动态", "🛍️ 机场免税", "💰 离岛免税", "📜 政策动态", "🏖️ 旅游客流"])

news_categories = [
    ("airport_news", "✈️ 机场动态"),
    ("duty_free_news", "🛍️ 机场免税"),
    ("li_island_news", "💰 离岛免税"),
    ("policy_news", "📜 政策动态"),
    ("travel_news", "🏖️ 旅游客流"),
]

for key, label in news_categories:
    tab_idx = news_categories.index((key, label))
    with news_tabs[tab_idx]:
        items = safe_news(data, key)
        if items:
            for i, (title, url) in enumerate(items):
                if url:
                    st.markdown(f"{i+1}. [{title}]({url})")
                else:
                    st.markdown(f"{i+1}. {title}")
        else:
            st.info(f"暂无{label}相关新闻")

# ============================================================
# 模块九：关键数据摘要
# ============================================================

st.markdown("---")
st.subheader("📊 关键数据摘要")

summary = data.get("summary", [])
if summary:
    seen_summary = set()
    summary_rows = []
    for item in summary:
        if isinstance(item, (tuple, list)):
            if len(item) >= 3:
                icon, val, ctx = item[0], item[1], item[2]
            elif len(item) == 2:
                icon, val = item[0], item[1]
                ctx = ""
            else:
                icon, val, ctx = str(item), "", ""
        else:
            icon, val, ctx = str(item), "", ""
        key = f"{icon}|{val}|{ctx[:30]}"
        if key not in seen_summary and ctx.strip():
            seen_summary.add(key)
            summary_rows.append({"类别": icon, "数据": val, "说明": ctx})
    if summary_rows:
        summary_df = pd.DataFrame(summary_rows)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无摘要数据")
else:
    st.info("暂无摘要数据")

# ============================================================
# 页脚：数据来源说明
# ============================================================

st.markdown("---")
st.markdown("### 📌 数据来源说明")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**🟢 官方数据**")
    for s in SOURCE_NOTE["official"]:
        st.markdown(f"- {s}")
with col2:
    st.markdown("**🟡 估算 / 公开整理**")
    for s in SOURCE_NOTE["estimated"]:
        st.markdown(f"- {s}")
with col3:
    st.markdown("**📰 实时抓取**")
    for s in SOURCE_NOTE["scraped"]:
        st.markdown(f"- {s}")
    st.markdown("—")
    st.markdown("⚠️ **机场境外游客客流定位**：CAAC公报仅公布机场『国际占比%』，分机场/分国别境外旅客明细为边检涉密级数据、公开源未披露；本页『境外客流』Tab 提供**国际航线城市 + 免签国覆盖（公开整理）**，并结合**海南省级入境游口径**（86国免签/138.5万进出境）做联动分析。")

st.caption(f"本报告由海南免税商情监控 v9.0（合并版）自动生成 | {today}")
