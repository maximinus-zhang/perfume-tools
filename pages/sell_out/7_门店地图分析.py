# pages/7_门店地图分析.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# ============================================================
# 页面配置
# ============================================================
st.title("🗺️ 门店网络与品牌覆盖分析")
st.markdown("---")

# ============================================================
# 1. 硬编码门店数据集（从 TR Store List YTD 2026.xlsx 提取）
# ============================================================

STORES = [
    # === 海南 ===
    {"pos": "Sanya HTB",          "city": "三亚",   "province": "海南", "lat": 18.2528, "lng": 109.5120, "operator": "CDFG HAINAN", "type": "DT", "status": "Existing"},
    {"pos": "Haikou XHG",         "city": "海口",   "province": "海南", "lat": 20.0440, "lng": 110.3540, "operator": "CDFG HAINAN", "type": "DT", "status": "Existing"},
    {"pos": "Haikou Mova",        "city": "海口",   "province": "海南", "lat": 20.0300, "lng": 110.3300, "operator": "CDFG HAINAN", "type": "DT", "status": "Existing"},
    {"pos": "Haikou Meilan AP",   "city": "海口",   "province": "海南", "lat": 19.9349, "lng": 110.4590, "operator": "CDFG HAINAN", "type": "Airport", "status": "Existing"},
    {"pos": "Sanya AP",           "city": "三亚",   "province": "海南", "lat": 18.3029, "lng": 109.4122, "operator": "CDFG HAINAN", "type": "Airport", "status": "Existing"},
    {"pos": "BoAo Store",         "city": "琼海",   "province": "海南", "lat": 19.1500, "lng": 110.4800, "operator": "CDFG HAINAN", "type": "DT", "status": "Existing"},
    {"pos": "Sanya CNSC",         "city": "三亚",   "province": "海南", "lat": 18.2400, "lng": 109.5100, "operator": "CNSC", "type": "DT", "status": "Existing"},
    {"pos": "LAGARDERE Sanya DT", "city": "三亚",   "province": "海南", "lat": 18.2300, "lng": 109.5000, "operator": "LTR", "type": "DT", "status": "Existing"},
    {"pos": "WFJ Wanning DT",     "city": "万宁",   "province": "海南", "lat": 18.7953, "lng": 110.3930, "operator": "WFJ", "type": "DT", "status": "Existing"},
    {"pos": "DUFRY Haikou DT",    "city": "海口",   "province": "海南", "lat": 20.0200, "lng": 110.3400, "operator": "ADJV", "type": "DT", "status": "Existing"},
    {"pos": "Sanya Int'l AP",     "city": "三亚",   "province": "海南", "lat": 18.3030, "lng": 109.4130, "operator": "CDFG", "type": "Airport", "status": "New"},
    
    # === 上海 ===
    {"pos": "Shanghai Pudong AP T1&T2", "city": "上海", "province": "上海", "lat": 31.1443, "lng": 121.8083, "operator": "CDFG/Sunrise", "type": "Airport", "status": "Existing"},
    {"pos": "Shanghai Hongqiao AP",     "city": "上海", "province": "上海", "lat": 31.1979, "lng": 121.3363, "operator": "CDFG/Sunrise", "type": "Airport", "status": "Existing"},
    {"pos": "CDFG Sunrise Shanghai DT","city": "上海", "province": "上海", "lat": 31.2300, "lng": 121.4700, "operator": "CDFG/Sunrise", "type": "DT", "status": "New"},
    {"pos": "CNSC Shanghai DT",         "city": "上海", "province": "上海", "lat": 31.2200, "lng": 121.4600, "operator": "CNSC", "type": "DT", "status": "Existing"},
    {"pos": "CDFG Adora Cruise",        "city": "上海", "province": "上海", "lat": 31.1400, "lng": 121.4900, "operator": "CDFG", "type": "Cruise", "status": "Existing"},
    {"pos": "CDFG Mediterranea Cruise", "city": "上海", "province": "上海", "lat": 31.1450, "lng": 121.4950, "operator": "CDFG", "type": "Cruise", "status": "Existing"},
    {"pos": "CDFG Piano Land Cruise",   "city": "上海", "province": "上海", "lat": 31.1500, "lng": 121.5000, "operator": "CDFG", "type": "Cruise", "status": "Existing"},
    
    # === 北京 ===
    {"pos": "Beijing Capital AP T2&T3", "city": "北京", "province": "北京", "lat": 40.0799, "lng": 116.6031, "operator": "CDFG/Sunrise", "type": "Airport", "status": "Existing"},
    {"pos": "Beijing Daxing AP",        "city": "北京", "province": "北京", "lat": 39.5098, "lng": 116.4105, "operator": "CDFG/Sunrise", "type": "Airport", "status": "New"},
    {"pos": "CNSC Beijing DT",          "city": "北京", "province": "北京", "lat": 39.9200, "lng": 116.4200, "operator": "CNSC", "type": "DT", "status": "Existing"},
    {"pos": "CDF Sunrise Beijing DT",   "city": "北京", "province": "北京", "lat": 39.9400, "lng": 116.4400, "operator": "CDFG/Sunrise", "type": "DT", "status": "New"},
    
    # === 广东 ===
    {"pos": "Guangzhou Baiyun AP",      "city": "广州", "province": "广东", "lat": 23.3925, "lng": 113.3088, "operator": "CDFG", "type": "Airport", "status": "Existing"},
    {"pos": "Shenzhen BaoAn AP",        "city": "深圳", "province": "广东", "lat": 22.6397, "lng": 113.8148, "operator": "SZDF", "type": "Airport", "status": "Existing"},
    {"pos": "Guangzhou DT",             "city": "广州", "province": "广东", "lat": 23.1300, "lng": 113.2600, "operator": "CDFG", "type": "DT", "status": "New"},
    {"pos": "Shenzhen DT",              "city": "深圳", "province": "广东", "lat": 22.5400, "lng": 114.0500, "operator": "CDFG", "type": "DT", "status": "New"},
    {"pos": "SKYCONNECTION LMC",        "city": "深圳", "province": "广东", "lat": 22.5300, "lng": 114.0600, "operator": "SKY", "type": "Border", "status": "Existing"},
    {"pos": "SKYCONNECTION LuWu",       "city": "深圳", "province": "广东", "lat": 22.5350, "lng": 114.0650, "operator": "SKY", "type": "Border", "status": "Existing"},
    {"pos": "ZHDF Zhuhai Gongbei",      "city": "珠海", "province": "广东", "lat": 22.2150, "lng": 113.5434, "operator": "ZHDF", "type": "Border", "status": "Existing"},
    
    # === 江苏 ===
    {"pos": "Nanjing Lukou AP",         "city": "南京", "province": "江苏", "lat": 31.7420, "lng": 118.8620, "operator": "CDFG", "type": "Airport", "status": "Existing"},
    {"pos": "Nanjing Int'l AP Departure","city": "南京", "province": "江苏", "lat": 31.7450, "lng": 118.8650, "operator": "CDFG", "type": "Airport", "status": "New"},
    {"pos": "CNSC Nanjing DT",          "city": "南京", "province": "江苏", "lat": 32.0600, "lng": 118.7800, "operator": "CNSC", "type": "DT", "status": "Existing"},
    {"pos": "Wuxi Int'l AP",            "city": "无锡", "province": "江苏", "lat": 31.4944, "lng": 120.4291, "operator": "SZDF", "type": "Airport", "status": "New"},
    
    # === 浙江 ===
    {"pos": "Wenzhou AP",               "city": "温州", "province": "浙江", "lat": 27.8485, "lng": 120.7026, "operator": "CDFG", "type": "Airport", "status": "Existing"},
    {"pos": "CNSC Hangzhou DT",         "city": "杭州", "province": "浙江", "lat": 30.2700, "lng": 120.1500, "operator": "CNSC", "type": "DT", "status": "Existing"},
    
    # === 四川 ===
    {"pos": "Chengdu Tianfu AP",        "city": "成都", "province": "四川", "lat": 30.3197, "lng": 104.4413, "operator": "CDFG", "type": "Airport", "status": "Existing"},
    
    # === 湖北 ===
    {"pos": "Wuhan Tianhe AP",          "city": "武汉", "province": "湖北", "lat": 30.7838, "lng": 114.2081, "operator": "CDFG", "type": "Airport", "status": "Existing"},
    {"pos": "WFJ Wuhan DT",             "city": "武汉", "province": "湖北", "lat": 30.5800, "lng": 114.2700, "operator": "WFJ", "type": "DT", "status": "New"},
    
    # === 湖南 ===
    {"pos": "CDFG Changsha AP",         "city": "长沙", "province": "湖南", "lat": 28.1898, "lng": 113.2200, "operator": "CDFG", "type": "Airport", "status": "New"},
    {"pos": "WFJ Changsha DT",          "city": "长沙", "province": "湖南", "lat": 28.2000, "lng": 112.9700, "operator": "WFJ", "type": "DT", "status": "New"},
    
    # === 山东 ===
    {"pos": "Qingdao Jiaodong AP",      "city": "青岛", "province": "山东", "lat": 36.2614, "lng": 120.0035, "operator": "CDFG", "type": "Airport", "status": "Existing"},
    {"pos": "CDFG Jinan AP",            "city": "济南", "province": "山东", "lat": 36.6500, "lng": 117.1000, "operator": "CDFG", "type": "Airport", "status": "New"},
    {"pos": "CNSC Qingdao DT",          "city": "青岛", "province": "山东", "lat": 36.0700, "lng": 120.3800, "operator": "CNSC", "type": "DT", "status": "Existing"},
    
    # === 辽宁 ===
    {"pos": "Shenyang AP",              "city": "沈阳", "province": "辽宁", "lat": 41.6398, "lng": 123.4830, "operator": "CDFG", "type": "Airport", "status": "Existing"},
    {"pos": "Dalian ZhouShuiZi AP",     "city": "大连", "province": "辽宁", "lat": 38.9657, "lng": 121.5376, "operator": "CDFG", "type": "Airport", "status": "Existing"},
    {"pos": "CDFG Dalian DT",           "city": "大连", "province": "辽宁", "lat": 38.9100, "lng": 121.6100, "operator": "CDFG", "type": "DT", "status": "Existing"},
    
    # === 黑龙江 ===
    {"pos": "Haerbin AP",               "city": "哈尔滨", "province": "黑龙江", "lat": 45.6234, "lng": 126.2504, "operator": "WFJ", "type": "Airport", "status": "New"},
    {"pos": "CNSC Harbin DT",           "city": "哈尔滨", "province": "黑龙江", "lat": 45.7500, "lng": 126.6300, "operator": "CNSC", "type": "DT", "status": "Existing"},
    
    # === 福建 ===
    {"pos": "CDFG Xiamen AP",           "city": "厦门", "province": "福建", "lat": 24.5440, "lng": 118.1277, "operator": "CDFG", "type": "Airport", "status": "New"},
    {"pos": "CDFG Fuzhou AP",           "city": "福州", "province": "福建", "lat": 25.9350, "lng": 119.4600, "operator": "CDFG", "type": "Airport", "status": "New"},
    {"pos": "Xiamen DT",                "city": "厦门", "province": "福建", "lat": 24.4800, "lng": 118.0900, "operator": "CDFG", "type": "DT", "status": "New"},
    {"pos": "Fuzhou DT",                "city": "福州", "province": "福建", "lat": 26.0700, "lng": 119.3000, "operator": "CDFG", "type": "DT", "status": "New"},
    
    # === 重庆 ===
    {"pos": "Chongqing AP DF",          "city": "重庆", "province": "重庆", "lat": 29.7192, "lng": 106.6417, "operator": "CNSC", "type": "Airport", "status": "Existing"},
    {"pos": "CNSC Chongqing DT",        "city": "重庆", "province": "重庆", "lat": 29.5600, "lng": 106.5700, "operator": "CNSC", "type": "DT", "status": "Existing"},
    
    # === 天津 ===
    {"pos": "Tianjin AP",               "city": "天津", "province": "天津", "lat": 39.1242, "lng": 117.3462, "operator": "CDFG", "type": "Airport", "status": "Existing"},
    {"pos": "CDFG Tianjin DT",          "city": "天津", "province": "天津", "lat": 39.1300, "lng": 117.2000, "operator": "CDFG", "type": "DT", "status": "New"},
    
    # === 云南 ===
    {"pos": "Kunming Int'l AP",         "city": "昆明", "province": "云南", "lat": 25.1019, "lng": 102.9291, "operator": "CDFG", "type": "Airport", "status": "Existing"},
    {"pos": "CNSC Kunming DT",          "city": "昆明", "province": "云南", "lat": 25.0400, "lng": 102.7100, "operator": "CNSC", "type": "DT", "status": "Existing"},
    
    # === 陕西 ===
    {"pos": "CDFG Xi'an AP",            "city": "西安", "province": "陕西", "lat": 34.4471, "lng": 108.7516, "operator": "CDFG", "type": "Airport", "status": "New"},
    
    # === 河南 ===
    {"pos": "Zhengzhou Int'l AP",       "city": "郑州", "province": "河南", "lat": 34.5197, "lng": 113.8408, "operator": "CNSC", "type": "Airport", "status": "New"},
    {"pos": "CNSC Zhengzhou DT",        "city": "郑州", "province": "河南", "lat": 34.7500, "lng": 113.6500, "operator": "CNSC", "type": "DT", "status": "Existing"},
    
    # === 新疆 ===
    {"pos": "Urumqi AP",                "city": "乌鲁木齐", "province": "新疆", "lat": 43.9072, "lng": 87.4742, "operator": "CDFG", "type": "Airport", "status": "Existing"},
    
    # === 内蒙古 ===
    {"pos": "CDFG Erlianhaote Border",  "city": "二连浩特", "province": "内蒙古", "lat": 43.6475, "lng": 111.9794, "operator": "CDFG", "type": "Border", "status": "Existing"},
    {"pos": "CDFG Manzhouli Border",    "city": "满洲里",   "province": "内蒙古", "lat": 49.5967, "lng": 117.4353, "operator": "CDFG", "type": "Border", "status": "Existing"},
    
    # === 黑龙江(边境) ===
    {"pos": "CDFG Heihe Border",        "city": "黑河", "province": "黑龙江", "lat": 50.2453, "lng": 127.4878, "operator": "CDFG", "type": "Border", "status": "Existing"},
    
    # === 吉林 ===
    {"pos": "CDFG Hunchun Border",      "city": "珲春", "province": "吉林", "lat": 42.8675, "lng": 130.3613, "operator": "CDFG", "type": "Border", "status": "Existing"},
    
    # === 🌏 境外 ===
    {"pos": "CDFG Macau DT",            "city": "澳门", "province": "澳门", "lat": 22.1987, "lng": 113.5439, "operator": "CDFG", "type": "DT", "status": "Existing"},
    {"pos": "City Gates Hong Kong",     "city": "香港", "province": "香港", "lat": 22.3000, "lng": 114.1700, "operator": "CDFG", "type": "DT", "status": "Existing"},
]

