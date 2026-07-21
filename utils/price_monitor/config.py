# -*- coding: utf-8 -*-
"""
竞品价格监控 · 配置中心 v1.0
============================
本文件是「海南免税竞品价格监控」唯一的静态配置入口：
  · RETAILERS_MONITOR : 要监控的零售商（已与 MAX 确认 v1 = 中免 + 海旅 + 海控 + 中服）
  · PERFUME_SKUS      : 香水主力 SKU（竞品对标清单，按品牌旗舰款挑选）
  · GUARDRAILS        : 抓取合规护栏（限速 / 重试 / 仅公开价 / 登录墙拦截）

⚠️ 动态数值（价格时序）由采集层填充，绝不写进本文件。
⚠️ 合规红线：只抓「公开标价页」，绝不碰登录墙 / 小程序加密 API / 个人隐私。
   命中登录墙的零售商 → 标记 status=blocked_login 并跳过，不拖垮整轮抓取。
"""

from datetime import datetime

# ============================================================
# 🛡️ 抓取合规护栏（贯穿采集层，所有适配器共用）
# ============================================================
GUARDRAILS = {
    "min_interval_seconds": 10,   # 每个 SKU / 每家之间的最小间隔（限速，避免被封）
    "max_retries": 3,             # 单条抓取失败重试上限
    "timeout_seconds": 30,        # 单页渲染等待上限
    "random_user_agent": True,    # 随机 UA 池（见 base.py）
    "only_public_prices": True,   # 只抓公开标价，拒绝任何登录/会员专属价
    "respect_login_wall": True,   # 命中登录墙 → blocked_login 跳过
    "source_label": True,         # 每条记录强制带来源标签
    "headless": True,             # 无头浏览器（服务器无显示器）
}

# ============================================================
# 🏢 零售商注册表（v1 四家，已与 MAX 确认）
# ============================================================
# 字段说明
#   id            : 内部唯一标识
#   name          : 展示名
#   mall_url      : 商城首页（公开）
#   search_url    : 搜索入口模板，{kw} 替换为关键词；None 表示需在适配器内自行定位
#   verify        : True = B 档「先验证再抓」，首次运行必须确认是否真公开
#   login_wall    : True = 预期可能卡登录墙（海控/中服），命中即跳过
#   engine        : 抓取引擎（统一 Playwright 无头）
#   note          : 备注（可用性结论）
RETAILERS_MONITOR = [
    {
        "id": "cdfg",
        "name": "中免 CDF",
        "mall_url": "https://m.cdfhnmall.com",
        "search_url": "https://m.cdfhnmall.com/#/search?keyword={kw}",
        "verify": False,
        "login_wall": False,
        "engine": "api",
        "note": "A 档 · 纯 HTTP 搜索接口（service.cdfhnmall.com/mini/findGoodsList），无需登录、无需浏览器（已实测返回 200 + 免税价）",
    },
    {
        "id": "hailv",
        "name": "海旅免税",
        "mall_url": "https://m.hltmsp.com",
        "search_url": "https://m.hltmsp.com/#/search?keyword={kw}",
        "verify": False,
        "login_wall": False,
        "engine": "playwright",
        "note": "A 档 · 公开标价、无需登录（已实测返回 200，uniapp H5 商城）",
    },
    {
        "id": "haikong",
        "name": "海控 GDF会员购",
        "mall_url": "https://shop.gdfplaza.com",
        "search_url": None,
        "verify": True,
        "login_wall": True,
        "engine": "playwright",
        "note": "B 档 · 会员制商城，curl 实测超时；可能卡登录墙，首次运行需验证",
    },
    {
        "id": "zhongfu",
        "name": "中服 CNSC",
        "mall_url": "https://www.zhongfusanya.com",
        "search_url": None,
        "verify": True,
        "login_wall": True,
        "engine": "playwright",
        "note": "B 档 · 企业站，线上商城入口不明，疑似小程序为主；首次运行需验证",
    },
]

