import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random

st.set_page_config(page_title="库存预警", layout="wide")
st.title("📦 香水供应链·库存预警看板")

# ============================================================
# 模拟库存数据
# ============================================================
@st.cache_data(ttl=600)
def generate_inventory_data():
    brands = ["CHANEL", "DIOR", "HERMES", "JO MALONE", "TOM FORD",
              "GUCCI", "YSL", "ARMANI", "BVLGARI", "LOEWE"]
    stores = ["三亚国际免税城", "海口国际免税城", "海口日月广场免税店",
              "海口美兰机场免税店", "三亚凤凰机场免税店",
              "海旅免税城", "中服免税店", "博鳌免税店"]
    products = [
        ("香奈儿5号", 50, 100), ("迪奥小姐", 30, 80), ("大地", 40, 90),
        ("蓝风铃", 35, 75), ("乌木沉香", 80, 150), ("罪爱", 45, 95),
        ("寄情", 55, 110), ("大吉岭茶", 60, 120)
    ]

    records = []
    for store in stores:
        for p_name, min_stock, max_stock in products:
            # 随机库存，部分低于安全库存触发预警
            stock = random.randint(
                int(min_stock * 0.3),  # 最低可能库存
                int(max_stock * 1.2)   # 最高库存
            )
            safety_stock = min_stock * 0.8  # 安全库存线
            daily_sales = random.uniform(0.5, 3)  # 日均销量

            records.append({
                '门店': store,
                '产品': p_name,
                '品牌': random.choice(brands),
                '当前库存': stock,
                '安全库存': round(safety_stock, 0),
                '最大库存': max_stock,
                '日均销量': round(daily_sales, 1),
                '预计天数': round(stock / daily_sales, 1) if daily_sales > 0 else 999,
                '库存状态': '⚠️ 预警' if stock < safety_stock else
                          '🟡 偏低' if stock < safety_stock * 1.5 else '✅ 正常',
                '建议补货': max(0, int(safety_stock * 2 - stock)) if stock < safety_stock * 1.5 else 0,
            })

    return pd.DataFrame(records)

# ============================================================
# 加载数据
# ============================================================
df = generate_inventory_data()

# ============================================================
# 筛选
# ============================================================
with st.sidebar:
    st.header("🔍 筛选条件")
    selected_status = st.multiselect(
        "库存状态", ["✅ 正常", "🟡 偏低", "⚠️ 预警"],
        default=["⚠️ 预警", "🟡 偏低"]
    )
    selected_store = st.multiselect(
        "门店", sorted(df['门店'].unique()), default=[]
    )
    selected_brand = st.multiselect(
        "品牌", sorted(df['品牌'].unique()), default=[]
    )

filtered = df[df['库存状态'].isin(selected_status)]
if selected_store:
    filtered = filtered[filtered['门店'].isin(selected_store)]
if selected_brand:
    filtered = filtered[filtered['品牌'].isin(selected_brand)]

# ============================================================
# KPI
# ============================================================
total_items = len(filtered)
alert_count = len(filtered[filtered['库存状态'] == '⚠️ 预警'])
low_count = len(filtered[filtered['库存状态'] == '🟡 偏低'])
need_reorder = filtered['建议补货'].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("📦 监控品类数", total_items)
col2.metric("🚨 库存预警", alert_count, delta_color="inverse")
col3.metric("🟡 库存偏低", low_count)
col4.metric("📋 建议补货量", f"{need_reorder:.0f} 件")

# ============================================================
# 图表
# ============================================================
tab1, tab2, tab3 = st.tabs(["🚨 预警详情", "📊 库存分布", "📋 补货建议"])

with tab1:
    st.subheader("库存预警明细")
    alerts = filtered[filtered['库存状态'] == '⚠️ 预警'].sort_values('预计天数')

    if len(alerts) > 0:
        # 高亮显示
        def highlight_alert(row):
            if row['库存状态'] == '⚠️ 预警':
                return ['background-color: #ffe0e0'] * len(row)
            elif row['库存状态'] == '🟡 偏低':
                return ['background-color: #fff3cd'] * len(row)
            return [''] * len(row)

        st.dataframe(
            alerts.style.apply(highlight_alert, axis=1),
            use_container_width=True,
            column_config={
                '建议补货': st.column_config.NumberColumn(format="%d 件"),
            }
        )

        # 下载预警清单
        csv = alerts.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
        st.download_button("📥 下载预警清单", csv, "库存预警.csv")

        # 预警可视化
        fig = px.bar(
            alerts.head(15),
            x='产品', y='当前库存',
            color='门店', barmode='group',
            title="Top 15 预警产品库存对比",
            labels={'当前库存': '库存量'},
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        # 添加安全库存线
        fig.add_hline(
            y=alerts['安全库存'].mean(),
            line_dash="dash", line_color="red",
            annotation_text="平均安全库存线"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("✅ 暂无库存预警！")

with tab2:
    col1, col2 = st.columns(2)

    with col1:
        # 各门店库存状态分布
        store_status = filtered.groupby(['门店', '库存状态']).size().reset_index(name='数量')
        fig = px.bar(
            store_status, x='门店', y='数量', color='库存状态',
            title="各门店库存状态分布",
            color_discrete_map={
                '✅ 正常': '#2ecc71', '🟡 偏低': '#f39c12', '⚠️ 预警': '#e74c3c'
            },
            barmode='stack'
        )
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 库存天数分布
        fig = px.histogram(
            filtered, x='预计天数', color='库存状态',
            title="库存天数分布（预计可销售天数）",
            nbins=20,
            color_discrete_map={
                '✅ 正常': '#2ecc71', '🟡 偏低': '#f39c12', '⚠️ 预警': '#e74c3c'
            }
        )
        fig.add_vline(x=30, line_dash="dash", line_color="red",
                      annotation_text="30天警戒线")
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("📋 自动补货建议")

    # 只显示需要补货的
    need_reorder_df = filtered[filtered['建议补货'] > 0].sort_values('建议补货', ascending=False)

    if len(need_reorder_df) > 0:
        st.info(f"📌 共 {len(need_reorder_df)} 个品类需要补货，总建议补货量 {need_reorder_df['建议补货'].sum():.0f} 件")

        # 按门店汇总补货建议
        store_reorder = need_reorder_df.groupby('门店').agg({
            '建议补货': 'sum',
            '产品': 'count'
        }).reset_index().rename(columns={'产品': '需补货品类数'})

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(
                store_reorder.sort_values('建议补货'),
                x='门店', y='建议补货',
                title="各门店建议补货量",
                color='需补货品类数', color_continuous_scale='Reds',
                text_auto=True
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.dataframe(
                need_reorder_df[['门店', '产品', '当前库存', '安全库存', '日均销量', '预计天数', '建议补货']],
                use_container_width=True,
                column_config={
                    '建议补货': st.column_config.NumberColumn(format="%d 件"),
                }
            )
            csv = need_reorder_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
            st.download_button("📥 下载补货清单", csv, "补货建议.csv")
    else:
        st.success("✅ 所有品类库存充足，无需补货")

st.caption(f"📊 {datetime.now().strftime('%Y-%m-%d %H:%M')} | 数据来源：模拟数据（生产环境请接入库存API）")
