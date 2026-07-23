# -*- coding: utf-8 -*-
"""
模块导航的「单一数据源」。
app.py 用它生成侧边栏导航；销售看板的「模块快捷入口」也用它自动生成卡片。
以后新增/改名/调整顺序，只需改这里，两处自动同步。
每个页面：path=文件相对路径, title=显示名, icon=图标
"""
NAV = {
    "🏪 Sell Out 销售端": [
        {"path": "pages/sell_out/7_门店地图分析.py",          "title": "门店地图分析",     "icon": "🗺️"},
        {"path": "pages/sell_out/8_全国免税商情监控.py",      "title": "全国免税商情监控", "icon": "📡"},
        {"path": "pages/sell_out/12_商情监控看板.py",         "title": "海南免税商情监控看板", "icon": "📈"},
        {"path": "pages/sell_out/13_竞品价格监控.py",         "title": "竞品价格监控",       "icon": "🛒"},
        {"path": "pages/sell_out/14_品牌表现分析.py",         "title": "品牌表现分析", "icon": "🔒"},
    ],
    "📦 Sell In 采购端": [
        {"path": "pages/sell_in/1_order_fulfillment_analysis.py", "title": "订单满足率分析", "icon": "✅"},
        {"path": "pages/sell_in/8_合同审查工具.py",           "title": "合同审查工具",     "icon": "📄"},
        {"path": "pages/sell_in/7_需求预测.py",               "title": "需求预测",         "icon": "📈"},
        {"path": "pages/sell_in/2_发货明细生成工具.py",       "title": "发货明细生成工具", "icon": "📊"},
        {"path": "pages/sell_in/15_sell_in_深度分析.py",      "title": "SELL IN 深度分析", "icon": "🔒"},
        {"path": "pages/sell_in/16_采购深度分析.py",          "title": "采购深度分析", "icon": "🔒"},
    ],
    "🚚 物流模块": [
        {"path": "pages/logistics/34_物流跟踪.py",            "title": "发货物流跟踪",     "icon": "📍"},
    ],
    "🎯 新品上市规划": [
        {"path": "pages/marketing/35_新品上市规划.py",        "title": "新品上市规划", "icon": "🔒"},
    ],
}
