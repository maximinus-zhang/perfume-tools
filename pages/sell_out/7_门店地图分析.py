# pages/7_门店地图分析.py
# ...（文件开头到第6节保持不变）...

# ============================================================
# 7. 中国地图（核心可视化）- ✨ 修复版
# ============================================================
st.subheader("📍 中国门店分布与品牌覆盖地图")

# 创建地图
fig_map = go.Figure()

# ---- 7a. 所有省份灰色底色 ----
all_province_names = list(PROVINCE_EN.values())
fig_map.add_trace(go.Choropleth(
    locations=all_province_names,
    locationmode="country names",
    z=[0] * len(all_province_names),
    text=[f"{cn}" for cn in PROVINCE_EN.keys()],
    hoverinfo="text",
    marker_line_color="#aaaaaa",
    marker_line_width=0.5,
    showscale=False,
    colorscale=[[0, "#f5f5f5"], [1, "#f5f5f5"]],
    geo="geo"
))

# ---- 7b. 品牌覆盖高亮 ----
if selected_brands:
    # 交集 → 深橙
    for prov_cn in covered_all:
        prov_en = PROVINCE_EN.get(prov_cn, prov_cn)
        fig_map.add_trace(go.Choropleth(
            locations=[prov_en],
            locationmode="country names",
            z=[1],
            text=f"✅ {prov_cn} — 全部选中品牌均已覆盖",
            hoverinfo="text",
            marker_line_color="#E65100",
            marker_line_width=2.5,
            showscale=False,
            colorscale=[[0, "#FFB300"], [1, "#FFB300"]],
            geo="geo",
            visible=True
        ))
    
    # 并集非交集 → 浅橙
    partial_provinces = union_all - covered_all
    for prov_cn in partial_provinces:
        prov_en = PROVINCE_EN.get(prov_cn, prov_cn)
        brand_list = [b for b in selected_brands if prov_cn in BRAND_COVERAGE.get(b, {}).get("provinces", [])]
        fig_map.add_trace(go.Choropleth(
            locations=[prov_en],
            locationmode="country names",
            z=[0.5],
            text=f"⚠️ {prov_cn} — 部分覆盖 ({', '.join(brand_list)})",
            hoverinfo="text",
            marker_line_color="#FF8F00",
            marker_line_width=1.5,
            showscale=False,
            colorscale=[[0, "#FFE0B2"], [1, "#FFE0B2"]],
            geo="geo",
            visible=True
        ))

# ---- 7c. 门店标记（始终显示所有门店，按类型分色）----
TYPE_COLORS = {
    "Airport": "#1E88E5",   # 蓝
    "DT":      "#E53935",   # 红
    "Border":  "#43A047",   # 绿
    "Cruise":  "#8E24AA",   # 紫
}
TYPE_SYMBOLS = {
    "Airport": "diamond",
    "DT":      "circle",
    "Border":  "square",
    "Cruise":  "triangle-up",
}
TYPE_LABELS = {
    "Airport": "机场店",
    "DT":      "市区店",
    "Border":  "边境店",
    "Cruise":  "游轮店",
}

# 使用全部门店（不按品牌过滤门店标记，品牌仅影响色块）
df_map_stores = df_filtered.copy()

# 构建每个门店的悬停详情
hover_texts = []
marker_colors = []
marker_symbols = []
marker_sizes = []

for _, store in df_map_stores.iterrows():
    # 品牌覆盖信息
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
        f"🏷️ {store['type']} | {'✅ 已开业' if store['status']=='Existing' else '🆕 新店'}<br>"
        f"{brand_info}"
    )
    marker_colors.append(TYPE_COLORS.get(store["type"], "#999"))
    marker_symbols.append(TYPE_SYMBOLS.get(store["type"], "circle"))
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
        opacity=0.85
    ),
    showlegend=False,
    name="门店位置"
))

# ---- 7d. 省份名称标注（用不可见 marker + text，确保渲染兼容）----
prov_labels = []
prov_lats = []
prov_lngs = []
for prov_cn, center in PROVINCE_CENTERS.items():
    prov_labels.append(prov_cn)
    prov_lats.append(center["lat"])
    prov_lngs.append(center["lng"])