# ============================================================
# 🌸 香水主力 SKU（竞品对标清单）
# ============================================================
# 每个 SKU 字段
#   id        : 内部唯一标识
#   brand     : 品牌（中文）
#   name_cn   : 产品中文名
#   name_en   : 产品英文名（辅助匹配）
#   size_ml   : 规格（ml），多规格用 "/" 分隔；监控取搜索首条标价
#   keyword   : 搜索关键词（优先 品牌+中文名，命中率最高）
#   category  : 品类（统一「香水」）
PERFUME_SKUS = [
    {"id": "chanel_coco", "brand": "香奈儿", "name_cn": "可可小姐", "name_en": "Coco Mademoiselle", "size_ml": "50/100", "keyword": "香奈儿可可小姐", "category": "香水"},
    {"id": "chanel_chance", "brand": "香奈儿", "name_cn": "邂逅柔情", "name_en": "Chance Eau Tendre", "size_ml": "50/100", "keyword": "香奈儿邂逅柔情", "category": "香水"},
    {"id": "chanel_no5", "brand": "香奈儿", "name_cn": "五号", "name_en": "N°5", "size_ml": "50/100", "keyword": "香奈儿五号香水", "category": "香水"},
    {"id": "chanel_bleu", "brand": "香奈儿", "name_cn": "蔚蓝男士", "name_en": "Bleu de Chanel", "size_ml": "100", "keyword": "香奈儿蔚蓝男士", "category": "香水"},
    {"id": "dior_jadore", "brand": "迪奥", "name_cn": "真我", "name_en": "J'adore", "size_ml": "50/100", "keyword": "迪奥真我香水", "category": "香水"},
    {"id": "dior_miss", "brand": "迪奥", "name_cn": "花漾甜心", "name_en": "Miss Dior", "size_ml": "50/100", "keyword": "迪奥花漾甜心", "cdf_keyword": "迪奥小姐花漾", "aliases": ["花漾女士淡香水"], "category": "香水"},
    {"id": "dior_sauvage", "brand": "迪奥", "name_cn": "旷野", "name_en": "Sauvage", "size_ml": "60/100", "keyword": "迪奥旷野男士", "category": "香水"},
    {"id": "jomalone_pear", "brand": "祖玛珑", "name_cn": "英国梨与小苍兰", "name_en": "English Pear & Freesia", "size_ml": "30/100", "keyword": "祖玛珑英国梨与小苍兰", "category": "香水"},
    {"id": "jomalone_bluebell", "brand": "祖玛珑", "name_cn": "蓝风铃", "name_en": "Wild Bluebell", "size_ml": "30/100", "keyword": "祖玛珑蓝风铃", "category": "香水"},
    {"id": "jomalone_sage", "brand": "祖玛珑", "name_cn": "鼠尾草与海盐", "name_en": "Wood Sage & Sea Salt", "size_ml": "100", "keyword": "祖玛珑鼠尾草与海盐", "category": "香水"},
    {"id": "jomalone_orange", "brand": "祖玛珑", "name_cn": "橙花", "name_en": "Orange Blossom", "size_ml": "100", "keyword": "祖玛珑橙花", "category": "香水"},
    {"id": "tomford_noirextreme", "brand": "汤姆福特", "name_cn": "黑之黑", "name_en": "Noir Extreme", "size_ml": "50/100", "keyword": "汤姆福特黑之黑", "cdf_keyword": "Noir Extreme", "aliases": ["烈夜奢黑香型"], "category": "香水"},
    {"id": "tomford_tobacco", "brand": "汤姆福特", "name_cn": "烟草香草", "name_en": "Tobacco Vanille", "size_ml": "50", "keyword": "汤姆福特烟草香草", "cdf_keyword": "汤姆福特烟草", "aliases": ["韵度烟草香型"], "category": "香水"},
    {"id": "hermes_terre", "brand": "爱马仕", "name_cn": "大地", "name_en": "Terre d'Hermès", "size_ml": "50/100", "keyword": "爱马仕大地男士", "category": "香水"},
    {"id": "hermes_merveilles", "brand": "爱马仕", "name_cn": "橘彩星光", "name_en": "Eau des Merveilles", "size_ml": "50", "keyword": "爱马仕橘彩星光", "category": "香水"},
    {"id": "ysl_libre", "brand": "圣罗兰", "name_cn": "自由之水", "name_en": "Libre", "size_ml": "50/90", "keyword": "圣罗兰自由之水", "category": "香水"},
    {"id": "ysl_blackopium", "brand": "圣罗兰", "name_cn": "黑鸦片", "name_en": "Black Opium", "size_ml": "50/90", "keyword": "圣罗兰黑鸦片", "category": "香水"},
    {"id": "armani_gio", "brand": "阿玛尼", "name_cn": "寄情", "name_en": "Acqua di Giò", "size_ml": "50/100", "keyword": "阿玛尼寄情", "category": "香水"},
    {"id": "gucci_bloom", "brand": "古驰", "name_cn": "花悦", "name_en": "Bloom", "size_ml": "50/100", "keyword": "古驰花悦", "category": "香水"},
    {"id": "bvlgari_pourhomme", "brand": "宝格丽", "name_cn": "大吉岭原茶", "name_en": "Pour Homme", "size_ml": "50/100", "keyword": "宝格丽大吉岭原茶", "cdf_keyword": "宝格丽大吉岭", "aliases": ["大吉岭茶香"], "category": "香水"},
    {"id": "bvlgari_amethyste", "brand": "宝格丽", "name_cn": "紫晶", "name_en": "Omnia Amethyste", "size_ml": "40", "keyword": "宝格丽紫晶", "category": "香水"},
    {"id": "guerlain_robe", "brand": "娇兰", "name_cn": "小黑裙", "name_en": "La Petite Robe Noire", "size_ml": "50/100", "keyword": "娇兰小黑裙", "category": "香水"},
    {"id": "chloe_edp", "brand": "蔻依", "name_cn": "同名", "name_en": "Chloé EDP", "size_ml": "50/75", "keyword": "蔻依同名香水", "category": "香水"},
    {"id": "burberry_london", "brand": "巴宝莉", "name_cn": "伦敦", "name_en": "London", "size_ml": "50/100", "keyword": "巴宝莉伦敦男士", "category": "香水"},
    {"id": "versace_crystal", "brand": "范思哲", "name_cn": "心动", "name_en": "Bright Crystal", "size_ml": "50/90", "keyword": "范思哲心动女士", "category": "香水"},
    {"id": "lanvin_eclat", "brand": "浪凡", "name_cn": "光韵", "name_en": "Éclat d'Arpège", "size_ml": "50/100", "keyword": "浪凡光韵", "category": "香水"},
    {"id": "diptyque_philosykos", "brand": "蒂普提克", "name_cn": "水中影", "name_en": "Philosykos", "size_ml": "50/100", "keyword": "蒂普提克水中影", "cdf_keyword": "Philosykos", "aliases": ["希腊无花果香调", "无花果"], "category": "香水"},
    {"id": "atelier_orange", "brand": "欧珑", "name_cn": "赤霞橘光", "name_en": "Orange Sanguine", "size_ml": "30/100", "keyword": "欧珑赤霞橘光", "category": "香水"},
    {"id": "marcjacobs_daisy", "brand": "马克雅各布", "name_cn": "小雏菊", "name_en": "Daisy", "size_ml": "50/100", "keyword": "马克雅各布小雏菊", "category": "香水"},
    {"id": "coach_edp", "brand": "蔻驰", "name_cn": "同名", "name_en": "Coach EDP", "size_ml": "50/90", "keyword": "蔻驰香水", "category": "香水"},
]

