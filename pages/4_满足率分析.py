import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(page_title="订单满足率分析", layout="wide")
st.title("📊 订单满足率分析仪表板")

# ---- 文件上传 ----
uploaded_file = st.file_uploader("📁 上传 2026 订单满足率 Excel 文件", type=["xlsx"])

if uploaded_file is None:
    st.info("👆 请上传文件以开始分析")
    st.markdown("""
    **核心指标定义**：
    - **订单数** = 客户下单数
    - **SO数** = 实际销售出货数
    - **满足率** = SO数 / 订单数（order>0 时有效）
    """)
    st.stop()

# ============================================
# 1. 解析 Excel 文件
# ============================================
@st.cache_data
def load_and_parse(file):
    """读取 Excel 并解析为规整格式"""
    
    xls = pd.ExcelFile(file)
    all_records = []
    
    for sheet_name in xls.sheet_names:
        df_raw = pd.read_excel(file, sheet_name=sheet_name, header=None)
        rows = df_raw.values.tolist()
        
        # --- 找到汇总行和明细行起始 ---
        summary_rows = []
        detail_start_row = None
        
        for i, row in enumerate(rows):
            first = str(row[0]) if pd.notna(row[0]) else ''
            if '满足率' in first:
                summary_rows.append(i)
            if any('负责人' in str(c) for c in row[:3] if pd.notna(c)) and \
               any('ItemName' in str(c) for c in row if pd.notna(c)):
                detail_start_row = i
        
        # --- 解析汇总 ---
        if summary_rows:
            # 获取月份列表
            for j in range(summary_rows[0], -1, -1):
                months_found = [str(c) if pd.notna(c) else '' 
                              for c in rows[j] if pd.notna(c) and 
                              str(c) in ['Jan','Feb','Mar','Apr','May','Jun',
                                        'Jul','Aug','Sep','Oct','Nov','Dec']]
                if months_found:
                    months = months_found
                    break
            else:
                months = ['Jan','Feb','Mar','Apr','May']
            
            for idx in summary_rows:
                row = rows[idx]
                name = str(row[0]).replace('满足率', '').strip()
                col = 1
                for m in months:
                    order_val = row[col] if col < len(row) and pd.notna(row[col]) else 0
                    so_val = row[col+1] if col+1 < len(row) and pd.notna(row[col+1]) else 0
                    col += 3
                    
                    order_val = int(order_val) if order_val else 0
                    so_val = int(so_val) if so_val else 0
                    
                    # 满足率 = SO/订单（在汇总层直接计算）
                    rate = so_val / order_val * 100 if order_val > 0 else 0
                    
                    all_records.append({
                        '类型': '负责人汇总',
                        '负责人': name,
                        '月份': m,
                        '品牌': '(全部)',
                        'SKU': '(全部)',
                        '门店': '(全部)',
                        '订单数': order_val,
                        'SO数': so_val,
                        '满足率': round(rate, 1)
                    })
        
        # --- 解析SKU明细 ---
        if detail_start_row is not None:
            # 提取门店名称
            store_names = []
            for j in range(detail_start_row - 20, detail_start_row):
                if j >= 0:
                    for c in rows[j]:
                        if pd.notna(c) and isinstance(c, str) and c.strip():
                            store_names.append(c.strip())
            
            exclude = ['order','SO','fullfillment','负责人','month','Brand',
                      'U_OldItemNo','ItemName','Total']
            store_names = [s for s in store_names if s not in exclude]
            seen = set()
            store_names_unique = []
            for s in store_names:
                if s not in seen:
                    seen.add(s)
                    store_names_unique.append(s)
            store_names = store_names_unique[:15]
            
            # 解析SKU行
            i = detail_start_row + 1
            while i < len(rows):
                row = rows[i]
                first = str(row[0]) if pd.notna(row[0]) else ''
                
                if first in ['RENEE', 'MAX', 'Jarvis&Lee', '纯白版'] and len(row) >= 4:
                    person = first
                    month_val = str(row[1]) if len(row) > 1 and pd.notna(row[1]) else ''
                    brand = str(row[2]) if len(row) > 2 and pd.notna(row[2]) else ''
                    item_no = str(row[3]) if len(row) > 3 and pd.notna(row[3]) else ''
                    
                    # 品名
                    item_parts = []
                    j = 4
                    while j < min(len(row), 12):
                        val = row[j]
                        if pd.notna(val) and isinstance(val, str) and val.strip():
                            item_parts.append(val.strip())
                        elif pd.notna(val) and isinstance(val, (int, float)):
                            break
                        j += 1
                    item_name = ' '.join(item_parts) if item_parts else '(未知)'
                    
                    # 找下一个SKU/Total位置
                    next_line = None
                    for k in range(i+1, min(i+100, len(rows))):
                        next_first = str(rows[k][0]) if pd.notna(rows[k][0]) else ''
                        if next_first in ['RENEE', 'MAX', 'Jarvis&Lee', '纯白版', 'Total']:
                            next_line = k
                            break
                    if next_line is None:
                        next_line = len(rows)
                    
                    # 提取数据值
                    data_values = []
                    for k in range(i, min(next_line, len(rows))):
                        for val in rows[k]:
                            if pd.notna(val) and isinstance(val, (int, float)):
                                data_values.append(val)
                    
                    # 按门店分配（每3个数一组：order, SO, fulfillment）
                    for s_idx, store in enumerate(store_names):
                        if s_idx * 3 + 2 < len(data_values):
                            order_val = int(data_values[s_idx * 3])
                            so_val = int(data_values[s_idx * 3 + 1])
                            
                            # 满足率 = SO / order
                            rate = so_val / order_val * 100 if order_val > 0 else 0
                            
                            all_records.append({
                                '类型': 'SKU明细',
                                '负责人': person,
                                '月份': month_val,
                                '品牌': brand,
                                'SKU': f"{item_no} - {item_name[:25]}",
                                '门店': store,
                                '订单数': order_val,
                                'SO数': so_val,
                                '满足率': round(rate, 1)
                            })
                    
                    i = next_line
                else:
                    i += 1
    
    return pd.DataFrame(all_records)

