import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import random
from utils.oss_helper import upload_section, read_excel_from_oss

st.title("📋 香水供应链·订单管理看板")

# ============================================================
# 上传区域（侧边栏）
# ============================================================
with st.sidebar:
    st.markdown("---")
    upload_section("logistics/order_data.xlsx", "上传订单数据")

# ============================================================
# 示例数据生成函数（放在前面，供 load_orders 使用）
# ============================================================
def generate_sample_orders(n=200):
    """生成示例订单数据"""
    brands = ["CHANEL", "DIOR", "HERMES", "JO MALONE", "TOM FORD",
              "GUCCI", "YSL", "ARMANI", "BVLGARI", "LOEWE"]
    stores = ["三亚国际免税城", "海口国际免税城", "海口日月广场免税店",
              "海口美兰机场免税店", "三亚凤凰机场免税店"]
    statuses = ["已发货", "运输中", "已签收", "待处理"]
    categories = ["香水EDP", "香水EDT", "古龙水", "旅行装", "礼盒套装"]

    orders = []
    base_date = datetime(2025, 6, 1)

    for i in range(n):
        order_date = base_date - timedelta(days=random.randint(0, 180))
        estimated_delivery = order_date + timedelta(days=random.randint(3, 15))
        actual_delivery = estimated_delivery + timedelta(days=random.randint(-2, 5))

        orders.append({
            '订单号': f'ORD-{202506:06d}-{i+1:04d}',
            '品牌': random.choice(brands),
            '产品类别': random.choice(categories),
            '门店': random.choice(stores),
            '数量': random.randint(1, 100),
            '单价(USD)': round(random.uniform(50, 500), 2),
            '总金额(USD)': 0,
            '下单日期': order_date.strftime('%Y-%m-%d'),
            '预计交货': estimated_delivery.strftime('%Y-%m-%d'),
            '实际交货': actual_delivery.strftime('%Y-%m-%d') if random.random() > 0.2 else '',
            '状态': random.choices(statuses, weights=[0.3, 0.3, 0.3, 0.1])[0],
            '物流商': random.choice(['顺丰', '京东', '中通', '德邦']),
            '运单号': f'SF{random.randint(1000000000, 9999999999)}',
        })

    df = pd.DataFrame(orders)
    df['总金额(USD)'] = df['数量'] * df['单价(USD)']
    df['交货延迟(天)'] = df.apply(
        lambda r: max(0, (datetime.strptime(r['实际交货'], '%Y-%m-%d') -
                          datetime.strptime(r['预计交货'], '%Y-%m-%d')).days)
        if r['实际交货'] else 0, axis=1
    )
    return df


# ============================================================
# 加载订单数据（优先从 OSS，不存在则用示例数据）
# ============================================================
def load_orders():
    """从 OSS 读取订单数据（Sheet 2），不存在则生成示例数据"""
    # 使用 prefix_filter 自动过滤非 ORD- 开头的行
    # ⚠️ 数据在第二个 Sheet（索引 1），不是第一个 Sheet
    df_oss = read_excel_from_oss("logistics/order_data.xlsx", sheet_name=1, prefix_filter='ORD-')

    if not df_oss.empty:
        df = df_oss.copy()
        df.columns = [c.strip() for c in df.columns]

        # 检查必要列
        required = ['订单号', '品牌', '数量', '单价(USD)', '下单日期', '预计交货', '状态']
        missing = [c for c in required if c not in df.columns]
        if missing:
            st.error(f"文件缺少列：{missing}，请检查模板格式")
            return generate_sample_orders(300)

        # 计算总金额
        if '总金额(USD)' not in df.columns:
            df['总金额(USD)'] = pd.to_numeric(df['数量'], errors='coerce') * pd.to_numeric(df['单价(USD)'], errors='coerce')
        else:
            df['总金额(USD)'] = df['总金额(USD)'].fillna(
                pd.to_numeric(df['数量'], errors='coerce') * pd.to_numeric(df['单价(USD)'], errors='coerce')
            )

        # 日期转字符串
        for col in ['下单日期', '预计交货', '实际交货']:
            if col in df.columns:
                df[col] = df[col].astype(str)

        # 计算延迟
        df['交货延迟(天)'] = df.apply(
            lambda r: max(0, (pd.to_datetime(r['实际交货'], errors='coerce') -
                              pd.to_datetime(r['预计交货'], errors='coerce')).days)
            if pd.notna(r.get('实际交货')) and str(r['实际交货']).strip() not in ['', 'nan', 'NaT'] else 0,
            axis=1
        )

        if '状态' not in df.columns:
            df['状态'] = '已发货'

        st.success(f"✅ 已加载上传的真实订单数据（共 {len(df)} 条）")
        return df
    else:
        st.info("📊 暂无上传数据，使用示例数据")
        return generate_sample_orders(300)


# ============================================================
# 数据加载
# ============================================================
df = load_orders()

