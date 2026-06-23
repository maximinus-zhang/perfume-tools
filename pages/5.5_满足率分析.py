import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import calendar

st.set_page_config(page_title="订单满足率分析", layout="wide")
st.title("📊 订单满足率分析仪表板（BY SKU）")

uploaded_file = st.file_uploader("📁 上传 2026 订单满足率 Excel 文件", type=["xlsx"])

if uploaded_file is None:
    st.info("👆 请上传文件以开始分析")
    st.markdown("""
    **文件格式说明**：
    - 包含按负责人、月份、品牌、SKU 的满足率数据
    - `fulfillment` 列 = 满足率（百分比）
    - `order = 0` 表示该 SKU 当月无订单，不计入统计
    """)
    st.stop()

# ============================================
# 1. 用 Pandas 直接读取 Excel（逐 sheet）
# ============================================
@st.cache_data
def load_and_parse(file):
    """读取 Excel 所有 sheet，解析并合并为规整 DataFrame"""
    
    xls = pd.ExcelFile(file)
    all_records = []
    
    for sheet_name in xls.sheet_names:
        df_raw = pd.read_excel(file, sheet_name=sheet_name, header=None)
        rows = df_raw.values.tolist()
        
        # --- 找到负责人级别的汇总行 ---
        summary_rows = []
        detail_start_row = None
        
        for i, row in enumerate(rows):
            first = str(row[0]) if pd.notna(row[0]) else ''
            # 汇总行：包含 "满足率"
            if '满足率' in first:
                summary_rows.append(i)
            # 明细头：包含 "负责人" 和 "ItemName"
            if ('负责人' in first or '负责人' in str(row).replace('nan', '')) and \
               any('ItemName' in str(c) for c in row if pd.notna(c)):
                detail_start_row = i
        
        # --- 解析汇总数据 ---
        if summary_rows:
            # 找月份标题行（在第一个汇总行之前）
            month_row_idx = max(0, summary_rows[0] - 1)
            for j in range(month_row_idx, -1, -1):
                month_candidates = [str(c) if pd.notna(c) else '' for c in rows[j]]
                months_found = [m for m in month_candidates 
                                if m in ['Jan','Feb','Mar','Apr','May','Jun',
                                        'Jul','Aug','Sep','Oct','Nov','Dec']]
                if months_found:
                    months = months_found
                    break
            else:
                months = ['Jan','Feb','Mar','Apr','May','Jun',
                         'Jul','Aug','Sep','Oct','Nov','Dec']
            
            for idx in summary_rows:
                row = rows[idx]
                name = str(row[0]).replace('满足率', '').strip()
                col = 1
                for m in months:
                    order_val = row[col] if col < len(row) and pd.notna(row[col]) else 0
                    so_val = row[col+1] if col+1 < len(row) and pd.notna(row[col+1]) else 0
                    fulfill_val = row[col+2] if col+2 < len(row) and pd.notna(row[col+2]) else 0
                    col += 3
                    all_records.append({
                        '类型': '负责人汇总',
                        '负责人': name,
                        '月份': m,
                        '品牌': '(全部)',
                        'SKU': '(全部)',
                        '订单数': int(order_val) if order_val else 0,
                        'SO数': int(so_val) if so_val else 0,
                        '满足率': float(fulfill_val) if fulfill_val else 0.0
                    })
        
        # --- 解析SKU明细数据 ---
        if detail_start_row is not None:
            # 找到该sheet中的门店列表（在明细头上方）
            store_names = []
            for j in range(detail_start_row - 20, detail_start_row):
                if j >= 0:
                    for c in rows[j]:
                        if pd.notna(c) and isinstance(c, str) and c.strip():
                            store_names.append(c.strip())
            # 过滤掉标题词
            exclude = ['order','SO','fullfillment','负责人','month','Brand',
                      'U_OldItemNo','ItemName','Total','order','SO','fullfillment']
            store_names = [s for s in store_names if s not in exclude]
            # 去重并保留顺序
            seen = set()
            store_names_unique = []
            for s in store_names:
                if s not in seen:
                    seen.add(s)
                    store_names_unique.append(s)
            store_names = store_names_unique[:20]  # 最多取20个门店
            
            # 解析每个SKU行
            i = detail_start_row + 1
            while i < len(rows):
                row = rows[i]
                first = str(row[0]) if pd.notna(row[0]) else ''
                
                # SKU起始行：负责人名字开头
                if first in ['RENEE', 'MAX', 'Jarvis&Lee', '纯白版'] and len(row) >= 4:
                    person = first
                    month_val = str(row[1]) if len(row) > 1 and pd.notna(row[1]) else ''
                    brand = str(row[2]) if len(row) > 2 and pd.notna(row[2]) else ''
                    item_no = str(row[3]) if len(row) > 3 and pd.notna(row[3]) else ''
                    
                    # 品名可能跨多行，收集
                    item_parts = []
                    j = 4
                    while j < min(len(row), 15):
                        val = row[j]
                        if pd.notna(val) and isinstance(val, str) and val.strip():
                            item_parts.append(val.strip())
                        elif pd.notna(val) and isinstance(val, (int, float)):
                            # 遇到数字意味着数据列开始
                            break
                        j += 1
                    item_name = ' '.join(item_parts) if item_parts else '(未知)'
                    
                    # 下一个SKU的起始行或总计行
                    next_sku_line = None
                    total_data = {}
                    
                    for k in range(i+1, min(i+80, len(rows))):
                        next_row = rows[k]
                        next_first = str(next_row[0]) if pd.notna(next_row[0]) else ''
                        if next_first in ['RENEE', 'MAX', 'Jarvis&Lee', '纯白版']:
                            next_sku_line = k
                            break
                        if 'Total' in next_first:
                            # 读取总计行数据
                            for t_idx, t_val in enumerate(next_row):
                                if pd.notna(t_val) and t_idx > 0:
                                    total_data[t_idx] = t_val
                            next_sku_line = k + 1
                            break
                    
                    if next_sku_line is None:
                        next_sku_line = len(rows)
                    
                    # 提取门店数据
                    data_start = min(5, len(row))
                    data_values = []
                    for k in range(i, min(next_sku_line, len(rows))):
                        for val in rows[k]:
                            if pd.notna(val) and isinstance(val, (int, float)):
                                data_values.append(float(val))
                    
                    # 每3个一组 (order, SO, fulfillment)
                    for s_idx, store in enumerate(store_names):
                        if s_idx * 3 + 2 < len(data_values):
                            order_val = int(data_values[s_idx * 3])
                            so_val = int(data_values[s_idx * 3 + 1])
                            fulfill_val = data_values[s_idx * 3 + 2]
                            
                            all_records.append({
                                '类型': 'SKU明细',
                                '负责人': person,
                                '月份': month_val,
                                '品牌': brand,
                                'SKU': f"{item_no} - {item_name[:30]}",
                                '门店': store,
                                '订单数': order_val,
                                'SO数': so_val,
                                '满足率': fulfill_val
                            })
                    
                    i = next_sku_line
                else:
                    i += 1
    
    return pd.DataFrame(all_records)