# ============================================================
# 💄 彩妆主力 SKU（竞品对标清单，category=彩妆）
# ============================================================
MAKEUP_SKUS = [
    {"id": "dior_rouge", "brand": "迪奥", "name_cn": "烈艳蓝金唇膏", "name_en": "Dior Rouge", "size_ml": "3.5g", "keyword": "迪奥烈艳蓝金唇膏", "category": "彩妆"},
    {"id": "ysl_rougepur", "brand": "圣罗兰", "name_cn": "小金条唇釉", "name_en": "YSL Rouge Pur", "size_ml": "2.2g", "keyword": "圣罗兰小金条", "category": "彩妆"},
    {"id": "armani_red", "brand": "阿玛尼", "name_cn": "红管唇釉", "name_en": "Armani Lip Maestro", "size_ml": "6.5ml", "keyword": "阿玛尼红管唇釉", "category": "彩妆"},
    {"id": "lancome_rouge", "brand": "兰蔻", "name_cn": "菁纯唇膏", "name_en": "Lancome L'Absolu", "size_ml": "3.4g", "keyword": "兰蔻菁纯唇膏", "category": "彩妆"},
    {"id": "estee_rouge", "brand": "雅诗兰黛", "name_cn": "倾慕唇膏", "name_en": "Estee Lauder Pure Color", "size_ml": "3.5g", "keyword": "雅诗兰黛倾慕唇膏", "category": "彩妆"},
    {"id": "tf_lip", "brand": "汤姆福特", "name_cn": "黑管唇膏", "name_en": "Tom Ford Lip Color", "size_ml": "3g", "keyword": "汤姆福特唇膏", "category": "彩妆"},
    {"id": "mac_bullet", "brand": "魅可", "name_cn": "子弹头唇膏", "name_en": "MAC Retro Matte", "size_ml": "3g", "keyword": "魅可子弹头唇膏", "category": "彩妆"},
    {"id": "dior_forever", "brand": "迪奥", "name_cn": "凝脂恒久粉底液", "name_en": "Dior Forever", "size_ml": "30ml", "keyword": "迪奥凝脂恒久粉底液", "category": "彩妆"},
    {"id": "estee_dw", "brand": "雅诗兰黛", "name_cn": "DW粉底液", "name_en": "Double Wear", "size_ml": "30ml", "keyword": "雅诗兰黛DW粉底液", "category": "彩妆"},
    {"id": "ysl_touche", "brand": "圣罗兰", "name_cn": "明彩笔", "name_en": "Touche Eclat", "size_ml": "2.5ml", "keyword": "圣罗兰明彩笔", "category": "彩妆"},
    {"id": "cpb_lip", "brand": "肌肤之钥", "name_cn": "唇膏", "name_en": "CPB Lipstick", "size_ml": "3.8g", "keyword": "肌肤之钥唇膏", "category": "彩妆"},
    {"id": "nars_powder", "brand": "NARS", "name_cn": "裸光蜜粉饼", "name_en": "NARS Light Reflecting", "size_ml": "10g", "keyword": "NARS 蜜粉饼", "category": "彩妆"},
]