# ============================================================
# 筛选器
# ============================================================
with st.sidebar:
    st.header("🔍 筛选条件")
    date_range = st.date_input("下单日期范围", [datetime(2025, 1, 1), datetime(2025, 6, 30)])
    selected_brands = st.multiselect("品牌", sorted(df['品牌'].unique()), default=[])
    selected_stores = st.multiselect("门店", sorted(df['门店'].unique()), default=[])
    selected_status = st.multiselect("订单状态", sorted(df['状态'].unique()), default=[])

# ============================================================
# 数据过滤
# ============================================================
filtered = df.copy()
if len(date_range) == 2:
    filtered = filtered[(filtered['下单日期'] >= date_range[0].strftime('%Y-%m-%d')) &
                        (filtered['下单日期'] <= date_range[1].strftime('%Y-%m-%d'))]
if selected_brands:
    filtered = filtered[filtered['品牌'].isin(selected_brands)]
if selected_stores:
    filtered = filtered[filtered['门店'].isin(selected_stores)]
if selected_status:
    filtered = filtered[filtered['状态'].isin(selected_status)]

# ============================================================
# KPI
# ============================================================
total_orders = len(filtered)
total_revenue = filtered['总金额(USD)'].sum()
avg_order_value = filtered['总金额(USD)'].mean()
avg_delay = filtered[filtered['状态'] == '已签收']['交货延迟(天)'].mean()
pending_orders = len(filtered[filtered['状态'] == '待处理'])

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("📦 总订单数", f"{total_orders}")
col2.metric("💰 总销售额", f"${total_revenue:,.0f}")
col3.metric("📊 平均客单价", f"${avg_order_value:,.0f}")
col4.metric("⏱ 平均延迟(天)", f"{avg_delay:.1f}" if not pd.isna(avg_delay) else "0")
col5.metric("⚠️ 待处理", f"{pending_orders}", delta_color="inverse")

# ============================================================
# 图表
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs(["📊 销售分析", "🏪 门店对比", "🚚 物流状态", "📋 订单明细"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        brand_sales = filtered.groupby('品牌')['总金额(USD)'].sum().reset_index()
        fig = px.bar(brand_sales.sort_values('总金额(USD)', ascending=True),
                     x='总金额(USD)', y='品牌', orientation='h',
                     title="各品牌销售额 Top10",
                     color='总金额(USD)', color_continuous_scale='Blues', text_auto='.0s')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        filtered['下单月份'] = pd.to_datetime(filtered['下单日期']).dt.strftime('%Y-%m')
        monthly = filtered.groupby('下单月份').agg({'总金额(USD)': 'sum', '订单号': 'count'}).reset_index()
        fig = px.line(monthly, x='下单月份', y='总金额(USD)', title="月度销售额趋势", markers=True)
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        store_sales = filtered.groupby('门店')['总金额(USD)'].sum().reset_index()
        fig = px.pie(store_sales, values='总金额(USD)', names='门店', title="各门店销售额占比")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        store_orders = filtered.groupby('门店')['订单号'].count().reset_index()
        fig = px.bar(store_orders, x='门店', y='订单号', title="各门店订单量", color='订单号',
                     color_continuous_scale='Oranges', text_auto=True)
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    col1, col2, col3 = st.columns(3)
    with col1:
        status_dist = filtered['状态'].value_counts().reset_index()
        fig = px.pie(status_dist, values='count', names='状态', title="订单状态分布",
                     color_discrete_map={'已发货': '#3498db', '运输中': '#f39c12',
                                         '已签收': '#2ecc71', '待处理': '#e74c3c'})
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        carrier_dist = filtered['物流商'].value_counts().reset_index()
        fig = px.bar(carrier_dist, x='物流商', y='count', title="物流商使用分布",
                     color='count', color_continuous_scale='Greens', text_auto=True)
        st.plotly_chart(fig, use_container_width=True)
    with col3:
        delay_dist = filtered[filtered['交货延迟(天)'] > 0]['交货延迟(天)'].value_counts().reset_index()
        if len(delay_dist) > 0:
            delay_dist.columns = ['延迟天数', '订单数']
            fig = px.bar(delay_dist.head(10), x='延迟天数', y='订单数',
                         title="订单延迟天数分布", color='订单数',
                         color_continuous_scale='Reds', text_auto=True)
            st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("订单明细")
    page_size = 20
    total = len(filtered)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = st.number_input("页码", 1, total_pages, 1)
    start = (page - 1) * page_size
    end = start + page_size
    st.dataframe(filtered.iloc[start:end], use_container_width=True,
                 column_config={'总金额(USD)': st.column_config.NumberColumn(format="$%.2f"),
                                '单价(USD)': st.column_config.NumberColumn(format="$%.2f")})
    if st.button("📥 导出全部订单"):
        csv = filtered.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
        st.download_button("下载CSV", csv, f"订单数据_{datetime.now().strftime('%Y%m%d')}.csv")

st.caption(f"📊 {datetime.now().strftime('%Y-%m-%d %H:%M')} | 数据来源：上传文件或示例数据")
