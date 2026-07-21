# -*- coding: utf-8 -*-
"""
竞品价格监控 · 中免 CDF 适配器（纯 HTTP，无需浏览器） v1.0
==========================================================
实测可用接口（合规、无需登录）：
  GET https://service.cdfhnmall.com/mini/findGoodsList
      ?keyword=<关键词>&pageNum=0&pageSize=10&orderBy=0
      &deviceId=...&channelType=1&version=3.1&...
  响应 data.list[] 每项含：
      goodsId / productName / brandName / brandId / smallImage
      salesPrice(有税参考价) / estimatePrice(预估) / discountPrice / seckillPrice(秒杀价)
      goodsPrice.showPrice(实际展示免税价) + showPriceDesc(促销标签，如「秒杀价」)

  折扣维度：折扣率(免税省%) = (salesPrice − showPrice) / salesPrice，由看板现算。
  注意：公开接口【无销量字段】，故「销量/销售」维度无法提供（合规只抓公开标价）。

价格口径：监控「实际展示免税售价」= goodsPrice.showPrice（与 H5 页面渲染一致）。
匹配口径：
  · 优先取 productName 含 SKU 中文名(name_cn) / 英文名(name_en) / 别名(aliases) 的商品；
  · 品牌兜底时限定「香水」类（productName 含 香水/香型/淡香…），避免误抓同品牌彩妆；
  · 同 goodsId 重复上架时，优先取有价格的条目（中免实测存在 price=None 的无货副本）；
  · 关键词可用 cdf_keyword 覆盖（个别款中免命名差异，如 TF 烟草香草→韵度烟草香型）。
"""

from typing import Optional, Tuple, List, Any, Dict
from utils.price_monitor.adapters.base import ApiBaseAdapter, http_get_json
from utils.price_monitor.config import CATEGORY_HINTS

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

    def _hints(self, sku: dict) -> Tuple[str, ...]:
        """按 SKU 品类返回匹配信号词（香水/彩妆/护肤 各不相同）。"""
        cat = (sku.get("category") or "香水")
        return CATEGORY_HINTS.get(cat, PERFUME_HINTS)

    def match_product(self, items: List[dict], sku: dict) -> Optional[dict]:
        items = self._dedup(items)
        hints = self._hints(sku)
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

        # 2) 品牌兜底，但限定同品类信号词（避免同品牌跨品类误抓，
        #    如迪奥品牌兜底时只认香水/彩妆/护肤 各自品类词）
        brand = (sku.get("brand") or "").lower()
        if brand:
            for it in items:
                pn = (it.get("productName") or "").lower()
                bn = (it.get("brandName") or "").lower()
                if brand in bn or brand in pn:
                    if any(h in pn for h in hints):
                        return it

        # 3) 兜底：首个有价格的同品类条目
        for it in items:
            pn = (it.get("productName") or "").lower()
            if any(h in pn for h in hints) and it.get("_price") is not None:
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

    def extract_meta(self, item: dict) -> Tuple[Optional[float], str]:
        """额外抓出：有税参考价(salesPrice) 与 促销标签(showPriceDesc/秒杀)。
        这两个维度用于看板算「免税省%」并展示促销状态。"""
        sales = item.get("salesPrice")
        sales_price = float(sales) if sales not in (None, 0) else None
        gp = item.get("goodsPrice") or {}
        desc = (gp.get("showPriceDesc") or "").strip()
        promo = desc
        if not promo and item.get("seckillStatus"):
            promo = "秒杀"
        return sales_price, promo

    def run(self, sku: dict, page=None) -> "PriceRecord":
        """重写基类 run：在抽取价格的同时，把有税参考价/促销标签写入记录。"""
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
            sales_price, promo = self.extract_meta(item)
            if price is None:
                rec.status = "not_found"
                rec.note = note or "商品存在但无价格字段"
            else:
                rec.price = price
                rec.product_url = url or ""
                rec.note = note
                rec.sales_price = sales_price
                rec.promo_label = promo
                rec.status = "ok"
        except Exception as e:
            rec.status = "error"
            rec.note = f"{type(e).__name__}: {e}"
        return self._finalize(rec)


def detect_category(product_name: str) -> str:
    """按商品名识别品类（香水/彩妆/护肤/其他），用于品牌货架归类。"""
    pn = (product_name or "").lower()
    for cat, hints in CATEGORY_HINTS.items():
        if any(h.lower() in pn for h in hints):
            return cat
    return "其他"


def search_shelf(keyword: str, category: str = "") -> List[dict]:
    """实时按关键词(品牌名)拉取中免在售商品货架，返回统一结构列表。
    不依赖具体 SKU 清单，用于「品牌货架速览」模式。

    品类偏置：给定 category(香水/彩妆/护肤)时，把品类词并入选词
    （如「迪奥 彩妆」），让中免返回该品类商品；并用更大的 pageSize
    提升覆盖。返回项仍按 detect_category 二次归类，确保列示准确。
    返回项：{name, brand, price, sales_price, promo, category, url, image}
    """
    adapter = CdfApiAdapter({"id": "cdfg", "name": "中免 CDF"}, {}, "")
    kw = f"{keyword} {category}".strip() if category else keyword
    params = adapter.build_params({"keyword": kw})
    params["pageSize"] = "20"
    data = http_get_json(CdfApiAdapter.api_url, params, adapter.request_headers(), timeout=30)
    items = adapter.parse_items(data) or []
    items = adapter._dedup(items)
    out = []
    for it in items:
        price, url, _ = adapter.extract(it, {})
        sales_price, promo = adapter.extract_meta(it)
        out.append({
            "name": it.get("productName"),
            "brand": it.get("brandLinkName") or it.get("brandName"),
            "price": price,
            "sales_price": sales_price,
            "promo": promo,
            "category": detect_category(it.get("productName", "")),
            "url": url,
            "image": it.get("smallImage"),
        })
    if category:
        out = [o for o in out if o["category"] == category]
    return out