# ============================================
# 2. 加载数据
# ============================================
with st.spinner("🔍 正在解析大型 Excel 文件（请耐心等待30-60秒）..."):
    try:
        df = load_and_parse(uploaded_file)
        if df.empty:
            st.error("未能解析出有效数据")
            st.stop()
        st.success(f"✅ 解析完成！共 {len(df):,} 条记录")
    except Exception as e:
        st.error(f"解析出错: {e}")
        import traceback
        st.code(traceback.format_exc())
        st.stop()

# ============================================
# 3. 数据清洗与筛选
# ============================================
# 仅保留有订单的记录（order > 0）
df_active = df[df['订单数'] > 0].copy()
st.caption(f"📌 过滤掉 order=0 的{len(df)-len(df_active):,}条记录后，有效数据 {len(df_active):,} 条")

# 侧边栏筛选
st.sidebar.header("🔎 筛选条件")

available_persons = ['全部'] + sorted(df_active['负责人'].unique().tolist())
selected_person = st.sidebar.selectbox("负责人", available_persons)

available_months = ['全部'] + sorted(df_active['月份'].unique().tolist())
selected_month = st.sidebar.selectbox("月份", available_months)

available_brands = ['全部'] + sorted(df_active['品牌'].unique().tolist())
selected_brand = st.sidebar.selectbox("品牌", available_brands)

# 应用
df_filtered = df_active.copy()
if selected_person != '全部':
    df_filtered = df_filtered[df_filtered['负责人'] == selected_person]
if selected_month != '全部':
    df_filtered = df_filtered[df_filtered['月份'] == selected_month]
if selected_brand != '全部':
    df_filtered = df_filtered[df_filtered['品牌'] == selected_brand]

df_summary = df_filtered[df_filtered['类型'] == '负责人汇总']
df_sku = df_filtered[df_filtered['类型'] == 'SKU明细']

