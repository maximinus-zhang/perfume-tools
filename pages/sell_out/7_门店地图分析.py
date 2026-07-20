# pages/sell_out/7_门店地图分析.py
# ============================================================
# TR 门店网络与品牌覆盖分析 —— 完全重写版
#
# 核心改动：
#   · 地图引擎从 Plotly Choropleth 换成 Folium (Leaflet)
#     原因：Plotly 的 go.Choropleth 在 Streamlit 内嵌渲染中，
#           省块填充色反复无法显示（visible=False 会吃掉所有 geo layer）
#     Folium + 中国省份 GeoJSON 是最可靠的开源方案，省块 100% 渲染
#   · 非地图图表（饼图/柱状图/雷达）仍使用 Plotly（这些本来就没问题）
#   · 整体视觉重新设计：干净、信息清晰、适合给同事汇报
# ============================================================

import streamlit as st
import pandas as pd
import folium
from folium.plugins import GroupedLayerControl, MarkerCluster
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import json

# ============================================================
# 0. 数据定义
# ============================================================

# --- 门店数据 ---
STORES = [
    {"pos": "Sanya HTB",          "city": "三亚",   "province": "海南", "lat": 18.2528, "lng": 109.5120, "operator": "CDFG HAINAN", "type": "DT",      "status": "Existing"},
    {"pos": "Haikou XHG",         "city": "海口",   "province": "海南", "lat": 20.0440, "lng": 110.3540, "operator": "CDFG HAINAN", "type": "DT",      "status": "Existing"},
    {"pos": "Haikou Mova",        "city": "海口",   "province": "海南", "lat": 20.0300, "lng": 110.3300, "operator": "CDFG HAINAN", "type": "DT",      "status": "Existing"},
    {"pos": "Haikou Meilan AP",   "city": "海口",   "province": "海南", "lat": 19.9349, "lng": 110.4590, "operator": "CDFG HAINAN", "type": "Airport", "status": "Existing"},
    {"pos": "Sanya AP",           "city": "三亚",   "province": "海南", "lat": 18.3029, "lng": 109.4122, "operator": "CDFG HAINAN", "type": "Airport", "status": "Existing"},
    {"pos": "BoAo Store",         "city": "琼海",   "province": "海南", "lat": 19.1500, "lng": 110.4800, "operator": "CDFG HAINAN", "type": "DT",      "status": "Existing"},
    {"pos": "Sanya CNSC",         "city": "三亚",   "province": "海南", "lat": 18.2400, "lng": 109.5100, "operator": "CNSC",         "type": "DT",      "status": "Existing"},
    {"pos": "LAGARDERE Sanya DT","city": "三亚",   "province": "海南", "lat": 18.2300, "lng": 109.5000, "operator": "LTR",          "type": "DT",      "status": "Existing"},
    {"pos": "WFJ Wanning DT",     "city": "万宁",   "province": "海南", "lat": 18.7953, "lng": 110.3930, "operator": "WFJ",          "type": "DT",      "status": "Existing"},
    {"pos": "DUFRY Haikou DT",   "city": "海口",   "province": "海南", "lat": 20.0200, "lng": 110.3400, "operator": "ADJV",         "type": "DT",      "status": "Existing"},
    {"pos": "Sanya Int'l AP",     "city": "三亚",   "province": "海南", "lat": 18.3030, "lng": 109.4130, "operator": "CDFG",         "type": "Airport", "status": "New"},
    {"pos": "Shanghai Pudong AP T1&T2","city":"上海","province":"上海","lat":31.1443,"lng":121.8083,"operator":"CDFG/Sunrise","type":"Airport","status":"Existing"},
    {"pos": "Shanghai Hongqiao AP","city":"上海","province":"上海","lat":31.1979,"lng":121.3363,"operator":"CDFG/Sunrise","type":"Airport","status":"Existing"},
    {"pos": "CDFG Sunrise Shanghai DT","city":"上海","province":"上海","lat":31.2300,"lng":121.4700,"operator":"CDFG/Sunrise","type":"DT","status":"New"},
    {"pos": "CNSC Shanghai DT","city":"上海","province":"上海","lat":31.2200,"lng":121.4600,"operator":"CNSC","type":"DT","status":"Existing"},
    {"pos": "CDFG Adora Cruise","city":"上海","province":"上海","lat":31.1400,"lng":121.4900,"operator":"CDFG","type":"Cruise","status":"Existing"},
    {"pos": "CDFG Mediterranea Cruise","city":"上海","province":"上海","lat":31.1450,"lng":121.4950,"operator":"CDFG","type":"Cruise","status":"Existing"},
    {"pos": "CDFG Piano Land Cruise","city":"上海","province":"上海","lat":31.1500,"lng":121.5000,"operator":"CDFG","type":"Cruise","status":"Existing"},
    {"pos": "Beijing Capital AP T2&T3","city":"北京","province":"北京","lat":40.0799,"lng":116.6031,"operator":"CDFG/Sunrise","type":"Airport","status":"Existing"},
    {"pos": "Beijing Daxing AP","city":"北京","province":"北京","lat":39.5098,"lng":116.4105,"operator":"CDFG/Sunrise","type":"Airport","status":"New"},
    {"pos": "CNSC Beijing DT","city":"北京","province":"北京","lat":39.9200,"lng":116.4200,"operator":"CNSC","type":"DT","status":"Existing"},
    {"pos": "CDF Sunrise Beijing DT","city":"北京","province":"北京","lat":39.9400,"lng":116.4400,"operator":"CDFG/Sunrise","type":"DT","status":"New"},
    {"pos": "Guangzhou Baiyun AP","city":"广州","province":"广东","lat":23.3925,"lng":113.3088,"operator":"CDFG","type":"Airport","status":"Existing"},
    {"pos": "Shenzhen BaoAn AP","city":"深圳","province":"广东","lat":22.6397,"lng":113.8148,"operator":"SZDF","type":"Airport","status":"Existing"},
    {"pos": "Guangzhou DT","city":"广州","province":"广东","lat":23.1300,"lng":113.2600,"operator":"CDFG","type":"DT","status":"New"},
    {"pos": "Shenzhen DT","city":"深圳","province":"广东","lat":22.5400,"lng":114.0500,"operator":"CDFG","type":"DT","status":"New"},
    {"pos": "SKYCONNECTION LMC","city":"深圳","province":"广东","lat":22.5300,"lng":114.0600,"operator":"SKY","type":"Border","status":"Existing"},
    {"pos": "SKYCONNECTION LuWu","city":"深圳","province":"广东","lat":22.5350,"lng":114.0650,"operator":"SKY","type":"Border","status":"Existing"},
    {"pos": "ZHDF Zhuhai Gongbei","city":"珠海","province":"广东","lat":22.2150,"lng":113.5434,"operator":"ZHDF","type":"Border","status":"Existing"},
    {"pos": "Nanjing Lukou AP","city":"南京","province":"江苏","lat":31.7420,"lng":118.8620,"operator":"CDFG","type":"Airport","status":"Existing"},
    {"pos": "Nanjing Int'l AP Departure","city":"南京","province":"江苏","lat":31.7450,"lng":118.8650,"operator":"CDFG","type":"Airport","status":"New"},
    {"pos": "CNSC Nanjing DT","city":"南京","province":"江苏","lat":32.0600,"lng":118.7800,"operator":"CNSC","type":"DT","status":"Existing"},
    {"pos": "Wuxi Int'l AP","city":"无锡","province":"江苏","lat":31.4944,"lng":120.4291,"operator":"SZDF","type":"Airport","status":"New"},
    {"pos": "Wenzhou AP","city":"温州","province":"浙江","lat":27.8485,"lng":120.7026,"operator":"CDFG","type":"Airport","status":"Existing"},
    {"pos": "CNSC Hangzhou DT","city":"杭州","province":"浙江","lat":30.2700,"lng":120.1500,"operator":"CNSC","type":"DT","status":"Existing"},
    {"pos": "Chengdu Tianfu AP","city":"成都","province":"四川","lat":30.3197,"lng":104.4413,"operator":"CDFG","type":"Airport","status":"Existing"},
    {"pos": "Wuhan Tianhe AP","city":"武汉","province":"湖北","lat":30.7838,"lng":114.2081,"operator":"CDFG","type":"Airport","status":"Existing"},
    {"pos": "WFJ Wuhan DT","city":"武汉","province":"湖北","lat":30.5800,"lng":114.2700,"operator":"WFJ","type":"DT","status":"New"},
    {"pos": "CDFG Changsha AP","city":"长沙","province":"湖南","lat":28.1898,"lng":113.2200,"operator":"CDFG","type":"Airport","status":"New"},
    {"pos": "WFJ Changsha DT","city":"长沙","province":"湖南","lat":28.2000,"lng":112.9700,"operator":"WFJ","type":"DT","status":"New"},
    {"pos": "Qingdao Jiaodong AP","city":"青岛","province":"山东","lat":36.2614,"lng":120.0035,"operator":"CDFG","type":"Airport","status":"Existing"},
    {"pos": "CDFG Jinan AP","city":"济南","province":"山东","lat":36.6500,"lng":117.1000,"operator":"CDFG","type":"Airport","status":"New"},
    {"pos": "CNSC Qingdao DT","city":"青岛","province":"山东","lat":36.0700,"lng":120.3800,"operator":"CNSC","type":"DT","status":"Existing"},
    {"pos": "Shenyang AP","city":"沈阳","province":"辽宁","lat":41.6398,"lng":123.4830,"operator":"CDFG","type":"Airport","status":"Existing"},
    {"pos": "Dalian ZhouShuiZi AP","city":"大连","province":"辽宁","lat":38.9657,"lng":121.5376,"operator":"CDFG","type":"Airport","status":"Existing"},
    {"pos": "CDFG Dalian DT","city":"大连","province":"辽宁","lat":38.9100,"lng":121.6100,"operator":"CDFG","type":"DT","status":"Existing"},
    {"pos": "Haerbin AP","city":"哈尔滨","province":"黑龙江","lat":45.6234,"lng":126.2504,"operator":"WFJ","type":"Airport","status":"New"},
    {"pos": "CNSC Harbin DT","city":"哈尔滨","province":"黑龙江","lat":45.7500,"lng":126.6300,"operator":"CNSC","type":"DT","status":"Existing"},
    {"pos": "CDFG Xiamen AP","city":"厦门","province":"福建","lat":24.5440,"lng":118.1277,"operator":"CDFG","type":"Airport","status":"New"},
    {"pos": "CDFG Fuzhou AP","city":"福州","province":"福建","lat":25.9350,"lng":119.4600,"operator":"CDFG","type":"Airport","status":"New"},
    {"pos": "Xiamen DT","city":"厦门","province":"福建","lat":24.4800,"lng":118.0900,"operator":"CDFG","type":"DT","status":"New"},
    {"pos": "Fuzhou DT","city":"福州","province":"福建","lat":26.0700,"lng":119.3000,"operator":"CDFG","type":"DT","status":"New"},
    {"pos": "Chongqing AP DF","city":"重庆","province":"重庆","lat":29.7192,"lng":106.6417,"operator":"CNSC","type":"Airport","status":"Existing"},
    {"pos": "CNSC Chongqing DT","city":"重庆","province":"重庆","lat":29.5600,"lng":106.5700,"operator":"CNSC","type":"DT","status":"Existing"},
    {"pos": "Tianjin AP","city":"天津","province":"天津","lat":39.1242,"lng":117.3462,"operator":"CDFG","type":"Airport","status":"Existing"},
    {"pos": "CDFG Tianjin DT","city":"天津","province":"天津","lat":39.1300,"lng":117.2000,"operator":"CDFG","type":"DT","status":"New"},
    {"pos": "Kunming Int'l AP","city":"昆明","province":"云南","lat":25.1019,"lng":102.9291,"operator":"CDFG","type":"Airport","status":"Existing"},
    {"pos": "CNSC Kunming DT","city":"昆明","province":"云南","lat":25.0400,"lng":102.7100,"operator":"CNSC","type":"DT","status":"Existing"},
    {"pos": "CDFG Xi'an AP","city":"西安","province":"陕西","lat":34.4471,"lng":108.7516,"operator":"CDFG","type":"Airport","status":"New"},
    {"pos": "Zhengzhou Int'l AP","city":"郑州","province":"河南","lat":34.5197,"lng":113.8408,"operator":"CNSC","type":"Airport","status":"New"},
    {"pos": "CNSC Zhengzhou DT","city":"郑州","province":"河南","lat":34.7500,"lng":113.6500,"operator":"CNSC","type":"DT","status":"Existing"},
    {"pos": "Urumqi AP","city":"乌鲁木齐","province":"新疆","lat":43.9072,"lng":87.4742,"operator":"CDFG","type":"Airport","status":"Existing"},
    {"pos": "CDFG Erlianhaote Border","city":"二连浩特","province":"内蒙古","lat":43.6475,"lng":111.9794,"operator":"CDFG","type":"Border","status":"Existing"},
    {"pos": "CDFG Manzhouli Border","city":"满洲里","province":"内蒙古","lat":49.5967,"lng":117.4353,"operator":"CDFG","type":"Border","status":"Existing"},
    {"pos": "CDFG Heihe Border","city":"黑河","province":"黑龙江","lat":50.2453,"lng":127.4878,"operator":"CDFG","type":"Border","status":"Existing"},
    {"pos": "CDFG Hunchun Border","city":"珲春","province":"吉林","lat":42.8675,"lng":130.3613,"operator":"CDFG","type":"Border","status":"Existing"},
    {"pos": "CDFG Macau DT","city":"澳门","province":"澳门","lat":22.1987,"lng":113.5439,"operator":"CDFG","type":"DT","status":"Existing"},
    {"pos": "City Gates Hong Kong","city":"香港","province":"香港","lat":22.3000,"lng":114.1700,"operator":"CDFG","type":"DT","status":"Existing"},
]

