# -*- coding: utf-8 -*-
"""
竞品价格监控 · 通用 H5 适配器 v1.0
==================================
先用「通用」实现打通整条链路：中免 / 海旅 这种标准 uniapp H5 商城可直接验证抓取。
海控 / 中服 等 B 档商城在 #10 阶段会拆出各自的精调子类（精确选择器 + 自定义导航），
届时替换 ADAPTER_REGISTRY 中的映射即可，无需改动 fetcher。

通用策略
--------
· navigate_search : 直接跳转 search_url 模板（已在 config 配置）
· is_login_wall   : 页面文本出现「登录 / 注册 / 微信登录 / 请先登录」即判为登录墙
· extract_price  : 抓搜索结果区文本，抠第一个 ¥ 价格（粗匹配，#10 按商城收紧）
"""

from utils.price_monitor.adapters.base import BaseAdapter


class GenericH5Adapter(BaseAdapter):
    """通用 H5 商城适配器（中免 / 海旅 可直接用，其余待 #10 精调）。"""

    LOGIN_HINTS = ["请登录", "微信登录", "立即登录", "登录/注册", "登录后查看", "会员登录"]

    def is_login_wall(self, page) -> bool:
        try:
            text = (page.inner_text("body") or "")[:500]
        except Exception:
            return False
        return any(h in text for h in self.LOGIN_HINTS)

    def extract_price(self, page, sku: dict):
        # 优先在常见结果容器里找价格文本
        containers = ["//div[contains(@class,'goods')]",
                      "//div[contains(@class,'product')]",
                      "//li[contains(@class,'item')]",
                      "body"]
        price = None
        url = page.url
        note = ""
        for sel in containers:
            try:
                if sel == "body":
                    txt = page.inner_text("body") or ""
                else:
                    node = page.query_selector(sel)
                    if not node:
                        continue
                    txt = node.inner_text() or ""
                price = self.parse_price(txt)
                if price:
                    note = "通用提取（首个 ¥ 价格，待 #10 按商城收紧选择器）"
                    break
            except Exception:
                continue
        if price is None:
            note = "通用提取未命中价格（#10 需为该商城定制选择器）"
        return price, url, note
