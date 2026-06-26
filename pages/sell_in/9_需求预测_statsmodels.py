import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import warnings
warnings.filterwarnings('ignore')
from utils.oss_helper import upload_section, read_excel_from_oss

st.title("📊 香水供应链·需求预测（statsmodels）")

# ===== 上传区域 =====
with st.sidebar:
    st.markdown("---")
    upload_section("sell_in/sales_history.xlsx", "上传历史销售数据")

# ===== 读取数据 =====
df_oss = pd.DataFrame()
has_data = False
try:
    df_oss = read_excel_from_oss("sell_in/sales_history.xlsx", sheet_name=0, prefix_filter=None)
    has_data = not df_oss.empty
except:
    pass

st.markdown("---")

# ===== 参数设置 =====
col1, col2, col3 = st.columns(3)
with col1:
    forecast_days = st.number_input("预测天数", min_value=7, max_value=365, value=30, step=7, key='sm_forecast_days')
with col2:
    model_order = st.selectbox("模型阶数", ["自动(推荐)", "ARIMA(1,1,1)", "ARIMA(2,1,2)", "ARIMA(1,1,2)", "ARIMA(2,1,1)"], index=0)
with col3:
    confidence = st.slider("置信区间", 50, 99, 80, 5, key='sm_confidence')

# ===== 加载数据 =====
if has_data:
    df_oss.columns = [c.strip() for c in df_oss.columns]
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
        st.error("数据缺少日期列或销量列")
        st.stop()
else:
    st.info("📊 暂无上传数据，使用示例数据")
    np.random.seed(42)
    dates = pd.date_range(start='2025-01-01', end='2026-06-25', freq='D')
    trend = np.linspace(50, 80, len(dates))
    season = 15 * np.sin(2 * np.pi * np.arange(len(dates)) / 365)
    noise = np.random.normal(0, 8, len(dates))
    sales = trend + season + noise
    df = pd.DataFrame({'ds': dates, 'y': np.maximum(sales, 5)})
    st.info(f"使用模拟数据：{len(df)} 条")

# ===== KPI =====
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
col1.metric("📊 历史数据总量", f"{len(df)} 条")
col2.metric("📅 起始日期", df['ds'].min().strftime('%Y-%m-%d'))
col3.metric("📅 结束日期", df['ds'].max().strftime('%Y-%m-%d'))
col4.metric("📈 日均销量", f"{df['y'].mean():.0f}")

# ===== 训练模型 =====
st.markdown("---")
st.subheader(f"🤖 正在训练 SARIMA 模型（未来 {forecast_days} 天）...")

with st.spinner("模型训练中，请稍候..."):
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX
        from statsmodels.tsa.seasonal import seasonal_decompose
        
        # 准备时间序列数据
        ts_data = df.set_index('ds')['y'].asfreq('D')
        ts_data = ts_data.fillna(method='ffill')
        
        # 确定模型阶数
        if model_order == "自动(推荐)":
            # 简单尝试几个常见参数，选AIC最小的
            best_aic = float('inf')
            best_order = (1, 1, 1)
            best_seasonal_order = (1, 1, 1, 7)
            for p in range(0, 3):
                for d in range(0, 2):
                    for q in range(0, 3):
                        try:
                            model = SARIMAX(ts_data, order=(p, d, q), seasonal_order=(1, 1, 1, 7),
                                           enforce_stationarity=False, enforce_invertibility=False)
                            results = model.fit(disp=False, maxiter=200)
                            if results.aic < best_aic:
                                best_aic = results.aic
                                best_order = (p, d, q)
                        except:
                            pass
            order = best_order
            seasonal_order = (1, 1, 1, 7)
        else:
            # 手动选择
            order_map = {
                "ARIMA(1,1,1)": (1, 1, 1),
                "ARIMA(2,1,2)": (2, 1, 2),
                "ARIMA(1,1,2)": (1, 1, 2),
                "ARIMA(2,1,1)": (2, 1, 1),
            }
            order = order_map.get(model_order, (1, 1, 1))
            seasonal_order = (1, 1, 1, 7)
        
        # 训练最终模型
        model = SARIMAX(ts_data, order=order, seasonal_order=seasonal_order,
                       enforce_stationarity=False, enforce_invertibility=False)
        results = model.fit(disp=False, maxiter=200)
        
        # 预测
        forecast_result = results.get_forecast(steps=forecast_days)
        forecast_mean = forecast_result.predicted_mean
        forecast_ci = forecast_result.conf_int(alpha=1-confidence/100)
        
        st.success(f"✅ 模型训练完成！使用 SARIMA{order}×{seasonal_order}")
        st.caption(f"AIC: {results.aic:.1f} | BIC: {results.bic:.1f}")
        
    except Exception as e:
        st.error(f"模型训练失败：{e}")
        st.info("提示：如果一直失败，可以尝试安装完整依赖：pip install statsmodels")
        st.stop()

# ===== 预测结果展示 =====
st.markdown("---")
st.subheader("📈 销量预测结果")

fig = go.Figure()

# 历史数据
fig.add_trace(go.Scatter(
    x=df['ds'], y=df['y'],
    mode='lines', name='历史销量',
    line=dict(color='#2E86AB', width=2)
))

# 预测数据
future_dates = pd.date_range(start=df['ds'].max() + timedelta(days=1), periods=forecast_days, freq='D')
fig.add_trace(go.Scatter(
    x=future_dates, y=forecast_mean.values,
    mode='lines', name='预测销量',
    line=dict(color='#E53935', width=2, dash='dash')
))

# 置信区间
fig.add_trace(go.Scatter(
    x=pd.concat([pd.Series(future_dates), pd.Series(future_dates)[::-1]]),
    y=pd.concat([pd.Series(forecast_ci.iloc[:, 1].values), pd.Series(forecast_ci.iloc[:, 0].values)[::-1]]),
    fill='toself', fillcolor='rgba(229, 57, 53, 0.1)',
    line=dict(color='rgba(255,255,255,0)'),
    name=f'{confidence}% 置信区间'
))

fig.update_layout(title="销量历史与预测（statsmodels SARIMA）", xaxis_title="日期", yaxis_title="销量", height=500, hovermode='x unified')
st.plotly_chart(fig, use_container_width=True)

# ===== 预测数据表 =====
st.markdown("---")
st.subheader("📋 预测数据明细")

forecast_show = pd.DataFrame({
    '日期': future_dates,
    '预测销量': forecast_mean.values.round(0).astype(int),
    '下限': forecast_ci.iloc[:, 0].values.round(0).astype(int),
    '上限': forecast_ci.iloc[:, 1].values.round(0).astype(int),
})

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

# ===== 残差分析 =====
st.markdown("---")
st.subheader("🔍 模型诊断")

residuals = results.resid
fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=residuals.index, y=residuals.values, mode='lines', name='残差'))
fig2.update_layout(title="残差分布（应随机分布）", height=300)
st.plotly_chart(fig2, use_container_width=True)

# ===== 下载 =====
csv = forecast_show.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
st.download_button(label="📥 下载预测数据 CSV", data=csv,
                   file_name=f"需求预测_statsmodels_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")

st.caption(f"📊 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 模型：SARIMA")