# ============================================
# 4. 核心工具函数：正确计算满足率
# ============================================
def calc_fulfillment_rate(group_df):
    """正确计算满足率 = sum(SO) / sum(订单) * 100"""
    total_orders = group_df['订单数'].sum()
    total_sos = group_df['SO数'].sum()
    if total_orders > 0:
        return round(total_sos / total_orders * 100, 1)
    return 0.0

# ============================================
# 5. 可视化仪表板
# ============================================

# --- 5.1 KPI ---
st.subheader("📌 核心指标（当前筛选范围）")
kpi_cols = st.columns(4)

total_orders = int(df_filtered['订单数'].sum())
total_sos = int(df_filtered['SO数'].sum())
overall_rate = calc_fulfillment_rate(df_filtered)
total_skus = df_sku['SKU'].nunique() if not df_sku.empty else 0

with kpi_cols[0]:
    st.metric("📦 总订单数", f"{total_orders:,}")
with kpi_cols[1]:
    st.metric("📤 总SO数", f"{total_sos:,}")
with kpi_cols[2]:
    st.metric("✅ 整体满足率", f"{overall_rate:.1f}%")
with kpi_cols[3]:
    st.metric("🏷️ SKU数", f"{total_skus:,}")

# --- 5.2 满足率趋势（负责人月度） ---
st.subheader("📈 各负责人月度满足率趋势")

if not df_summary.empty:
    # 按负责人+月份聚合（重算满足率）
    trend_data = df_summary.groupby(['负责人', '月份']).apply(
        lambda g: pd.Series({
            '订单数': g['订单数'].sum(),
            'SO数': g['SO数'].sum(),
            '满足率': calc_fulfillment_rate(g)
        })
    ).reset_index()
    
    fig = px.line(
        trend_data, x='月份', y='满足率', color='负责人',
        markers=True,
        title='各负责人月度满足率变化（满足率 = SO/订单）',
        labels={'满足率': '满足率 (%)', '月份': '月份'},
        category_orders={'月份': ['Jan','Feb','Mar','Apr','May','Jun',
                                   'Jul','Aug','Sep','Oct','Nov','Dec']}
    )
    fig.update_layout(hovermode='x unified', height=450)
    fig.update_traces(line=dict(width=3))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("当前筛选范围无汇总数据，使用SKU明细计算...")
    if not df_sku.empty:
        sku_trend = df_sku.groupby(['负责人', '月份']).apply(
            lambda g: pd.Series({
                '订单数': g['订单数'].sum(),
                'SO数': g['SO数'].sum(),
                '满足率': calc_fulfillment_rate(g)
            })
        ).reset_index()
        
        if not sku_trend.empty:
            fig = px.line(
                sku_trend, x='月份', y='满足率', color='负责人',
                markers=True, title='SKU明细层面：各负责人月度满足率趋势'
            )
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)

# --- 5.3 订单量 vs 满足率双轴图 ---
st.subheader("📊 订单量 vs 满足率（月度汇总）")

if not df_summary.empty or not df_sku.empty:
    source = df_summary if not df_summary.empty else df_sku
    
    monthly_agg = source.groupby('月份').apply(
        lambda g: pd.Series({
            '订单数': g['订单数'].sum(),
            'SO数': g['SO数'].sum(),
            '满足率': calc_fulfillment_rate(g)
        })
    ).reset_index()
    
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig2.add_trace(
        go.Bar(x=monthly_agg['月份'], y=monthly_agg['订单数'],
               name='订单数', marker_color='lightblue'),
        secondary_y=False
    )
    
    fig2.add_trace(
        go.Scatter(x=monthly_agg['月份'], y=monthly_agg['满足率'],
                   name='满足率', mode='lines+markers',
                   marker=dict(size=10, color='red'),
                   line=dict(width=3, color='red')),
        secondary_y=True
    )
    
    fig2.update_layout(
        title='月度订单总量 vs 整体满足率（SO/订单）',
        hovermode='x unified', height=400
    )
    fig2.update_yaxes(title_text="订单数", secondary_y=False)
    fig2.update_yaxes(title_text="满足率 (%)", secondary_y=True, range=[0, 105])
    
    st.plotly_chart(fig2, use_container_width=True)

