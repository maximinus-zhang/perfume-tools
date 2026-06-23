import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import openpyxl

st.set_page_config(page_title="门店地图与品牌覆盖", layout="wide")
st.title("🗺️ TR 免税门店分布与品牌覆盖")

# ---- 坐标数据库 ----
CITY_COORDS = {
    'Sanya': [18.25, 109.51], 'Haikou': [20.04, 110.35], 'Wanning': [18.80, 110.39],
    'BoAo': [19.16, 110.58], 'Shanghai': [31.23, 121.47], 'Beijing': [39.90, 116.41],
    'Guangzhou': [23.13, 113.26], 'Shenzhen': [22.54, 114.06], 'Chengdu': [30.57, 104.07],
    'Chongqing': [29.43, 106.91], 'Xian': [34.34, 108.94], 'Xiamen': [24.48, 118.09],
    'Fuzhou': [26.07, 119.30], 'Nanjing': [32.06, 118.80], 'Hangzhou': [30.27, 120.16],
    'Wuhan': [30.59, 114.31], 'Changsha': [28.23, 112.94], 'Shenyang': [41.81, 123.43],
    'Dalian': [38.91, 121.61], 'Qingdao': [36.07, 120.38], 'Jinan': [36.65, 117.12],
    'Tianjing': [39.34, 117.36], 'Tianjin': [39.34, 117.36], 'Kunming': [25.04, 102.72],
    'URUMCHI': [43.83, 87.62], 'Haerbin': [45.80, 126.54], 'Zhengzhou': [34.75, 113.62],
    'MACAU': [22.20, 113.54], 'Hongkong': [22.32, 114.17],
    'ERLIANHAOTE': [43.65, 111.98], 'HEIHE': [50.25, 127.49],
    'HUN CHUNG': [43.72, 131.11], 'MANZHOULI': [49.60, 117.38],
    'ZHUHAI': [22.27, 113.58], 'Zhuhai': [22.27, 113.58], 'Wuxi': [31.49, 120.31],
    'Angkor': [13.36, 103.86], 'Phnom Penh': [11.56, 104.93],
    'Xigang': [30.58, 117.25],  # 西岗 approximate
    'Zhejiang': [28.00, 120.50], 'Nanjin': [32.06, 118.80],
}

PROVINCE_MAP = {
    'Sanya': '海南', 'Haikou': '海南', 'Wanning': '海南', 'BoAo': '海南',
    'Shanghai': '上海', 'Beijing': '北京', 'Tianjing': '天津', 'Tianjin': '天津',
    'Guangzhou': '广东', 'Shenzhen': '广东', 'ZHUHAI': '广东', 'Zhuhai': '广东',
    'Chengdu': '四川', 'Chongqing': '重庆', 'Xian': '陕西',
    'Xiamen': '福建', 'Fuzhou': '福建', 'Nanjing': '江苏', 'Wuxi': '江苏', 'Nanjin': '江苏',
    'Hangzhou': '浙江', 'Wuhan': '湖北', 'Changsha': '湖南',
    'Shenyang': '辽宁', 'Dalian': '辽宁', 'Qingdao': '山东', 'Jinan': '山东',
    'Kunming': '云南', 'URUMCHI': '新疆', 'Haerbin': '黑龙江',
    'ERLIANHAOTE': '内蒙古', 'HEIHE': '黑龙江', 'HUN CHUNG': '吉林',
    'MANZHOULI': '内蒙古', 'MACAU': '澳门', 'Hongkong': '香港',
    'Zhejiang': '浙江', 'Angkor': '海外', 'Phnom Penh': '海外', 'Xigang': '海外',
}

KNOWN_CITIES = set(c.lower() for c in CITY_COORDS.keys())

SINGLE_WORD_HEADERS = {'TD', 'DT', 'WFJ', 'ADJV', 'SZDF', 'CNSC', 'SKY', 'ZHDF',
                       'LTR', 'CSG', 'CDFG', 'GDF', 'SEA TR', 'MPP',
                       'Border', 'Cruise', 'Inflight', 'City Gates',
                       'CONNECTION', 'Sunrise Apps', 'Generic New brand'}

uploaded_file = st.file_uploader("📁 上传 TR Store List YTD 2026.xlsx", type=["xlsx"])