# ============================================================
# 2. 品牌覆盖数据
# ============================================================
BRAND_COVERAGE = {
    "VERSACE":      {"provinces": ["海南", "上海", "北京", "广东", "江苏", "浙江", "四川", "湖北", "湖南", "山东", "辽宁", "福建", "重庆", "天津", "云南", "陕西", "河南", "新疆", "内蒙古", "黑龙江", "吉林", "澳门"], "store_count": 65},
    "ANNA SUI":     {"provinces": ["海南", "上海", "北京", "广东", "江苏", "浙江", "四川", "湖北", "山东", "辽宁", "福建", "重庆", "天津", "云南", "陕西", "河南", "新疆"], "store_count": 48},
    "4711":         {"provinces": ["海南", "上海", "北京", "广东", "江苏", "湖北", "山东", "辽宁", "福建", "重庆", "天津", "云南"], "store_count": 35},
    "ATKINSONS":    {"provinces": ["海南", "上海", "北京", "广东", "江苏", "浙江", "四川", "湖北", "山东", "辽宁", "福建", "重庆", "天津", "云南", "陕西", "河南"], "store_count": 40},
    "CHOPARD":      {"provinces": ["海南", "上海", "北京", "广东", "江苏", "浙江", "四川", "湖北", "湖南", "山东", "辽宁", "福建", "重庆", "天津", "云南", "陕西", "河南", "新疆"], "store_count": 42},
    "FERRAGAMO":    {"provinces": ["海南", "上海", "北京", "广东", "江苏", "浙江", "四川", "湖北", "湖南", "山东", "辽宁", "福建", "重庆", "天津", "云南", "陕西", "河南", "新疆", "澳门"], "store_count": 50},
    "GRAFF":        {"provinces": ["海南", "上海", "北京", "广东", "江苏", "浙江", "四川", "湖北", "山东", "重庆", "天津", "云南"], "store_count": 25},
    "MAISON 21G":   {"provinces": ["海南", "上海", "北京", "广东", "江苏", "湖北", "山东", "辽宁", "重庆"], "store_count": 18},
    "MCM":          {"provinces": ["海南", "上海", "北京", "广东", "江苏", "浙江", "四川", "湖北", "湖南", "山东", "辽宁", "福建", "重庆", "天津", "云南", "陕西", "河南", "新疆", "澳门"], "store_count": 45},
    "MEMO":         {"provinces": ["海南", "上海", "北京", "广东", "江苏", "浙江", "四川", "湖北", "山东", "辽宁", "福建", "重庆", "天津", "云南", "陕西", "河南"], "store_count": 38},
    "MOSCHINO":     {"provinces": ["海南", "上海", "北京", "广东", "江苏", "浙江", "四川", "湖北", "湖南", "山东", "辽宁", "福建", "重庆", "天津", "云南", "陕西", "河南", "新疆", "内蒙古", "黑龙江", "吉林", "澳门"], "store_count": 55},
    "Clean":        {"provinces": ["海南", "上海", "北京", "广东", "江苏", "浙江", "四川", "湖北", "山东", "辽宁", "福建", "重庆", "天津", "云南"], "store_count": 30},
    "Lalique":      {"provinces": ["海南", "上海", "北京", "广东", "江苏", "浙江", "湖北", "山东", "辽宁", "福建", "重庆", "天津", "云南"], "store_count": 28},
    "CREED":        {"provinces": ["海南", "上海", "北京", "广东", "江苏", "浙江", "四川", "湖北", "湖南", "山东", "辽宁", "福建", "重庆", "天津", "云南", "陕西", "河南", "新疆", "澳门"], "store_count": 42},
    "Furla":        {"provinces": ["海南", "上海", "北京", "广东", "江苏", "湖北", "山东", "辽宁", "福建", "重庆", "天津", "云南"], "store_count": 22},
    "MK (Michael Kors)": {"provinces": ["海南", "上海", "北京", "广东", "江苏", "浙江", "四川", "湖北", "湖南", "山东", "辽宁", "福建", "重庆", "天津", "云南", "陕西", "河南"], "store_count": 35},
}

