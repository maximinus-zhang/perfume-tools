import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="门店地图与品牌覆盖分析", layout="wide")
st.title("🗺️ 门店分布与品牌覆盖仪表板")
st.markdown("基于 TR Store List YTD 2026 数据，可视化全国门店布局与各品牌入驻情况")

# ---- 文件上传 ----
uploaded_file = st.file_uploader("📁 上传 TR Store List YTD 2026.xlsx", type=["xlsx"])

if uploaded_file is None:
    st.info("👆 请上传文件以开始分析")
    st.markdown("""
    **数据概览**：
    - 渠道（机场、市内店、边境店、邮轮等）
    - 门店名称、城市、省份、运营商
    - 品牌覆盖（VERSACE、ANNA SUI、4711 等近30个品牌）
    """)
    st.stop()

# ============================================
# 1. 中国城市坐标映射
# ============================================
CHINA_CITY_COORDS = {
    'Sanya': (18.2528, 109.5120), 'Haikou': (20.0440, 110.3533), 'Wanning': (18.7963, 110.3892),
    'BoAo': (19.1594, 110.5815), 'Shanghai': (31.2304, 121.4737), 'Beijing': (39.9042, 116.4074),
    'Guangzhou': (23.1291, 113.2644), 'Shenzhen': (22.5431, 114.0579), 'Chengdu': (30.5728, 104.0668),
    'Chongqing': (29.4316, 106.9123), 'Xian': (34.3416, 108.9398), 'Xiamen': (24.4798, 118.0894),
    'Fuzhou': (26.0745, 119.2965), 'Nanjing': (32.0603, 118.7969), 'Nanjing': (32.0603, 118.7969),
    'Hangzhou': (30.2741, 120.1551), 'Wuhan': (30.5928, 114.3055), 'Changsha': (28.2282, 112.9388),
    'Shenyang': (41.8057, 123.4315), 'Dalian': (38.9140, 121.6147), 'Qingdao': (36.0671, 120.3826),
    'Jinan': (36.6512, 117.1201), 'Tianjing': (39.3434, 117.3616), 'Tianjin': (39.3434, 117.3616),
    'Kunming': (25.0389, 102.7183), 'URUMCHI': (43.8256, 87.6168), 'Urumchi': (43.8256, 87.6168),
    'Haerbin': (45.8038, 126.5350), 'Zhengzhou': (34.7473, 113.6249), 'Hefei': (31.8206, 117.2272),
    'Changchun': (43.8961, 125.3250), 'Taiyuan': (37.8706, 112.5489), 'Lanzhou': (36.0611, 103.8343),
    'Guiyang': (26.6470, 106.6302), 'Nanning': (22.8170, 108.3665), 'Lhasa': (29.6500, 91.1000),
    'Yinchuan': (38.4872, 106.2256), 'Xining': (36.6232, 101.7782), 'Hohhot': (40.8422, 111.7498),
    'MACAU': (22.1987, 113.5439), 'Macau': (22.1987, 113.5439),
    'Hongkong': (22.3193, 114.1694), 'Hong Kong': (22.3193, 114.1694),
    'ERLIANHAOTE': (43.6475, 111.9770), 'HEIHE': (50.2454, 127.4899),
    'HUN CHUNG': (43.7231, 131.1078), 'MANZHOULI': (49.5983, 117.3795),
    'ZHUHAI': (22.2710, 113.5767), 'Zhuhai': (22.2710, 113.5767),
    'Wuxi': (31.4909, 120.3123), 'Zhejiang': (30.2700, 120.1500),  # approximate for Wenzhou
    'Phnom Penh': (11.5564, 104.9282),  # overseas
    'CAMBODIA': (11.5564, 104.9282),
}

