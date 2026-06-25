import streamlit as st
import pandas as pd
from datetime import datetime
from utils.oss_helper import upload_section, read_excel_from_oss

# ===== 上传区域 =====
with st.sidebar:
    st.markdown("---")
    upload_section("sell_in/purchase_data.xlsx", "上传采购数据")

# ===== 读取数据 =====
df_oss = read_excel_from_oss("sell_in/purchase_data.xlsx")
has_data = not df_oss.empty

if has_data:
    df_oss.columns = [c.strip() for c in df_oss.columns]
    st.success(f"✅ 已加载采购数据（共 {len(df_oss)} 条）")
else:
    st.info("📊 暂无上传数据，显示示例数据")

st.title("📦 Sell In · 采购总看板")
st.markdown("---")

# ===== KPI 统计 =====
if has_data:
    total_orders = len(df_oss)

    # 采购金额
    amount_col = None
    for col in df_oss.columns:
        if '金额' in col:
            amount_col = col
            break
    total_amount = df_oss[amount_col].sum() if amount_col else 38500000

    # 满足率：直接从"满足率(%)"列读取平均值
    satisfy_col = None
    for col in df_oss.columns:
        if '满足' in col:
            satisfy_col = col
            break

    if satisfy_col:
        # 直接取平均值（用户填的百分比数值）
        satisfy_values = pd.to_numeric(df_oss[satisfy_col], errors='coerce')
        if satisfy_values.notna().sum() > 0:
            satisfy_rate = satisfy_values.mean()
        else:
            satisfy_rate = 87.5
    else:
        satisfy_rate = 87.5
else:
    total_orders = 168
    total_amount = 38500000
    satisfy_rate = 87.5

col1, col2, col3 = st.columns(3)
col1.metric("📋 本月采购单", f"{total_orders} 单")
col2.metric("💰 采购金额", f"¥{total_amount/10000:.0f}万")
col3.metric("✅ 满足率", f"{satisfy_rate:.1f}%")

st.markdown("---")
st.subheader("📌 模块快捷入口")

cols = st.columns(2)
with cols[0]:
    with st.container(border=True):
        st.markdown("#### ✅ 满足率分析")
        st.metric("平均满足率", f"{satisfy_rate:.1f}%")
        st.markdown("👉 从左侧导航进入")
with cols[1]:
    with st.container(border=True):
        st.markdown("#### 📊 采购趋势")
        st.caption("各月份采购金额走势（来自上传数据）")

st.markdown("---")

# ===== 月度采购趋势（完全从上传数据读取） =====
st.subheader("📈 月度采购趋势")

if has_data:
    date_col = None
    for col in df_oss.columns:
        if '下单日期' in col or '日期' in col:
            date_col = col
            break

    if date_col and amount_col:
        df_temp = df_oss.copy()
        # 处理 Excel 日期数字格式
        df_temp[date_col] = pd.to_numeric(df_temp[date_col], errors='coerce')
        df_temp[date_col] = pd.to_datetime(df_temp[date_col], origin='1899-12-30', unit='D', errors='coerce')
        # 如果还是无效，尝试直接解析字符串
        df_temp[date_col] = df_temp[date_col].fillna(pd.to_datetime(df_oss[date_col], errors='coerce'))

        df_temp['月份'] = df_temp[date_col].dt.strftime('%Y-%m')
        monthly = df_temp.groupby('月份')[amount_col].sum().reset_index()
        monthly.columns = ['月份', '金额']

        if len(monthly) > 0:
            # 按月份排序
            monthly = monthly.sort_values('月份')
            chart_data = monthly.set_index('月份')
            # 金额转换为万
            chart_data['金额(万)'] = (chart_data['金额'] / 10000).round(0)
            st.line_chart(chart_data['金额(万)'])
            # 显示数据表
            with st.expander("查看月度数据明细"):
                st.dataframe(monthly, use_container_width=True, hide_index=True)
        else:
            st.info("无法解析日期列，请检查日期格式")
    else:
        st.info("缺少日期列或金额列，无法生成趋势图")
else:
    st.info("上传采购数据后，此处将显示月度趋势")

st.caption(f"📊 {datetime.now().strftime('%Y-%m-%d %H:%M')} | {'📤 使用上传数据' if has_data else '📊 暂无数据，请先上传'}")

# ===== 数据明细查看 =====
if has_data:
    st.markdown("---")
    with st.expander("📋 查看上传的采购数据明细"):
        st.dataframe(df_oss, use_container_width=True, hide_index=True)
