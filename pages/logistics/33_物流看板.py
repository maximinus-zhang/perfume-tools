import streamlit as st
import pandas as pd
from datetime import datetime
from utils.oss_helper import read_excel_from_oss

st.title("🚚 物流模块 · 物流总看板")

# ===== 从 OSS 读取订单数据（与订单管理共用同一个文件，读取 Sheet 1）= 
df_oss = read_excel_from_oss("logistics/order_data.xlsx", sheet_name=0)

if not df_oss.empty:
    # 清理列名
    df_oss.columns = [c.strip() for c in df_oss.columns]

    # 只保留 ORD- 开头的有效订单
    first_col = df_oss.columns[0]
    df_oss = df_oss[df_oss[first_col].astype(str).str.startswith('ORD-', na=False)]
    df_oss = df_oss.reset_index(drop=True)

    has_data = not df_oss.empty
else:
    has_data = False

if has_data:
    st.success(f"✅ 已加载订单数据（共 {len(df_oss)} 条）")
else:
    st.info("📊 暂无上传数据，显示示例信息")

# ===== 数据来源标识 =====
st.markdown("---")
st.caption(f"{'📤 数据来源：订单管理上传' if has_data else '📊 暂无数据'} | 请先在订单管理页面上传数据")

# ===== KPI 指标（从真实数据统计） =====
if has_data:
    # 找到状态列
    status_col = None
    for col in df_oss.columns:
        if '状态' in col:
            status_col = col
            break

    # 找到实际交货和预计交货列
    delivery_col = None
    est_delivery_col = None
    for col in df_oss.columns:
        if '实际交货' in col:
            delivery_col = col
        if '预计交货' in col:
            est_delivery_col = col

    if status_col:
        in_transit = len(df_oss[df_oss[status_col].astype(str).str.contains('运输')])
        delivered = len(df_oss[df_oss[status_col].astype(str).str.contains('签收')])
        pending = len(df_oss[df_oss[status_col].astype(str).str.contains('待处理')])
        abnormal = len(df_oss[df_oss[status_col].astype(str).str.contains('异常|退回|拒收')])
    else:
        in_transit = 45
        delivered = 128
        pending = 15
        abnormal = 5

    # 计算平均时效
    if delivery_col and est_delivery_col:
        df_temp = df_oss.copy()
        df_temp[delivery_col] = pd.to_datetime(df_temp[delivery_col], errors='coerce')
        df_temp[est_delivery_col] = pd.to_datetime(df_temp[est_delivery_col], errors='coerce')
        valid_delivery = df_temp[df_temp[delivery_col].notna()]
        if len(valid_delivery) > 0:
            avg_days = max((valid_delivery[delivery_col] - valid_delivery[est_delivery_col]).dt.days.mean(), 0)
        else:
            avg_days = 3.2
    else:
        avg_days = 3.2
else:
    in_transit = 45
    delivered = 128
    pending = 15
    abnormal = 5
    avg_days = 3.2

col1, col2, col3, col4 = st.columns(4)
col1.metric("🚚 运输中订单", f"{in_transit} 单")
col2.metric("✅ 已签收", f"{delivered} 单")
col3.metric("⏱ 平均时效", f"{avg_days:.1f} 天")
col4.metric("⚠️ 异常件", f"{abnormal} 单")

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
        if has_data and status_col:
            total = len(df_oss)
            on_time = total - abnormal - pending
            on_time_rate = on_time / total * 100 if total > 0 else 94.2
        else:
            on_time_rate = 94.2
        st.metric("准时率", f"{on_time_rate:.1f}%")
        st.caption("目标: ≥95%")

st.markdown("---")
st.subheader("🚚 各物流商时效对比")

if has_data:
    carrier_col = None
    for col in df_oss.columns:
        if '物流' in col:
            carrier_col = col
            break

    if carrier_col:
        carrier_stats = df_oss.groupby(carrier_col).agg(
            订单数=('订单号', 'count') if '订单号' in df_oss.columns else (carrier_col, 'count')
        ).reset_index()

        if delivery_col and est_delivery_col:
            df_temp = df_oss.copy()
            df_temp[delivery_col] = pd.to_datetime(df_temp[delivery_col], errors='coerce')
            df_temp[est_delivery_col] = pd.to_datetime(df_temp[est_delivery_col], errors='coerce')
            df_temp['时效(天)'] = (df_temp[delivery_col] - df_temp[est_delivery_col]).dt.days.clip(lower=0)
            carrier_avg = df_temp.groupby(carrier_col)['时效(天)'].mean().reset_index()
            carrier_stats = carrier_stats.merge(carrier_avg, on=carrier_col)
            carrier_stats.columns = [carrier_col, '订单数', '平均时效(天)']
            on_time = df_temp[df_temp['时效(天)'] <= 0].groupby(carrier_col).size().reset_index(name='准时数')
            carrier_stats = carrier_stats.merge(on_time, on=carrier_col, how='left')
            carrier_stats['准时数'] = carrier_stats['准时数'].fillna(0)
            carrier_stats['准时率(%)'] = (carrier_stats['准时数'] / carrier_stats['订单数'] * 100).round(1)
            carrier_stats = carrier_stats.drop(columns=['准时数'])
        else:
            carrier_stats.columns = [carrier_col, '订单数']
            carrier_stats['平均时效(天)'] = '-'
            carrier_stats['准时率(%)'] = '-'

        st.dataframe(carrier_stats, width='stretch', hide_index=True)
    else:
        st.dataframe(pd.DataFrame({"物流商": ["顺丰", "京东", "中通", "德邦"],
                                    "平均时效(天)": [2.1, 2.5, 3.8, 4.2],
                                    "准时率(%)": [98.5, 96.2, 91.0, 88.5]}),
                     width='stretch', hide_index=True)
else:
    carrier = pd.DataFrame({
        "物流商": ["顺丰", "京东", "中通", "德邦"],
        "平均时效(天)": [2.1, 2.5, 3.8, 4.2],
        "准时率(%)": [98.5, 96.2, 91.0, 88.5],
    })
    st.dataframe(carrier, width='stretch', hide_index=True)

st.caption(f"📊 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