# 省份映射
CITY_TO_PROVINCE = {
    'Sanya': '海南', 'Haikou': '海南', 'Wanning': '海南', 'BoAo': '海南',
    'Shanghai': '上海', 'Beijing': '北京', 'Tianjing': '天津', 'Tianjin': '天津',
    'Guangzhou': '广东', 'Shenzhen': '广东', 'ZHUHAI': '广东', 'Zhuhai': '广东',
    'Chengdu': '四川', 'Chongqing': '重庆',
    'Xian': '陕西', 'Xiamen': '福建', 'Fuzhou': '福建',
    'Nanjing': '江苏', 'Wuxi': '江苏', 'Nanjin': '江苏',
    'Hangzhou': '浙江', 'Wuhan': '湖北', 'Changsha': '湖南',
    'Shenyang': '辽宁', 'Dalian': '辽宁',
    'Qingdao': '山东', 'Jinan': '山东',
    'Kunming': '云南', 'URUMCHI': '新疆', 'Urumchi': '新疆',
    'Haerbin': '黑龙江', 'Zhengzhou': '河南',
    'ERLIANHAOTE': '内蒙古', 'HOHHOT': '内蒙古',
    'HEIHE': '黑龙江', 'HUN CHUNG': '吉林',
    'MANZHOULI': '内蒙古', 'MACAU': '澳门', 'Macau': '澳门',
    'Hongkong': '香港', 'Hong Kong': '香港',
    'Zhejiang': '浙江',
}

# ============================================
# 2. 解析函数
# ============================================
@st.cache_data
def parse_store_list(file):
    """解析垂直格式的门店列表文件"""
    
    import openpyxl
    wb = openpyxl.load_workbook(file, data_only=True)
    ws = wb.active
    
    rows = list(ws.iter_rows(values_only=True))
    
    # --- 提取品牌列表（rows 19-46）---
    brands = []
    for i in range(18, 46):  # 0-indexed, rows 19-46
        if i < len(rows) and rows[i][0]:
            name = str(rows[i][0]).strip()
            if name and name not in ['Brand', 'ML CN TR', 'Y']:
                brands.append(name)
    
    st.session_state['brands_found'] = brands
    n_brands = len(brands)
    
    # --- 解析数据记录 ---
    records = []
    
    i = 48  # Data starts around row 49 (0-indexed: 48)
    while i < len(rows):
        val = str(rows[i][0]).strip() if rows[i] and rows[i][0] else ''
        
        # Skip separator lines
        if val in ['0', 'NaN', '', 'TD', 'DT', 'WFJ', 'ADJV', 'SZDF', 'CNSC', 
                    'SKY', 'ZHDF', 'LTR', 'Inflight', 'CSG', 'City Gates',
                    'Border', 'Cruise', '统一比例'] and len(val) < 20:
            i += 1
            continue
        
        # Skip section headers (all caps short names)
        if val.isupper() and len(val) <= 10 and val not in ['SANYA', 'HAIKOU']:
            i += 1
            continue
        
        # Check if this looks like a store record - contains Chinese or is a store name
        # A record starts with: Territory name, then OPERATOR name
        # Store names usually contain Chinese characters or specific patterns
        
        # Try to parse a record
        record_start = i
        
        # Read up to 40 rows to form a record
        block = []
        for j in range(i, min(i + 50, len(rows))):
            r_val = str(rows[j][0]).strip() if rows[j] and rows[j][0] else ''
            # Stop at NaN separator or known section headers
            if r_val in ['NaN', '0'] and j > record_start + 5:
                # Check if this is a true separator
                if j + 1 < len(rows):
                    next_val = str(rows[j+1][0]).strip() if rows[j+1] and rows[j+1][0] else ''
                    if next_val in ['NaN', '0', ''] or any(c.isalpha() for c in next_val):
                        break
            block.append(r_val)
        
        if len(block) < 4:
            i += 1
            continue
        
        # Parse the block to extract store attributes
        record = {}
        
        # First value is usually the Territory/Operator combined
        idx = 0
        
        # Check if first value looks like a territory name (e.g., CDFG HAINAN, CDFG / Sunrise)
        first_val = block[idx] if idx < len(block) else ''
        
        # Sometimes the first row has a very short territory indicator
        # Store name is usually the OPERATOR field
        
        # Let's build the record based on position patterns:
        # Position 0: Territory/Operator group name
        # Position 1: Store name (OPERATOR)
        # Position 2: AP Ranking (optional, number)
        # Position 3: City
        # Position 4: Area (usually ML CN)
        # Position 5: Online/Offline
        # Position 6: Category
        # Position 7: Type of Shop
        # Position 8: Opening Date
        # Position 9: Existing or NEW
        
        # Not all positions are always present. Let me use a flexible approach.
        
        # Find city (look for known city names)
        city_found = None
        for city_name in CHINA_CITY_COORDS.keys():
            for b_idx, bval in enumerate(block[:15]):
                if city_name.lower() in bval.lower().strip():
                    city_found = city_name
                    city_pos = b_idx
                    break
            if city_found:
                break
        
        if city_found is None:
            i += 1
            continue
        
        # Now parse based on position relative to city
        # Territory/Store name is before city
        attr_fields = block[:city_pos]
        # After city: Area, Online/Offline, Category, Type, Opening Date, NEW/Existing
        after_city = block[city_pos+1:] if city_pos + 1 < len(block) else []
        
        # Extract store info
        store_name = attr_fields[0] if attr_fields else first_val
        # If store name seems wrong, try the field before city
        if len(attr_fields) >= 2:
            store_name = attr_fields[-1]  # Usually the last before city is the store name
            # The territory might be attr_fields[0]
        
        territory = attr_fields[0] if attr_fields else ''
        ap_rank = ''
        for af in attr_fields[:-1]:
            if af.isdigit() or (af.replace('.','').isdigit()):
                ap_rank = af
        
        city = city_found
        area = after_city[0] if len(after_city) > 0 else ''
        online_offline = after_city[1] if len(after_city) > 1 else ''
        category = after_city[2] if len(after_city) > 2 else ''
        shop_type = after_city[3] if len(after_city) > 3 else ''
        opening_info = after_city[4] if len(after_city) > 4 else ''
        status = after_city[5] if len(after_city) > 5 else ''
        
        if 'online' in online_offline.lower():
            online_offline = 'Online'
        elif 'offline' in online_offline.lower():
            online_offline = 'Offline'
        
        # Brand data starts after the attribute fields
        # The remaining rows in the block after attributes are brand statuses
        attr_count = min(city_pos + len(after_city) + 1, len(block))
        brand_data = block[attr_count:] if attr_count < len(block) else []
        
        # Map brand values
        brand_statuses = {}
        for b_idx, brand in enumerate(brands):
            if b_idx < len(brand_data):
                val = brand_data[b_idx].strip()
                brand_statuses[brand] = val
            else:
                brand_statuses[brand] = ''
        
        # Determine province
        province = CITY_TO_PROVINCE.get(city, '其他')
        
        # Get coordinates
        lat, lng = CHINA_CITY_COORDS.get(city, (None, None))
        
        record = {
            '门店名称': store_name,
            '运营商/渠道': territory,
            '城市': city,
            '省份': province,
            '区域': area,
            '渠道类型': online_offline,
            '品类': category,
            '门店形态': shop_type,
            '开业信息': opening_info,
            '状态': status,
            'AP排名': ap_rank,
            '纬度': lat,
            '经度': lng,
            **brand_statuses
        }
        
        records.append(record)
        
        # Move to next record
        # A record is approximately 9 attributes + brand values rows
        # But the block already captured up to the separator
        # Estimate: attribute rows (variable) + brand rows (~n_brands)
        estimated_len = len(attr_fields) + len(after_city) + 1 + n_brands
        i += min(len(block), estimated_len)
    
    df = pd.DataFrame(records)
    return df

