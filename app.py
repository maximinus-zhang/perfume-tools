import streamlit as st
from datetime import datetime
from utils.nav_meta import NAV

st.set_page_config(
    page_title="香水供应链小助手",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 由 utils/nav_meta.py 的 NAV 统一生成各模块页面（单一数据源）
nav = {}
for group, pages in NAV.items():
    nav[group] = [
        st.Page(p["path"], title=p["title"], icon=p["icon"]) for p in pages
    ]

pg = st.navigation(nav)

st.sidebar.title("🧭 功能导航")
st.sidebar.markdown("---")
st.sidebar.caption(f"TR 供应链管理系统 v2.0\n{datetime.now().strftime('%Y-%m-%d')}")

pg.run()
