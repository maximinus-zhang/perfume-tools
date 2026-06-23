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
    st.Page("pages/sell_out/11_销售看板.py",        title="销售看板",        icon="📊"),
    st.Page("pages/sell_out/6_海南免税市场分析.py",  title="海南免税市场分析", icon="🏝️"),
    st.Page("pages/sell_out/7_门店地图分析.py",      title="门店地图分析",    icon="🗺️"),
    st.Page("pages/sell_out/10_库存预警.py",         title="库存预警",        icon="⚠️"),
]

# ============================================================
# 📦 Sell In 模块
# ============================================================
sell_in = [
    st.Page("pages/sell_in/22_采购看板.py",    title="采购看板",   icon="📋"),
    st.Page("pages/sell_in/4_满足率分析.py",   title="满足率分析", icon="✅"),
    st.Page("pages/sell_in/5_报表汇总.py",     title="报表汇总",   icon="📊"),
]

# ============================================================
# 🚚 物流模块
# ============================================================
logistics = [
    st.Page("pages/logistics/33_物流看板.py",  title="物流看板",   icon="🚚"),
    st.Page("pages/logistics/9_订单管理.py",   title="订单管理",   icon="📦"),
]

# ============================================================
# 导航
# ============================================================
pg = st.navigation({
    "🏪 Sell Out 销售端": sell_out,
    "📦 Sell In 采购端":   sell_in,
    "🚚 物流模块":         logistics,
})

st.sidebar.title("🧭 功能导航")
st.sidebar.markdown("---")
st.sidebar.caption(f"TR 供应链管理系统 v2.0\n{datetime.now().strftime('%Y-%m-%d')}")

pg.run()