# ============================================================
# 3. 数据预处理
# ============================================================
df_stores = pd.DataFrame(STORES)

# 省份中心坐标
PROVINCE_CENTERS = {
    "海南": {"lat": 19.5, "lng": 110.0}, "上海": {"lat": 31.2, "lng": 121.5},
    "北京": {"lat": 39.9, "lng": 116.4}, "广东": {"lat": 23.1, "lng": 113.3},
    "江苏": {"lat": 32.1, "lng": 118.8}, "浙江": {"lat": 30.3, "lng": 120.2},
    "四川": {"lat": 30.6, "lng": 104.1}, "湖北": {"lat": 30.6, "lng": 114.3},
    "湖南": {"lat": 28.2, "lng": 112.9}, "山东": {"lat": 36.7, "lng": 117.0},
    "辽宁": {"lat": 41.8, "lng": 123.4}, "福建": {"lat": 26.1, "lng": 119.3},
    "重庆": {"lat": 29.6, "lng": 106.6}, "天津": {"lat": 39.1, "lng": 117.2},
    "云南": {"lat": 25.0, "lng": 102.7}, "陕西": {"lat": 34.3, "lng": 108.9},
    "河南": {"lat": 34.8, "lng": 113.7}, "新疆": {"lat": 43.8, "lng": 87.6},
    "内蒙古": {"lat": 43.6, "lng": 112.0}, "黑龙江": {"lat": 45.8, "lng": 126.5},
    "吉林": {"lat": 43.9, "lng": 129.5}, "澳门": {"lat": 22.2, "lng": 113.55},
    "香港": {"lat": 22.32, "lng": 114.18},
}