# ============================================
# 3. 加载并解析
# ============================================
with st.spinner("🔍 正在解析门店数据..."):
    try:
        df = parse_store_list(uploaded_file)
        if df.empty:
            st.error("未能解析出门店数据，请检查文件格式。")
            st.stop()
        
        # Get brand columns
        brand_cols = [c for c in df.columns if c not in [
            '门店名称', '运营商/渠道', '城市', '省份', '区域', '渠道类型',
            '品类', '门店形态', '开业信息', '状态', 'AP排名', '纬度', '经度'
        ]]
        
        st.success(f"✅ 解析完成！共 {len(df)} 个门店，{len(brand_cols)} 个品牌")
        st.session_state['store_data'] = df
        st.session_state['brand_cols'] = brand_cols
        
    except Exception as e:
        st.error(f"解析出错: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        st.stop()

# ============================================
# 4. 侧边栏筛选
# ============================================
st.sidebar.header("🔎 筛选条件")

# 品牌筛选
selected_brand = st.sidebar.selectbox(
    "选择品牌查看覆盖门店",
    ['全部品牌'] + sorted(brand_cols)
)

# 省份筛选
provinces = ['全部'] + sorted(df['省份'].unique().tolist())
selected_province = st.sidebar.selectbox("省份", provinces)

# 渠道筛选
channels = ['全部'] + sorted(df['渠道类型'].unique().tolist())
selected_channel = st.sidebar.selectbox("渠道类型", channels)

# 门店形态筛选
types = ['全部'] + sorted(df['门店形态'].unique().tolist())
selected_type = st.sidebar.selectbox("门店形态", types)

# 应用筛选
df_filtered = df.copy()

if selected_brand != '全部品牌':
    # 只显示该品牌已入驻的门店
    df_filtered = df_filtered[df_filtered[selected_brand].notna() & 
                               (df_filtered[selected_brand] != '') &
                               ~df_filtered[selected_brand].str.contains('NOT LAUNCH|NO|TBC', na=False)]

if selected_province != '全部':
    df_filtered = df_filtered[df_filtered['省份'] == selected_province]

if selected_channel != '全部':
    df_filtered = df_filtered[df_filtered['渠道类型'] == selected_channel]

if selected_type != '全部':
    df_filtered = df_filtered[df_filtered['门店形态'] == selected_type]

# ============================================
# 5. KPI 概览
# ============================================
st.subheader("📊 概览统计")

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
with kpi1:
    st.metric("🏪 总门店数", len(df_filtered))
with kpi2:
    st.metric("🗺️ 覆盖城市", df_filtered['城市'].nunique())
with kpi3:
    st.metric("🏛️ 覆盖省份", df_filtered['省份'].nunique())
with kpi4:
    st.metric("📦 品牌总数", len(brand_cols))
with kpi5:
    if selected_brand != '全部品牌':
        st.metric(f"🔷 {selected_brand} 门店数", len(df_filtered))
    else:
        online = len(df_filtered[df_filtered['渠道类型'].str.contains('Online', na=False)])
        st.metric("🌐 线上门店", online)

# ============================================
# 6. 中国地图
# ============================================
st.subheader("🗺️ 中国门店分布地图")

# 按城市汇总门店数量
city_counts = df_filtered.groupby(['城市', '纬度', '经度', '省份']).size().reset_index(name='门店数')
city_counts = city_counts.dropna(subset=['纬度', '经度'])

if not city_counts.empty:
    # 地图标题
    if selected_brand != '全部品牌':
        map_title = f'{selected_brand} 品牌覆盖门店分布'
    else:
        map_title = '全品牌门店分布'
    
    # 创建地图
    fig_map = go.Figure()
    
    # 添加中国省份边界（简化）
    fig_map.add_trace(go.Scattergeo(
        lon=city_counts['经度'],
        lat=city_counts['纬度'],
        text=city_counts.apply(
            lambda r: f"<b>{r['城市']}</b><br>门店数: {r['门店数']}<br>省份: {r['省份']}", axis=1
        ),
        mode='markers+text',
        marker=dict(
            size=city_counts['门店数'] * 8 + 10,
            color='#FF6B35',
            line=dict(width=1, color='#fff'),
            sizemode='area',
            sizemin=8,
        ),
        textposition='top center',
        textfont=dict(size=10, color='#333'),
        name='门店'
    ))
    
    fig_map.update_layout(
        title=dict(text=map_title, x=0.5),
        geo=dict(
            scope='asia',
            projection=dict(type='natural earth'),
            showland=True,
            landcolor='rgb(243, 243, 243)',
            countrycolor='rgb(204, 204, 204)',
            coastlinecolor='rgb(204, 204, 204)',
            showcountries=True,
            lonaxis=dict(range=[73, 135]),
            lataxis=dict(range=[18, 54]),
            center=dict(lat=35, lon=105),
        ),
        height=600,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    
    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.warning("当前筛选条件下没有可显示的门店位置数据。")

# ============================================
# 7. 图表分析
# ============================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏛️ 省份分布 Top 15")
    prov_counts = df_filtered['省份'].value_counts().head(15).reset_index()
    prov_counts.columns = ['省份', '门店数']
    
    fig_prov = px.bar(
        prov_counts, x='门店数', y='省份', orientation='h',
        title='门店数量 Top 15 省份',
        color='门店数', color_continuous_scale='Blues',
        text='门店数'
    )
    fig_prov.update_traces(textposition='outside')
    fig_prov.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_prov, use_container_width=True)

with col2:
    st.subheader("🏪 门店形态分布")
    type_counts = df_filtered['门店形态'].value_counts().reset_index()
    type_counts.columns = ['门店形态', '数量']
    
    fig_type = px.pie(
        type_counts, values='数量', names='门店形态',
        title='门店形态占比',
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig_type.update_layout(height=400)
    st.plotly_chart(fig_type, use_container_width=True)

col3, col4 = st.columns(2)

with col3:
    st.subheader("📡 渠道类型分布")
    ch_counts = df_filtered['渠道类型'].value_counts().reset_index()
    ch_counts.columns = ['渠道类型', '数量']
    
    fig_ch = px.bar(
        ch_counts, x='渠道类型', y='数量',
        title='线上 vs 线下分布',
        color='渠道类型', text='数量'
    )
    fig_ch.update_layout(height=350, showlegend=False)
    st.plotly_chart(fig_ch, use_container_width=True)

with col4:
    st.subheader("📊 品牌覆盖热度")
    if selected_brand == '全部品牌':
        # 显示品牌覆盖门店数 Top 15
        brand_coverage = {}
        for b in brand_cols:
            count = len(df[df[b].notna() & (df[b] != '') & 
                          ~df[b].str.contains('NOT LAUNCH|NO|TBC', na=False)])
            brand_coverage[b] = count
        
        bc_df = pd.DataFrame(list(brand_coverage.items()), columns=['品牌', '覆盖门店数'])
        bc_df = bc_df.sort_values('覆盖门店数', ascending=False).head(15)
        
        fig_bc = px.bar(
            bc_df, x='覆盖门店数', y='品牌', orientation='h',
            title='品牌覆盖门店数 Top 15',
            color='覆盖门店数', color_continuous_scale='Greens',
            text='覆盖门店数'
        )
        fig_bc.update_traces(textposition='outside')
        fig_bc.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_bc, use_container_width=True)
    else:
        # 显示该品牌在各个省份的覆盖
        brand_prov = df_filtered[df_filtered[selected_brand].notna() & 
                                 (df_filtered[selected_brand] != '') &
                                 ~df_filtered[selected_brand].str.contains('NOT LAUNCH|NO|TBC', na=False)]
        prov_brand = brand_prov['省份'].value_counts().reset_index()
        prov_brand.columns = ['省份', '门店数']
        
        fig_bp = px.bar(
            prov_brand, x='门店数', y='省份', orientation='h',
            title=f'{selected_brand} 各省份覆盖门店',
            color='门店数', color_continuous_scale='Oranges',
            text='门店数'
        )
        fig_bp.update_traces(textposition='outside')
        fig_bp.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_bp, use_container_width=True)