if uploaded_file:
    with st.spinner("读取中..."):
        wb = openpyxl.load_workbook(uploaded_file, data_only=True)
        ws = wb.active
        
        # 读取列A所有值
        vals = []
        for row in ws.iter_rows(min_col=1, max_col=1, values_only=True):
            v = row[0]
            s = str(v).strip() if v is not None else ''
            vals.append(s)
        
        # 提取品牌列表（第19-46行）
        brand_list = []
        for i in range(18, min(46, len(vals))):
            n = vals[i]
            if n and n not in ('Brand', 'ML CN TR', 'Y', '0', 'NaN', ''):
                brand_list.append(n)
        
        n_brands = len(brand_list)
        
        # ---- 用 NaN 分割记录 ----
        # 找到所有 NaN 位置作为分隔
        nan_positions = [i for i, v in enumerate(vals) if v == 'NaN']
        
        records = []
        seen_stores = set()
        
        # 从第49行开始到第一个NaN之前收集记录
        # 然后用NaN之间的块收集
        segments = []
        prev = 48  # 数据从第49行开始
        
        for np in nan_positions:
            if np > prev:
                segments.append((prev, np))
            prev = np + 1
        
        # 最后一个NaN之后到结束或到汇总
        end_pos = len(vals)
        for i in range(prev, len(vals)):
            if vals[i].startswith('Distribution Summary'):
                end_pos = i
                break
        if end_pos > prev:
            segments.append((prev, end_pos))
        
        # 解析每个段
        for start, end in segments:
            block = [vals[i] for i in range(start, end) if vals[i] and vals[i] != '0']
            
            if len(block) < 5:
                continue
            
            # 找城市名
            city_idx = -1
            city_name = ''
            for idx, bv in enumerate(block):
                bv_lower = bv.strip().lower().rstrip('.')
                if bv_lower in KNOWN_CITIES:
                    # 找到匹配
                    for ck in CITY_COORDS:
                        if ck.lower() == bv_lower:
                            city_name = ck
                            city_idx = idx
                            break
                    break
            
            if city_idx < 0 or city_name in ('S', ''):
                continue
            
            # 城市前的值 = 属性
            before = block[:city_idx]
            after = block[city_idx+1:]
            
            # 门店名 = before的最后一个
            store_name = before[-1] if before else '(未知)'
            territory = before[0] if len(before) > 1 else ''
            
            # 跳过单字标题
            if store_name in SINGLE_WORD_HEADERS:
                continue
            
            # 跳过重复
            if store_name in seen_stores:
                continue
            seen_stores.add(store_name)
            
            # 解析城市后的属性
            area = after[0] if len(after) > 0 else 'ML CN'
            channel = ''
            category = ''
            shop_type = ''
            opening = ''
            
            attr_end = 0
            for idx, av in enumerate(after):
                avl = av.strip().lower()
                if avl in ('offline', 'online'):
                    channel = av.strip()
                    attr_end = idx + 1
                elif avl in ('hn', 'intl ap', 'dt', 'border, cruise, others', 'border'):
                    category = av.strip()
                    attr_end = max(attr_end, idx + 1)
                elif 'international ap' in avl or avl in ('border shop', 'cruise', 'inflight'):
                    shop_type = av.strip()
                    attr_end = max(attr_end, idx + 1)
                elif avl.startswith('existing') or avl.startswith('new') or avl.startswith('20') or 'sell' in avl or '开业' in avl:
                    opening = av.strip()
                    attr_end = max(attr_end, idx + 1)
            
            # 如果没找到channel，默认Offline
            if not channel:
                channel = 'Offline'
            # 如果没找到category
            if not category:
                # 从after中推断
                for av in after[:5]:
                    avl = av.strip().lower()
                    if 'hn' in avl:
                        category = 'HN'
                    elif 'intl' in avl:
                        category = 'INTL AP'
                    elif 'border' in avl:
                        category = 'BORDER'
                if not category:
                    category = 'DT'
            
            # 品牌数据 = 剩余的值
            brand_start = 1 + len(after[:attr_end+1]) if attr_end > 0 else min(8, len(after))
            brand_vals = block[city_idx + 1 + brand_start:]
            
            # 如果品牌值太少，调整
            if len(brand_vals) < 5:
                brand_vals = block[city_idx + 7:]
            
            brand_data = {}
            for bi, bn in enumerate(brand_list):
                if bi < len(brand_vals):
                    brand_data[bn] = brand_vals[bi]
                else:
                    brand_data[bn] = ''
            
            # 计算已入驻品牌
            active_brands = sum(1 for bv in brand_data.values() 
                              if bv and bv not in ('', 'NOT LAUNCH', 'NO', 'NaN', 'nan', '??', '0') 
                              and 'TBC' not in str(bv) and 'wait' not in str(bv).lower())
            
            lat, lng = CITY_COORDS.get(city_name, (None, None))
            province = PROVINCE_MAP.get(city_name, '其他')
            
            records.append({
                '门店名称': store_name,
                '运营商': territory,
                '城市': city_name,
                '省份': province,
                '区域': area,
                '渠道': channel,
                '品类': category,
                '门店形态': shop_type if shop_type else category,
                '开业信息': opening,
                '纬度': lat,
                '经度': lng,
                '入驻品牌数': active_brands,
                **brand_data
            })
        
        if records:
            df = pd.DataFrame(records)
            st.success(f"✅ 解析成功！共 {len(df)} 个门店，{len(brand_list)} 个品牌")
        else:
            st.error("未能解析出门店数据")
            st.stop()
    
    # ---- 筛选 ----
    st.sidebar.header("🔎 筛选")
    
    brand_options = ['全部品牌'] + sorted(brand_list)
    selected_brand = st.sidebar.selectbox("选择品牌", brand_options)
    
    provinces = ['全部'] + sorted(df['省份'].unique().tolist())
    selected_province = st.sidebar.selectbox("省份", provinces)
    
    df_filtered = df.copy()
    
    if selected_brand != '全部品牌':
        df_filtered = df_filtered[
            df_filtered[selected_brand].apply(
                lambda x: x and str(x) not in ('', 'NOT LAUNCH', 'NO', 'NaN', 'nan', '??') 
                         and 'TBC' not in str(x) and 'wait' not in str(x).lower()
            )
        ]
    
    if selected_province != '全部':
        df_filtered = df_filtered[df_filtered['省份'] == selected_province]
    
    # ---- KPI ----
    st.subheader("📊 概览")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("🏪 门店数", len(df_filtered))
    with c2: st.metric("🗺️ 城市数", df_filtered['城市'].nunique())
    with c3: st.metric("🏛️ 省份数", df_filtered['省份'].nunique())
    with c4:
        ab = df_filtered['入驻品牌数'].mean()
        st.metric("📦 平均品牌数", f"{ab:.0f}" if not pd.isna(ab) else "N/A")
    
    # ---- 地图 ----
    st.subheader("🗺️ 中国门店地图")
    
    city_stats = df_filtered.groupby(['城市', '省份', '纬度', '经度']).size().reset_index(name='门店数')
    city_stats = city_stats.dropna(subset=['纬度'])
    
    if not city_stats.empty:
        title = f'{selected_brand} - 覆盖门店' if selected_brand != '全部品牌' else '全品牌门店分布'
        
        fig = go.Figure()
        fig.add_trace(go.Scattergeo(
            lon=city_stats['经度'], lat=city_stats['纬度'],
            text=city_stats.apply(lambda r: f"<b>{r['城市']}</b><br>{r['门店数']}店 | {r['省份']}", axis=1),
            mode='markers+text',
            marker=dict(
                size=city_stats['门店数'] * 12 + 10,
                color='#FF6B35', line=dict(width=1, color='white'),
                sizemode='area'
            ),
            textposition='top center', textfont=dict(size=9),
        ))
        fig.update_layout(
            title=title,
            geo=dict(
                scope='asia',
                projection=dict(type='natural earth'),
                showland=True, landcolor='rgb(240,240,240)',
                countrycolor='rgb(200,200,200)',
                lonaxis=dict(range=[73, 135]),
                lataxis=dict(range=[18, 54]),
                center=dict(lat=35, lon=105),
            ),
            height=550, margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("无地图数据")
    
    # ---- 图表 ----
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏛️ 省份分布")
        pv = df_filtered['省份'].value_counts().head(15).reset_index()
        pv.columns = ['省份', '门店数']
        fig = px.bar(pv, x='门店数', y='省份', orientation='h',
                    color='门店数', color_continuous_scale='Blues', text='门店数')
        fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🏪 门店形态")
        tv = df_filtered['门店形态'].value_counts().reset_index()
        tv.columns = ['门店形态', '数量']
        fig = px.pie(tv, values='数量', names='门店形态',
                    color_discrete_sequence=px.colors.qualitative.Set3)
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # ---- 品牌覆盖排名 ----
    st.subheader("📊 品牌覆盖排名")
    if selected_brand == '全部品牌':
        bc = {}
        for b in brand_list:
            cnt = df[b].apply(lambda x: 1 if x and str(x) not in ('', 'NOT LAUNCH', 'NO', 'NaN', '??') 
                            and 'TBC' not in str(x) and 'wait' not in str(x).lower() else 0).sum()
            bc[b] = cnt
        bdf = pd.DataFrame(list(bc.items()), columns=['品牌', '覆盖门店数']).sort_values('覆盖门店数', ascending=False).head(20)
        fig = px.bar(bdf, x='覆盖门店数', y='品牌', orientation='h',
                    color='覆盖门店数', color_continuous_scale='Greens', text='覆盖门店数')
        fig.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        bv = df_filtered['省份'].value_counts().reset_index()
        bv.columns = ['省份', '门店数']
        fig = px.bar(bv, x='门店数', y='省份', orientation='h',
                    color='门店数', color_continuous_scale='Oranges', text='门店数')
        fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    # ---- 门店列表 ----
    st.subheader("📋 门店列表")
    cols = ['门店名称', '城市', '省份', '渠道', '门店形态', '入驻品牌数']
    if selected_brand != '全部品牌':
        cols.append(selected_brand)
    st.dataframe(df_filtered[cols].sort_values(['省份', '城市']), use_container_width=True, height=400)
    
    # ---- 导出 ----
    csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载 CSV", csv, f"门店_{datetime.now():%Y%m%d}.csv", "text/csv")

else:
    st.info("👆 请上传文件")