# 省份英文名（Plotly 用）
PROVINCE_EN = {
    "海南": "Hainan", "上海": "Shanghai", "北京": "Beijing", "广东": "Guangdong",
    "江苏": "Jiangsu", "浙江": "Zhejiang", "四川": "Sichuan", "湖北": "Hubei",
    "湖南": "Hunan", "山东": "Shandong", "辽宁": "Liaoning", "福建": "Fujian",
    "重庆": "Chongqing", "天津": "Tianjin", "云南": "Yunnan", "陕西": "Shaanxi",
    "河南": "Henan", "新疆": "Xinjiang", "内蒙古": "Inner Mongolia",
    "黑龙江": "Heilongjiang", "吉林": "Jilin",
    "澳门": "Macao",       # Plotly 用 Macao 而非 Macau
    "香港": "Hong Kong",
}

# ============================================================
# 4. 侧边栏筛选
# ============================================================
st.sidebar.header("🔍 筛选条件")

all_brands = sorted(list(BRAND_COVERAGE.keys()))
selected_brands = st.sidebar.multiselect(
    "选择品牌（可多选）",
    options=all_brands,
    default=["VERSACE"]
)

store_type_filter = st.sidebar.multiselect(
    "门店类型",
    options=["All"] + sorted(df_stores["type"].unique()),
    default=["All"]
)

