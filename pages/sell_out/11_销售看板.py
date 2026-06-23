import streamlit as st
import pandas as pd
from datetime import datetime

st.title("🏪 Sell Out · 销售总看板")
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)
col1.metric("📊 本月总销售额", "¥18,250万", "+12.3%")
col2.metric("🏪 活跃门店", "12 家", "持平")
col3.metric("✅ 订单满足率", "87.5%", "+2.1%")
col4.metric("📈 同比增速", "+15.8%", "+3.2%")

st.markdown("---")
st.subheader("📌 模块快捷入口")

cols = st.columns(3)
with cols[0]:
    with st.container(border=True):
        st.markdown("#### 🏝️ 海南免税")
        st.metric("本月销售额", "¥8,520万")
        st.markdown("👉 从左侧导航进入")
with cols[1]:
    with st.container(border=True):
        st.markdown("#### 🗺️ 门店地图")
        st.metric("覆盖省份", "22 省")
        st.markdown("👉 从左侧导航进入")
with cols[2]:
    with st.container(border=True):
        st.markdown("#### ⚠️ 库存预警")
        st.metric("预警项", "23 项")
        st.markdown("👉 从左侧导航进入")

st.markdown("---")

st.subheader("🏪 各门店销售排行")
store_data = pd.DataFrame({
    "门店": ["三亚国际免税城", "海口国际免税城", "海口日月广场", "美兰机场", "凤凰机场", "海旅免税城"],
    "销售额(万)": [5200, 3800, 2100, 1500, 1200, 850],
    "环比(%)": [8.5, 6.2, 4.1, -2.3, 5.0, 3.5],
})
st.dataframe(store_data, use_container_width=True, hide_index=True)

st.caption(f"📊 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