# ============================================
# 2. 加载并解析
# ============================================
with st.spinner("🔍 正在解析 Excel 文件（217,000+行，请耐心等待）..."):
    try:
        df = load_and_parse(uploaded_file)
        if df.empty:
            st.error("未能解析出有效数据，请检查文件格式。")
            st.stop()
        st.success(f"✅ 解析完成！共 {len(df):,} 条记录")
    except Exception as e:
        st.error(f"解析出错: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        st.stop()

# ============================================
# 3. 数据处理与过滤
# ============================================
# 过滤：只保留有订单的数据（order > 0）
df_active = df[df['订单数'] > 0].copy()
st.caption(f"📌 过滤掉 order=0 的无效记录后，有效数据 {len(df_active):,} 条")

# 确保满足率是数值
df_active['满足率'] = pd.to_numeric(df_active['满足率'], errors='coerce').fillna(0)

# 侧边栏筛选
st.sidebar.header("🔎 筛选条件")

available_persons = ['全部'] + sorted(df_active['负责人'].unique().tolist())
selected_person = st.sidebar.selectbox("负责人", available_persons)

available_months = ['全部'] + sorted(df_active['月份'].unique().tolist())
selected_month = st.sidebar.selectbox("月份", available_months)

available_brands = ['全部'] + sorted(df_active['品牌'].unique().tolist())
selected_brand = st.sidebar.selectbox("品牌", available_brands)

# 应用筛选
df_filtered = df_active.copy()
if selected_person != '全部':
    df_filtered = df_filtered[df_filtered['负责人'] == selected_person]
if selected_month != '全部':
    df_filtered = df_filtered[df_filtered['月份'] == selected_month]
if selected_brand != '全部':
    df_filtered = df_filtered[df_filtered['品牌'] == selected_brand]

# 汇总数据
df_summary = df_filtered[df_filtered['类型'] == '负责人汇总']
df_sku = df_filtered[df_filtered['类型'] == 'SKU明细']

# ============================================
# 4. 可视化仪表板
# ============================================

# --- 4.1 核心KPI卡片 ---
st.subheader("📌 核心指标总览")
kpi_cols = st.columns(4)

with kpi_cols[0]:
    total_orders = int(df_active['订单数'].sum())
    st.metric("总有效订单数", f"{total_orders:,}")

with kpi_cols[1]:
    total_skus = df_active[df_active['类型'] == 'SKU明细']['SKU'].nunique()
    st.metric("涉及SKU数", f"{total_skus:,}")

with kpi_cols[2]:
    total_persons = df_active['负责人'].nunique()
    st.metric("负责人数", total_persons)

with kpi_cols[3]:
    total_brands = df_active['品牌'].nunique()
    st.metric("品牌数", total_brands)

# --- 4.2 负责人月度满足率趋势 ---
st.subheader("📈 满足率趋势分析")

if not df_summary.empty:
    fig = px.line(
        df_summary,
        x='月份', y='满足率', color='负责人',
        markers=True,
        title='各负责人月度满足率变化趋势',
        labels={'满足率': '满足率 (%)', '月份': '月份', '负责人': '负责人'},
        category_orders={'月份': ['Jan','Feb','Mar','Apr','May','Jun',
                                   'Jul','Aug','Sep','Oct','Nov','Dec']}
    )
    fig.update_layout(hovermode='x unified', height=450)
    fig.update_traces(line=dict(width=3))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("筛选条件下无汇总数据")

# --- 4.3 双轴图：订单量 vs 满足率 ---
st.subheader("📊 订单量与满足率对比")

if not df_summary.empty:
    # 按月份聚合
    monthly_agg = df_summary.groupby('月份').agg({
        '订单数': 'sum',
        '满足率': 'mean'
    }).reset_index()
    
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig2.add_trace(
        go.Bar(x=monthly_agg['月份'], y=monthly_agg['订单数'], 
               name='订单数', marker_color='lightblue'),
        secondary_y=False
    )
    
    fig2.add_trace(
        go.Scatter(x=monthly_agg['月份'], y=monthly_agg['满足率'],
                   name='平均满足率', mode='lines+markers',
                   marker=dict(size=10, color='red'),
                   line=dict(width=3, color='red')),
        secondary_y=True
    )
    
    fig2.update_layout(
        title='月度订单总量 vs 平均满足率',
        hovermode='x unified',
        height=400
    )
    fig2.update_yaxes(title_text="订单数", secondary_y=False)
    fig2.update_yaxes(title_text="满足率 (%)", secondary_y=True, range=[0, 105])
    
    st.plotly_chart(fig2, use_container_width=True)

# --- 4.4 满足率分布直方图 ---
st.subheader("🎯 满足率分布")

if not df_sku.empty:
    # 统计每个满足率区间的SKU数量
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    labels = ['0-10%','10-20%','20-30%','30-40%','40-50%',
              '50-60%','60-70%','70-80%','80-90%','90-100%']
    
    df_sku['满足率区间'] = pd.cut(df_sku['满足率'], bins=bins, labels=labels, right=True)
    dist_data = df_sku['满足率区间'].value_counts().sort_index().reset_index()
    dist_data.columns = ['满足率区间', 'SKU数量']
    
    colors = ['#d32f2f','#e64a19','#ff5722','#ff9800','#ffc107',
              '#cddc39','#8bc34a','#4caf50','#388e3c','#1b5e20']
    
    fig3 = px.bar(
        dist_data, x='满足率区间', y='SKU数量',
        title='满足率分布（SKU维度）',
        labels={'满足率区间': '满足率', 'SKU数量': 'SKU数量'},
        color='满足率区间',
        color_discrete_sequence=colors
    )
    fig3.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)

