"""
海南免税商情监控 v1.0 - Streamlit 可视化仪表盘
每日自动刷新 + 手动刷新按钮
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from utils.hainan_scraper import HainanScraper, AIRPORT_DB

st.set_page_config(page_title="机场+海南商情监控", page_icon="🏝️", layout="wide")

# ============================================================
# 缓存：每日自动刷新（TTL=86400秒=24小时）
# ============================================================

@st.cache_data(ttl=86400, show_spinner="🔄 正在爬取最新数据，请稍候...")
def get_scraped_data(force_refresh=False):
    """缓存爬取结果，每日自动刷新"""
    scraper = HainanScraper()
    return scraper.scrape_all()


# ============================================================
# 页面标题
# ============================================================

st.title("🏝️ 机场+海南商情监控")
st.caption(f"数据来源: CAAC民航局 + 百度新闻实时搜索  |  每日自动更新")

col1, col2 = st.columns([3, 1])
with col1:
    st.caption("")
with col2:
    if st.button("🔄 手动刷新数据", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ============================================================
# 加载数据
# ============================================================

data = get_scraped_data()
today = data["date"]

st.success(f"📅 数据更新于: {today}  |  共 {len(data.get('airport_news',[]))+len(data.get('duty_free_news',[]))+len(data.get('li_island_news',[]))+len(data.get('policy_news',[]))+len(data.get('travel_news',[]))} 条新闻")

# ============================================================
# 📊 核心指标卡片
# ============================================================

st.markdown("---")
st.subheader("📊 核心指标")

metrics_cols = st.columns(6)
airport_keys = list(AIRPORT_DB.keys())
airport_data = AIRPORT_DB

for i, code in enumerate(airport_keys):
    info = airport_data[code]
    with metrics_cols[i]:
        st.metric(
            label=f"🛫 {code}",
            value=f"{info['annual']} 万",
            delta=f"全国第 {info['rank']}",
            help=f"国内 {info['domestic_pct']}% | 国际 {info['international_pct']}%"
        )

# 第六个卡片放离岛免税累计
with metrics_cols[5]:
    st.metric(
        label="🛍️ 离岛免税累计",
        value="2864 亿元",
        help="截至2026年累计购物金额"
    )

# ============================================================
# 📊 机场吞吐量对比（条形图）
# ============================================================

st.markdown("---")
st.subheader("📈 机场年吞吐量对比")

chart_data = pd.DataFrame({
    "机场": airport_keys,
    "年吞吐量(万人次)": [airport_data[k]["annual"] for k in airport_keys],
    "国内(万)": [round(airport_data[k]["annual"] * airport_data[k]["domestic_pct"] / 100, 0) for k in airport_keys],
    "国际(万)": [round(airport_data[k]["annual"] * airport_data[k]["international_pct"] / 100, 0) for k in airport_keys],
})

col1, col2 = st.columns([2, 1])
with col1:
    st.bar_chart(chart_data, x="机场", y=["年吞吐量(万人次)", "国内(万)", "国际(万)"],
                 color=["#FF6B6B", "#4ECDC4", "#45B7D1"], height=400)
with col2:
    # 境内外占比表
    st.dataframe(
        chart_data.style.highlight_max(axis=0, subset=["年吞吐量(万人次)"], color="#FFD700"),
        use_container_width=True,
        hide_index=True
    )

# ============================================================
# 📅 月度客流分布（交互式）
# ============================================================

st.markdown("---")
st.subheader("📅 月度旅客流量分布（交互查看）")

months = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]

selected_airport = st.selectbox("选择机场查看月度分布", airport_keys, index=0)
info = airport_data[selected_airport]

# 计算月度数据
total_pct = sum(info["monthly_distribution"])
monthly_vals = [round(info["annual"] * p / total_pct, 1) for p in info["monthly_distribution"]]

monthly_df = pd.DataFrame({
    "月份": months,
    "客流量(万人次)": monthly_vals,
    "占比(%)": info["monthly_distribution"]
})

col1, col2 = st.columns([3, 1])
with col1:
    st.line_chart(monthly_df.set_index("月份")["客流量(万人次)"], 
                  color="#FF6B6B", height=350)
with col2:
    st.metric(f"🛫 {selected_airport} 年吞吐量", f"{info['annual']} 万")
    st.metric("国内占比", f"{info['domestic_pct']}%")
    st.metric("国际占比", f"{info['international_pct']}%")
    st.metric("旺季(7-8月均)", f"{sum(monthly_vals[6:8])/2:.0f} 万/月")
    st.metric("淡季(5-6月均)", f"{sum(monthly_vals[4:6])/2:.0f} 万/月")

# ============================================================
# 🏗️ 航站楼 & 航线总览
# ============================================================

st.markdown("---")
st.subheader("🏗️ 航站楼 & 航线总览")

for code in airport_keys:
    info = airport_data[code]
    with st.expander(f"🛫 **{code}** — {info['annual']}万/年 | 全国第{info['rank']}"):
        tabs = st.tabs(["🏗️ 航站楼", "✈️ 主力航司", "🛍️ 免税业务"])
        
        with tabs[0]:
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

# ============================================================
# 📋 五大机场对比表
# ============================================================

st.markdown("---")
st.subheader("📋 五大机场核心指标对比")

compare_data = []
for code in airport_keys:
    info = airport_data[code]
    dom = round(info["annual"] * info["domestic_pct"] / 100, 0)
    intl = round(info["annual"] * info["international_pct"] / 100, 0)
    compare_data.append({
        "机场": code,
        "年吞吐量(万)": info["annual"],
        "全国排名": info["rank"],
        "国内(万)": f"{dom:.0f}({info['domestic_pct']}%)",
        "国际(万)": f"{intl:.0f}({info['international_pct']}%)",
        "航站楼数": len(info["terminals"]),
        "主力航司数": len(info["major_airlines"]),
    })

compare_df = pd.DataFrame(compare_data)
st.dataframe(compare_df, use_container_width=True, hide_index=True)

# ============================================================
# 📰 最新动态
# ============================================================

st.markdown("---")
st.subheader("📰 最新动态")

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
            for i, n in enumerate(items):
                st.markdown(f"{i+1}. {n}")
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
# 页脚
# ============================================================

st.markdown("---")
st.caption(f"本报告由海南免税商情监控 v1.0 自动生成 | {today}")
st.caption("机场年度数据来源: CAAC民航局2024年全国机场吞吐量排名")
st.caption("月度分布/航站楼/航司/境内外基于公开数据估算, 免税信息来自公开报道")
