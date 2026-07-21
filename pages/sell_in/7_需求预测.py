# -*- coding: utf-8 -*-
"""
需求预测（Prophet）· 基于 SA-007A 真实出货数据
==============================================
数据来源：data/logistics/sa007a_sales.xlsx
  · 字段：SIS BPCode / CustomerName / Date / InvoiceNo / Brand / U_OldItemNo / ItemName / Qty / LineDiscountedTotal
  · 覆盖：25 个品牌 / 1160 个 SKU / 2026-01 ~ 2026-07 出货
支持粒度：全部汇总 / 按品牌 / 按单品(SKU) 三种 Prophet 预测。
优先读 OSS（生产），未配置密钥时自动回落本地真实文件。
"""
import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from prophet import Prophet
from utils.oss_helper import upload_section, read_excel_from_oss

st.title("📈 香水供应链·需求预测（出货数据）")
st.caption("数据源：SA-007A 真实出货明细（25 品牌 / 1160 SKU / 2026-01 ~ 2026-07）。可切换 品牌→商品 粒度做分 SKU 预测。")

# 真实出货数据文件
OSS_KEY = "sell_in/sa007a_sales.xlsx"
LOCAL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "logistics", "sa007a_sales.xlsx")
)

# ===== 上传区域 =====
with st.sidebar:
    st.markdown("---")
    upload_section(OSS_KEY, "上传 SA-007A 出货数据")

# ===== 工具函数 =====
def _oss_configured() -> bool:
    """是否已配置 OSS 密钥（生产环境用）。未配置则直接用本地真实数据。"""
    try:
        _ = st.secrets["OSS_ACCESS_KEY"]
        return True
    except Exception:
        return False


def _load_raw_sa007a():
    """优先 OSS，回落本地真实文件；返回 (df, source_label)。"""
    if _oss_configured():
        try:
            d = read_excel_from_oss(OSS_KEY, sheet_name=0, prefix_filter=None)
            if not d.empty and any("qty" in str(c).lower() or "date" in str(c).lower() for c in d.columns):
                return d, "OSS 云端"
        except Exception:
            pass
    if os.path.exists(LOCAL_PATH):
        try:
            d = pd.read_excel(LOCAL_PATH, sheet_name=0, header=0)
            if not d.empty and any("qty" in str(c).lower() or "date" in str(c).lower() for c in d.columns):
                return d, "本地 data/logistics/sa007a_sales.xlsx（真实出货数据）"
        except Exception:
            pass
    return pd.DataFrame(), None


def _pick(cols, *kws):
    """在列名里挑第一个包含任一关键字的列。"""
    for kw in kws:
        for c in cols:
            if kw.lower() in str(c).lower():
                return c
    return None


# ===== 读取真实出货数据 =====
raw, data_source = _load_raw_sa007a()
has_data = not raw.empty

if not has_data:
    st.warning("⚠️ 未找到 SA-007A 出货数据（OSS 与本地均无），以下为**模拟示例数据**，仅供演示界面。")
    np.random.seed(42)
    dates = pd.date_range(start='2026-01-01', end='2026-07-20', freq='D')
    trend = np.linspace(50, 80, len(dates))
    season = 15 * np.sin(2 * np.pi * np.arange(len(dates)) / 365)
    noise = np.random.normal(0, 8, len(dates))
    df = pd.DataFrame({'ds': dates, 'y': np.maximum(trend + season + noise, 5)})
    sel_label = "模拟数据"
    data_source = "模拟示例数据"
else:
    date_col = _pick(raw.columns, "date")
    qty_col = _pick(raw.columns, "qty", "数量", "quantity")
    brand_col = _pick(raw.columns, "brand", "品牌")
    item_col = _pick(raw.columns, "itemname", "sku", "商品", "name")
    if not (date_col and qty_col):
        st.error("出货数据缺少日期列或数量列，请检查 SA-007A 文件格式")
        st.stop()

    raw[date_col] = pd.to_datetime(raw[date_col], errors="coerce")
    raw[qty_col] = pd.to_numeric(raw[qty_col], errors="coerce").fillna(0)

    # ----- 选择器（品牌 -> 商品 SKU）-----
    st.markdown("---")
    brands = sorted(raw[brand_col].dropna().unique().tolist())
    brand_sel = st.selectbox("选择品牌", ["全部品牌（汇总出货量）"] + brands)
    if brand_sel == "全部品牌（汇总出货量）":
        sub = raw
        sel_label = "全部品牌汇总"
    else:
        sub = raw[raw[brand_col] == brand_sel]
        skus = sorted(sub[item_col].dropna().unique().tolist())
        sku_sel = st.selectbox("选择商品（SKU）", ["该品牌全部（汇总）"] + skus)
        if sku_sel == "该品牌全部（汇总）":
            sel_label = brand_sel
        else:
            sub = sub[sub[item_col] == sku_sel]
            sel_label = sku_sel

    # ----- 按日聚合（无出货的日期补 0，保证连续日度序列）-----
    sub = sub[[date_col, qty_col]].copy()
    sub.columns = ["ds", "y"]
    sub = sub.dropna(subset=["ds"])
    daily = sub.groupby(sub["ds"].dt.normalize())["y"].sum().reset_index()
    full = pd.date_range(daily["ds"].min(), daily["ds"].max(), freq="D")
    df = daily.set_index("ds").reindex(full, fill_value=0).rename_axis("ds").reset_index()
    df["y"] = df["y"].astype(float)

    n_days = len(df)
    n_nonzero = int((df["y"] > 0).sum())
    st.success(f"✅ 已加载出货数据：{sel_label} ｜ {n_days} 天 ｜ {n_nonzero} 天有出货（来源：{data_source}）")
    if n_nonzero < 30:
        st.info(f"ℹ️ 该粒度下仅 {n_nonzero} 天有出货记录，样本偏少，预测仅供参考；"
                 f"可切到「品牌」或「全部品牌」视图获得更稳的趋势。")

