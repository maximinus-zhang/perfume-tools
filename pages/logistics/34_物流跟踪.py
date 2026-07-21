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
from datetime import datetime, timedelta
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
    """取上海时区的当前时间（部署在海外服务器时也能对上国内日期）。
    返回 naive（去时区）是为了和 Excel 读出的 naive 日期直接比较，
    避免 pandas 'can't compare offset-naive and offset-aware datetimes' 报错。"""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)
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
    height=min(420, max(280, len(table) * 32 + 40)),
    column_config={
        "发货日": st.column_config.TextColumn("发货日", width="small"),
        "门店":   st.column_config.TextColumn("门店",   width="medium"),
        "发票号": st.column_config.TextColumn("发票号", width="small"),
        "货号":   st.column_config.TextColumn("货号",   width="medium"),
        "中文名": st.column_config.TextColumn("中文名", width="medium"),
        "数量":   st.column_config.NumberColumn("数量",   width="small", format="%d"),
        "当前状态": st.column_config.TextColumn("当前状态", width="small"),
        "进度%":  st.column_config.ProgressColumn(
            "进度%", min_value=0, max_value=100, format="%d%%", width="medium"
        ),
    },
)

# ===== 物流流水线看板（直接可读，无需悬停）=====
st.markdown("---")
st.subheader("🚚 物流流水线看板（每笔发货 × 各节点状态）")
st.caption("绿色 = 已到达该节点 ｜ 橙色 = 当前进行中 ｜ 灰色 = 尚未到达 ｜ 单元格内为计划/实际日期(MM-DD)")

# 取最近若干笔，避免表格过宽过长；完整笔数见上方明细表
BOARD_LIMIT = 80
view_board = view.sort_values("Date", ascending=False).head(BOARD_LIMIT)

# 列头：9 个物流节点
header_cells = "".join(
    f'<th class="stage">{i+1}.{name}</th>' for i, (off, name) in enumerate(MILESTONES)
)

legend = (
    '<div class="legend">'
    '<span class="lg done">■ 已到达</span>'
    '<span class="lg active">■ 进行中</span>'
    '<span class="lg future">■ 未到达</span>'
    '</div>'
)

rows_html = ""
for _, r in view_board.iterrows():
    dates = r["_dates"]
    idx = int(r["_idx"])
    active_idx = idx + 1 if idx + 1 < len(MILESTONES) else None
    cn = r["中文名"] if r["中文名"] else r["U_OldItemNo"]
    store = r["CustomerName"] if pd.notna(r["CustomerName"]) else ""
    qty = r["Qty"] if pd.notna(r["Qty"]) else 0
    cells = ""
    for i, (off, name) in enumerate(MILESTONES):
        d = dates[i]
        if d <= today:
            cls = "done"
        elif i == active_idx:
            cls = "active"
        else:
            cls = "future"
        cells += f'<td class="{cls}">{d:%m-%d}</td>'
    rows_html += (
        '<tr>'
        f'<td class="info sticky">'
        f'<div class="cn">{cn}</div>'
        f'<div class="meta">{r["U_OldItemNo"]} ｜ {store}</div>'
        f'<div class="qty">数量 {qty:,.0f} · 当前：{r["当前状态"]}</div>'
        '</td>'
        f'{cells}'
        '</tr>'
    )

css = """
<style>
.board-wrap { overflow-x: auto; border-radius: 12px; border: 1px solid #e6e8ec;
             max-width: 100%; }
table.board { border-collapse: separate; border-spacing: 0; width: 100%;
              table-layout: fixed; font-size: 12px; }
table.board th, table.board td { padding: 5px 4px; text-align: center;
                                white-space: nowrap; overflow: hidden;
                                text-overflow: ellipsis; }
table.board th.stage { background: #f3f5f8; color: #333; font-weight: 600;
    border-bottom: 2px solid #d9dde3; white-space: normal; line-height: 1.15;
    vertical-align: bottom; font-size: 11px; }
table.board td.info { background: #fff; text-align: left; border-right: 2px solid #e6e8ec;
                     width: 22%; }
table.board td.sticky { position: sticky; left: 0; z-index: 2; background: #fff;
                       box-shadow: 2px 0 4px rgba(0,0,0,.06); }
.cn { font-weight: 700; color: #1a1a1a; font-size: 12px; white-space: nowrap;
      overflow: hidden; text-overflow: ellipsis; }
.meta { color: #6b7280; font-size: 10px; white-space: nowrap;
        overflow: hidden; text-overflow: ellipsis; }
.qty { color: #2563eb; font-weight: 600; font-size: 11px; }
td.done { background: #2ca02c; color: #fff; font-size: 11px; }
td.active { background: #f0a30a; color: #1a1a1a; font-weight: 700; font-size: 11px;
           outline: 2px solid #b9790a; }
td.future { background: #eceff3; color: #9aa3af; font-size: 11px; }
.legend { margin: 6px 0 10px; font-size: 12px; }
.legend .lg { margin-right: 14px; }
</style>
"""

html = css + (
    '<div class="board-wrap">'
    '<table class="board">'
    f'<thead><tr><th class="info sticky">SKU / 门店</th>{header_cells}</tr></thead>'
    f'<tbody>{rows_html}</tbody>'
    '</table>'
    '</div>'
    f'{legend}'
)
st.markdown(html, unsafe_allow_html=True)

if len(view) > len(view_board):
    st.caption(f"⚠️ 看板仅展示最近 {len(view_board)} 笔以便阅读；完整 {len(view)} 笔见上方明细表。")

# ===== 数据刷新（与订单管理一致的上传入口）=====
st.sidebar.markdown("---")
st.sidebar.subheader("🔄 数据刷新")
upload_section(SA_OSS, label="上传 SA-007A 销售明细（请另存为 .xlsx）")
upload_section(SKU_OSS, label="上传 商品中文名映射 sku_cn_names.csv")