operator_filter = st.sidebar.multiselect(
    "运营商",
    options=["All"] + sorted(df_stores["operator"].unique()),
    default=["All"]
)

df_filtered = df_stores.copy()
if "All" not in store_type_filter:
    df_filtered = df_filtered[df_filtered["type"].isin(store_type_filter)]
if "All" not in operator_filter:
    df_filtered = df_filtered[df_filtered["operator"].isin(operator_filter)]

# ============================================================
# 5. 顶部 KPI 指标卡
# ============================================================
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("🏪 总门店数", len(df_stores))
with col2:
    st.metric("📍 覆盖城市", df_stores["city"].nunique())
with col3:
    st.metric("🗺️ 覆盖省级区域", df_stores["province"].nunique())
with col4:
    st.metric("🏷️ 品牌总数", len(all_brands))

st.markdown("---")

# ============================================================
# 6. 品牌筛选后的省份覆盖分析
# ============================================================
if selected_brands:
    covered_provinces = set()
    for brand in selected_brands:
        if brand in BRAND_COVERAGE:
            if not covered_provinces:
                covered_provinces = set(BRAND_COVERAGE[brand]["provinces"])
            else:
                covered_provinces = covered_provinces & set(BRAND_COVERAGE[brand]["provinces"])
    
    union_provinces = set()
    for brand in selected_brands:
        if brand in BRAND_COVERAGE:
            union_provinces |= set(BRAND_COVERAGE[brand]["provinces"])
    
    all_regions = set(PROVINCE_EN.keys())
    covered_all = covered_provinces & all_regions
    union_all = union_provinces & all_regions
    
    st.subheader(f"📊 品牌覆盖分析: {' + '.join(selected_brands)}")
    
    brand_cols = st.columns(len(selected_brands))
    for i, brand in enumerate(selected_brands):
        with brand_cols[i]:
            info = BRAND_COVERAGE.get(brand, {"provinces": [], "store_count": 0})
            st.info(f"**{brand}**\n\n门店: {info['store_count']} 家\n省份/区域: {len(info['provinces'])} 个")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("共同覆盖区域（交集）", len(covered_all))
    with c2:
        st.metric("任一品牌覆盖区域（并集）", len(union_all))
    with c3:
        coverage_pct = round(len(covered_all) / len(all_regions) * 100, 1)
        st.metric("全域覆盖率", f"{coverage_pct}%")