# --- 品牌覆盖矩阵（来自 Excel 的 YES 列）---
BRAND_COVERAGE = {
    "VERSACE":      {"provinces":["海南","上海","北京","广东","江苏","浙江","四川","湖北","湖南","山东","辽宁","福建","重庆","天津","云南","陕西","河南","新疆","内蒙古","黑龙江","吉林","澳门"], "store_count":65},
    "ANNA SUI":     {"provinces":["海南","上海","北京","广东","江苏","浙江","四川","湖北","山东","辽宁","福建","重庆","天津","云南","陕西","河南","新疆"], "store_count":48},
    "4711":         {"provinces":["海南","上海","北京","广东","江苏","湖北","山东","辽宁","福建","重庆","天津","云南"], "store_count":35},
    "ATKINSONS":    {"provinces":["海南","上海","北京","广东","江苏","浙江","四川","湖北","山东","辽宁","福建","重庆","天津","云南","陕西","河南"], "store_count":40},
    "CHOPARD":      {"provinces":["海南","上海","北京","广东","江苏","浙江","四川","湖北","湖南","山东","辽宁","福建","重庆","天津","云南","陕西","河南","新疆"], "store_count":42},
    "FERRAGAMO":    {"provinces":["海南","上海","北京","广东","江苏","浙江","四川","湖北","湖南","山东","辽宁","福建","重庆","天津","云南","陕西","河南","新疆","澳门"], "store_count":50},
    "GRAFF":        {"provinces":["海南","上海","北京","广东","江苏","浙江","四川","湖北","山东","重庆","天津","云南"], "store_count":25},
    "MAISON 21G":   {"provinces":["海南","上海","北京","广东","江苏","湖北","山东","辽宁","重庆"], "store_count":18},
    "MCM":          {"provinces":["海南","上海","北京","广东","江苏","浙江","四川","湖北","湖南","山东","辽宁","福建","重庆","天津","云南","陕西","河南","新疆","澳门"], "store_count":45},
    "MEMO":         {"provinces":["海南","上海","北京","广东","江苏","浙江","四川","湖北","山东","辽宁","福建","重庆","天津","云南","陕西","河南"], "store_count":38},
    "MOSCHINO":     {"provinces":["海南","上海","北京","广东","江苏","浙江","四川","湖北","湖南","山东","辽宁","福建","重庆","天津","云南","陕西","河南","新疆","内蒙古","黑龙江","吉林","澳门"], "store_count":55},
    "Clean":        {"provinces":["海南","上海","北京","广东","江苏","浙江","四川","湖北","山东","辽宁","福建","重庆","天津","云南"], "store_count":30},
    "Lalique":      {"provinces":["海南","上海","北京","广东","江苏","浙江","湖北","山东","辽宁","福建","重庆","天津","云南"], "store_count":28},
    "CREED":        {"provinces":["海南","上海","北京","广东","江苏","浙江","四川","湖北","湖南","山东","辽宁","福建","重庆","天津","云南","陕西","河南","新疆","澳门"], "store_count":42},
    "Furla":        {"provinces":["海南","上海","北京","广东","江苏","湖北","山东","辽宁","福建","重庆","天津","云南"], "store_count":22},
    "MK (Michael Kors)":{"provinces":["海南","上海","北京","广东","江苏","浙江","四川","湖北","湖南","山东","辽宁","福建","重庆","天津","云南","陕西","河南"], "store_count":35},
}

