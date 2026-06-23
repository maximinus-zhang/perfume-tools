# app.py - 新版导航中枢
import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="香水供应链小助手",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 🏪 Sell Out 模块
# ============================================================
sell_out = [
    st.Page("pages/1_销售看板.py",           title="销售看板",           icon="📊"),
    st.Page("pages/6_海南免税市场分析.py",    title="海南免税市场分析",    icon="🏝️"),
    st.Page("pages/6_门店地图与品牌覆盖.py",  title="门店地图与品牌覆盖",  icon="🗺️"),
    st.Page("pages/10_库存预警.py",           title="库存预警",           icon="⚠️"),
]

# ============================================================
# 📦 Sell In 模块
# ============================================================
sell_in = [
    st.Page("pages/2_采购看板.py",           title="采购看板",   icon="📋"),
    st.Page("pages/3_满足率分析.py",          title="满足率分析", icon="✅"),
]

# ============================================================
# 🚚 物流模块
# ============================================================
logistics = [
    st.Page("pages/4_物流看板.py",           title="物流看板",   icon="🚚"),
    st.Page("pages/9_订单管理.py",            title="订单管理",   icon="📦"),
]

# ============================================================
# 导航设置
# ============================================================
pg = st.navigation({
    "🏪 Sell Out 销售端": sell_out,
    "📦 Sell In 采购端":   sell_in,
    "🚚 物流模块":         logistics,
})

st.logo("🧴", size="large")

with st.sidebar:
    st.markdown("---")
    st.caption(f"📊 TR 供应链管理系统 v2.0\n{datetime.now().strftime('%Y-%m-%d')}")

pg.run()
