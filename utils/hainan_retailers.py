# -*- coding: utf-8 -*-
"""
海南免税 零售商 / 门店 主数据 v1.0
========================================
用途: 商情监控看板 的「零售商 — 门店」维度主数据

字段说明
--------
cooperation : 与 MAX 团队的合作状态（用户确认各零售商均有合作）
data_source :
    'public'      = 公开披露（官方 / 财报 / 新闻），数值可信
    'cooperation' = 合作方提供（内部口径）
    'estimate'    = 代理估算（无公开时序，见 hainan_estimator，禁止当实测）
weight      : 门店在所属零售商内的相对体量代理权重（仅供估算分摊，非实测）

⚠️ 本文件只放「静态主数据」。动态数值（销售/客流）由
   hainan_estimator（门店级估算）与采集层填充，且门店级一律标 is_estimate=True。
"""

# ============================================================
# 🏢 零售商 + 门店清单（尽量详细）
# ============================================================

RETAILERS = [
    {
        "id": "cdfg",
        "name": "中国中免（CDFG）",
        "full_name": "中国免税品（集团）有限责任公司",
        "listed": True,
        "ticker": "601888.SH",
        "cooperation": "合作",
        "data_source": "public",
        # 公开口径（2026 Q1 财报）：海南地区营收 125.85 亿，同比 +28.26%
        "hainan_q1_2026_rev": 125.85,
        "note": "海南离岛免税绝对龙头，六店 + 线上商城全覆盖",
        "stores": [
            {"id": "cdf_sanya", "name": "cdf 三亚国际免税城", "city": "三亚",
             "area": "海棠湾", "type": "离岛免税城", "opened": "2014",
             "weight": 0.34,
             "note": "旗舰店，近1000品牌；春节单日峰值破2亿/客流9.2万（公开）"},
            {"id": "cdf_haikou", "name": "cdf 海口国际免税城", "city": "海口",
             "area": "新海港", "type": "离岛免税城", "opened": "2022-10",
             "weight": 0.22,
             "note": "2025-11新政后累计客流338万(+46%，公开)；2026上半年新开近40店"},
            {"id": "cdf_rixin", "name": "cdf 海口日月广场免税店", "city": "海口",
             "area": "日月广场", "type": "离岛免税店", "opened": "2019",
             "weight": 0.10, "note": "市区核心商圈店"},
            {"id": "cdf_meilan", "name": "cdf 美兰机场免税店", "city": "海口",
             "area": "美兰机场", "type": "机场免税店", "opened": "2019",
             "weight": 0.09, "note": "2026上半年集中开业近40间品牌店"},
            {"id": "cdf_phoenix", "name": "cdf 三亚凤凰机场免税店", "city": "三亚",
             "area": "凤凰机场", "type": "机场免税店", "weight": 0.05,
             "note": "DIPTYQUE 等首店入驻"},
            {"id": "cdf_boao", "name": "cdf 琼海博鳌免税店", "city": "琼海",
             "area": "博鳌", "type": "离岛免税店", "opened": "2019",
             "weight": 0.03, "note": "论坛/会展客群"},
            {"id": "cdf_online", "name": "cdf 中免海南官方商城（线上）", "city": "线上",
             "area": "—", "type": "线上免税", "weight": 0.17,
             "note": "封关后品类扩容（茶叶/乐器/数码等）"},
        ],
    },
    {
        "id": "wangfujing",
        "name": "王府井免税",
        "full_name": "王府井集团股份有限公司（免税业务）",
        "listed": True,
        "ticker": "600859.SH",
        "cooperation": "合作",
        "data_source": "public",
        # 公开口径（2026-04-29 经营数据公告）：免税业务收入约 1.39 亿，同比 +39.79%
        "hainan_q1_2026_rev": 1.39,
        "use_actual_q1": True,  # 用实际 Q1 推导占比（覆盖代理 RETAILER_SHARE）
        "note": "万宁王府井国际免税港，岛内居民特惠购活动带动",
        "stores": [
            {"id": "wj_jiwei", "name": "王府井国际免税港", "city": "万宁",
             "area": "神州半岛", "type": "离岛免税城", "opened": "2023-01",
             "weight": 1.0, "note": "王府井在琼唯一免税门店"},
        ],
    },
    {
        "id": "hk_global",
        "name": "海控全球精品免税城",
        "full_name": "海南控股全球精品（海口）免税城有限公司",
        "listed": False,
        "ticker": None,
        "cooperation": "合作",
        "data_source": "public",
        "hainan_q1_2026_rev": None,
        "note": "海南发控旗下；H1 客流同比 +32%（公开新闻）",
        "stores": [
            {"id": "hk_global_haikou", "name": "海控全球精品免税城", "city": "海口",
             "area": "日月广场", "type": "离岛免税店", "weight": 1.0,
             "note": "与中免日月广场店同商圈竞争"},
        ],
    },
    {
        "id": "hlt",
        "name": "海旅免税",
        "full_name": "海南旅投免税品有限公司",
        "listed": False,
        "ticker": None,
        "cooperation": "合作",
        "data_source": "public",
        "hainan_q1_2026_rev": None,
        "note": "海南旅投旗下",
        "stores": [
            {"id": "hlt_sanya", "name": "海旅免税城", "city": "三亚",
             "area": "解放路/河口", "type": "离岛免税店", "weight": 1.0,
             "note": "市区文旅客流店"},
        ],
    },
    {
        "id": "sz_mian",
        "name": "深免（深圳免税）",
        "full_name": "深圳市国有免税商品（集团）有限公司",
        "listed": False,
        "ticker": None,
        "cooperation": "合作",
        "data_source": "public",
        "hainan_q1_2026_rev": None,
        "note": "国资免税集团",
        "stores": [
            {"id": "sz_mian_sanya", "name": "深免三亚国际免税店", "city": "三亚",
             "area": "—", "type": "离岛免税店", "weight": 1.0,
             "note": "三亚布局"},
        ],
    },
    {
        "id": "zhongfu",
        "name": "中服免税",
        "full_name": "中出服免税品有限公司",
        "listed": False,
        "ticker": None,
        "cooperation": "合作",
        "data_source": "public",
        "hainan_q1_2026_rev": None,
        "note": "中出服（中国出国人员服务）旗下",
        "stores": [
            {"id": "zhongfu_sanya", "name": "中服三亚国际免税购物公园", "city": "三亚",
             "area": "—", "type": "离岛免税店", "weight": 1.0,
             "note": "购物公园业态"},
        ],
    },
]


def iter_stores():
    """生成器：扁平化遍历 (retailer_dict, store_dict)，方便页面/估算调用。"""
    for r in RETAILERS:
        for s in r.get("stores", []):
            yield r, s


def store_count():
    """门店总数（含线上）。"""
    return sum(len(r.get("stores", [])) for r in RETAILERS)


# 供其他模块引用，避免硬编码字符串
COOPERATION_ALL = "合作"  # 用户确认：各零售商均有合作
