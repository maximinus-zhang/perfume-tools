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
        return cls(**known)

    @property
    def ok(self) -> bool:
        return self.status == "ok" and self.price is not None


# CSV 表头顺序（看板 / 下载统一使用）
CSV_COLUMNS = [
    "captured_at", "retailer_id", "retailer_name", "sku_id", "brand",
    "name_cn", "name_en", "size_ml", "category", "price", "currency",
    "product_url", "source", "status", "note", "is_estimate",
]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