fig_map.add_trace(go.Scattergeo(
    lon=prov_lngs,
    lat=prov_lats,
    text=prov_labels,
    mode="markers+text",       # ⚠️ 必须同时有 marker 和 text
    marker=dict(
        size=0.01,              # 不可见 marker
        color="rgba(0,0,0,0)",
        opacity=0
    ),
    textfont=dict(
        size=13,
        color="#555555",
        family="Arial, sans-serif",
    ),
    textposition="middle center",
    hoverinfo="skip",
    showlegend=False,
    name="省份标注"
))

# ---- 7e. 城市名称标注（去重，每个城市只标1次）----
city_agg = df_map_stores.groupby(["city", "province"]).agg(
    lat=("lat", "mean"),
    lng=("lng", "mean"),
    store_count=("pos", "count")
).reset_index()

fig_map.add_trace(go.Scattergeo(
    lon=city_agg["lng"],
    lat=city_agg["lat"],
    text=city_agg.apply(
        lambda r: f"{r['city']} ({r['store_count']}家)",
        axis=1
    ),
    mode="markers+text",       # ⚠️ 必须同时有 marker 和 text
    marker=dict(
        size=0.01,
        color="rgba(0,0,0,0)",
        opacity=0
    ),
    textfont=dict(
        size=city_agg["store_count"].apply(
            lambda x: min(9 + x * 1.5, 14)
        ).tolist(),
        color="#333333",
        family="Arial",
    ),
    textposition="top center",
    hoverinfo="skip",
    showlegend=False,
    name="城市标注"
))

# ---- 7f. 地图布局 ----
fig_map.update_layout(
    title=dict(
        text=f"TR 品牌门店中国分布图{' | 品牌: ' + ' + '.join(selected_brands) if selected_brands else ' | 全部门店'}",
        font=dict(size=18, color="#333"),
        x=0.5,
        xanchor="center"
    ),
    geo=dict(
        scope="asia",
        projection=dict(type="natural earth"),
        showland=True,
        landcolor="#f9f9f9",
        countrycolor="rgba(180,180,180,0.5)",
        countrywidth=0.8,
        coastlinecolor="rgba(150,150,150,0.3)",
        coastlinewidth=0.5,
        showocean=True,
        oceancolor="#e8f4f8",
        showlakes=True,
        lakecolor="#e8f4f8",
        showsubunits=True,
        subunitcolor="rgba(180,180,180,0.3)",
        subunitwidth=0.5,
        center=dict(lat=33, lon=106),
        projection_scale=4.2,
        lonaxis=dict(range=[73, 136]),
        lataxis=dict(range=[4, 56]),   # 下延以显示港澳
    ),
    height=750,
    margin=dict(l=10, r=10, t=60, b=20),
    showlegend=False,
)

st.plotly_chart(fig_map, use_container_width=True)

# ---- 7g. 图例说明（在 map 下方）----
legend_col1, legend_col2, legend_col3, legend_col4 = st.columns(4)
with legend_col1:
    st.markdown("🔵 **<span style='color:#1E88E5'>◆ 机场店</span>**", unsafe_allow_html=True)
with legend_col2:
    st.markdown("🔴 **<span style='color:#E53935'>● 市区店</span>**", unsafe_allow_html=True)
with legend_col3:
    st.markdown("🟢 **<span style='color:#43A047'>■ 边境店</span>**", unsafe_allow_html=True)
with legend_col4:
    st.markdown("🟣 **<span style='color:#8E24AA'>▲ 游轮店</span>**", unsafe_allow_html=True)

if selected_brands:
    st.caption("🟠 深色省份 = 全部选中品牌覆盖 | 浅色省份 = 部分品牌覆盖 | 灰色 = 无覆盖")

# ============================================================
# 8. 品牌覆盖区域详情表格（包含港澳）
# ============================================================
# ...（后续代码保持不变）...