# ============================================
# 8. 城市门店详情表
# ============================================
st.subheader("📋 门店列表")

if selected_brand != '全部品牌':
    # 显示该品牌入驻的门店详情
    brand_stores = df_filtered[df_filtered[selected_brand].notna() & 
                                (df_filtered[selected_brand] != '') &
                                ~df_filtered[selected_brand].str.contains('NOT LAUNCH|NO|TBC', na=False)]
    
    display_cols = ['门店名称', '城市', '省份', '渠道类型', '门店形态', '状态', selected_brand]
    display_df = brand_stores[display_cols].sort_values(['省份', '城市'])
    st.dataframe(display_df, use_container_width=True, height=400)
else:
    display_cols = ['门店名称', '城市', '省份', '渠道类型', '门店形态', '状态']
    display_df = df_filtered[display_cols].sort_values(['省份', '城市'])
    st.dataframe(display_df, use_container_width=True, height=400)

# ============================================
# 9. 品牌覆盖矩阵
# ============================================
with st.expander("📊 查看品牌 × 门店覆盖矩阵"):
    if selected_brand == '全部品牌':
        st.info("正在计算品牌覆盖矩阵...")
        
        # 为每个品牌创建覆盖列
        matrix_data = []
        for _, row in df.iterrows():
            store_name = row['门店名称']
            city = row['城市']
            province = row['省份']
            record = {'门店': f"{city} - {store_name}", '城市': city, '省份': province}
            
            for b in brand_cols:
                val = str(row[b]) if pd.notna(row[b]) else ''
                if val and val not in ['', 'NOT LAUNCH', 'NO', 'NaN', 'nan'] and 'TBC' not in val:
                    record[b] = '✓'
                else:
                    record[b] = ''
            
            matrix_data.append(record)
        
        matrix_df = pd.DataFrame(matrix_data)
        st.dataframe(matrix_df, use_container_width=True, height=500)
    else:
        st.info(f"当前筛选品牌: {selected_brand}")

# ============================================
# 10. 数据导出
# ============================================
st.subheader("💾 数据导出")

csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    "📥 下载当前筛选数据 (CSV)",
    csv,
    f"门店列表_{datetime.now():%Y%m%d}.csv",
    "text/csv"
)
