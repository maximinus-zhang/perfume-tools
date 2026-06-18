import streamlit as st

st.set_page_config(
    page_title="香水供应链小助手",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("🧭 功能导航")
st.sidebar.markdown("---")

st.title("📦 香水供应链自动化工具")
st.markdown("欢迎使用！请从左侧导航选择具体功能。")
st.info("💡 所有文件处理均在本地完成，数据不上传云端。")

# 显示版本与提示
st.caption("v1.0 | 由 Python + Streamlit 驱动")
