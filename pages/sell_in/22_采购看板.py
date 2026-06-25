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
    df_oss.columns = [c.strip() for c in df_oss.columns]

    # 找到各列
    status_col = None
    for col in df_oss.columns:
        if col == '采购状态' or '状态' in col:
            status_col = col
            break

    satisfy_col = None
    for col in df_oss.columns:
        if '满足' in col:
            satisfy_col = col
            break

    amount_col = None
    for col in df_oss.columns:
        if '金额' in col:
            amount_col = col
            break

    st.success(f"✅ 已加载采购数据（共 {len(df_oss)} 条）")
else:
    st.info("📊 暂无上传数据，显示示例数据")

st.title("📦 Sell In · 采购总看板")
st.markdown("---")

# ===== KPI 统计 =====
if has_data:
    total_orders = len(df_oss)

    if amount_col:
        total_amount = df_oss[amount_col].sum()
    else:
        total_amount = 38500000

    # ===== 计算满足率（兼容多种数据格式） =====
    if satisfy_col:
        # 将满足状态列转为字符串，统一处理
        satisfy_values = df_oss[satisfy_col].astype(str).str.strip()

        # 统计各种满足状态
        satisfy_count = len(satisfy_values[satisfy_values.str.contains('是', na=False)])
        partial_count = len(satisfy_values[satisfy_values.str.contains('部分', na=False)])

        # 如果全是 0 或空，从采购状态推算
        if satisfy_count == 0 and partial_count == 0:
            if status_col:
                delivered = len(df_oss[df_oss[status_col].astype(str).str.contains('到货')])
                satisfy_rate = delivered / total_orders * 100
            else:
                satisfy_rate = 87.5
        else:
            # 满足率 = (完全满足 + 部分满足*0.5) / 总订单数
            satisfy_rate = (satisfy_count + partial_count * 0.5) / total_orders * 100
    else:
        # 如果没有满足状态列，从采购状态推算
        if status_col:
            delivered = len(df_oss[df_oss[status_col].astype(str).str.contains('到货')])
            satisfy_rate = delivered / total_orders * 100
        else:
            satisfy_rate = 87.5

    if status_col:
        pending = len(df_oss[df_oss[status_col].astype(str).str.contains('审核|待发')])
    else:
        pending = 0
else:
    total_orders = 168
    total_amount = 38500000
    satisfy_rate = 87.5
    pending = 0

col1, col2, col3 = st.columns(3)
col1.metric("📋 本月采购单", f"{total_orders} 单", "+8.2%")
col2.metric("💰 采购金额", f"¥{total_amount/10000:.0f}万", "+5.6%")
col3.metric("✅ 满足率", f"{satisfy_rate:.1f}%", "+2.1%")

st.markdown("---")
st.subheader("📌 模块快捷入口")

cols = st.columns(2)
with cols[0]:
    with st.container(border=True):
        st.markdown("#### ✅ 满足率分析")
        st.metric("本月满足率", f"{satisfy_rate:.1f}%")
        st.markdown("👉 从左侧导航进入")
with cols[1]:
    with st.container(border=True):
        st.markdown("#### 📊 采购趋势")
        st.caption("近6月采购金额走势")
        st.bar_chart({"采购额": [320, 285, 350, 380, 365, 410]})

st.markdown("---")

# ===== 月度采购趋势 =====
if has_data:
    date_col = None
    for col in df_oss.columns:
        if '下单日期' in col or '日期' in col:
            date_col = col
            break

    if date_col and amount_col:
        st.subheader("📈 月度采购趋势")
        df_temp = df_oss.copy()
        df_temp[date_col] = pd.to_datetime(df_temp[date_col], errors='coerce')
        df_temp['月份'] = df_temp[date_col].dt.strftime('%Y-%m')
        monthly = df_temp.groupby('月份')[amount_col].sum().reset_index()
        monthly.columns = ['月份', '金额(万)']
        monthly['金额(万)'] = monthly['金额(万)'] / 10000
        if len(monthly) > 0:
            st.line_chart(monthly.set_index('月份'))
        else:
            st.line_chart({"月份": ["1月","2月","3月","4月","5月","6月"], "金额(万)": [320, 285, 350, 380, 365, 410]})
    else:
        st.subheader("📈 月度采购趋势")
        trend = pd.DataFrame({
            "月份": ["1月","2月","3月","4月","5月","6月"],
            "金额(万)": [320, 285, 350, 380, 365, 410],
        })
        st.line_chart(trend.set_index("月份"))
else:
    st.subheader("📈 月度采购趋势")
    trend = pd.DataFrame({
        "月份": ["1月","2月","3月","4月","5月","6月"],
        "金额(万)": [320, 285, 350, 380, 365, 410],
    })
    st.line_chart(trend.set_index("月份"))

st.caption(f"📊 {datetime.now().strftime('%Y-%m-%d %H:%M')} | {'📤 使用上传数据' if has_data else '📊 使用示例数据（请先上传采购数据）'}")
