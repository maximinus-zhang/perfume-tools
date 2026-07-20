# -*- coding: utf-8 -*-
"""
📍 物流跟踪页面 —— 按 SKU + 门店查询「今年每笔发货」的物流状态与时间轴
========================================================================
数据来源（均从阿里云 OSS 读取，与订单管理共用同一套 OSS 助手）：
    - logistics/sa007a_sales.xlsx ：SA-007A 销售发货明细（已清洗）
    - logistics/sku_cn_names.csv  ：A011 商品资料导出的「货号 → 中文名」映射

逻辑：
    每笔发货以「发货日(Date)」为起点，按固定天数推算各物流节点：
      发货 → +7 清关资料完成 → +10 零售商批准出运 → +13 订舱提货
           → +20 货物抵港 → +34 清关贴标 → +37 海关放行
           → +41 零售商入库 → +48 分拨到门店
    SKU 后缀 -A/-B/-C 忽略，当作同一 SKU 处理；中文名由 A011 匹配得来。
========================================================================
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from utils.oss_helper import read_excel_from_oss, read_csv_from_oss, upload_section

st.title("📍 物流模块 · 发货物流跟踪")

# ===== OSS 数据路径 =====
SA_OSS = "logistics/sa007a_sales.xlsx"      # SA-007A 清洗后的发货明细
SKU_OSS = "logistics/sku_cn_names.csv"      # A011 货号→中文名 映射

# ===== 物流里程碑（相对发货日的偏移天数 + 节点名称）=====
MILESTONES = [
    (0,  "发货"),
    (7,  "清关资料完成"),
    (10, "零售商批准出运"),
    (13, "订舱提货"),
    (20, "货物抵港"),
    (34, "清关贴标"),
    (37, "海关放行"),
    (41, "零售商入库"),
    (48, "分拨到门店"),
]


# ===== 数据加载（带缓存，避免重复读 OSS）=====
@st.cache_data(show_spinner="正在从云端加载销售发货明细…")
def load_sales():
    df = read_excel_from_oss(SA_OSS, sheet_name=0)
    if df.empty:
        return df
    # 清洗：仅保留有效发货行（有货号、有日期、有数量）
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df[df["U_OldItemNo"].notna() & df["Date"].notna() & df["Qty"].notna()].copy()
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce")
    df = df[df["Qty"].notna()]
    # SKU 去后缀 -A/-B/-C，当作同一 SKU
    df["sku_key"] = (
        df["U_OldItemNo"].astype(str).str.strip().str.replace(r"-[ABC]$", "", regex=True)
    )
    df["年份"] = df["Date"].dt.year
    return df.reset_index(drop=True)


@st.cache_data(show_spinner="正在加载商品中文名…")
def load_sku_names():
    d = read_csv_from_oss(SKU_OSS)
    if not d.empty and "sku_key" in d.columns:
        return d[["sku_key", "cn_name"]].dropna(subset=["sku_key"]).drop_duplicates("sku_key")
    return pd.DataFrame(columns=["sku_key", "cn_name"])


def now_shanghai():
    """取上海时区的当前时间（部署在海外服务器时也能对上国内日期）"""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Shanghai"))
    except Exception:
        return datetime.now()


def milestone_dates(ship_date):
    """返回 9 个节点的日期列表"""
    return [ship_date + timedelta(days=off) for off, _ in MILESTONES]


def status_of(dates, today):
    """根据今天，返回 (当前阶段名, 进度%, 已完成节点索引)"""
    if today < dates[0]:
        return "待发货", 0.0, -1
    idx = max(i for i, t in enumerate(dates) if t <= today)
    pct = idx / (len(dates) - 1) * 100
    return MILESTONES[idx][1], pct, idx


# ===== 加载数据 =====
sales = load_sales()
sku_names = load_sku_names()

if sales.empty:
    st.error("⚠️ 未能从云端读取销售明细，请确认 OSS 中已有 logistics/sa007a_sales.xlsx")
    st.stop()

# 合并中文名
name_map = dict(zip(sku_names["sku_key"], sku_names["cn_name"])) if not sku_names.empty else {}
sales["中文名"] = sales["sku_key"].map(name_map).fillna("")

# 限定今年
today = now_shanghai()
this_year = today.year
sales_y = sales[sales["年份"] == this_year].copy()
if sales_y.empty:
    st.info(f"📭 {this_year} 年暂无发货数据。")
    st.stop()

# ===== 侧边栏：筛选 =====
st.sidebar.subheader("🔎 查询条件")
# SKU 选项：来自今年数据的去重 SKU，带中文名
opt = sales_y[["sku_key", "中文名"]].drop_duplicates("sku_key")
opt["label"] = opt.apply(
    lambda r: f"{r['中文名']} ｜ {r['sku_key']}" if r["中文名"] else r["sku_key"], axis=1
)
opt = opt.sort_values("label")
sku_options = ["（全部 SKU）"] + opt["label"].tolist()
sku_sel = st.sidebar.selectbox("选择 SKU（中文名 / 货号）", sku_options, index=0)

stores = sorted(sales_y["CustomerName"].dropna().unique().tolist())
store_sel = st.sidebar.multiselect("选择门店（可多选，留空=全部门店）", stores)

# ===== 过滤视图 =====
if sku_sel != "（全部 SKU）":
    sel_key = sku_sel.split("｜")[-1].strip()
    view = sales_y[sales_y["sku_key"] == sel_key].copy()
else:
    view = sales_y.copy()
if store_sel:
    view = view[view["CustomerName"].isin(store_sel)]

# 计算每笔发货的节点日期与状态
view["_dates"] = view["Date"].apply(milestone_dates)
view[["当前状态", "进度", "_idx"]] = view["_dates"].apply(
    lambda ds: pd.Series(status_of(ds, today))
)
view = view.sort_values("Date")

if view.empty:
    st.warning("🔍 当前筛选条件下没有发货记录，试试调整 SKU 或门店。")
    st.stop()

# ===== KPI 指标卡 =====
done = int((view["当前状态"] == "分拨到门店").sum())
intransit = len(view) - done
total_qty = pd.to_numeric(view["Qty"], errors="coerce").fillna(0).sum()
c1, c2, c3, c4 = st.columns(4)
c1.metric("📦 发货笔数", f"{len(view)} 笔")
c2.metric("🔢 发货总量", f"{total_qty:,.0f}")
c3.metric("✅ 已分拨到店", f"{done} 笔")
c4.metric("🚚 在途", f"{intransit} 笔")

st.caption(f"数据范围：{this_year} 年 ｜ 当前参考时间：{today.strftime('%Y-%m-%d %H:%M')}（上海时区）")

# ===== 明细表 =====
st.markdown("---")
st.subheader("📋 每笔发货明细与当前状态")
table = view.rename(columns={
    "Date": "发货日", "CustomerName": "门店", "InvoiceNo": "发票号",
    "U_OldItemNo": "货号", "中文名": "中文名", "Qty": "数量",
    "当前状态": "当前状态", "进度": "进度%",
})
table = table[["发货日", "门店", "发票号", "货号", "中文名", "数量", "当前状态", "进度%"]]
table["发货日"] = table["发货日"].dt.strftime("%Y-%m-%d")
st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
    column_config={
        "进度%": st.column_config.ProgressColumn(
            "进度%", min_value=0, max_value=100, format="%d%%"
        ),
        "当前状态": st.column_config.TextColumn("当前状态"),
    },
)

# ===== 时间轴可视化（Plotly）=====
st.markdown("---")
st.subheader("🚚 物流时间轴（每笔发货的节点进度）")
# 笔数过多时只画最近的 60 笔，避免图过长
view_tl = view.sort_values("Date", ascending=False).head(60)
fig = go.Figure()
for _, r in view_tl.iterrows():
    ds = r["_dates"]
    lab = f"{r['CustomerName']} · {r['U_OldItemNo']} · {r['Date'].strftime('%m-%d')}"
    # 背景条：发货 → 分拨到门店
    fig.add_trace(go.Bar(
        x=[(ds[-1] - ds[0]).days], base=[ds[0]], y=[lab], orientation="h",
        marker_color="rgba(210,225,245,0.55)", showlegend=False,
        hoverinfo="text",
        hovertext=f"发货: {ds[0]:%Y-%m-%d}<br>分拨到店: {ds[-1]:%Y-%m-%d}",
    ))
    # 9 个节点标记（已到达=绿，未到达=灰）
    colors = ["#2ca02c" if ds[k] <= today else "#cfcfcf" for k in range(len(ds))]
    fig.add_trace(go.Scatter(
        x=ds, y=[lab] * len(ds), mode="markers",
        marker=dict(size=11, color=colors, line=dict(width=1, color="#888")),
        customdata=np.array([[name] for _, name in MILESTONES]),
        hovertemplate="%{customdata[0]}: %{x|%Y-%m-%d}<extra></extra>",
        showlegend=False,
    ))
# 今天参考线
fig.add_vline(x=today, line_dash="dash", line_color="#e4572e",
              annotation_text="今天", annotation_position="top")
fig.update_layout(
    height=max(320, 42 * len(view_tl) + 80),
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis_title="日期", yaxis_title="", showlegend=False,
    xaxis=dict(type="date"),
)
st.plotly_chart(fig, use_container_width=True)
if len(view) > len(view_tl):
    st.caption(f"⚠️ 为图表清晰，时间轴仅展示最近 {len(view_tl)} 笔；完整 {len(view)} 笔见上方明细表。")

# ===== 数据刷新（与订单管理一致的上传入口）=====
st.sidebar.markdown("---")
st.sidebar.subheader("🔄 数据刷新")
upload_section(SA_OSS, label="上传 SA-007A 销售明细（请另存为 .xlsx）")
upload_section(SKU_OSS, label="上传 商品中文名映射 sku_cn_names.csv")