# ============================================================
# 🧴 护肤主力 SKU（竞品对标清单，category=护肤）
# ============================================================
SKINCARE_SKUS = [
    {"id": "el_anr", "brand": "雅诗兰黛", "name_cn": "小棕瓶精华", "name_en": "Advanced Night Repair", "size_ml": "30/50ml", "keyword": "雅诗兰黛小棕瓶", "category": "护肤"},
    {"id": "lancome_genifique", "brand": "兰蔻", "name_cn": "小黑瓶精华", "name_en": "Genifique", "size_ml": "30/50ml", "keyword": "兰蔻小黑瓶", "category": "护肤"},
    {"id": "skii_essence", "brand": "SK-II", "name_cn": "神仙水", "name_en": "Facial Treatment Essence", "size_ml": "75/160ml", "keyword": "SK-II 神仙水", "category": "护肤"},
    {"id": "lamer_cream", "brand": "海蓝之谜", "name_cn": "精华面霜", "name_en": "Crème de la Mer", "size_ml": "30/60ml", "keyword": "海蓝之谜面霜", "category": "护肤"},
    {"id": "shiseido_ultimate", "brand": "资生堂", "name_cn": "红妍肌活精华", "name_en": "Ultimate Revitalizer", "size_ml": "30/50ml", "keyword": "资生堂红妍肌活精华", "category": "护肤"},
    {"id": "skinceuticals_ce", "brand": "修丽可", "name_cn": "维生素CE精华", "name_en": "C E Ferulic", "size_ml": "30ml", "keyword": "修丽可CE精华", "category": "护肤"},
    {"id": "hr_cream", "brand": "赫莲娜", "name_cn": "黑绷带面霜", "name_en": "Replasty Cream", "size_ml": "50ml", "keyword": "赫莲娜黑绷带面霜", "category": "护肤"},
    {"id": "clarins_double", "brand": "娇韵诗", "name_cn": "双萃精华", "name_en": "Double Serum", "size_ml": "30/50ml", "keyword": "娇韵诗双萃精华", "category": "护肤"},
    {"id": "kiehls_ultra", "brand": "科颜氏", "name_cn": "高保湿面霜", "name_en": "Ultra Facial Cream", "size_ml": "50/125ml", "keyword": "科颜氏高保湿面霜", "category": "护肤"},
    {"id": "sulwhasoo_first", "brand": "雪花秀", "name_cn": "润燥精华", "name_en": "First Care", "size_ml": "60ml", "keyword": "雪花秀润燥精华", "category": "护肤"},
    {"id": "lancome_absolue", "brand": "兰蔻", "name_cn": "菁纯面霜", "name_en": "Absolue", "size_ml": "60ml", "keyword": "兰蔻菁纯面霜", "category": "护肤"},
    {"id": "el_revit", "brand": "雅诗兰黛", "name_cn": "白金面霜", "name_en": "Re-Nutriv", "size_ml": "50ml", "keyword": "雅诗兰黛白金面霜", "category": "护肤"},
]

