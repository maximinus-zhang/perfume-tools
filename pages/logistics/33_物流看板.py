import streamlit as st
import pandas as pd
from datetime import datetime
from utils.oss_helper import upload_section, read_excel_from_oss

st.title("🚚 物流模块 · 物流总看板")

# ===== 上传区域（侧边栏） =====
with st.sidebar:
    st.markdown("---")
    upload_section("logistics/logistics_data.xlsx", "上传物流数据")

# ===== 从 OSS 读取数据 =====
df_oss = read_excel_from_oss("logistics/logistics_data.xlsx")
has_data = not df_oss.empty

if has_data:
    # 清理列名
    df_oss.columns = [c.strip() for c in df_oss.columns]
    st.success("✅ 已加载上传的物流数据")
else:
    # 使用默认示例数据
    df_oss = pd.DataFrame({
        "物流商": ["顺丰", "京东", "中通", "德邦"],
        "平均时效(天)": [2.1, 2.5, 3.8, 4.2],
        "准时率(%)": [98.5, 96.2, 91.0, 88.5],
    })

st.markdown("---")

# 从上传数据读取 KPI 值（如果存在对应列）
kpi_transit = len(df_oss[df_oss.get('状态', '').astype(str).str.contains('运输', na=False)]) if '状态' in df_oss.columns else 45
kpi_delivered = len(df_oss[df_oss.get('状态', '').astype(str).str.contains('签收', na=False)]) if '状态' in df_oss.columns else 128
kpi_avg_time = df_oss['平均时效(天)'].mean() if '平均时效(天)' in df_oss.columns else 3.2
kpi_abnormal = len(df_oss[df_oss.get('状态', '').astype(str).str.contains('异常', na=False)]) if '状态' in df_oss.columns else 5

col1, col2, col3, col4 = st.columns(4)
col1.metric("🚚 运输中订单", f"{kpi_transit} 单", "+3")
col2.metric("✅ 今日签收", f"{kpi_delivered} 单", "+12.5%")
col3.metric("⏱ 平均时效", f"{kpi_avg_time:.1f} 天", "-0.3天")
col4.metric("⚠️ 异常件", f"{kpi_abnormal} 单", "-2单")

st.markdown("---")
st.subheader("📌 模块快捷入口")

cols = st.columns(2)
with cols[0]:
    with st.container(border=True):
        st.markdown("#### 📦 订单管理")
        st.metric("待处理订单", "15 单")
        st.markdown("👉 从左侧导航进入")
with cols[1]:
    with st.container(border=True):
        st.markdown("#### 🚚 物流时效")
        st.metric("准时率", "94.2%")
        st.caption("目标: ≥95%")

st.markdown("---")
st.subheader("🚚 各物流商时效对比")
st.dataframe(df_oss, use_container_width=True, hide_index=True)

st.caption(f"📊 {datetime.now().strftime('%Y-%m-%d %H:%M')} | {'📤 使用上传数据' if has_data else '📊 使用示例数据'}")
