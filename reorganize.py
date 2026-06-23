"""
一键重组 pages 目录为模块化结构
运行: python reorganize.py
"""
import os
import shutil
import re

# 项目根目录
BASE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(BASE, "pages")

# ============================================================
# 配置：每个模块对应的文件
# ============================================================
MODULES = {
    "sell_out": {
        "title": "Sell Out 销售端",
        "files": [
            "11_销售看板.py",
            "6_海南免税市场分析.py",
            "7_门店地图分析.py",
            "10_库存预警.py",
        ]
    },
    "sell_in": {
        "title": "Sell In 采购端",
        "files": [
            "22_采购看板.py",
            "4_满足率分析.py",
            "5_报表汇总.py",
        ]
    },
    "logistics": {
        "title": "物流模块",
        "files": [
            "33_物流看板.py",
            "9_订单管理.py",
        ]
    }
}

def main():
    print("=" * 50)
    print("📦 开始重组 pages 目录...")
    print("=" * 50)

    # 1. 创建模块文件夹
    for module in MODULES:
        folder = os.path.join(PAGES, module)
        os.makedirs(folder, exist_ok=True)
        # 创建 __init__.py
        init_file = os.path.join(folder, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("")
            print(f"📁 创建: pages/{module}/__init__.py")

    # 2. 移动文件到对应模块
    moved_files = []
    for module, config in MODULES.items():
        for filename in config["files"]:
            src = os.path.join(PAGES, filename)
            dst = os.path.join(PAGES, module, filename)
            if os.path.exists(src):
                # 读取并修改文件：移除 st.set_page_config
                with open(src, "r", encoding="utf-8") as f:
                    content = f.read()
                # 移除 st.set_page_config(...) 行
                content = re.sub(
                    r'st\.set_page_config\([^)]*\)\s*\n?',
                    '',
                    content
                )
                # 写回目标位置
                with open(dst, "w", encoding="utf-8") as f:
                    f.write(content)
                # 删除原文件
                os.remove(src)
                moved_files.append(f"{filename} → {module}/")
                print(f"✅ 移动: {filename} → pages/{module}/")
            else:
                print(f"⚠️ 未找到: {filename}")

    # 3. 生成新的 app.py
    new_app = '''import streamlit as st
import os
from datetime import datetime

st.set_page_config(
    page_title="香水供应链小助手",
    page_icon="\\U0001F4E6",
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
    "\\U0001F3EA Sell Out 销售端": sell_out_pages,
    "\\U0001F4E6 Sell In 采购端":   sell_in_pages,
    "\\U0001F69A 物流模块":         logistics_pages,
})

st.sidebar.title("\\U0001F9ED 功能导航")
st.sidebar.markdown("---")
st.sidebar.caption(f"TR 供应链管理系统 v2.0\\n{datetime.now().strftime('%Y-%m-%d')}")

pg.run()
'''

    with open(os.path.join(BASE, "app.py"), "w", encoding="utf-8") as f:
        f.write(new_app)
    print("\n✅ app.py 已更新（自动扫描模式）")

    # 4. 删除遗留的旧文件（不在任何模块中的 .py 文件）
    for f in os.listdir(PAGES):
        fpath = os.path.join(PAGES, f)
        if f.endswith(".py") and f != "__init__.py":
            # 检查是否在任一模块中
            found = False
            for config in MODULES.values():
                if f in config["files"]:
                    found = True
                    break
            if not found:
                os.remove(fpath)
                print(f"🗑️ 删除旧文件: {f}")

    print("\n" + "=" * 50)
    print("🎉 重组完成！")
    print("=" * 50)
    print("\n📋 后续操作：")
    print("  1. 运行: streamlit run app.py")
    print("  2. 新增页面直接丢进对应模块文件夹")
    print("     eg. pages/sell_out/5_新功能.py")
    print("     重启后自动出现在导航中！")

if __name__ == "__main__":
    main()
