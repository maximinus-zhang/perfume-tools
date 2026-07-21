# -*- coding: utf-8 -*-
"""
竞品价格监控 · 数据模型 v1.0
============================
PriceRecord : 单条「某零售商 × 某 SKU」的价格观测。
  价格永远是「实测公开标价」，is_estimate 固定为 False（与商情看板的估算数据严格区分）。
  status 取值：
    'ok'            - 成功抓到公开标价
    'not_found'     - 该商城未上架 / 搜索无结果
    'blocked_login' - 命中登录墙（合规拦截，跳过）
    'error'         - 技术异常（超时 / 渲染失败），受重试上限约束
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional


@dataclass
class PriceRecord:
    retailer_id: str
    retailer_name: str
    sku_id: str
    brand: str
    name_cn: str
    name_en: str
    size_ml: str
    price: Optional[float] = None          # 公开标价（CNY）；未抓到为 None
    sales_price: Optional[float] = None     # 有税参考价（专柜/含税价），用于算「免税省%」
    promo_label: str = ""                   # 促销标签（秒杀价 / 促销 等）
    currency: str = "CNY"
    product_url: str = ""                   # 商品/搜索页 URL（来源可追溯）
    captured_at: str = ""                   # 抓取时间 ISO 8601
    source: str = ""                        # 来源标签，如「中免CDF官网公开标价」
    status: str = "ok"                      # ok | not_found | blocked_login | error
    note: str = ""
    is_estimate: bool = False               # 占位：价格恒为实测，固定 False
    category: str = "香水"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PriceRecord":
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        # CSV DictReader 全部返回 str；对数值 / 布尔字段做类型强转
        raw = known.get("price")
        if raw is not None:
            known["price"] = float(raw) if raw != "" else None
        raw_sales = known.get("sales_price")
        if raw_sales is not None:
            known["sales_price"] = float(raw_sales) if raw_sales != "" else None
        raw_est = known.get("is_estimate")
        if isinstance(raw_est, str):
            known["is_estimate"] = raw_est.lower() in ("true", "1")
        return cls(**known)

    @property
    def discount_rate(self) -> Optional[float]:
        """免税省% = (有税参考价 − 实际免税价) / 有税参考价；缺字段返回 None。"""
        if self.sales_price and self.price and self.sales_price > 0:
            return (self.sales_price - self.price) / self.sales_price
        return None

    @property
    def ok(self) -> bool:
        return self.status == "ok" and self.price is not None


# CSV 表头顺序（看板 / 下载统一使用）
CSV_COLUMNS = [
    "captured_at", "retailer_id", "retailer_name", "sku_id", "brand",
    "name_cn", "name_en", "size_ml", "category", "price", "sales_price",
    "promo_label", "currency", "product_url", "source", "status", "note",
    "is_estimate",
]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