# --- 4.5 品牌满足率排行 ---
st.subheader("🏆 品牌满足率排行")

if not df_sku.empty:
    brand_rank = df_sku.groupby('品牌').agg({
        '订单数': 'sum',
        '满足率': 'mean',
        'SKU': 'nunique'
    }).reset_index().rename(columns={'SKU': 'SKU数'})
    brand_rank = brand_rank.sort_values('满足率', ascending=True).tail(20)
    
    fig4 = px.bar(
        brand_rank, x='满足率', y='品牌', orientation='h',
        title='品牌平均满足率（Top 20，从低到高）',
        labels={'满足率': '平均满足率 (%)', '品牌': '品牌'},
        color='满足率', color_continuous_scale='RdYlGn',
        text='满足率'
    )
    fig4.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig4.update_layout(height=600)
    st.plotly_chart(fig4, use_container_width=True)

# --- 4.6 满足率热力图（负责人 × 月份）---
st.subheader("🗺️ 负责人 × 月份 满足率矩阵")

if not df_summary.empty:
    pivot = df_summary.pivot_table(
        index='负责人', columns='月份', values='满足率', aggfunc='mean'
    )
    # 补全缺失月份
    for m in ['Jan','Feb','Mar','Apr','May','Jun',
              'Jul','Aug','Sep','Oct','Nov','Dec']:
        if m not in pivot.columns:
            pivot[m] = np.nan
    # 按正确顺序排序列
    month_order = [m for m in ['Jan','Feb','Mar','Apr','May','Jun',
                               'Jul','Aug','Sep','Oct','Nov','Dec'] if m in pivot.columns]
    pivot = pivot[month_order]
    
    fig5 = px.imshow(
        pivot, text_auto='.1f', aspect='auto',
        color_continuous_scale='RdYlGn',
        title='满足率矩阵 (%)',
        labels=dict(x='月份', y='负责人', color='满足率 %')
    )
    fig5.update_layout(height=350)
    st.plotly_chart(fig5, use_container_width=True)

