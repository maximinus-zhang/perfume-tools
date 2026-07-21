import streamlit as st
from datetime import datetime
from utils.nav_meta import NAV

# 防御：st.navigation 需要 Streamlit >= 1.36，版本过低时明确提示，避免静默失效
if not hasattr(st, "navigation"):
    st.error(
        "⚠️ 当前 Streamlit 版本过低，不支持侧边栏导航（st.navigation 需要 >= 1.36）。\n\n"
        "请在命令行（已激活 venv）执行：\n"
        "    pip install --upgrade streamlit\n"
        "然后重新启动本应用。"
    )
    st.stop()

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