# --- 5.4 SKU满足率分布 ---
st.subheader("🎯 SKU满足率分布")

if not df_sku.empty:
    # 按SKU汇总（先合并同SKU的订单和SO）
    sku_agg = df_sku.groupby(['负责人','月份','品牌','SKU']).apply(
        lambda g: pd.Series({
            '订单数': g['订单数'].sum(),
            'SO数': g['SO数'].sum(),
            '满足率': calc_fulfillment_rate(g)
        })
    ).reset_index()
    
    # 分区间统计
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    labels = ['0-10%','10-20%','20-30%','30-40%','40-50%',
              '50-60%','60-70%','70-80%','80-90%','90-100%']
    
    sku_agg['满足率区间'] = pd.cut(sku_agg['满足率'], bins=bins, labels=labels, right=True)
    dist_data = sku_agg['满足率区间'].value_counts().sort_index().reset_index()
    dist_data.columns = ['满足率区间', 'SKU数量']
    
    colors = ['#d32f2f','#e64a19','#ff5722','#ff9800','#ffc107',
              '#cddc39','#8bc34a','#4caf50','#388e3c','#1b5e20']
    
    fig3 = px.bar(
        dist_data, x='满足率区间', y='SKU数量',
        title=f'SKU满足率分布（共{len(sku_agg)}个SKU行，满足率=SO/订单）',
        color='满足率区间', color_discrete_sequence=colors
    )
    fig3.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)

# --- 5.5 品牌满足率排行 ---
st.subheader("🏆 品牌满足率排行")

if not df_sku.empty:
    brand_agg = df_sku.groupby('品牌').apply(
        lambda g: pd.Series({
            '订单数': g['订单数'].sum(),
            'SO数': g['SO数'].sum(),
            'SKU数': g['SKU'].nunique(),
            '满足率': calc_fulfillment_rate(g)
        })
    ).reset_index()
    
    brand_agg = brand_agg.sort_values('满足率', ascending=True).tail(20)
    
    fig4 = px.bar(
        brand_agg, x='满足率', y='品牌', orientation='h',
        title='品牌满足率排行（SO/订单，Top 20，从低到高）',
        labels={'满足率': '满足率 (%)', '品牌': '品牌'},
        color='满足率', color_continuous_scale='RdYlGn',
        text='满足率'
    )
    fig4.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig4.update_layout(height=600)
    st.plotly_chart(fig4, use_container_width=True)

# --- 5.6 负责人×月份 矩阵 ---
st.subheader("🗺️ 满足率矩阵（负责人 × 月份）")

source_matrix = df_summary if not df_summary.empty else df_sku

if not source_matrix.empty:
    matrix_data = source_matrix.groupby(['负责人', '月份']).apply(
        lambda g: calc_fulfillment_rate(g)
    ).reset_index(name='满足率')
    
    pivot = matrix_data.pivot_table(
        index='负责人', columns='月份', values='满足率', aggfunc='mean'
    )
    
    month_order = [m for m in ['Jan','Feb','Mar','Apr','May','Jun',
                               'Jul','Aug','Sep','Oct','Nov','Dec'] if m in pivot.columns]
    pivot = pivot[month_order]
    
    fig5 = px.imshow(
        pivot, text_auto='.1f', aspect='auto',
        color_continuous_scale='RdYlGn',
        title='满足率矩阵 (%)（SO/订单）',
        labels=dict(x='月份', y='负责人', color='满足率 %')
    )
    fig5.update_layout(height=350)
    st.plotly_chart(fig5, use_container_width=True)

# ============================================
# 6. 月度分析报告
# ============================================
st.subheader("📝 月度分析报告")

