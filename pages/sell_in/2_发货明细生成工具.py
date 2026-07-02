# -*- coding: utf-8 -*-
"""
Streamlit - 发货明细生成工具 v2
修复：按 EX-PDF 定位提取记录，过滤只保留 HAINAN/NON-HAINAN
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io

st.set_page_config(
    page_title="发货明细生成工具",
    page_icon="📦",
    layout="wide"
)

st.title("📦 发货明细生成工具 v2")
st.markdown("每月从 SELL IN 表自动生成 **海南** 和 **非海南** 两张发货明细表")

# ========== 文件上传 ==========
col1, col2 = st.columns(2)

with col1:
    sell_in_file = st.file_uploader(
        "📄 上传 SELL IN 报表（Excel格式）",
        type=['xlsx', 'xls'],
        help="SAP SA-007A 销售报表，包含EX-PDF客户出货信息"
    )

with col2:
    bpcode_file = st.file_uploader(
        "📋 上传 SIS BPCode List（Excel格式）",
        type=['xlsx', 'xls'],
        help="包含 SIS BPCode 与 District 的映射关系"
    )

# ========== 解析函数 ==========
def parse_sell_in(file_obj):
    """
    解析 SELL IN 文件
    正确方法：找到每个 EX-PDF 起始位置，取后续 8 个字段组成一条 9 字段记录
    """
    df_raw = pd.read_excel(file_obj, header=None, dtype=str)
    
    # 找到第一个 EX-PDF 的位置
    start_row = None
    start_col = None
    for row_idx in range(len(df_raw)):
        for col_idx in range(len(df_raw.columns)):
            val = df_raw.iloc[row_idx, col_idx]
            if isinstance(val, str) and 'EX-PDF' in val:
                start_row = row_idx
                start_col = col_idx
                break
        if start_row is not None:
            break
    
    if start_row is None:
        st.error("未找到以 'EX-PDF' 开头的行，请检查文件格式。")
        return None
    
    # 展平从起始位置开始的所有非空单元格
    flat_values = []
    for row_idx in range(start_row, len(df_raw)):
        row_vals = df_raw.iloc[row_idx, :].tolist()
        for v in row_vals:
            if pd.notna(v) and str(v).strip() != '':
                flat_values.append(str(v).strip())
    
    # 找到所有以 EX-PDF 开头的单元格的索引
    ex_pdf_indices = [i for i, v in enumerate(flat_values) if v.startswith('EX-PDF')]
    
    if len(ex_pdf_indices) == 0:
        st.error("展平后未找到 EX-PDF 记录。")
        return None
    
    # 对每个 EX-PDF 索引，取后续 8 个字段组成一条完整记录
    records = []
    for pdf_idx in ex_pdf_indices:
        if pdf_idx + 8 < len(flat_values):
            record = flat_values[pdf_idx : pdf_idx + 9]
            # 确保有 9 个字段
            if len(record) == 9:
                records.append(record)
    
    if len(records) == 0:
        st.error("没有解析到任何有效记录。")
        return None
    
    # 构建 DataFrame
    columns = ['SIS_BPCode', 'CustomerName', 'Date', 'InvoiceNo', 
               'Brand', 'SKU', 'ItemName', 'Qty', 'Amount']
    df = pd.DataFrame(records, columns=columns)
    
    # 解析日期
    def parse_date(val):
        if val in ['', None, 'None', 'nan']:
            return pd.NaT
        try:
            numeric_date = float(val)
            base = datetime(1899, 12, 30)
            return base + timedelta(days=int(numeric_date))
        except:
            pass
        try:
            return pd.to_datetime(val, errors='coerce')
        except:
            return pd.NaT
    
    df['Date'] = df['Date'].apply(parse_date)
    df = df.dropna(subset=['Date'])
    
    # 数值转换
    df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0).astype(int)
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    
    return df


def parse_bpcode_list(file_obj):
    """解析 SIS BPCode List"""
    df = pd.read_excel(file_obj, header=None, dtype=str)
    df = df.iloc[:, :2]
    df.columns = ['SIS_BPCode', 'District']
    df['SIS_BPCode'] = df['SIS_BPCode'].str.strip()
    df['District'] = df['District'].str.strip()
    # 只保留 EX-PDF 开头的有效行
    df = df[df['SIS_BPCode'].notna() & df['District'].notna()]
    df = df[df['SIS_BPCode'].str.startswith('EX-PDF')]
    return df


# ========== 主处理逻辑 ==========
if st.button("🚀 生成发货明细", type="primary", use_container_width=True):
    if sell_in_file is None or bpcode_file is None:
        st.error("请先上传 SELL IN 报表和 SIS BPCode List 文件！")
        st.stop()
    
    progress_bar = st.progress(0, text="开始处理...")
    
    # 1. 解析 SELL IN
    progress_bar.progress(10, text="📖 解析 SELL IN 报表...")
    df_sell_in = parse_sell_in(sell_in_file)
    if df_sell_in is None:
        st.stop()
    
    total_parsed = len(df_sell_in)
    st.success(f"✅ SELL IN 解析完成：{total_parsed} 条记录")
    
    # 打印前几条记录用于调试
    st.caption(f"前 3 条记录样例：")
    st.dataframe(df_sell_in.head(3), use_container_width=True)
    
    # 2. 解析 SIS BPCode List
    progress_bar.progress(30, text="📋 解析 SIS BPCode List...")
    df_bpcode = parse_bpcode_list(bpcode_file)
    
    if len(df_bpcode) == 0:
        st.error("SIS BPCode List 中没有找到有效数据。")
        st.stop()
    
    st.success(f"✅ SIS BPCode List 解析完成：{len(df_bpcode)} 个映射关系")
    
    # 3. 建立映射字典
    bpcode_map = dict(zip(df_bpcode['SIS_BPCode'], df_bpcode['District']))
    
    # 4. 合并数据
    progress_bar.progress(50, text="🔗 关联 BPCode 映射...")
    df_sell_in['District'] = df_sell_in['SIS_BPCode'].map(bpcode_map)
    
    # 统计映射结果
    mapped_count = df_sell_in['District'].notna().sum()
    unmapped_count = total_parsed - mapped_count
    st.info(f"📊 映射结果：已匹配 {mapped_count} 条，未匹配 {unmapped_count} 条")
    
    # 显示未匹配的 BPCode（如果有）
    if unmapped_count > 0:
        unmapped_bpcodes = df_sell_in[df_sell_in['District'].isna()]['SIS_BPCode'].unique()
        st.warning(f"⚠️ 以下 {len(unmapped_bpcodes)} 个 BPCode 在映射表中未找到：")
        st.write(", ".join(unmapped_bpcodes[:20]))
        if len(unmapped_bpcodes) > 20:
            st.write(f"...及其他 {len(unmapped_bpcodes)-20} 个")
    
    # 5. 只保留 HAINAN 和 NON-HAINAN
    valid_districts = ['HAINAN', 'NON-HAINAN']
    df_filtered = df_sell_in[df_sell_in['District'].isin(valid_districts)].copy()
    
    filtered_total = len(df_filtered)
    hainan_count = len(df_filtered[df_filtered['District'] == 'HAINAN'])
    non_hainan_count = len(df_filtered[df_filtered['District'] == 'NON-HAINAN'])
    
    st.success(f"✅ 过滤结果：HAINAN {hainan_count} 条，NON-HAINAN {non_hainan_count} 条，共 {filtered_total} 条")
    
    if filtered_total == 0:
        st.error("过滤后没有数据，无法生成文件。")
        st.stop()
    
    # 6. 区分产品/FOC
    df_filtered['Type'] = df_filtered['Amount'].apply(lambda x: '产品' if x > 0 else 'FOC')
    
    product_count = len(df_filtered[df_filtered['Type'] == '产品'])
    foc_count = len(df_filtered[df_filtered['Type'] == 'FOC'])
    st.info(f"📊 类型分布：产品 {product_count} 条，FOC {foc_count} 条")
    
    # 7. 按区域拆分
    df_hainan = df_filtered[df_filtered['District'] == 'HAINAN'].copy()
    df_non_hainan = df_filtered[df_filtered['District'] == 'NON-HAINAN'].copy()
    
    # 8. 生成 Excel 文件
    progress_bar.progress(70, text="📝 生成 Excel 文件...")
    
    output_columns = ['District', 'SIS_BPCode', 'CustomerName', 'Date', 
                      'InvoiceNo', 'Brand', 'SKU', 'ItemName', 'Qty']
    
    def make_excel_bytes(df_source, title):
        """生成 Excel 文件（产品+FOC两个sheet）"""
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 产品 sheet
            df_product = df_source[df_source['Type'] == '产品'][output_columns].copy()
            df_product['Date'] = df_product['Date'].dt.strftime('%Y-%m-%d')
            df_product.to_excel(writer, sheet_name='产品', index=False)
            
            # FOC sheet
            df_foc = df_source[df_source['Type'] == 'FOC'][output_columns].copy()
            df_foc['Date'] = df_foc['Date'].dt.strftime('%Y-%m-%d')
            df_foc.to_excel(writer, sheet_name='FOC', index=False)
            
            # 自动调整列宽
            for sheet_name in ['产品', 'FOC']:
                ws = writer.sheets[sheet_name]
                for col in ws.columns:
                    max_length = 0
                    for cell in col:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    ws.column_dimensions[col[0].column_letter].width = adjusted_width
        
        output.seek(0)
        return output
    
    # 海南文件
    hainan_bytes = make_excel_bytes(df_hainan, "海南")
    
    # 非海南文件
    non_hainan_bytes = make_excel_bytes(df_non_hainan, "非海南")
    
    progress_bar.progress(100, text="✅ 完成！")
    
    # 9. 提供下载
    st.markdown("---")
    st.subheader("📥 下载生成的文件")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        hainan_product = len(df_hainan[df_hainan['Type'] == '产品'])
        hainan_foc = len(df_hainan[df_hainan['Type'] == 'FOC'])
        st.download_button(
            label=f"📥 下载 海南 发货明细（产品{hainan_product} / FOC{hainan_foc}）",
            data=hainan_bytes,
            file_name=f"海南_发货明细_{datetime.now().strftime('%Y%m')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col_b:
        non_hainan_product = len(df_non_hainan[df_non_hainan['Type'] == '产品'])
        non_hainan_foc = len(df_non_hainan[df_non_hainan['Type'] == 'FOC'])
        st.download_button(
            label=f"📥 下载 非海南 发货明细（产品{non_hainan_product} / FOC{non_hainan_foc}）",
            data=non_hainan_bytes,
            file_name=f"非海南_发货明细_{datetime.now().strftime('%Y%m')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    # 10. 数据预览
    st.markdown("---")
    st.subheader("👁️ 数据预览")
    
    tab1, tab2, tab3 = st.tabs(["📊 汇总统计", "🔍 产品预览", "🔍 FOC 预览"])
    
    with tab1:
        # 交叉统计
        summary = df_filtered.groupby(['District', 'Type']).size().unstack(fill_value=0)
        st.dataframe(summary, use_container_width=True)
    
    with tab2:
        preview_cols = ['District', 'SIS_BPCode', 'CustomerName', 'Brand', 'SKU', 'ItemName', 'Qty']
        df_product_preview = df_filtered[df_filtered['Type'] == '产品'][preview_cols].head(20)
        st.dataframe(df_product_preview, use_container_width=True)
    
    with tab3:
        df_foc_preview = df_filtered[df_filtered['Type'] == 'FOC'][preview_cols].head(20)
        st.dataframe(df_foc_preview, use_container_width=True)

# ========== 使用说明 ==========
st.markdown("---")
with st.expander("📖 使用说明"):
    st.markdown("""
    ### 操作步骤
    1. **上传 SELL IN 报表**：选择 SAP SA-007A 销售报表（Excel格式）
    2. **上传 SIS BPCode List**：选择包含 EX-PDF 编码与区域映射关系的文件
    3. 点击 **"生成发货明细"** 按钮
    4. 下载生成的 2 个 Excel 文件
    
    ### 文件说明
    - **海南_发货明细.xlsx**：仅包含 District=HAINAN 的客户数据
    - **非海南_发货明细.xlsx**：仅包含 District=NON-HAINAN 的客户数据
    - 每个文件包含 **产品 Sheet**（Amount>0）和 **FOC Sheet**（Amount=0）
    
    ### 数据安全
    - 所有计算在本地完成，不上传服务器
    """)
