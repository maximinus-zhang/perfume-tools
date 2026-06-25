import streamlit as st
import pandas as pd
from datetime import datetime
from utils.oss_helper import read_excel_from_oss

st.title("🚚 物流模块 · 物流总看板")

# ===== 从 OSS 读取订单数据（与订单管理共用同一个文件） =====
df_oss = read_excel_from_oss("logistics/order_data.xlsx"，sheet_name=0)
has_data = not df_oss.empty

if has_data:
    # 清理列名
    df_oss.columns = [c.strip() for c in df_oss.columns]
    
    # 确保状态列存在
    status_col = None
    for col in df_oss.columns:
        if '状态' in col:
            status_col = col
            break
    
    # 物流商列
    carrier_col = None
    for col in df_oss.columns:
        if '物流' in col:
            carrier_col = col
            break
    
    # 实际交货列
    delivery_col = None
    for col in df_oss.columns:
        if '实际交货' in col:
            delivery_col = col
            break
    
    # 预计交货列
    est_delivery_col = None
    for col in df_oss.columns:
        if '预计交货' in col:
            est_delivery_col = col
            break
    
    st.success(f"✅ 已加载订单数据（共 {len(df_oss)} 条）")
else:
    st.info("📊 暂无上传数据，显示示例信息")
    # 没有数据时使用默认值

# ===== KPI 指标（从订单数据中真实统计） =====
st.markdown("---")

if has_data and status_col:
    # 从真实数据统计
    in_transit = len(df_oss[df_oss[status_col].astype(str).str.contains('运输')])
    delivered = len(df_oss[df_oss[status_col].astype(str).str.contains('签收')])
    pending = len(df_oss[df_oss[status_col].astype(str).str.contains('待处理')])
    abnormal = len(df_oss[df_oss[status_col].astype(str).str.contains('异常|退回|拒收')])
    
    # 计算平均时效（如果有实际交货和预计交货）
    if delivery_col and est_delivery_col:
        df_temp = df_oss.copy()
        df_temp[delivery_col] = pd.to_datetime(df_temp[delivery_col], errors='coerce')
        df_temp[est_delivery_col] = pd.to_datetime(df_temp[est_delivery_col], errors='coerce')
        valid_delivery = df_temp[df_temp[delivery_col].notna()]
        if len(valid_delivery) > 0:
            avg_days = (valid_delivery[delivery_col] - valid_delivery[est_delivery_col]).dt.days.mean()
            avg_days = max(avg_days, 0)  # 不允许负数
        else:
            avg_days = 3.2
    else:
        avg_days = 3.2
else:
    # 默认值
    in_transit = 45
    delivered = 128
    pending = 15
    abnormal = 5
    avg_days = 3.2

col1, col2, col3, col4 = st.columns(4)
col1.metric("🚚 运输中订单", f"{in_transit} 单", "+3")
col2.metric("✅ 已签收", f"{delivered} 单", "+12.5%")
col3.metric("⏱ 平均时效", f"{avg_days:.1f} 天", "-0.3天")
col4.metric("⚠️ 异常件", f"{abnormal} 单", "-2单")

st.markdown("---")
st.subheader("📌 模块快捷入口")

cols = st.columns(2)
with cols[0]:
    with st.container(border=True):
        st.markdown("#### 📦 订单管理")
        st.metric("待处理订单", f"{pending} 单")
        st.markdown("👉 从左侧导航进入")
with cols[1]:
    with st.container(border=True):
        st.markdown("#### 🚚 物流时效")
        st.metric("准时率", f"{94.2 if not has_data else 100 - (abnormal / max(len(df_oss), 1) * 100):.1f}%")
        st.caption("目标: ≥95%")

# ===== 物流商时效对比（如果数据中有物流商列） =====
st.markdown("---")
st.subheader("🚚 各物流商时效对比")

if has_data and carrier_col:
    carrier_stats = df_oss.groupby(carrier_col).agg(
        订单数=('订单号', 'count') if '订单号' in df_oss.columns else (carrier_col, 'count')
    ).reset_index()
    
    # 如果能计算时效
    if delivery_col and est_delivery_col:
        df_temp = df_oss.copy()
        df_temp[delivery_col] = pd.to_datetime(df_temp[delivery_col], errors='coerce')
        df_temp[est_delivery_col] = pd.to_datetime(df_temp[est_delivery_col], errors='coerce')
        df_temp['时效(天)'] = (df_temp[delivery_col] - df_temp[est_delivery_col]).dt.days
        df_temp['时效(天)'] = df_temp['时效(天)'].clip(lower=0)
        
        carrier_avg = df_temp.groupby(carrier_col)['时效(天)'].mean().reset_index()
        carrier_stats = carrier_stats.merge(carrier_avg, on=carrier_col)
        carrier_stats.columns = [carrier_col, '订单数', '平均时效(天)']
        
        # 准时率（时效 <= 0 的占比）
        on_time = df_temp[df_temp['时效(天)'] <= 0].groupby(carrier_col).size().reset_index(name='准时数')
        carrier_stats = carrier_stats.merge(on_time, on=carrier_col, how='left')
        carrier_stats['准时数'] = carrier_stats['准时数'].fillna(0)
        carrier_stats['准时率(%)'] = (carrier_stats['准时数'] / carrier_stats['订单数'] * 100).round(1)
        carrier_stats = carrier_stats.drop(columns=['准时数'])
    else:
        carrier_stats.columns = [carrier_col, '订单数']
        carrier_stats['平均时效(天)'] = '-'
        carrier_stats['准时率(%)'] = '-'
    
    st.dataframe(carrier_stats, use_container_width=True, hide_index=True)
else:
    # 显示示例数据
    carrier = pd.DataFrame({
        "物流商": ["顺丰", "京东", "中通", "德邦"],
        "平均时效(天)": [2.1, 2.5, 3.8, 4.2],
        "准时率(%)": [98.5, 96.2, 91.0, 88.5],
    })
    st.dataframe(carrier, use_container_width=True, hide_index=True)

st.caption(f"📊 {datetime.now().strftime('%Y-%m-%d %H:%M')} | {'📤 数据来源：订单管理上传' if has_data else '📊 使用示例数据（请先在订单管理页面上传数据）'}")
