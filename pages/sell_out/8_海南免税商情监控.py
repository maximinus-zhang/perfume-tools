"""
海南免税商情监控 v1.2 - Streamlit 可视化仪表盘
✅ 超链接可点击  ✅ 年份标注  ✅ 全国12大机场  ✅ 数据来源区分
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from utils.hainan_scraper import HainanScraper, AIRPORT_DB

st.set_page_config(page_title="海南免税商情监控", page_icon="🏝️", layout="wide")

# ============================================================
# 缓存：TTL=86400秒（24小时）
# ============================================================

@st.cache_data(ttl=86400, show_spinner="🔄 正在爬取最新数据，请稍候...")
def get_scraped_data(force_refresh=False):
    scraper = HainanScraper()
    return scraper.scrape_all()

# ============================================================
# 页面
# ============================================================

st.title("🏝️ 海南免税商情监控")
st.caption("数据来源: CAAC民航局 **2024年**官方排名 + 百度新闻实时搜索  |  每日自动更新")

col1, col2 = st.columns([3, 1])
with col2:
    if st.button("🔄 手动刷新数据", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

data = get_scraped_data()
today = data["date"]

total_news = sum(len(data.get(k, [])) for k in
                 ["airport_news","duty_free_news","li_island_news","policy_news","travel_news"])
st.success(f"📅 数据更新于: {today}  |  共 {total_news} 条新闻")

# ============================================================
# 📊 核心指标卡片
# ============================================================

st.markdown("---")
st.subheader("📊 核心指标 (2024年 CAAC 数据)")

# 全国前十机场
airport_keys = list(AIRPORT_DB.keys())

# 第一行：前6个
cols = st.columns(6)
for i, code in enumerate(airport_keys[:6]):
    info = AIRPORT_DB[code]
    with cols[i]:
        st.metric(
            label=f"🛫 {code}",
            value=f"{info['annual']} 万",
            delta=f"全国第{info['rank']}名",
            help=f"国内 {info['domestic_pct']}% | 国际 {info['international_pct']}% | {info['data_year']}年"
        )

# 第二行：后6个
cols = st.columns(6)
for i, code in enumerate(airport_keys[6:]):
    info = AIRPORT_DB[code]
    with cols[i]:
        st.metric(
            label=f"🛫 {code}",
            value=f"{info['annual']} 万",
            delta=f"全国第{info['rank']}名",
            help=f"国内 {info['domestic_pct']}% | 国际 {info['international_pct']}% | {info['data_year']}年"
        )

# ============================================================
# 📈 机场吞吐量对比（条形图）
# ============================================================

st.markdown("---")
st.subheader("📈 机场年吞吐量对比 (2024年 CAAC官方数据)")

chart_data = pd.DataFrame({
    "机场": airport_keys,
    "年吞吐量(万人次)": [AIRPORT_DB[k]["annual"] for k in airport_keys],
    "国内(万)": [round(AIRPORT_DB[k]["annual"] * AIRPORT_DB[k]["domestic_pct"] / 100, 0) for k in airport_keys],
    "国际(万)": [round(AIRPORT_DB[k]["annual"] * AIRPORT_DB[k]["international_pct"] / 100, 0) for k in airport_keys],
})

col1, col2 = st.columns([2, 1])
with col1:
    st.bar_chart(chart_data, x="机场", y=["年吞吐量(万人次)", "国内(万)", "国际(万)"],
                 color=["#FF6B6B", "#4ECDC4", "#45B7D1"], height=400)
with col2:
    st.dataframe(
        chart_data.style.highlight_max(axis=0, subset=["年吞吐量(万人次)"], color="#FFD700"),
        use_container_width=True, hide_index=True
    )

# ============================================================
# 📅 月度客流分布（交互式）
# ============================================================

st.markdown("---")
st.subheader("📅 月度旅客流量分布")
st.caption("⚠️ **月度分布为基于季节规律的估算值，非官方数据，仅供参考**")

months = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]

selected_airport = st.selectbox("选择机场查看月度分布", airport_keys, index=0)
info = AIRPORT_DB[selected_airport]

total_pct = sum(info["monthly_pct"])
monthly_vals = [round(info["annual"] * p / total_pct, 1) for p in info["monthly_pct"]]

monthly_df = pd.DataFrame({
    "月份": months,
    "客流量(万人次)": monthly_vals,
    "占比(%)": info["monthly_pct"]
})

col1, col2 = st.columns([3, 1])
with col1:
    st.line_chart(monthly_df.set_index("月份")["客流量(万人次)"],
                  color="#FF6B6B", height=350)
with col2:
    st.metric(f"🛫 {selected_airport} (2024)", f"{info['annual']} 万/年")
    st.caption(f"✅ 年总量: CAAC官方数据")
    st.caption(f"⚠️ 月度分布: 估算值")
    st.metric("国内占比", f"{info['domestic_pct']}%")
    st.metric("国际占比", f"{info['international_pct']}%")
    peak = max(monthly_vals)
    peak_month = months[monthly_vals.index(peak)]
    st.metric(f"旺季 ({peak_month})", f"{peak:.0f} 万")
    low = min(monthly_vals)
    low_month = months[monthly_vals.index(low)]
    st.metric(f"淡季 ({low_month})", f"{low:.0f} 万")

# ============================================================
# 🏗️ 航站楼 & 航线总览（含最新搜索）
# ============================================================

st.markdown("---")
st.subheader("🏗️ 航站楼 & 航线总览")
st.caption("航站楼/航司: 基于公开资料整理  |  最新动态: 百度新闻实时搜索")

for code in airport_keys:
    info = AIRPORT_DB[code]
    airport_news = data.get("airport_latest_news", {}).get(code, [])

    with st.expander(f"🛫 **{code}** — {info['annual']}万/年 (全国第{info['rank']})"):
        tabs = st.tabs(["🏗️ 航站楼", "✈️ 主力航司", "🛍️ 免税业务", "📰 最新动态"])

        with tabs[0]:
            st.caption(f"数据来源: 公开资料 (截至{info['data_year']}年)")
            for t_code, t_desc in info["terminals"].items():
                st.markdown(f"- **{t_code}**: {t_desc}")

        with tabs[1]:
            for airline in info["major_airlines"]:
                st.markdown(f"- ✈️ {airline}")

        with tabs[2]:
            df = info["duty_free"]
            st.markdown(f"- **运营商**: {df['operator']}")
            st.markdown(f"- **门店**: {df['stores']}")
            st.markdown(f"- **备注**: {df['note']}")

        with tabs[3]:
            if airport_news:
                for i, (title, url) in enumerate(airport_news):
                    st.markdown(f"{i+1}. [{title}]({url})")
            else:
                st.info("暂无最新动态")

# ============================================================
# 📋 全国机场对比表
# ============================================================

st.markdown("---")
st.subheader("📋 全国12大机场核心指标对比 (2024年 CAAC官方数据)")

compare_data = []
for code in airport_keys:
    info = AIRPORT_DB[code]
    dom = round(info["annual"] * info["domestic_pct"] / 100, 0)
    intl = round(info["annual"] * info["international_pct"] / 100, 0)
    compare_data.append({
        "机场": code,
        "年吞吐量(万)": info["annual"],
        "全国排名": info["rank"],
        "数据年份": info["data_year"],
        "国内(万)": f"{dom:.0f}({info['domestic_pct']}%)",
        "国际(万)": f"{intl:.0f}({info['international_pct']}%)",
        "航站楼数": len(info["terminals"]),
        "主力航司数": len(info["major_airlines"]),
    })

compare_df = pd.DataFrame(compare_data)
st.dataframe(compare_df, use_container_width=True, hide_index=True)

# ============================================================
# 📰 最新动态（带超链接）
# ============================================================

st.markdown("---")
st.subheader("📰 最新动态 (点击标题打开原文)")

news_tabs = st.tabs(["✈️ 机场动态", "🛍️ 机场免税", "💰 离岛免税", "📜 政策动态", "🏖️ 旅游客流"])

news_categories = [
    ("airport_news", "✈️ 机场动态", 0),
    ("duty_free_news", "🛍️ 机场免税", 1),
    ("li_island_news", "💰 离岛免税", 2),
    ("policy_news", "📜 政策动态", 3),
    ("travel_news", "🏖️ 旅游客流", 4),
]

for key, label, tab_idx in news_categories:
    with news_tabs[tab_idx]:
        items = data.get(key, [])
        if items:
            for i, (title, url) in enumerate(items):
                st.markdown(f"{i+1}. [{title}]({url})")
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
    for icon, val, ctx in summary:
        key = f"{icon}|{val}|{ctx[:30]}"
        if key not in seen_summary and ctx.strip():
            seen_summary.add(key)
            summary_rows.append({"类别": icon, "数据": val, "说明": ctx})

    summary_df = pd.DataFrame(summary_rows)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
else:
    st.info("暂无摘要数据")

# ============================================================
# 页脚 - 数据来源说明
# ============================================================

st.markdown("---")
st.markdown("### 📌 数据来源说明")
col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    ✅ **真实数据（CAAC官方）**
    - 年吞吐量 — 民航局2024年全国机场排名
    - 航站楼分布 — 公开资料
    - 主力航司 — 公开资料
    - 免税业务 — 公开报道
    """)
with col2:
    st.markdown("""
    ⚠️ **估算数据（仅供参考）**
    - 月度客流分布 — 基于季节性规律估算
    - 国内/国际占比 — 基于年报估算
    - 最新动态 — 百度新闻实时搜索
    """)

st.caption(f"本报告由海南免税商情监控 v1.2 自动生成 | {today}")