st.markdown("---")

# # ============================================================
# 7. 中国地图（核心可视化）- ✨ 单Choropleth修复版
# ============================================================
st.subheader("📍 中国门店分布与品牌覆盖地图")

fig_map = go.Figure()

# ---- 7a. 构建单层 Choropleth（z值区分颜色）----
all_province_names = list(PROVINCE_EN.values())
all_province_cn = list(PROVINCE_EN.keys())

# 构建 z 值数组和 hover 文本
z_values = []
hover_texts = []

for prov_cn in all_province_cn:
    if selected_brands:
        if prov_cn in covered_all:
            z_values.append(1.0)  # 深橙 — 全部覆盖
            hover_texts.append(f"🟠 {prov_cn} — 全部选中品牌均已覆盖")
        elif prov_cn in union_all:
            # 部分覆盖
            brand_list = [b for b in selected_brands 
                          if prov_cn in BRAND_COVERAGE.get(b, {}).get("provinces", [])]
            z_values.append(0.5)  # 浅橙 — 部分覆盖
            hover_texts.append(f"🟡 {prov_cn} — 部分覆盖 ({', '.join(brand_list)})")
        else:
            z_values.append(0.0)  # 灰色 — 无覆盖
            hover_texts.append(f"⬜ {prov_cn} — 无品牌覆盖")
    else:
        z_values.append(0.0)
        hover_texts.append(f"{prov_cn}")

fig_map.add_trace(go.Choropleth(
    locations=all_province_names,
    locationmode="country names",
    z=z_values,
    text=hover_texts,
    hoverinfo="text",
    marker_line_color="#aaaaaa",
    marker_line_width=0.8,
    showscale=False,
    colorscale=[
        [0.0, "#f0f0f0"],        # 灰色：无覆盖
        [0.4, "#FFE0B2"],        # 过渡
        [0.5, "#FFE0B2"],        # 浅橙：部分覆盖
        [0.9, "#FFB300"],        # 过渡
        [1.0, "#FFB300"],        # 深橙：全部覆盖
    ],
    geo="geo"
))

# ---- 7b. 门店标记（始终显示所有门店，按类型分色）----
TYPE_STYLE = {
    "Airport": {"color": "#1E88E5", "symbol": "diamond", "label": "机场店"},
    "DT":      {"color": "#E53935", "symbol": "circle",  "label": "市区店"},
    "Border":  {"color": "#43A047", "symbol": "square",  "label": "边境店"},
    "Cruise":  {"color": "#8E24AA", "symbol": "triangle-up", "label": "游轮店"},
}

df_map_stores = df_filtered.copy()

hover_texts = []
marker_colors = []
marker_symbols = []
marker_sizes = []

for _, store in df_map_stores.iterrows():
    if selected_brands:
        covered_brands = [b for b in selected_brands 
                          if store["province"] in BRAND_COVERAGE.get(b, {}).get("provinces", [])]
        brand_info = f"覆盖品牌: {', '.join(covered_brands) if covered_brands else '无'}"
    else:
        brand_info = ""
    hover_texts.append(
        f"<b>{store['pos']}</b><br>"
        f"📍 {store['city']}, {store['province']}<br>"
        f"🏢 {store['operator']}<br>"
        f"🏷️ {store['type']} | {'✅' if store['status']=='Existing' else '🆕'}<br>{brand_info}"
    )
    marker_colors.append(TYPE_STYLE.get(store["type"], {}).get("color", "#999"))
    marker_symbols.append(TYPE_STYLE.get(store["type"], {}).get("symbol", "circle"))
    marker_sizes.append(11)

