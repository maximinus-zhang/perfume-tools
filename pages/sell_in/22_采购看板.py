import streamlit as st
import pandas as pd
from datetime import datetime
from utils.oss_helper import upload_section, read_excel_from_oss

# ===== 上传区域（侧边栏） =====
upload_section("sell_in/purchase_data.xlsx", "上传采购数据")

# ===== 从 OSS 读取数据（如果存在） =====
df_oss = read_excel_from_oss("sell_in/purchase_data.xlsx")

# ===== 原有界面（保持不变） =====
st.title("📦 Sell In · 采购总看板")
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)
col1.metric("📋 本月采购单", "168 单", "+8.2%")
col2.metric("💰 采购金额", "¥3,850万", "+5.6%")
col3.metric("📦 库存周转率", "4.2 天", "-0.5天")
col4.metric("✅ 满足率", "87.5%", "+2.1%")

st.markdown("---")
st.subheader("📌 模块快捷入口")

cols = st.columns(2)
with cols[0]:
    with st.container(border=True):
        st.markdown("#### ✅ 满足率分析")
        st.metric("本月满足率", "87.5%")
        st.markdown("👉 从左侧导航进入")
with cols[1]:
    with st.container(border=True):
        st.markdown("#### 📊 采购趋势")
        st.caption("近6月采购金额走势")
        st.bar_chart({"采购额": [320, 285, 350, 380, 365, 410]})

st.markdown("---")
st.subheader("📈 月度采购趋势")
trend = pd.DataFrame({
    "月份": ["1月","2月","3月","4月","5月","6月"],
    "金额(万)": [320, 285, 350, 380, 365, 410],
})
st.line_chart(trend.set_index("月份"))

st.caption(f"📊 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