# ============================================================
# 🗂️ 全品类监控清单（看板默认全量抓取；也用于 sku_by_id 检索）
# ============================================================
ALL_MONITOR_SKUS = PERFUME_SKUS + MAKEUP_SKUS + SKINCARE_SKUS

# ============================================================
# 🏷️ 品类信号词（与 cdf_api.match_product / detect_category 共用）
# ============================================================
CATEGORY_HINTS = {
    "香水": ("香水", "香型", "淡香", "浓香", "香氛", "香精", "香体", "发香", "edp", "edt", "parfum"),
    "彩妆": ("口红", "唇膏", "唇釉", "唇蜜", "丰唇", "润唇", "唇彩", "粉底", "眼影", "腮红",
             "睫毛膏", "遮瑕", "散粉", "气垫", "彩妆", "妆前", "眉笔", "眼线", "高光", "甲油"),
    "护肤": ("面霜", "精华", "水乳", "眼霜", "洁面", "面膜", "乳液", "护肤", "防晒",
             "爽肤水", "化妆水", "柔肤水", "保湿", "护肤水"),
}

# ============================================================
# 🛒 品牌货架速览目录（「品牌货架速览」模式：按 品类 + 品牌 实时拉取中免在售）
# ============================================================
BRAND_SHELF = {
    "香水": ["香奈儿", "迪奥", "祖玛珑", "汤姆福特", "爱马仕", "圣罗兰", "阿玛尼", "古驰", "宝格丽", "娇兰", "蔻依", "范思哲"],
    "彩妆": ["迪奥", "圣罗兰", "阿玛尼", "兰蔻", "雅诗兰黛", "汤姆福特", "魅可", "香奈儿", "NARS", "纪梵希", "肌肤之钥", "植村秀"],
    "护肤": ["雅诗兰黛", "兰蔻", "SK-II", "海蓝之谜", "资生堂", "修丽可", "赫莲娜", "娇韵诗", "科颜氏", "雪花秀", "肌肤之钥", "莱珀妮"],
}


def snapshot_date() -> str:
    """返回当前快照日期（YYYY-MM-DD），用作 OSS 分区与文件名。"""
    return datetime.now().strftime("%Y-%m-%d")


def sku_by_id(sku_id: str) -> dict | None:
    for s in ALL_MONITOR_SKUS:
        if s["id"] == sku_id:
            return s
    return None


def retailer_by_id(rid: str) -> dict | None:
    for r in RETAILERS_MONITOR:
        if r["id"] == rid:
            return r
    return None
