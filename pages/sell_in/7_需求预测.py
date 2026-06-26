import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from prophet import Prophet
from utils.oss_helper import upload_section, read_excel_from_oss

st.title("📈 香水供应链·需求预测")

# ===== 上传区域 =====
with st.sidebar:
    st.markdown("---")
    upload_section("sell_in/sales_history.xlsx", "上传历史销售数据")

# ===== 读取数据 =====
df_oss = read_excel_from_oss("sell_in/sales_history.xlsx", sheet_name=0, prefix_filter=None)
has_data = not df_oss.empty

st.markdown("---")

# ===== 参数设置 =====
col1, col2, col3 = st.columns(3)
with col1:
    forecast_days = st.number_input("预测天数", min_value=7, max_value=365, value=30, step=7)
with col2:
    seasonality = st.selectbox("季节性周期", ["自动检测", "每周", "每月", "每年"], index=0)
with col3:
    confidence = st.slider("置信区间", 50, 99, 80, 5)

# ===== 生成或加载数据 =====
if has_data:
    # 使用上传的数据
    df_oss.columns = [c.strip() for c in df_oss.columns]
    
    # 找日期列和销量列
    date_col = None
    sales_col = None
    for col in df_oss.columns:
        if any(kw in col for kw in ['日期', '时间', 'date', 'ds']):
            date_col = col
        if any(kw in col for kw in ['销量', '销售', '数量', 'sales', 'y']):
            sales_col = col
    
    if date_col and sales_col:
        df = df_oss[[date_col, sales_col]].copy()
        df.columns = ['ds', 'y']
        df['ds'] = pd.to_datetime(df['ds'], errors='coerce')
        df['y'] = pd.to_numeric(df['y'], errors='coerce')
        df = df.dropna()
        st.success(f"✅ 已加载销售数据，共 {len(df)} 条记录")
    else:
        st.error("数据缺少日期列或销量列，请检查模板格式")
        st.stop()
else:
    # 使用示例数据
    st.info("📊 暂无上传数据，使用示例数据")
    np.random.seed(42)
    dates = pd.date_range(start='2025-01-01', end='2026-06-25', freq='D')
    trend = np.linspace(50, 80, len(dates))
    season = 15 * np.sin(2 * np.pi * np.arange(len(dates)) / 365)
    noise = np.random.normal(0, 8, len(dates))
    sales = trend + season + noise
    df = pd.DataFrame({'ds': dates, 'y': np.maximum(sales, 5)})
    
    # 加一些节假日效应（春节、国庆）
    holiday_dates = ['2025-01-28', '2025-01-29', '2025-01-30', '2025-10-01', '2025-10-02', '2025-10-03']
    for hd in holiday_dates:
        idx = df[df['ds'] == hd].index
        if len(idx) > 0:
            df.loc[idx, 'y'] *= 1.3
    
    st.info(f"使用模拟数据：{len(df)} 条，{df['ds'].min().date()} ~ {df['ds'].max().date()}")

# ===== KPI =====
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
col1.metric("📊 历史数据总量", f"{len(df)} 条")
col2.metric("📅 起始日期", df['ds'].min().strftime('%Y-%m-%d'))
col3.metric("📅 结束日期", df['ds'].max().strftime('%Y-%m-%d'))
col4.metric("📈 日均销量", f"{df['y'].mean():.0f}")

# ===== 训练 Prophet 模型 =====
st.markdown("---")
st.subheader(f"🤖 正在训练预测模型（未来 {forecast_days} 天）...")

with st.spinner("模型训练中，请稍候..."):
    # 配置模型
    model = Prophet(
        interval_width=confidence / 100,
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
    )
    
    # 添加节假日（可选）
    # 节假日数据可以自定义
    
    model.fit(df)
    
    # 预测
    future = model.make_future_dataframe(periods=forecast_days)
    forecast = model.predict(future)

st.success("✅ 模型训练完成！")

# ===== 预测结果展示 =====
st.markdown("---")
st.subheader("📈 销量预测结果")

# 历史+预测图
fig = go.Figure()

# 历史数据
fig.add_trace(go.Scatter(
    x=df['ds'], y=df['y'],
    mode='lines', name='历史销量',
    line=dict(color='#2E86AB', width=2)
))

# 预测数据
forecast_plot = forecast[forecast['ds'] > df['ds'].max()]
fig.add_trace(go.Scatter(
    x=forecast_plot['ds'], y=forecast_plot['yhat'],
    mode='lines', name='预测销量',
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
    title="销量历史与预测",
    xaxis_title="日期",
    yaxis_title="销量",
    height=500,
    hovermode='x unified'
)

st.plotly_chart(fig, use_container_width=True)

# ===== 预测数据表 =====
st.markdown("---")
st.subheader("📋 预测数据明细")

forecast_show = forecast_plot[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
forecast_show.columns = ['日期', '预测销量', '下限', '上限']
forecast_show['预测销量'] = forecast_show['预测销量'].round(0).astype(int)
forecast_show['下限'] = forecast_show['下限'].round(0).astype(int)
forecast_show['上限'] = forecast_show['上限'].round(0).astype(int)

st.dataframe(forecast_show, use_container_width=True, hide_index=True)

# ===== 关键指标 =====
st.markdown("---")
st.subheader("📊 关键预测指标")

total_forecast = forecast_show['预测销量'].sum()
avg_daily = forecast_show['预测销量'].mean()
peak_day = forecast_show.loc[forecast_show['预测销量'].idxmax()]

col1, col2, col3, col4 = st.columns(4)
col1.metric("📦 预测总销量", f"{total_forecast:.0f}")
col2.metric("📈 日均销量", f"{avg_daily:.0f}")
col3.metric("🏆 峰值日", peak_day['日期'].strftime('%m-%d'))
col4.metric("📊 峰值销量", f"{peak_day['预测销量']:.0f}")

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
st.plotly_chart(fig2, use_container_width=True)

# ===== 下载预测结果 =====
csv = forecast_show.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
st.download_button(
    label="📥 下载预测数据 CSV",
    data=csv,
    file_name=f"需求预测_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv"
)

st.caption(f"📊 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 模型：Prophet")
