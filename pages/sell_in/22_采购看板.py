import streamlit as st
import pandas as pd
from datetime import datetime
from utils.oss_helper import upload_section, read_excel_from_oss

# ===== 上传区域（侧边栏） =====
with st.sidebar:
    st.markdown("---")
    upload_section("sell_in/purchase_data.xlsx", "上传采购数据")

# ===== 从 OSS 读取数据 =====
df_oss = read_excel_from_oss("sell_in/purchase_data.xlsx")
has_data = not df_oss.empty

if has_data:
    # 清理列名
    df_oss.columns = [c.strip() for c in df_oss.columns]
    
    # 找到状态列
    status_col = None
    for col in df_oss.columns:
        if '状态' in col:
            status_col = col
            break
    
    # 找到金额列
    amount_col = None
    for col in df_oss.columns:
        if '金额' in col:
            amount_col = col
            break
    
    # 找到日期列
    date_col = None
    for col in df_oss.columns:
        if '下单日期' in col or '日期' in col:
            date_col = col
            break
    
    st.success(f"✅ 已加载采购数据（共 {len(df_oss)} 条）")
else:
    st.info("📊 暂无上传数据，显示示例数据")

st.title("📦 Sell In · 采购总看板")
st.markdown("---")

# ===== KPI 从真实数据统计 =====
if has_data:
    total_orders = len(df_oss)
    
    if amount_col:
        total_amount = df_oss[amount_col].sum()
    else:
        total_amount = 38500000  # 默认值
    
    if status_col:
        delivered = len(df_oss[df_oss[status_col].astype(str).str.contains('到货')])
        pending = len(df_oss[df_oss[status_col].astype(str).str.contains('审核|待发')])
        in_transit = len(df_oss[df_oss[status_col].astype(str).str.contains('运输')])
    else:
        delivered = 0
        pending = 0
        in_transit = 0
else:
    # 默认示例值
    total_orders = 168
    total_amount = 38500000
    delivered = 0
    pending = 0
    in_transit = 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("📋 本月采购单", f"{total_orders} 单", "+8.2%")
col2.metric("💰 采购金额", f"¥{total_amount/10000:.0f}万", "+5.6%")
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

# ===== 月度采购趋势（如果有日期数据） =====
if has_data and date_col:
    st.subheader("📈 月度采购趋势")
    df_temp = df_oss.copy()
    df_temp[date_col] = pd.to_datetime(df_temp[date_col], errors='coerce')
    
    if amount_col:
        df_temp['月份'] = df_temp[date_col].dt.strftime('%Y-%m')
        monthly = df_temp.groupby('月份')[amount_col].sum().reset_index()
        monthly.columns = ['月份', '金额(万)']
        monthly['金额(万)'] = monthly['金额(万)'] / 10000
        if len(monthly) > 0:
            st.line_chart(monthly.set_index('月份'))
        else:
            st.line_chart({"月份": ["1月","2月","3月","4月","5月","6月"], "金额(万)": [320, 285, 350, 380, 365, 410]})
    else:
        st.line_chart({"月份": ["1月","2月","3月","4月","5月","6月"], "金额(万)": [320, 285, 350, 380, 365, 410]})
else:
    st.subheader("📈 月度采购趋势")
    trend = pd.DataFrame({
        "月份": ["1月","2月","3月","4月","5月","6月"],
        "金额(万)": [320, 285, 350, 380, 365, 410],
    })
    st.line_chart(trend.set_index("月份"))

st.caption(f"📊 {datetime.now().strftime('%Y-%m-%d %H:%M')} | {'📤 使用上传数据' if has_data else '📊 使用示例数据（请先上传采购数据）'}")
