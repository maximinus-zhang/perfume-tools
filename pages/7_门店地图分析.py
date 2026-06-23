import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="TR门店地图与品牌覆盖", layout="wide")
st.title("🗺️ 免税门店分布与品牌覆盖仪表板")
st.markdown("基于 TR Store List YTD 2026 数据，可视化全国门店布局并筛选品牌查看覆盖位置")

# ---- 城市坐标 ----
CITY_COORDS = {
    'Sanya': (18.25, 109.51), 'Haikou': (20.04, 110.35), 'Wanning': (18.80, 110.39),
    'BoAo': (19.16, 110.58), 'Shanghai': (31.23, 121.47), 'Beijing': (39.90, 116.41),
    'Guangzhou': (23.13, 113.26), 'Shenzhen': (22.54, 114.06), 'Chengdu': (30.57, 104.07),
    'Chongqing': (29.43, 106.91), 'Xian': (34.34, 108.94), 'Xiamen': (24.48, 118.09),
    'Fuzhou': (26.07, 119.30), 'Nanjing': (32.06, 118.80), 'Hangzhou': (30.27, 120.16),
    'Wuhan': (30.59, 114.31), 'Changsha': (28.23, 112.94), 'Shenyang': (41.81, 123.43),
    'Dalian': (38.91, 121.61), 'Qingdao': (36.07, 120.38), 'Jinan': (36.65, 117.12),
    'Tianjing': (39.34, 117.36), 'Tianjin': (39.34, 117.36), 'Kunming': (25.04, 102.72),
    'URUMCHI': (43.83, 87.62), 'Haerbin': (45.80, 126.54), 'Zhengzhou': (34.75, 113.62),
    'MACAU': (22.20, 113.54), 'Macau': (22.20, 113.54), 'Hongkong': (22.32, 114.17),
    'ERLIANHAOTE': (43.65, 111.98), 'HEIHE': (50.25, 127.49),
    'HUN CHUNG': (43.72, 131.11), 'MANZHOULI': (49.60, 117.38),
    'ZHUHAI': (22.27, 113.58), 'Zhuhai': (22.27, 113.58), 'Wuxi': (31.49, 120.31),
}

PROVINCE_MAP = {
    'Sanya': '海南', 'Haikou': '海南', 'Wanning': '海南', 'BoAo': '海南',
    'Shanghai': '上海', 'Beijing': '北京', 'Tianjing': '天津', 'Tianjin': '天津',
    'Guangzhou': '广东', 'Shenzhen': '广东', 'ZHUHAI': '广东', 'Zhuhai': '广东',
    'Chengdu': '四川', 'Chongqing': '重庆', 'Xian': '陕西',
    'Xiamen': '福建', 'Fuzhou': '福建', 'Nanjing': '江苏', 'Wuxi': '江苏',
    'Hangzhou': '浙江', 'Wuhan': '湖北', 'Changsha': '湖南',
    'Shenyang': '辽宁', 'Dalian': '辽宁', 'Qingdao': '山东', 'Jinan': '山东',
    'Kunming': '云南', 'URUMCHI': '新疆', 'Haerbin': '黑龙江',
    'ERLIANHAOTE': '内蒙古', 'HEIHE': '黑龙江', 'HUN CHUNG': '吉林',
    'MANZHOULI': '内蒙古', 'MACAU': '澳门', 'Hongkong': '香港',
}

# ---- 上传 ----
uploaded_file = st.file_uploader("📁 上传 TR Store List YTD 2026.xlsx", type=["xlsx"])

if uploaded_file is None:
    st.info("👆 请上传文件以开始分析")
    st.markdown("""
    **数据来源**：TR Store List YTD 2026 文件  
    **包含信息**：渠道（机场/市内店/边境店等）、门店名称、城市、品牌覆盖现状
    """)
    st.stop()

