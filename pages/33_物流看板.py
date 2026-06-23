import streamlit as st
import pandas as pd
from datetime import datetime

st.title("🚚 物流模块 · 物流总看板")
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)
col1.metric("🚚 运输中订单", "45 单", "+3")
col2.metric("✅ 今日签收", "128 单", "+12.5%")
col3.metric("⏱ 平均时效", "3.2 天", "-0.3天")
col4.metric("⚠️ 异常件", "5 单", "-2单")

st.markdown("---")
st.subheader("📌 模块快捷入口")

cols = st.columns(2)
with cols[0]:
    with st.container(border=True):
        st.markdown("#### 📦 订单管理")
        st.metric("待处理订单", "15 单")
        st.page_link("pages/9_订单管理.py", label="进入 →", use_container_width=True)
with cols[1]:
    with st.container(border=True):
        st.markdown("#### 🚚 物流时效")
        st.metric("准时率", "94.2%")
        st.caption("目标: ≥95%")

st.markdown("---")
st.subheader("🚚 各物流商时效对比")
carrier = pd.DataFrame({
    "物流商": ["顺丰", "京东", "中通", "德邦"],
    "平均时效(天)": [2.1, 2.5, 3.8, 4.2],
    "准时率(%)": [98.5, 96.2, 91.0, 88.5],
})
st.dataframe(carrier, use_container_width=True, hide_index=True)

st.caption(f"📊 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