# --- 门店类型样式配置 ---
TYPE_CONFIG = {
    "Airport": {"color": "#1565C0", "icon": "✈️", "label": "机场店"},
    "DT":      {"color": "#C62828", "icon": "🏪", "label": "市区店(含免税)"},
    "Border":  {"color": "#2E7D32", "icon": "🛃", "label": "边境店"},
    "Cruise":  {"color": "#6A1B9A", "icon": "🚢", "label": "游轮店"},
}

# --- 地图配色方案 ---
COLOR_FULL     = "#EF6C00"   # 全部选中品牌覆盖 → 深橙
COLOR_PARTIAL  = "#FFB74D"   # 部分品牌覆盖 → 浅橙
COLOR_NONE     = "#ECEFF1"   # 无覆盖 / 无数据 → 浅灰
COLOR_BORDER   = "#FFFFFF"   # 省界线颜色

# --- 省份全称 ↔ 短名映射（GeoJSON 用全称如"内蒙古自治区"，数据用短名如"内蒙古"）---
FULL_NAME_MAP = {
    "北京市": "北京", "天津市": "天津", "河北省": "河北", "山西省": "山西",
    "内蒙古自治区": "内蒙古", "辽宁省": "辽宁", "吉林省": "吉林", "黑龙江省": "黑龙江",
    "上海市": "上海", "江苏省": "江苏", "浙江省": "浙江", "安徽省": "安徽",
    "福建省": "福建", "江西省": "江西", "山东省": "山东", "河南省": "河南",
    "湖北省": "湖北", "湖南省": "湖南", "广东省": "广东",
    "广西壮族自治区": "广西", "海南省": "海南", "重庆市": "重庆",
    "四川省": "四川", "贵州省": "贵州", "云南省": "云南",
    "西藏自治区": "西藏", "陕西省": "陕西", "甘肃省": "甘肃",
    "青海省": "青海", "宁夏回族自治区": "宁夏",
    "新疆维吾尔自治区": "新疆", "台湾省": "台湾",
    "香港特别行政区": "香港", "澳门特别行政区": "澳门",
}
SHORT_NAME_MAP = {v: k for k, v in FULL_NAME_MAP.items()}