# ============================================
# 解析函数——更稳健的垂直格式解析
# ============================================
@st.cache_data
def parse_store_file(file):
    import openpyxl
    wb = openpyxl.load_workbook(file, data_only=True)
    ws = wb.active
    
    # 读取列A所有值（第一列）
    col_a = []
    for row in ws.iter_rows(min_col=1, max_col=1, values_only=True):
        val = str(row[0]).strip() if row[0] is not None else ''
        col_a.append(val)
    
    # 提取品牌列表（第19-46行，索引18-45）
    brand_names = []
    for i in range(18, min(46, len(col_a))):
        v = col_a[i]
        if v and v not in ['Brand', 'ML CN TR', 'Y', '']:
            brand_names.append(v)
    
    known_cities = set(CITY_COORDS.keys())
    known_cities_lower = {k.lower(): k for k in known_cities}
    
    records = []
    i = 48  # 从第49行（index 48）开始
    
    while i < len(col_a):
        val = col_a[i]
        
        # 跳过分隔行
        if not val or val in ['NaN', 'nan', '0', '']:
            i += 1
            continue
        
        # 跳过已知的节标题
        section_headers = {'TD', 'DT', 'WFJ', 'ADJV', 'SZDF', 'CNSC', 'SKY', 'ZHDF',
                          'LTR', 'CSG', 'Border', 'Cruise', 'Inflight', 'City Gates',
                          'Distribution Summary 2025', 'Distribution Summary 2026 by brand',
                          '统一比例', 'Generic New brand', 'A', 'HP ready Jul', 'ID new brand',
                          'online new brand', 'Eternal CN TR DIstribution 2026 Plan & NEW POS PLAN'}
        if val in section_headers:
            i += 1
            continue
        if val.isupper() and len(val) <= 8 and val not in ['SANYA', 'HAIKOU', 'MACAU']:
            # 短大写词可能是节标题
            if i + 2 < len(col_a):
                next_val = col_a[i+1]
                if next_val and next_val.lower() in known_cities_lower:
                    pass  # 这是城市名，继续
                else:
                    i += 1
                    continue
        
        # 收集一条记录的数据块（从当前位置到下一个NaN或节标题）
        block = []
        j = i
        while j < len(col_a):
            v = col_a[j]
            if v in ['NaN', 'nan', ''] or (v in section_headers and j > i):
                break
            if v == '0' and len(block) > 5:
                # 检查是否是真正的分隔
                if j + 1 < len(col_a) and col_a[j+1] in ['NaN', 'nan', '']:
                    break
                if j + 1 < len(col_a) and col_a[j+1] in section_headers:
                    break
            block.append(v)
            j += 1
        
        if len(block) < 4:
            i = j + 1 if j < len(col_a) else len(col_a)
            continue
        
        # ---- 解析块中的记录 ----
        # 查找城市名——这是关键锚点
        city_idx = -1
        city_name = ''
        for idx, bv in enumerate(block):
            bv_clean = bv.strip().rstrip('.')
            if bv_clean in known_cities_lower:
                city_name = known_cities_lower[bv_clean]
                city_idx = idx
                break
            # 尝试部分匹配
            for ck, cv in known_cities_lower.items():
                if ck in bv_clean.lower() or bv_clean.lower() in ck:
                    if len(bv_clean) >= 3:
                        city_name = cv
                        city_idx = idx
                        break
            if city_idx >= 0:
                break
        
        if city_idx < 0:
            i = j + 1 if j < len(col_a) else len(col_a)
            continue
        
        # 城市名之前的字段 = 门店属性
        before_city = block[:city_idx]
        # 城市名之后的字段 = 地区、渠道、类型等 + 品牌状态
        after_city = block[city_idx+1:]
        
        # 确定门店名称
        store_name = ''
        territory = ''
        
        if len(before_city) >= 1:
            # 第一个可能是Territory，最后一个是门店名
            if len(before_city) == 1:
                store_name = before_city[0]
            elif len(before_city) >= 2:
                # 检查是否包含Territory
                first = before_city[0]
                if any(t in first.upper() for t in ['CDFG', 'SUNRISE', 'DUFRY', 'CNSC', 'LTR', 'WFJ']):
                    territory = first
                    store_name = before_city[-1]
                else:
                    store_name = before_city[-1]
                    if len(before_city) >= 3:
                        territory = before_city[0]
        
        # 解析城市后的字段
        area = after_city[0] if len(after_city) > 0 else ''
        channel = ''
        category = ''
        shop_type = ''
        opening = ''
        
        for av in after_city[1:6]:  # 检查前几个值
            av_lower = av.lower()
            if av_lower in ['offline', 'online']:
                channel = av
            elif av_lower in ['hn', 'intl ap', 'dt', 'border, cruise, others', 'border']:
                category = av
            elif 'international ap' in av_lower or av_lower in ['dt', 'border shop', 'cruise', 'inflight']:
                if not shop_type:
                    shop_type = av
            elif 'existing' in av_lower or 'new' in av_lower or av_lower.startswith('20'):
                if not opening:
                    opening = av
        
        # 剩余字段 = 品牌状态
        attr_count = 1 + len(before_city) + min(6, len(after_city))
        brand_data = block[attr_count:] if attr_count < len(block) else []
        
        brand_statuses = {}
        for bi, bn in enumerate(brand_names):
            if bi < len(brand_data):
                bv = brand_data[bi]
                brand_statuses[bn] = bv
            else:
                brand_statuses[bn] = ''
        
        # 省份
        province = PROVINCE_MAP.get(city_name, '其他')
        
        # 坐标
        lat, lng = CITY_COORDS.get(city_name, (None, None))
        
        # 计算已入驻品牌数
        brands_present = sum(1 for bv in brand_statuses.values() 
                             if bv and bv not in ['', 'NOT LAUNCH', 'NO', 'NaN', 'nan'] and 'TBC' not in bv and 'wait' not in bv.lower())
        
        record = {
            '门店名称': store_name,
            '运营商/渠道': territory,
            '城市': city_name,
            '省份': province,
            '区域': area,
            '渠道类型': channel if channel else ('Online' if 'online' in str(store_name).lower() else 'Offline'),
            '品类': category,
            '门店形态': shop_type,
            '开业信息': opening,
            '纬度': lat,
            '经度': lng,
            '入驻品牌数': brands_present,
            **brand_statuses
        }
        
        records.append(record)
        
        # 移到下一个记录
        i = j + 1 if j < len(col_a) else len(col_a)
    
    df = pd.DataFrame(records)
    return df, brand_names