st.markdown("---")

# ===== 参数设置 =====
col1, col2, col3 = st.columns(3)
with col1:
    forecast_days = st.number_input("预测天数", min_value=7, max_value=365, value=30, step=7)
with col2:
    seasonality = st.selectbox("季节性周期", ["自动检测", "每周", "每月", "每年"], index=0)
with col3:
    confidence = st.slider("置信区间", 50, 99, 80, 5)

# ===== KPI =====
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
col1.metric("📊 历史数据总量", f"{len(df)} 天")
col2.metric("📅 起始日期", df['ds'].min().strftime('%Y-%m-%d'))
col3.metric("📅 结束日期", df['ds'].max().strftime('%Y-%m-%d'))
col4.metric("📈 日均出货量", f"{df['y'].mean():.0f}")

# ===== 训练 Prophet 模型 =====
st.markdown("---")
st.subheader(f"🤖 正在训练预测模型（未来 {forecast_days} 天）...")

with st.spinner("模型训练中，请稍候..."):
    model = Prophet(
        interval_width=confidence / 100,
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
    )
    model.fit(df)

    future = model.make_future_dataframe(periods=forecast_days)
    forecast = model.predict(future)

st.success("✅ 模型训练完成！")

# ===== 预测结果展示 =====
st.markdown("---")
st.subheader("📈 出货量预测结果")

fig = go.Figure()

# 历史数据
fig.add_trace(go.Scatter(
    x=df['ds'], y=df['y'],
    mode='lines', name='历史出货量',
    line=dict(color='#2E86AB', width=2)
))

# 预测数据
forecast_plot = forecast[forecast['ds'] > df['ds'].max()]
fig.add_trace(go.Scatter(
    x=forecast_plot['ds'], y=forecast_plot['yhat'],
    mode='lines', name='预测出货量',
    line=dict(color='#E53935', width=2, dash='dash')
))

# 置信区间
fig.add_trace(go.Scatter(
    x=pd.concat([forecast_plot['ds'], forecast_plot['ds'][::-1]]),
    y=pd.concat([forecast_plot['yhat_upper'], forecast_plot['yhat_lower'][::-1]]),
    fill='toself', fillcolor='rgba(229, 57, 53, 0.1)',
    line=dict(color='rgba(255,255,255,0)'),
    name=f'{confidence}% 置信区间'
))

fig.update_layout(
    title=f"出货量历史与预测 · {sel_label}",
    xaxis_title="日期",
    yaxis_title="出货量",
    height=500,
    hovermode='x unified'
)

st.plotly_chart(fig, width='stretch')

# ===== 预测数据表 =====
st.markdown("---")
st.subheader("📋 预测数据明细")

forecast_show = forecast_plot[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
forecast_show.columns = ['日期', '预测出货量', '下限', '上限']
forecast_show['预测出货量'] = forecast_show['预测出货量'].round(0).astype(int)
forecast_show['下限'] = forecast_show['下限'].round(0).astype(int)
forecast_show['上限'] = forecast_show['上限'].round(0).astype(int)

st.dataframe(forecast_show, width='stretch', hide_index=True)

# ===== 关键指标 =====
st.markdown("---")
st.subheader("📊 关键预测指标")

total_forecast = forecast_show['预测出货量'].sum()
avg_daily = forecast_show['预测出货量'].mean()
peak_day = forecast_show.loc[forecast_show['预测出货量'].idxmax()]

col1, col2, col3, col4 = st.columns(4)
col1.metric("📦 预测总出货量", f"{total_forecast:.0f}")
col2.metric("📈 日均出货量", f"{avg_daily:.0f}")
col3.metric("🏆 峰值日", peak_day['日期'].strftime('%m-%d'))
col4.metric("📊 峰值出货量", f"{peak_day['预测出货量']:.0f}")

# ===== 成分分析 =====
st.markdown("---")
st.subheader("🔍 趋势成分分解")

fig2 = go.Figure()
components = ['trend', 'weekly', 'yearly']
labels = ['趋势', '周周期', '年周期']

for comp, label in zip(components, labels):
    if comp in forecast.columns:
        fig2.add_trace(go.Scatter(
            x=forecast['ds'], y=forecast[comp],
            mode='lines', name=label
        ))

fig2.update_layout(title="预测成分分解", height=400)
st.plotly_chart(fig2, width='stretch')

# ===== 下载预测结果 =====
csv = forecast_show.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
st.download_button(
    label="📥 下载预测数据 CSV",
    data=csv,
    file_name=f"需求预测_{sel_label}_{datetime.now():%Y%m%d}.csv",
    mime="text/csv"
)

st.caption(f"📊 生成时间：{datetime.now():%Y-%m-%d %H:%M} | 模型：Prophet | 数据来源：{data_source} | 粒度：{sel_label}")