# ============================================
# 5. 月度分析报告
# ============================================
st.subheader("📝 月度分析报告")

if not df_summary.empty:
    months_available = sorted(df_summary['月份'].unique())
    
    for month in months_available:
        month_data = df_summary[df_summary['月份'] == month]
        month_sku = df_sku[df_sku['月份'] == month] if not df_sku.empty else pd.DataFrame()
        
        total_orders_m = int(month_data['订单数'].sum())
        avg_rate_m = month_data['满足率'].mean()
        
        best_row = month_data.loc[month_data['满足率'].idxmax()]
        worst_row = month_data.loc[month_data['满足率'].idxmin()]
        
        # 该月满足率最低的品牌
        low_brand_msg = ''
        if not month_sku.empty:
            brand_month = month_sku.groupby('品牌')['满足率'].mean().sort_values()
            if not brand_month.empty:
                low_brand = brand_month.index[0]
                low_rate = brand_month.iloc[0]
                low_brand_msg = f"📉 该月满足率最低品牌：**{low_brand}**（{low_rate:.1f}%）"
        
        with st.expander(f"📅 **{month} 月分析报告**"):
            # 判断等级
            if avg_rate_m >= 90:
                level = '🟢优秀'
                comment = '订单满足率非常高，整体履行状况良好。'
            elif avg_rate_m >= 70:
                level = '🟡中等'
                comment = '订单满足率处于中等水平，建议重点关注未满足订单。'
            else:
                level = '🔴待改进'
                comment = '订单满足率较低，需深入分析原因并制定改进方案。'
            
            st.markdown(f"""
            #### {month} 满足率概览
            
            | 指标 | 数值 |
            |------|------|
            | 综合评价 | **{level}** |
            | 总订单数 | **{total_orders_m:,}** |
            | 平均满足率 | **{avg_rate_m:.1f}%** |
            | 最佳负责人 | **{best_row['负责人']}**（{best_row['满足率']:.1f}%） |
            | 待改进负责人 | **{worst_row['负责人']}**（{worst_row['满足率']:.1f}%） |
            
            **分析**：{comment}
            
            {low_brand_msg}
            """)
            
            # 负责人详细对比
            st.markdown("**各负责人表现**：")
            for _, r in month_data.iterrows():
                rate = r['满足率']
                emoji = '✅' if rate >= 90 else ('⚠️' if rate >= 70 else '❌')
                st.markdown(f"- {emoji} **{r['负责人']}**：满足率 {rate:.1f}%（订单 {int(r['订单数']):,}）")

# ============================================
# 6. 数据导出与原始数据查看
# ============================================
st.subheader("📋 数据导出")

col1, col2 = st.columns(2)

with col1:
    csv_summary = df_summary.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        "📥 下载汇总数据 (CSV)",
        csv_summary,
        f"满足率_汇总_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv"
    )

with col2:
    if not df_sku.empty:
        csv_sku = df_sku.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "📥 下载SKU明细 (CSV)",
            csv_sku,
            f"满足率_SKU明细_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )

with st.expander("🔍 查看原始解析数据"):
    st.dataframe(df_filtered, use_container_width=True)
