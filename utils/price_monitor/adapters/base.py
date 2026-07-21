# -*- coding: utf-8 -*-
"""
竞品价格监控 · 适配器基类 v1.0
==============================
所有零售商的抓取适配器都继承 BaseAdapter。

设计要点
--------
· 模板方法 run() 统一流程：导航搜索 → 检测登录墙 → 提取价格 → 组装 PriceRecord。
· 共用逻辑（限速、随机 UA、超时、来源标签、合规拦截）只在基类写一次。
· 子类只需实现三个钩子：
    navigate_search(page, sku) : 打开该商城的搜索结果页
    is_login_wall(page)        : 判断是否命中登录墙（合规红线）
    extract_price(page, sku)   : 从渲染后的 DOM 读价格，返回 (price, url, note)
· Playwright 采用「懒加载导入」：模块可被页面防御性导入，
  只有真正跑抓取时才要求 playwright 已安装（部署在阿里云轻量服务器上装 chromium）。
"""

from typing import Optional, Tuple, Dict, List, Any
from utils.price_monitor.models import PriceRecord, now_iso


def http_get_json(url: str, params: Dict[str, Any], headers: Dict[str, str], timeout: int = 30) -> Any:
    """纯标准库 HTTP GET → 解析 JSON（不依赖 requests，cron 服务器零额外依赖）。

    合规护栏：仅发 GET 到公开搜索接口，绝不带登录态 token（中免实测 token 为空即可）。
    """
    import json
    import urllib.parse
    import urllib.request
    full = url + "?" + urllib.parse.urlencode(params) if params else url
    req = urllib.request.Request(full, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

# 随机 UA 池（移动端为主，贴近真实 H5 访问）
USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
]


def random_ua() -> str:
    import random
    return random.choice(USER_AGENTS)


class BaseAdapter:
    """适配器基类：子类实现三个钩子即可。"""

    ENGINE = "playwright"  # 子类覆盖为 "api" 表示纯 HTTP 接口适配器（无需浏览器）

    def __init__(self, cfg: dict, guardrails: dict, source_label: str = ""):
        self.cfg = cfg
        self.g = guardrails
        self.source_label = source_label or f"{cfg.get('name', '未知')}官网公开标价"

    # ----------------------------------------------------------
    # 基类默认实现（可被子类覆盖）
    # ----------------------------------------------------------
    def navigate_search(self, page, sku: dict) -> None:
        """默认行为：直接跳转 search_url 模板（{kw}=关键词）。
        若商城需要「先点搜索框再输入」，请在子类中覆盖。"""
        url = self.cfg.get("search_url")
        if not url:
            raise NotImplementedError(f"{self.cfg['id']} 未配置 search_url，需在子适配器覆盖 navigate_search")
        kw = sku["keyword"]
        page.goto(url.format(kw=kw), wait_until="networkidle", timeout=self.g["timeout_seconds"] * 1000)

    def is_login_wall(self, page) -> bool:
        """默认：未识别登录墙。子类覆盖以实现具体判定（如检测到「登录/注册」遮罩）。"""
        return False

    def extract_price(self, page, sku: dict) -> Tuple[Optional[float], str, str]:
        """子类必须实现：返回 (价格, 商品URL, 备注)。价格抓不到返回 (None, '', note)。"""
        raise NotImplementedError(f"{self.cfg['id']} 适配器未实现 extract_price")

    # ----------------------------------------------------------
    # 模板方法：子类通常无需改动
    # ----------------------------------------------------------
    def run(self, sku: dict, page) -> PriceRecord:
        rec = self._blank_record(sku)
        try:
            self.navigate_search(page, sku)

            if self.g.get("respect_login_wall", True) and self.is_login_wall(page):
                rec.status = "blocked_login"
                rec.note = "命中登录墙，合规拦截（未抓取任何会员/登录专属价）"
                return self._finalize(rec)

            price, url, note = self.extract_price(page, sku)
            if price is None:
                rec.status = "not_found"
                rec.note = note or "搜索无结果 / 未提取到价格"
            else:
                rec.price = price
                rec.product_url = url
                rec.note = note
                rec.status = "ok"
        except Exception as e:  # 单次失败由 fetcher 统一重试
            rec.status = "error"
            rec.note = f"{type(e).__name__}: {e}"
        return self._finalize(rec)

    # ----------------------------------------------------------
    # 内部助手
    # ----------------------------------------------------------
    def _blank_record(self, sku: dict) -> PriceRecord:
        return PriceRecord(
            retailer_id=self.cfg["id"],
            retailer_name=self.cfg["name"],
            sku_id=sku["id"],
            brand=sku["brand"],
            name_cn=sku["name_cn"],
            name_en=sku["name_en"],
            size_ml=sku["size_ml"],
            category=sku.get("category", "香水"),
            source=self.source_label,
        )

    def _finalize(self, rec: PriceRecord) -> PriceRecord:
        rec.captured_at = now_iso()
        return rec

    @staticmethod
    def parse_price(text: str) -> Optional[float]:
        """从一段文本里抠出价格数字（支持 ¥ / ￥ / 逗号千分位）。"""
        if not text:
            return None
        import re
        m = re.search(r"[¥￥]?\s*([\d,]{2,}(?:\.\d{1,2})?)", text)
        if not m:
            return None
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None


class ApiBaseAdapter(BaseAdapter):
    """纯 HTTP 接口适配器基类（无需浏览器）。

    子类只需实现：
        api_url        : 搜索接口完整 URL
        build_params(sku)   : 构造查询参数
        parse_items(json)   : 从响应取出商品列表
        match_product(items, sku) -> (item|None)
        extract(item, sku)  : 返回 (price, product_url, note)
    基类 run() 统一处理 HTTP 调用 / 重试兜底 / 组装记录。
    """

    ENGINE = "api"

    def run(self, sku: dict, page=None) -> PriceRecord:
        rec = self._blank_record(sku)
        try:
            params = self.build_params(sku)
            headers = self.request_headers()
            data = http_get_json(self.api_url, params, headers, timeout=self.g["timeout_seconds"])
            items = self.parse_items(data) or []
            item = self.match_product(items, sku)
            if not item:
                rec.status = "not_found"
                rec.note = "搜索无匹配商品"
                return self._finalize(rec)
            price, url, note = self.extract(item, sku)
            if price is None:
                rec.status = "not_found"
                rec.note = note or "商品存在但无价格字段"
            else:
                rec.price = price
                rec.product_url = url or ""
                rec.note = note
                rec.status = "ok"
        except Exception as e:  # 单次失败由 fetcher 统一重试
            rec.status = "error"
            rec.note = f"{type(e).__name__}: {e}"
        return self._finalize(rec)

    # 子类可覆盖
    def request_headers(self) -> dict:
        return {
            "User-Agent": random_ua(),
            "appversion": "10.12.60",
            "channel": "big_frontend_h5",
            "token": "",
            "os": "h5",
            "Content-Type": "application/json",
        }

    def build_params(self, sku: dict) -> dict:  # pragma: no cover - 子类实现
        raise NotImplementedError

    def parse_items(self, data: Any) -> List[dict]:  # pragma: no cover - 子类实现
        raise NotImplementedError

    def match_product(self, items: List[dict], sku: dict) -> Optional[dict]:  # pragma: no cover
        raise NotImplementedError

    def extract(self, item: dict, sku: dict) -> Tuple[Optional[float], str, str]:  # pragma: no cover
        raise NotImplementedError
