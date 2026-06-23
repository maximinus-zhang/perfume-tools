import streamlit as st
import os
from datetime import datetime

st.set_page_config(
    page_title="香水供应链小助手",
    page_icon="\U0001F4E6",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 自动扫描 pages/ 下的模块文件夹
# ============================================================
BASE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(BASE, "pages")

def get_pages_from_folder(folder_path, icon_prefix=""):
    """读取文件夹内所有 .py 文件生成导航页"""
    pages = []
    if not os.path.exists(folder_path):
        return pages
    for f in sorted(os.listdir(folder_path)):
        if f.endswith(".py") and f != "__init__.py":
            filepath = os.path.join(folder_path, f)
            # 用文件名去掉数字前缀和 .py 作为标题
            title = f.replace(".py", "")
            # 去掉开头的数字和下划线
            title_parts = title.split("_", 1)
            if len(title_parts) > 1 and title_parts[0].isdigit():
                title = title_parts[1]
            pages.append(st.Page(filepath, title=title))
    return pages

# 加载各模块页面
sell_out_pages = get_pages_from_folder(os.path.join(PAGES, "sell_out"))
sell_in_pages = get_pages_from_folder(os.path.join(PAGES, "sell_in"))
logistics_pages = get_pages_from_folder(os.path.join(PAGES, "logistics"))

# ============================================================
# 导航
# ============================================================
pg = st.navigation({
    "\U0001F3EA Sell Out 销售端": sell_out_pages,
    "\U0001F4E6 Sell In 采购端":   sell_in_pages,
    "\U0001F69A 物流模块":         logistics_pages,
})

st.sidebar.title("\U0001F9ED 功能导航")
st.sidebar.markdown("---")
st.sidebar.caption(f"TR 供应链管理系统 v2.0\n{datetime.now().strftime('%Y-%m-%d')}")

pg.run()
