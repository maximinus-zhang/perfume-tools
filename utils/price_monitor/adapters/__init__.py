# -*- coding: utf-8 -*-
"""竞品价格监控 · 适配器包

ADAPTER_REGISTRY 把零售商 id 映射到适配器类。
#9 阶段：中免 / 海旅 用 GenericH5Adapter 直接验证；海控 / 中服 标记为待 #10 实现。
#10 阶段会把它们替换成各自精调的子类（精确选择器 + 自定义导航）。
"""

from utils.price_monitor.adapters.base import BaseAdapter
from utils.price_monitor.adapters.generic import GenericH5Adapter
from utils.price_monitor.adapters.cdf_api import CdfApiAdapter

# id -> 适配器类；None 表示该零售商适配器待 #10 实现（fetcher 会标 verify_pending）
#   · cdfg  : 纯 HTTP 接口适配器（ENGINE="api"，无需浏览器，已实测可抓公开免税价）
#   · hailv : 仍走通用 H5 适配器（ENGINE="playwright"，待 #10 拆纯 HTTP 版）
#   · haikong / zhongfu : 待 #10 实现（可能卡登录墙）
ADAPTER_REGISTRY = {
    "cdfg": CdfApiAdapter,
    "hailv": GenericH5Adapter,
    "haikong": None,   # 待 #10：GDF会员购，可能卡登录墙
    "zhongfu": None,   # 待 #10：CNSC，线上入口待确认
}

__all__ = ["BaseAdapter", "GenericH5Adapter", "CdfApiAdapter", "ADAPTER_REGISTRY"]