fig_map.add_trace(go.Scattergeo(
    lon=df_map_stores["lng"],
    lat=df_map_stores["lat"],
    text=hover_texts,
    hoverinfo="text",
    mode="markers",
    marker=dict(
        symbol=marker_symbols,
        size=marker_sizes,
        color=marker_colors,
        line=dict(color="white", width=1.5),
        opacity=0.9
    ),
    showlegend=False,
))

# ---- 7c. 省份名称标注 ---- 
prov_labels, prov_lats, prov_lngs = [], [], []
for prov_cn, center in PROVINCE_CENTERS.items():
    prov_labels.append(prov_cn)
    prov_lats.append(center["lat"])
    prov_lngs.append(center["lng"])

fig_map.add_trace(go.Scattergeo(
    lon=prov_lngs, lat=prov_lats,
    text=prov_labels,
    mode="markers+text",
    marker=dict(size=0.01, color="rgba(0,0,0,0)", opacity=0),
    textfont=dict(size=14, color="#444444", family="Arial, sans-serif"),
    textposition="middle center",
    hoverinfo="skip", showlegend=False,
))

# ---- 7d. 城市名称标注（去重）----
city_agg = df_map_stores.groupby(["city", "province"]).agg(
    lat=("lat", "mean"), lng=("lng", "mean"), store_count=("pos", "count")
).reset_index()

fig_map.add_trace(go.Scattergeo(
    lon=city_agg["lng"], lat=city_agg["lat"],
    text=city_agg.apply(lambda r: f"{r['city']} ({r['store_count']}家)", axis=1),
    mode="markers+text",
    marker=dict(size=0.01, color="rgba(0,0,0,0)", opacity=0),
    textfont=dict(
        size=city_agg["store_count"].apply(lambda x: min(9 + x * 1.5, 14)).tolist(),
        color="#333333", family="Arial",
    ),
    textposition="top center",
    hoverinfo="skip", showlegend=False,
))

# ---- 7e. 地图布局 ----
fig_map.update_layout(
    title=dict(
        text=f"TR 品牌门店中国分布图{' | 品牌: ' + ' + '.join(selected_brands) if selected_brands else ' | 全部门店'}",
        font=dict(size=18, color="#333"), x=0.5, xanchor="center"
    ),
    geo=dict(
        scope="asia",
        projection=dict(type="natural earth"),
        showland=True, landcolor="#f9f9f9",
        countrycolor="rgba(180,180,180,0.5)", countrywidth=0.8,
        coastlinecolor="rgba(150,150,150,0.3)", coastlinewidth=0.5,
        showocean=True, oceancolor="#e8f4f8",
        showlakes=True, lakecolor="#e8f4f8",
        showsubunits=True, subunitcolor="rgba(180,180,180,0.3)", subunitwidth=0.5,
        center=dict(lat=33, lon=106),
        projection_scale=4.2,
        lonaxis=dict(range=[73, 136]),
        lataxis=dict(range=[4, 56]),
    ),
    height=750,
    margin=dict(l=10, r=10, t=60, b=20),
    showlegend=False,
)

st.plotly_chart(fig_map, use_container_width=True)

# ---- 7f. 图例说明 ----
lc1, lc2, lc3, lc4 = st.columns(4)
lc1.markdown("🔵 **<span style='color:#1E88E5'>◆ 机场店</span>**", unsafe_allow_html=True)
lc2.markdown("🔴 **<span style='color:#E53935'>● 市区店</span>**", unsafe_allow_html=True)
lc3.markdown("🟢 **<span style='color:#43A047'>■ 边境店</span>**", unsafe_allow_html=True)
lc4.markdown("🟣 **<span style='color:#8E24AA'>▲ 游轮店</span>**", unsafe_allow_html=True)
if selected_brands:
    st.caption("🟠 深橙 = 全部覆盖 | 🟡 浅橙 = 部分覆盖 | ⬜ 灰色 = 无覆盖")
# 
============================================================
# 8. 品牌覆盖区域详情表格
# ============================================================
if selected_brands:
    st.markdown("---")
    st.subheader("📋 品牌覆盖区域明细")
    detail_rows = []
    for prov_cn in sorted(PROVINCE_EN.keys()):
        brand_status = {}
        for brand in selected_brands:
            info = BRAND_COVERAGE.get(brand, {"provinces": []})
            brand_status[brand] = "✅" if prov_cn in info["provinces"] else "❌"
        store_in_prov = df_filtered[df_filtered["province"] == prov_cn]
        is_overseas = "🌏" if prov_cn in ["澳门", "香港"] else ""
        detail_rows.append({
            "区域": f"{is_overseas} {prov_cn}",
            "门店数": len(store_in_prov),
            "覆盖城市": ", ".join(store_in_prov["city"].unique()) if len(store_in_prov) > 0 else "—",
            **brand_status
        })
    df_detail = pd.DataFrame(detail_rows)
    st.dataframe(df_detail, use_container_width=True, hide_index=True)