# 全部省级区域列表（用于覆盖统计）
ALL_PROVINCES = set(FULL_NAME_MAP.values())


# ============================================================
# 1. 工具函数：加载 GeoJSON & 计算品牌覆盖
# ============================================================
@st.cache_data(show_spinner="正在加载中国地图边界数据…")
def load_geojson():
    """加载中国省级边界 GeoJSON。优先本地文件，缺失则在线拉取。"""
    local = Path(__file__).parent / "china_provinces.json"
    if local.exists():
        try:
            return json.loads(local.read_text(encoding="utf-8"))
        except Exception:
            pass
    import urllib.request
    try:
        url = "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json"
        with urllib.request.urlopen(url, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def compute_coverage(selected_brands):
    """
    根据 selected_brands 列表，计算每个省份的覆盖等级。
    返回: dict[short_name] -> "full" | "partial" | "none"
          covered_set: 全部品牌共同覆盖的省份集合
          union_set:   任一品牌覆盖的省份集合
    """
    if not selected_brands:
        return {}, set(), set()

    brand_province_sets = []
    for b in selected_brands:
        provs = set(BRAND_COVERAGE.get(b, {}).get("provinces", []))
        brand_province_sets.append(provs)

    # 共同覆盖 = 所有品牌省份的交集
    covered = set(brand_province_sets[0])
    for s in brand_province_sets[1:]:
        covered &= s

    # 并集 = 任一品牌覆盖
    union = set()
    for s in brand_province_sets:
        union |= s

    # 每个省份的等级
    level_map = {}
    for p in ALL_PROVINCES:
        if p in covered:
            level_map[p] = "full"
        elif p in union:
            level_map[p] = "partial"
        else:
            level_map[p] = "none"

    return level_map, covered, union


def get_province_color(short_name, level_map):
    """根据覆盖等级返回填充色。"""
    level = level_map.get(short_name, "none")
    if level == "full":
        return COLOR_FULL
    elif level == "partial":
        return COLOR_PARTIAL
    else:
        return COLOR_NONE


# ============================================================
# 2. 页面初始化
# ============================================================
st.set_page_config(page_title="门店网络与品牌覆盖分析", layout="wide")
st.title("🗺️ TR 门店网络与品牌覆盖分析")
st.markdown("---")

# 加载 GeoJSON
gj = load_geojson()
if gj is None:
    st.error("❌ 无法加载中国地图边界数据。请确保 `china_provinces.json` 放在本脚本同一目录下。")
    st.stop()

df_stores = pd.DataFrame(STORES)
all_brands = sorted(BRAND_COVERAGE.keys())


# ============================================================
# 3. 侧边栏筛选
# ============================================================
with st.sidebar:
    st.header("🔍 筛选条件")

    selected_brands = st.multiselect(
        "选择品牌（可多选）", options=all_brands, default=["VERSACE"]
    )

    type_options = ["All"] + sorted(df_stores["type"].unique())
    store_type_filter = st.multiselect("门店类型", options=type_options, default=["All"])

    op_options = ["All"] + sorted(df_stores["operator"].unique())
    operator_filter = st.multiselect("运营商", options=op_options, default=["All"])

    st.markdown("---")
    st.caption(f"💡 提示：选择品牌后，地图上各省会按\n「全覆盖 / 部分覆盖 / 无覆盖」自动上色")

# 应用筛选
df_filtered = df_stores.copy()
if "All" not in store_type_filter:
    df_filtered = df_filtered[df_filtered["type"].isin(store_type_filter)]
if "All" not in operator_filter:
    df_filtered = df_filtered[df_filtered["operator"].isin(operator_filter)]


# ============================================================
# 4. 顶部指标卡片
# ============================================================
m1, m2, m3, m4 = st.columns(4)
m1.metric("🏪 总门店数", len(df_stores))
m2.metric("📍 覆盖城市", df_stores["city"].nunique())
m3.metric("🗺️ 覆盖省级区域", df_stores["province"].nunique())
m4.metric("🏷️ 合作品牌数", len(all_brands))
st.markdown("---")


# ============================================================
# 5. 品牌覆盖摘要
# ============================================================
if selected_brands:
    level_map, covered_set, union_set = compute_coverage(selected_brands)

    st.subheader(f"📊 品牌覆盖概览 — {', '.join(selected_brands)}")

    # 各品牌卡片
    nbrands = min(len(selected_brands), 4)  # 最多一行4个
    bc = st.columns(nbrands)
    for i, brand in enumerate(selected_brands):
        with bc[i % nbrands]:
            info = BRAND_COVERAGE.get(brand, {"provinces": [], "store_count": 0})
            st.info(
                f"**{brand}**\n\n"
                f"门店数: `{info['store_count']}` 家\n"
                f"覆盖区域: `{len(info['provinces'])}` 个省/区"
            )

    # 覆盖统计
    c1, c2, c3 = st.columns(3)
    c1.metric("🎯 共同覆盖（交集）", f"{len(covered_set)} 个区域")
    c2.metric("📋 总覆盖（并集）", f"{len(union_set)} 个区域")
    pct = round(len(covered_set) / len(ALL_PROVINCES) * 100, 1)
    c3.metric("📈 全域覆盖率", f"{pct}%")

    st.markdown("---")
else:
    level_map, covered_set, union_set = compute_coverage([])


# ============================================================
# 6. 🗺️ 中国地图（Folium + Leaflet）—— 核心！
# ============================================================
st.subheader("📍 中国门店分布与品牌覆盖地图")

# ---- 6a. 创建基础地图 ----
m = folium.Map(
    location=[35, 105],       # 中国中心点
    zoom_start=4,
    tiles="CartoDB positron", # 干净的浅色底图
    zoom_control=True,
    scrollWheelZoom=True,
)

# ---- 6b. 省份填充层（Choropleth 效果）----
prov_layer = folium.FeatureGroup(name="省份覆盖", show=True).add_to(m)

for feature in gj["features"]:
    full_name = feature.get("properties", {}).get("name", "")
    if not full_name:
        continue
    short_name = FULL_NAME_MAP.get(full_name)
    if not short_name:
        continue  # 南海诸岛等无名 feature 跳过

    color = get_province_color(short_name, level_map)

    # 构建 tooltip 文字
    if selected_brands and short_name in level_map:
        lvl = level_map[short_name]
        if lvl == "full":
            tooltip = f"<b>{short_name}</b><br>✅ 全部选中品牌均已入驻"
        elif lvl == "partial":
            brands_here = [b for b in selected_brands
                           if short_name in BRAND_COVERAGE.get(b, {}).get("provinces", [])]
            tooltip = f"<b>{short_name}</b><br>🟡 部分覆盖: {', '.join(brands_here)}"
        else:
            tooltip = f"<b>{short_name}</b><br>⬜ 暂无品牌覆盖"
    else:
        tooltip = f"<b>{short_name}</b>"

    style_fn = lambda x, c=color: {
        "fillColor": c,
        "fillOpacity": 0.65 if c != COLOR_NONE else 0.3,
        "color": COLOR_BORDER,
        "weight": 1.0,
    }
    highlight_fn = lambda x: {
        "fillOpacity": 0.85,
        "weight": 2.0,
        "color": "#333333",
    }

    folium.GeoJson(
        feature,
        style_function=lambda x, c=color: {
            "fillColor": c,
            "fillOpacity": 0.65 if c != COLOR_NONE else 0.3,
            "color": COLOR_BORDER,
            "weight": 1.0,
        },
        highlight_function=lambda x: {
            "fillOpacity": 0.85,
            "weight": 2.0,
            "color": "#333333",
        },
        tooltip=folium.Tooltip(tooltip, max_width=260),
    ).add_to(prov_layer)

# ---- 6c. 门店标记层 ----
marker_layer = folium.FeatureGroup(name="门店位置", show=True).add_to(m)

for _, row in df_filtered.iterrows():
    tcfg = TYPE_CONFIG.get(row["type"], TYPE_CONFIG["DT"])

    # 覆盖品牌信息
    if selected_brands:
        covered = [b for b in selected_brands
                  if row["province"] in BRAND_COVERAGE.get(b, {}).get("provinces", [])]
        brand_line = f"<br><b>覆盖:</b> {', '.join(covered) or '—'}"
    else:
        brand_line = ""

    status_icon = "✅" if row["status"] == "Existing" else "🆕"

    html_popup = (
        f"<div style='min-width:180px;font-family:sans-serif;'>"
        f"<b style='font-size:14px'>{row['pos']}</b><hr style='margin:4px 0'>"
        f"📍 {row['city']}, {row['province']}<br>"
        f"🏢 <i>{row['operator']}</i><br>"
        f"🏷️ {tcfg['icon']} {tcfg['label']} | {status_icon}"
        f"{brand_line}"
        f"</div>"
    )

    folium.CircleMarker(
        location=[row["lat"], row["lng"]],
        radius=8,
        color=tcfg["color"],
        fill=True,
        fill_color=tcfg["color"],
        fill_opacity=0.85,
        popup=folium.Popup(html_popup, max_width=280),
        tooltip=folium.Tooltip(
            f"<b>{row['pos']}</b><br>{row['city']} | {tcfg['label']}"
        ),
    ).add_to(marker_layer)

# ---- 6d. 图层控制 ----
folium.LayerControl(collapsed=False).add_to(m)

# ---- 6e. 自定义图例 HTML ----
legend_html = '''
<div style="
    position:fixed; bottom:40px; left:50px; z-index:9999;
    background:white; padding:12px 16px; border-radius:10px;
    box-shadow:0 2px 8px rgba(0,0,0,0.15); font-family:sans-serif;
    font-size:13px; line-height:1.8;
">
<b style="font-size:14px">📌 图例</b><hr style="margin:6px 0">
<div><span style="display:inline-block;width:18px;height:18px;
background:'''+COLOR_FULL+''';border-radius:3px;border:1px solid #ccc;margin-right:6px;vertical-align:middle"></span>
全部品牌覆盖</div>
<div><span style="display:inline-block;width:18px;height:18px;
background:'''+COLOR_PARTIAL+''';border-radius:3px;border:1px solid #ccc;margin-right:6px;vertical-align:middle"></span>
部分品牌覆盖</div>
<div><span style="display:inline-block;width:18px;height:18px;
background:'''+COLOR_NONE+''';border-radius:3px;border:1px solid #ccc;margin-right:6px;vertical-align:middle"></span>
无覆盖</div>
<hr style="margin:6px 0">
'''
for tname, tc in TYPE_CONFIG.items():
    legend_html += (
        f'<div><span style="color:{tc["color"]};font-weight:bold;'
        f'margin-right:4px">{tc["icon"]}</span>{tc["label"]}</div>'
    )
legend_html += "</div>"
m.get_root().html.add_child(folium.Element(legend_html))

# ---- 6f. 渲染到 Streamlit ----
map_result = st_folium(
    m,
    width="100%",
    height=600,
    returned_objects=["last_clicked", "last_object_clicked"],
    use_container_width=True,
)

st.caption("💡 操作提示：滚轮缩放 | 拖拽平移 | 点击省份查看详情 | 点击门店图标查看门店信息")


# ============================================================
# 7. 品牌覆盖明细表
# ============================================================
st.markdown("---")
if selected_brands:
    st.subheader("📋 各区域品牌覆盖明细表")

    rows = []
    for prov in sorted(ALL_PROVINCES):
        status_row = {}
        for b in selected_brands:
            info = BRAND_COVERAGE.get(b, {"provinces": []})
            status_row[b] = "✅" if prov in info["provinces"] else "❌"

        stores_in = df_filtered[df_filtered["province"] == prov]
        flag = "🌏" if prov in ("香港", "澳门") else ""
        cities = ", ".join(stores_in["city"].unique()) if len(stores_in) > 0 else "—"

        rows.append({
            "区域": f"{flag} {prov}",
            "门店数": len(stores_in),
            "覆盖城市": cities,
            **status_row,
        })

    df_detail = pd.DataFrame(rows)
    st.dataframe(df_detail, use_container_width=True, hide_index=True)


# ============================================================
# 8. 📊 分析图表（Plotly —— 这些本来就没问题）
# ============================================================
st.markdown("---")
st.subheader("📈 门店网络数据分析")

t1, t2, t3, t4 = st.tabs(["门店类型分布", "运营商分布", "区域门店排行", "品牌覆盖排行"])

with t1:
    tc = df_stores["type"].value_counts().reset_index()
    tc.columns = ["类型", "数量"]
    fig_pie = px.pie(
        tc, values="数量", names="类型",
        title="门店类型占比",
        hole=0.45,
        color_discrete_sequence=["#1565C0", "#C62828", "#2E7D32", "#6A1B9A"],
        template="plotly_white",
    )
    fig_pie.update_traces(textposition="inside", textinfo="percent+label",
                          textfont_size=13)
    st.plotly_chart(fig_pie, use_container_width=True)

with t2:
    oc = df_stores["operator"].value_counts().reset_index()
    oc.columns = ["运营商", "门店数"]
    fig_op = px.bar(
        oc, x="运营商", y="门店数",
        title="各运营商门店数量",
        color="门店数",
        color_continuous_scale="Blues",
        text_auto=True,
        template="plotly_white",
    )
    fig_op.update_layout(xaxis_tickangle=-35, xaxis_title="", yaxis_title="")
    st.plotly_chart(fig_op, use_container_width=True)

with t3:
    pc = df_stores["province"].value_counts().reset_index()
    pc.columns = ["区域", "门店数"]
    fig_pc = px.bar(
        pc.sort_values("门店数", ascending=True),
        x="门店数", y="区域",
        title="各省/区域门店数量排行（含港澳）",
        color="门店数",
        color_continuous_scale="OrRd",
        text_auto=True,
        orientation="h",
        template="plotly_white",
    )
    fig_pc.update_layout(height=max(480, len(pc) * 28), yaxis_title="", xaxis_title="")
    st.plotly_chart(fig_pc, use_container_width=True)

with t4:
    bd_rows = []
    for brand, info in BRAND_COVERAGE.items():
        bd_rows.append({"品牌": brand, "覆盖区域数": len(info["provinces"]), "门店数": info["store_count"]})
    df_bd = pd.DataFrame(bd_rows).sort_values("覆盖区域数", ascending=True)
    fig_bd = px.bar(
        df_bd, x="覆盖区域数", y="品牌",
        title="各品牌覆盖区域数量排行",
        color="门店数",
        color_continuous_scale="YlOrBr",
        text_auto=True,
        orientation="h",
        template="plotly_white",
    )
    fig_bd.update_layout(height=max(450, len(df_bd) * 27), yaxis_title="", xaxis_title="")
    st.plotly_chart(fig_bd, use_container_width=True)


# ============================================================
# 9. 🛡️ 品牌覆盖能力雷达图
# ============================================================
st.markdown("---")
st.subheader("🛡️ 多品牌覆盖能力对比")

if len(selected_brands) >= 2:
    dims = ["覆盖广度", "门店规模", "机场渠道", "市区渠道", "海南布局"]

    radar_traces = []
    airport_pool = {"上海","北京","广东","江苏","浙江","四川","湖北","湖南",
                    "山东","辽宁","福建","重庆","天津","云南","陕西","河南","新疆","海南"}
    dt_pool = {"海南","上海","北京","广东","江苏","浙江","湖北","山东",
               "辽宁","福建","重庆","天津","云南","澳门"}

    for brand in selected_brands:
        info = BRAND_COVERAGE.get(brand, {"provinces":[], "store_count":0})
        ps = info["provinces"]
        radar_traces.append(go.Scatterpolar(
            r=[
                len(ps)/23*100,
                min(info["store_count"]/65*100, 100),
                len(set(ps)&airport_pool)/len(airport_pool)*100,
                len(set(ps)&dt_pool)/len(dt_pool)*100,
                100 if "海南" in ps else 0,
            ],
            theta=dims,
            fill="toself",
            name=brand,
            line=dict(width=2),
        ))

    fig_radar = go.Figure(data=radar_traces)
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,100])),
        title=None,
        height=520,
        template="plotly_white",
        legend_orientation="h",
        legend_y=1.08,
    )
    st.plotly_chart(fig_radar, use_container_width=True)
else:
    st.info("ℹ️ 请在左侧选择 **至少 2 个品牌** 进行对比分析")


# ============================================================
# 10. 底部：原始数据 & 导出
# ============================================================
st.markdown("---")
with st.expander("📄 查看门店完整清单"):
    show_df = df_stores[["pos", "city", "province", "operator", "type", "status"]].copy()
    show_df.columns = ["门店名称", "城市", "区域", "运营商", "类型", "状态"]
    st.dataframe(show_df, use_container_width=True, hide_index=True)

    csv_buf = df_stores.to_csv(index=False).encode("utf-8-sig")  # BOM for Excel
    st.download_button(
        label="📥 下载门店数据 CSV",
        data=csv_buf,
        file_name=f"TR_Store_List_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

st.markdown("---")
st.caption(
    "数据来源: TR Store List YTD 2026  |  "
    f"最后更新: {datetime.now().strftime('%Y-%m-%d')}  |  "
    "地图底图: © CartoDB / OpenStreetMap"
)
