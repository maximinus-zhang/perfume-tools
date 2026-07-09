"""
海南免税商情监控 v3.0 - Streamlit 可视化仪表盘
✅ 12大机场 ✅ 2025 VS 2024 双年对比 ✅ 增量百分比 ✅ 月度对比图
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from utils.hainan_scraper import HainanScraper, AIRPORT_DB

st.set_page_config(page_title="海南免税商情监控 2025", page_icon="🏝️", layout="wide")

# ============================================================
# 缓存
# ============================================================

@st.cache_data(ttl=86400, show_spinner="🔄 正在爬取最新数据，请稍候...")
def get_scraped_data(force_refresh=False):
    scraper = HainanScraper()
    return scraper.scrape_all()

# ============================================================
# 页面
# ============================================================

st.title("🏝️ 海南免税商情监控 2025")
st.caption("📊 数据来源: CAAC民航局2025年全国民用运输机场生产统计公报 + 百度新闻实时搜索  |  2025 VS 2024 双年对比")

col1, col2 = st.columns([3, 1])
with col2:
    if st.button("🔄 手动刷新数据", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

data = get_scraped_data()
today = data.get("date", datetime.now().strftime("%Y-%m-%d"))

total_news = sum(len(data.get(k, [])) for k in
                 ["airport_news","duty_free_news","li_island_news","policy_news","travel_news"])
st.success(f"📅 数据更新于: {today}  |  共 {total_news} 条新闻")

# ============================================================
# 安全取值函数（兼容新旧字段）
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
    """格式化增长百分比"""
    if val_24 and val_24 > 0:
        pct = (val_25 - val_24) / val_24 * 100
        return f"+{pct:.1f}%" if pct > 0 else f"{pct:.1f}%"
    return "N/A"

# ============================================================
# 📊 核心指标卡片（12大机场—2025 VS 2024）
# ============================================================

st.markdown("---")
st.subheader("📊 全国12大机场核心指标 (2025年 CAAC数据)  —  2025 VS 2024 对比")

airport_keys = list(AIRPORT_DB.keys())

# 第一行：前6个
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

# 第二行：后6个
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
# 📈 机场吞吐量对比：2025 VS 2024
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
    # 柱状图对比
    st.bar_chart(chart_data, x="机场", y=["2025年(万人次)", "2024年(万人次)"],
                 color=["#1E90FF", "#FF8C00"], height=450)

with col2:
    # 显示增量百分比
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
# 📊 增长率排名图
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
# 📅 月度客流分布（2025 VS 2024 对比）
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

# 计算月度值
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
    # 双线对比图
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

# 显示月度明细对比表
with st.expander("📊 查看月度明细对比数据"):
    monthly_detail = monthly_df.copy()
    monthly_detail["同比增减(万)"] = [m2025[i] - m2024[i] for i in range(12)]
    monthly_detail["同比(%)"] = [
        f"+{((m2025[i]-m2024[i])/m2024[i]*100):.1f}%" if m2024[i] > 0 else "N/A"
        for i in range(12)
    ]
    st.dataframe(monthly_detail, use_container_width=True, hide_index=True)

# ============================================================
# 🏗️ 航站楼 & 航线总览（12大机场）
# ============================================================

st.markdown("---")
st.subheader("🏗️ 航站楼 & 航线总览（12大机场）")

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

    airport_news = safe_news(data, "airport_news")
    airport_filtered = [(t, u) for t, u in airport_news if code[:2] in t or code_en in t]

    with st.expander(f"🛫 **{code} ({code_en})** — {annual_25}万/年 (全国第{rank})  |  +{growth}%"):
        tabs = st.tabs(["🏗️ 航站楼", "✈️ 主力航司", "🛍️ 免税业务", "📊 双年对比", "📰 最新动态"])

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
            st.metric("2025年旅客量", f"{annual_25} 万")
            st.metric("2024年旅客量", f"{annual_24} 万")
            st.metric("同比增长", f"+{growth}%")
            st.metric("货邮吞吐量(2025)", f"{cargo_25} 万吨")
            st.metric("起降架次(2025)", f"{mov_25} 万架次")

        with tabs[4]:
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
# 📋 全国机场对比表（2025 VS 2024）
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
# 📰 最新动态（带超链接）
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
# 📊 关键数据摘要
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
# 页脚
# ============================================================

st.markdown("---")
st.markdown("### 📌 数据来源说明")
col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    ✅ **真实数据（CAAC官方）**
    - 年吞吐量2025 — 民航局2025年全国民用运输机场生产统计公报
    - 年吞吐量2024 — 民航局2024年全国机场排名（保留对比）
    - 增量百分比 — 基于官方数据计算
    - 航站楼分布 — 公开资料
    - 主力航司 — 公开资料
    - 免税业务 — 公开报道
    """)
with col2:
    st.markdown("""
    ⚠️ **估算数据（仅供参考）**
    - 月度客流分布 — 基于季节性规律模拟 (实地爬取CAAC月度数据失败时启用)
    - 国内/国际占比 — 基于年报估算
    - 最新动态 — 百度新闻实时搜索
    """)

st.caption(f"本报告由海南免税商情监控 v3.0 自动生成 | {today}")