st.markdown("---")

# ============================================================
# 9. 图表分析
# ============================================================
st.subheader("📈 门店网络分析图表")
tab1, tab2, tab3, tab4 = st.tabs(["门店类型分布", "运营商分布", "省份门店排行", "品牌覆盖排行"])

with tab1:
    type_counts = df_stores["type"].value_counts().reset_index()
    type_counts.columns = ["门店类型", "数量"]
    fig1 = px.pie(type_counts, values="数量", names="门店类型", title="门店类型分布",
                  color_discrete_sequence=px.colors.qualitative.Set2, hole=0.4)
    fig1.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig1, use_container_width=True)

with tab2:
    op_counts = df_stores["operator"].value_counts().reset_index()
    op_counts.columns = ["运营商", "数量"]
    fig2 = px.bar(op_counts, x="运营商", y="数量", title="运营商门店数量排行",
                  color="数量", color_continuous_scale="Viridis", text_auto=True)
    fig2.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    prov_counts = df_stores["province"].value_counts().reset_index()
    prov_counts.columns = ["省份", "门店数"]
    fig3 = px.bar(prov_counts.sort_values("门店数", ascending=True),
                  x="门店数", y="省份", title="各省份门店数量排行（含港澳）",
                  color="门店数", color_continuous_scale="Oranges", text_auto=True, orientation="h")
    fig3.update_layout(height=550)
    st.plotly_chart(fig3, use_container_width=True)

with tab4:
    brand_pc = []
    for brand, info in BRAND_COVERAGE.items():
        brand_pc.append({"品牌": brand, "覆盖区域数": len(info["provinces"]), "门店数": info["store_count"]})
    df_brand = pd.DataFrame(brand_pc).sort_values("覆盖区域数", ascending=True)
    fig4 = px.bar(df_brand, x="覆盖区域数", y="品牌", title="品牌覆盖区域数量排行",
                  color="门店数", color_continuous_scale="Blues", text_auto=True, orientation="h")
    fig4.update_layout(height=500)
    st.plotly_chart(fig4, use_container_width=True)

# ============================================================
# 10. 雷达图
# ============================================================
st.markdown("---")
st.subheader("🛡️ 品牌覆盖能力对比")

if len(selected_brands) >= 2:
    dimensions = ["覆盖区域", "门店规模", "机场渠道", "市区渠道", "海南布局"]
    radar_data = []
    for brand in selected_brands:
        info = BRAND_COVERAGE.get(brand, {"provinces": [], "store_count": 0})
        provinces = info["provinces"]
        prov_score = len(provinces) / 23 * 100
        store_score = min(info["store_count"] / 65 * 100, 100)
        airport_provs = {"上海", "北京", "广东", "江苏", "浙江", "四川", "湖北", "湖南",
                         "山东", "辽宁", "福建", "重庆", "天津", "云南", "陕西", "河南", "新疆", "海南"}
        airport_score = len(set(provinces) & airport_provs) / len(airport_provs) * 100
        dt_provs = {"海南", "上海", "北京", "广东", "江苏", "浙江", "湖北", "山东",
                    "辽宁", "福建", "重庆", "天津", "云南", "澳门"}
        dt_score = len(set(provinces) & dt_provs) / len(dt_provs) * 100
        hainan_score = 100 if "海南" in provinces else 0
        radar_data.append(go.Scatterpolar(
            r=[prov_score, store_score, airport_score, dt_score, hainan_score],
            theta=dimensions, fill="toself", name=brand
        ))
    fig_radar = go.Figure(data=radar_data)
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                            title="品牌覆盖能力雷达图对比", height=500)
    st.plotly_chart(fig_radar, use_container_width=True)
else:
    st.info("请选择至少 2 个品牌进行对比分析")

# ============================================================
# 11. 原始数据
# ============================================================
st.markdown("---")
with st.expander("📄 查看门店原始数据"):
    st.dataframe(df_stores, use_container_width=True, hide_index=True)
    csv = df_stores.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 下载门店数据 CSV",
        data=csv,
        file_name=f"TR_Stores_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

st.markdown("---")
st.caption("数据来源: TR Store List YTD 2026 | 更新日期: 2026年6月")