if not df_summary.empty or not df_sku.empty:
    source_report = df_summary if not df_summary.empty else df_sku
    months_available = sorted(source_report['月份'].unique())
    
    for month in months_available:
        month_data = source_report[source_report['月份'] == month]
        
        total_orders_m = int(month_data['订单数'].sum())
        total_sos_m = int(month_data['SO数'].sum())
        rate_m = calc_fulfillment_rate(month_data)
        
        # 各负责人表现
        person_perf = month_data.groupby('负责人').apply(
            lambda g: pd.Series({
                '订单数': int(g['订单数'].sum()),
                'SO数': int(g['SO数'].sum()),
                '满足率': calc_fulfillment_rate(g)
            })
        ).reset_index()
        
        best_person = person_perf.loc[person_perf['满足率'].idxmax(), '负责人']
        best_rate = person_perf['满足率'].max()
        worst_person = person_perf.loc[person_perf['满足率'].idxmin(), '负责人']
        worst_rate = person_perf['满足率'].min()
        
        # 该月最差品牌
        worst_brand_info = ''
        if '品牌' in month_data.columns:
            brand_perf = month_data.groupby('品牌').apply(
                lambda g: calc_fulfillment_rate(g)
            ).reset_index(name='满足率').sort_values('满足率')
            if not brand_perf.empty:
                wb = brand_perf.iloc[0]
                worst_brand_info = f"\n📉 该月满足率最低品牌：**{wb['品牌']}**（{wb['满足率']:.1f}%）"
        
        # 评价等级
        if rate_m >= 90:
            level = '🟢 优秀'
            comment = '整体满足率很高，订单履行状况非常良好。'
        elif rate_m >= 70:
            level = '🟡 中等'
            comment = '整体满足率处于中等水平，建议关注未满足订单的具体原因。'
        else:
            level = '🔴 待改进'
            comment = '满足率偏低，需要重点关注。建议排查：库存不足、物流延迟、订单取消等。'
        
        with st.expander(f"📅 **{month} 月分析报告**（满足率 {rate_m:.1f}%）"):
            st.markdown(f"""
            #### {month} 满足率概览

            | 指标 | 数值 |
            |------|------|
            | 综合评价 | **{level}** |
            | 总订单数 | **{total_orders_m:,}** |
            | 总SO数 | **{total_sos_m:,}** |
            | 整体满足率 | **{rate_m:.1f}%** |
            | 最佳负责人 | **{best_person}**（{best_rate:.1f}%） |
            | 待改进负责人 | **{worst_person}**（{worst_rate:.1f}%） |
            {worst_brand_info}

            **分析**：{comment}
            """)
            
            # 各负责人详情
            st.markdown("**各负责人满足率明细**（满足率 = SO / 订单）")
            for _, pr in person_perf.iterrows():
                pr_rate = pr['满足率']
                emoji = '✅' if pr_rate >= 90 else ('⚠️' if pr_rate >= 70 else '❌')
                st.markdown(
                    f"- {emoji} **{pr['负责人']}**：满足率 **{pr_rate:.1f}%** "
                    f"（订单 {pr['订单数']:,}，SO {pr['SO数']:,}）"
                )

# ============================================
# 7. 数据导出
# ============================================
st.subheader("💾 数据导出")

col1, col2 = st.columns(2)

with col1:
    # 导出汇总（按负责人+月份，正确计算满足率）
    if not df_summary.empty:
        export_summary = df_summary.groupby(['负责人', '月份']).apply(
            lambda g: pd.Series({
                '订单数': g['订单数'].sum(),
                'SO数': g['SO数'].sum(),
                '满足率(%)': calc_fulfillment_rate(g)
            })
        ).reset_index()
    else:
        export_summary = pd.DataFrame()
    
    if not export_summary.empty:
        csv = export_summary.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下载月度汇总 (CSV)", csv,
                          f"满足率_汇总_{datetime.now():%Y%m%d}.csv", "text/csv")

with col2:
    if not df_sku.empty:
        csv_sku = df_sku.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下载SKU明细 (CSV)", csv_sku,
                          f"满足率_SKU明细_{datetime.now():%Y%m%d}.csv", "text/csv")

# 原始数据查看
with st.expander("🔍 查看原始数据"):
    st.dataframe(df_filtered, use_container_width=True)
