# -*- coding: utf-8 -*-
"""
竞品价格监控 · 中免 CDF 适配器（纯 HTTP，无需浏览器） v1.0
==========================================================
实测可用接口（合规、无需登录）：
  GET https://service.cdfhnmall.com/mini/findGoodsList
      ?keyword=<关键词>&pageNum=0&pageSize=10&orderBy=0
      &deviceId=...&channelType=1&version=3.1&...
  响应 data.list[] 每项含：
      goodsId / productName / brandName
      salesPrice(有税参考) / estimatePrice(预估) / discountPrice
      goodsPrice.showPrice(实际展示免税价) + showPriceDesc

价格口径：监控「实际展示免税售价」= goodsPrice.showPrice（与 H5 页面渲染一致）。
匹配口径：
  · 优先取 productName 含 SKU 中文名(name_cn) / 英文名(name_en) / 别名(aliases) 的商品；
  · 品牌兜底时限定「香水」类（productName 含 香水/香型/淡香…），避免误抓同品牌彩妆；
  · 同 goodsId 重复上架时，优先取有价格的条目（中免实测存在 price=None 的无货副本）；
  · 关键词可用 cdf_keyword 覆盖（个别款中免命名差异，如 TF 烟草香草→韵度烟草香型）。
"""

from typing import Optional, Tuple, List, Any, Dict
from utils.price_monitor.adapters.base import ApiBaseAdapter

SERVICE_HOST = "https://service.cdfhnmall.com"
DETAIL_TMPL = "https://m.cdfhnmall.com/#/duty-paid/sub-packages/products/pages/goods-detail/index?goodsId={goodsId}"

# 品牌兜底时的「香水」类信号词，用于排除同品牌彩妆（眼影/唇膏等）
PERFUME_HINTS = ("香水", "香型", "淡香", "浓香", "香氛", "edp", "edt", "parfum")


class CdfApiAdapter(ApiBaseAdapter):
    api_url = f"{SERVICE_HOST}/mini/findGoodsList"
    DEVICE_ID = "17845996730332423270"

    def build_params(self, sku: dict) -> dict:
        # cdf_keyword 可覆盖默认 keyword（个别款中免命名差异）
        kw = sku.get("cdf_keyword") or sku["keyword"]
        return {
            "keyword": kw,
            "pageNum": "0",
            "pageSize": "10",
            "orderBy": "",
            "selectCategoryIds": "",
            "selectBrandIds": "",
            "deviceId": self.DEVICE_ID,
            "channelType": "1",
            "tabId": "",
            "storeId": "",
            "version": "3.1",
            "tabSwitch": "false",
            "pageFlg": "true",
            "fLabel": "",
            "customizeFilter": "",
            "priceRange": "",
        }

    def parse_items(self, data: Any) -> List[dict]:
        if not isinstance(data, dict):
            return []
        d = data.get("data") or {}
        return d.get("list") or []

    def _dedup(self, items: List[dict]) -> List[dict]:
        """按 goodsId 去重：同一商品多条上架时，优先保留有价格的条目。"""
        seen: Dict[str, dict] = {}
        for it in items:
            gid = str(it.get("goodsId") or it.get("productId") or id(it))
            price = (it.get("goodsPrice") or {}).get("showPrice")
            if gid not in seen or (price is not None and seen[gid].get("_price") is None):
                rec = dict(it)
                rec["_price"] = price
                seen[gid] = rec
        return list(seen.values())

    def match_product(self, items: List[dict], sku: dict) -> Optional[dict]:
        items = self._dedup(items)
        name_cn = (sku.get("name_cn") or "").lower()
        name_en = (sku.get("name_en") or "").lower()
        aliases = [a.lower() for a in (sku.get("aliases") or []) if a]

        # 1) 精确：商品名包含 中文名 / 英文名 / 别名
        for it in items:
            pn = (it.get("productName") or "").lower()
            if name_cn and name_cn in pn:
                return it
            if name_en and name_en in pn:
                return it
            if any(a and a in pn for a in aliases):
                return it

        # 2) 品牌兜底，但限定「香水」类（排除同品牌彩妆眼影/唇膏）
        brand = (sku.get("brand") or "").lower()
        if brand:
            for it in items:
                pn = (it.get("productName") or "").lower()
                bn = (it.get("brandName") or "").lower()
                if brand in bn or brand in pn:
                    if any(h in pn for h in PERFUME_HINTS):
                        return it

        # 3) 兜底：首个有价格的香水条目
        for it in items:
            pn = (it.get("productName") or "").lower()
            if any(h in pn for h in PERFUME_HINTS) and it.get("_price") is not None:
                return it

        # 4) 再不行：返回首个（交由 extract 判定有无价格）
        return items[0] if items else None

    def extract(self, item: dict, sku: dict) -> Tuple[Optional[float], str, str]:
        gp = item.get("goodsPrice") or {}
        show = gp.get("showPrice")
        if show not in (None, 0):
            # 主流口径：实际展示免税价（与 H5 页面渲染一致）
            price = float(show)
            src = f"实际免税价{gp.get('showPriceDesc','') or 'showPrice'}"
        else:
            # 中免部分款搜索列表不返回 showPrice（预售/无促销），退而取有税参考价，
            # 并在备注明确标注，避免被误读成免税价。
            fb = item.get("salesPrice")
            if fb in (None, 0):
                fb = item.get("discountPrice")
            if fb in (None, 0):
                return None, "", "无价格字段(showPrice/salesPrice 均空)"
            price = float(fb)
            src = "免税价未返回·取有税参考salesPrice"

        goods_id = item.get("goodsId") or item.get("productId") or ""
        url = DETAIL_TMPL.format(goodsId=goods_id) if goods_id else ""
        # 备注带齐三个参考价，便于看板区分「实际免税价 / 有税参考 / 预估」
        sales = item.get("salesPrice")
        est = item.get("estimatePrice")
        note = f"{src}={price}"
        if sales is not None:
            note += f"；有税参考{sales}"
        if est is not None:
            note += f"；预估{est}"
        return price, url, note
