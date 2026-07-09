"""
海南免税商情监控 v2.0 - Streamlit 可视化仪表盘
✅ 12大机场  ✅ 新闻超链接可点击  ✅ 月度真实分布  ✅ 年份标注
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from utils.hainan_scraper import HainanScraper, AIRPORT_DB

st.set_page_config(page_title="海南免税商情监控", page_icon="🏝️", layout="wide")

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

st.title("🏝️ 海南免税商情监控")
st.caption("数据来源: CAAC民航局官方排名 + 百度新闻实时搜索  |  每日自动更新")

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
# 安全取值函数
# ============================================================

def safe_info(code, key, default=None):
    info = AIRPORT_DB.get(code, {})
    return info.get(key, default)

def safe_news(data, key):
    """新闻数据可能是 (title, url) 元组或纯字符串"""
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

# ============================================================
# 📊 核心指标卡片（12大机场）
# ============================================================

st.markdown("---")
st.subheader("📊 全国12大机场核心指标 (2024年 CAAC 数据)")

airport_keys = list(AIRPORT_DB.keys())

# 第一行：前6个
cols = st.columns(6)
for i, code in enumerate(airport_keys[:6]):
    annual = safe_info(code, "annual", "N/A")
    rank   = safe_info(code, "rank", "?")
    dom    = safe_info(code, "domestic_pct", "?")
    intl   = safe_info(code, "international_pct", "?")
    year   = safe_info(code, "data_year", "2024")
    with cols[i]:
        st.metric(
            label=f"🛫 {code}",
            value=f"{annual} 万",
            delta=f"全国第{rank}名",
            help=f"国内 {dom}% | 国际 {intl}% | {year}年数据"
        )

# 第二行：后6个
cols = st.columns(6)
for i, code in enumerate(airport_keys[6:]):
    annual = safe_info(code, "annual", "N/A")
    rank   = safe_info(code, "rank", "?")
    dom    = safe_info(code, "domestic_pct", "?")
    intl   = safe_info(code, "international_pct", "?")
    year   = safe_info(code, "data_year", "2024")
    with cols[i]:
        st.metric(
            label=f"🛫 {code}",
            value=f"{annual} 万",
            delta=f"全国第{rank}名",
            help=f"国内 {dom}% | 国际 {intl}% | {year}年数据"
        )

# ============================================================
# 📈 机场吞吐量对比
# ============================================================

st.markdown("---")
st.subheader("📈 机场年吞吐量对比 (2024年 CAAC官方数据)")

chart_data = pd.DataFrame({
    "机场": airport_keys,
    "年吞吐量(万人次)": [safe_info(k, "annual", 0) for k in airport_keys],
    "国内(万)": [round(safe_info(k, "annual", 0) * safe_info(k, "domestic_pct", 50) / 100, 0) for k in airport_keys],
    "国际(万)": [round(safe_info(k, "annual", 0) * safe_info(k, "international_pct", 50) / 100, 0) for k in airport_keys],
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
# 📅 月度客流分布（真实分布）
# ============================================================

st.markdown("---")
st.subheader("📅 月度旅客流量分布（基于各机场历史季节规律估算）")
st.caption("✅ 年总量为 CAAC 官方数据  |  ⚠️ 月度分布基于历史季节规律估算，非官方数据")

months = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]

selected_airport = st.selectbox("选择机场查看月度分布", airport_keys, index=0)

annual      = safe_info(selected_airport, "annual", 0)
monthly_pct = safe_info(selected_airport, "monthly_pct", None)
dom_pct     = safe_info(selected_airport, "domestic_pct", 50)
intl_pct    = safe_info(selected_airport, "international_pct", 50)
data_year   = safe_info(selected_airport, "data_year", "2024")

# 如果有月度分布数据，计算实际值
if monthly_pct and len(monthly_pct) == 12:
    total_pct = sum(monthly_pct)
    if total_pct > 0:
        monthly_vals = [round(annual * p / total_pct, 1) for p in monthly_pct]
    else:
        monthly_vals = [round(annual / 12, 1)] * 12
else:
    # 没有数据则均分
    monthly_vals = [round(annual / 12, 1)] * 12
    monthly_pct = [8.33] * 12

monthly_df = pd.DataFrame({
    "月份": months,
    "客流量(万人次)": monthly_vals,
    "占比(%)": [round(p, 1) for p in monthly_pct]
})

col1, col2 = st.columns([3, 1])
with col1:
    st.line_chart(monthly_df.set_index("月份")["客流量(万人次)"],
                  color="#FF6B6B", height=350)
with col2:
    st.metric(f"🛫 {selected_airport} ({data_year})", f"{annual} 万/年")
    st.caption(f"✅ 年总量: CAAC 官方")
    st.caption(f"⚠️ 月度分布: 估算")
    st.metric("国内占比", f"{dom_pct}%")
    st.metric("国际占比", f"{intl_pct}%")
    if monthly_vals:
        peak = max(monthly_vals)
        peak_month = months[monthly_vals.index(peak)]
        low = min(monthly_vals)
        low_month = months[monthly_vals.index(low)]
        st.metric(f"📈 旺季 ({peak_month})", f"{peak:.0f} 万")
        st.metric(f"📉 淡季 ({low_month})", f"{low:.0f} 万")

# 显示月度数据表
with st.expander("📊 查看月度明细数据"):
    st.dataframe(monthly_df, use_container_width=True, hide_index=True)

# ============================================================
# 🏗️ 航站楼 & 航线总览
# ============================================================

st.markdown("---")
st.subheader("🏗️ 航站楼 & 航线总览（12大机场）")
st.caption("航站楼/航司: 基于公开资料整理  |  最新动态: 百度新闻实时搜索")

for code in airport_keys:
    info        = AIRPORT_DB.get(code, {})
    annual      = info.get("annual", "N/A")
    rank        = info.get("rank", "?")
    data_year   = info.get("data_year", "2024")
    terminals   = info.get("terminals", {})
    airlines    = info.get("major_airlines", [])
    duty_free   = info.get("duty_free", {"operator": "暂无", "stores": "暂无", "note": "暂无"})
    code_en     = info.get("code_en", code)

    # 获取该机场的最新新闻
    airport_news = safe_news(data, "airport_news")
    # 过滤包含机场名的新闻
    airport_filtered = [(t, u) for t, u in airport_news if code[:2] in t or code_en in t]

    with st.expander(f"🛫 **{code} ({code_en})** — {annual}万/年 (全国第{rank})"):
        tabs = st.tabs(["🏗️ 航站楼", "✈️ 主力航司", "🛍️ 免税业务", "📰 最新动态"])

        with tabs[0]:
            st.caption(f"数据来源: 公开资料 (截至{data_year}年)")
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
# 📋 全国机场对比表
# ============================================================

st.markdown("---")
st.subheader("📋 全国12大机场核心指标对比 (2024年 CAAC官方数据)")

compare_data = []
for code in airport_keys:
    annual = safe_info(code, "annual", 0)
    dom_pct = safe_info(code, "domestic_pct", 0)
    intl_pct = safe_info(code, "international_pct", 0)
    rank = safe_info(code, "rank", "?")
    data_year = safe_info(code, "data_year", "2024")
    code_en = safe_info(code, "code_en", "")
    terminals = safe_info(code, "terminals", {})
    airlines = safe_info(code, "major_airlines", [])

    dom = round(annual * dom_pct / 100, 0)
    intl = round(annual * intl_pct / 100, 0)
    compare_data.append({
        "机场": code,
        "代码": code_en,
        "年吞吐量(万)": annual,
        "全国排名": rank,
        "数据年份": data_year,
        "国内(万)": f"{dom:.0f}({dom_pct}%)",
        "国际(万)": f"{intl:.0f}({intl_pct}%)",
        "航站楼数": len(terminals),
        "主力航司数": len(airlines),
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

st.caption(f"本报告由海南免税商情监控 v2.0 自动生成 | {today}")