# ---- 加载 ----
with st.spinner("🔍 正在解析门店数据..."):
    try:
        df, brand_names = parse_store_file(uploaded_file)
        
        if df.empty:
            st.error("未能解析出门店数据，请确认文件格式正确。")
            st.stop()
        
        st.success(f"✅ 解析完成！共识别 {len(df)} 个门店，{len(brand_names)} 个品牌")
        
    except Exception as e:
        st.error(f"解析出错: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        st.stop()

# ---- 侧边栏筛选 ----
st.sidebar.header("🔎 筛选条件")

selected_brand = st.sidebar.selectbox(
    "选择品牌查看覆盖门店",
    ['全部品牌'] + sorted(brand_names)
)

provinces = ['全部'] + sorted(df['省份'].unique().tolist())
selected_province = st.sidebar.selectbox("省份", provinces)

# 品牌状态筛选
df_filtered = df.copy()

if selected_brand != '全部品牌':
    # 过滤出该品牌已入驻的门店
    mask = df_filtered[selected_brand].apply(
        lambda x: x and str(x) not in ['', 'NOT LAUNCH', 'NO', 'NaN', 'nan'] and 'TBC' not in str(x) and 'wait' not in str(x).lower()
    )
    df_filtered = df_filtered[mask]

if selected_province != '全部':
    df_filtered = df_filtered[df_filtered['省份'] == selected_province]

# ---- KPI ----
st.subheader("📊 概览统计")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric("🏪 门店数", len(df_filtered))
with kpi2:
    st.metric("🗺️ 城市数", df_filtered['城市'].nunique())
with kpi3:
    st.metric("🏛️ 省份数", df_filtered['省份'].nunique())
with kpi4:
    avg_brands = df_filtered['入驻品牌数'].mean()
    st.metric("📦 平均品牌数", f"{avg_brands:.0f}" if not pd.isna(avg_brands) else "N/A")

# ---- 中国地图 ----
st.subheader("🗺️ 中国门店分布地图")

city_stats = df_filtered.groupby(['城市', '省份', '纬度', '经度']).size().reset_index(name='门店数')
city_stats = city_stats.dropna(subset=['纬度', '经度'])

if not city_stats.empty:
    title = f'{selected_brand} 品牌覆盖门店' if selected_brand != '全部品牌' else '全品牌门店分布'
    
    fig = go.Figure()
    
    fig.add_trace(go.Scattergeo(
        lon=city_stats['经度'],
        lat=city_stats['纬度'],
        text=city_stats.apply(
            lambda r: f"<b>{r['城市']}</b><br>门店: {r['门店数']} | 省份: {r['省份']}", axis=1
        ),
        mode='markers+text',
        marker=dict(
            size=np.sqrt(city_stats['门店数']) * 20 + 10,
            color='#FF6B35',
            line=dict(width=1, color='white'),
            sizemode='area',
            sizemin=8,
        ),
        textposition='top center',
        textfont=dict(size=9, color='#333'),
    ))
    
    fig.update_layout(
        title=dict(text=title, x=0.5),
        geo=dict(
            scope='asia',
            projection=dict(type='natural earth'),
            showland=True,
            landcolor='rgb(240, 240, 240)',
            countrycolor='rgb(200, 200, 200)',
            coastlinecolor='rgb(200, 200, 200)',
            showcountries=True,
            lonaxis=dict(range=[73, 135]),
            lataxis=dict(range=[18, 54]),
            center=dict(lat=35, lon=105),
        ),
        height=600,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("当前筛选条件下无地图数据")

# ---- 图表 ----
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏛️ 省份分布")
    prov_df = df_filtered['省份'].value_counts().head(15).reset_index()
    prov_df.columns = ['省份', '门店数']
    
    fig_p = px.bar(prov_df, x='门店数', y='省份', orientation='h',
                   color='门店数', color_continuous_scale='Blues', text='门店数')
    fig_p.update_traces(textposition='outside')
    fig_p.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_p, use_container_width=True)

with col2:
    st.subheader("🏪 门店形态分布")
    type_df = df_filtered['门店形态'].value_counts().reset_index()
    type_df.columns = ['门店形态', '数量']
    
    fig_t = px.pie(type_df, values='数量', names='门店形态',
                   color_discrete_sequence=px.colors.qualitative.Set3)
    fig_t.update_layout(height=400)
    st.plotly_chart(fig_t, use_container_width=True)

# ---- 品牌覆盖排名 ----
st.subheader("📊 品牌覆盖门店排名")

if selected_brand == '全部品牌':
    brand_counts = {}
    for b in brand_names:
        cnt = df[b].apply(
            lambda x: 1 if x and str(x) not in ['', 'NOT LAUNCH', 'NO', 'NaN', 'nan'] 
                     and 'TBC' not in str(x) and 'wait' not in str(x).lower() else 0
        ).sum()
        brand_counts[b] = cnt
    
    bc_df = pd.DataFrame(list(brand_counts.items()), columns=['品牌', '覆盖门店数'])
    bc_df = bc_df.sort_values('覆盖门店数', ascending=False).head(20)
    
    fig_bc = px.bar(bc_df, x='覆盖门店数', y='品牌', orientation='h',
                    color='覆盖门店数', color_continuous_scale='Greens', text='覆盖门店数')
    fig_bc.update_traces(textposition='outside')
    fig_bc.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_bc, use_container_width=True)
else:
    # 显示该品牌的省份分布
    brand_prov = df_filtered['省份'].value_counts().reset_index()
    brand_prov.columns = ['省份', '门店数']
    
    fig_bp = px.bar(brand_prov, x='门店数', y='省份', orientation='h',
                    color='门店数', color_continuous_scale='Oranges', text='门店数')
    fig_bp.update_traces(textposition='outside')
    fig_bp.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_bp, use_container_width=True)

# ---- 门店列表 ----
st.subheader("📋 门店列表")
display_cols = ['门店名称', '城市', '省份', '渠道类型', '门店形态', '入驻品牌数']
if selected_brand != '全部品牌':
    display_cols.append(selected_brand)

ddf = df_filtered[display_cols].sort_values(['省份', '城市'])
st.dataframe(ddf, use_container_width=True, height=400)

# ---- 导出 ----
st.subheader("💾 导出")
csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
st.download_button("📥 下载 CSV", csv, f"门店列表_{datetime.now():%Y%m%d}.csv", "text/csv")
