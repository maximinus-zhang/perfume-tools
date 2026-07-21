# -*- coding: utf-8 -*-
"""
新闻自动分析器 v1.0
==================
用途：从已爬取的新闻标题/摘要中，按模块上下文提取相关信号并生成判断备注。
设计原则：
  1. 完全离线、不依赖 LLM API，保证页面启动速度和稳定性；
  2. 按关键词 + 信号词匹配，生成结构化 bullet；
  3. 每个模块只返回最相关的 2-4 条，避免信息过载；
  4. 无相关新闻时给出「暂无」提示，不报错。

后续升级：若需要更深度的语义分析，可在此模块内新增 LLM 调用层，
页面代码无需改动。
"""

import re
from typing import List, Tuple, Optional

# Streamlit 为可选依赖（utils 模块可能被非 Streamlit 脚本导入）
try:
    import streamlit as st
    _HAS_ST = True
except Exception:  # pragma: no cover
    _HAS_ST = False

# ============================================================
# 模块上下文配置：每个上下文定义「筛选关键词」+「信号词」+「输出模板」
# ============================================================
NEWS_CONTEXTS = {
    "hainan_overview": {
        "label": "海南免税整体",
        "filter_kw": [
            "海南", "离岛免税", "免税购物", "cdf", "中免", "海口", "三亚",
            "免税销售", "免税金额", "购物金额", "自贸港", "封关",
        ],
        "signals": {
            "消费券|优惠券|补贴": ("🎫 政策刺激", "消费券/补贴政策可能短期提振客流与客单"),
            "暑期|暑运|暑假|夏季": ("☀️ 旺季预期", "暑期传统旺季临近，客流与销售额通常季节性回升"),
            "春运|春节|国庆|五一|端午|中秋": ("🎉 节点消费", "节假日是海南免税销售高峰，关注备货与促销节奏"),
            "增长|上升|增加|突破|向好": ("📈 增长信号", "新闻显示市场景气度上行"),
            "下降|下滑|放缓|减少|承压": ("📉 放缓信号", "新闻显示市场增速有所放缓，需警惕库存与补货节奏"),
            "客单价|人均消费|件单价": ("🛒 价格信号", "客单价/件单价变化直接影响香化品类补货策略"),
            "入境|免签|国际游客|境外": ("🌍 入境客流", "免签/入境客流变化可能带来增量客源"),
        },
    },
    "quarterly": {
        "label": "季度对比",
        "filter_kw": [
            "一季度", "二季度", "三季度", "上半年", "H1", "Q1", "Q2", "Q3",
            "同比", "增长", "下降", "海南", "免税",
        ],
        "signals": {
            "一季度|Q1|1-3月|1月至3月": ("🌸 Q1 表现", "Q1 通常为春节/寒假旺季，关注高基数效应"),
            "二季度|Q2|4-6月|4月至6月": ("🏖️ Q2 表现", "Q2 进入传统淡季，但端午/618 可形成小高峰"),
            "三季度|Q3|7-9月|7月至9月": ("☀️ Q3 预期", "Q3 暑期是全年关键旺季，新闻景气度影响全年预测"),
            "上半年|H1": ("📅 H1 总结", "H1 数据为全年基调，关注同比基数与政策红利"),
            "同比": ("📊 同比变化", "新闻中提及的同比增速可与当前数据交叉验证"),
        },
    },
    "monthly": {
        "label": "月度分析",
        "filter_kw": [
            "月", "销售额", "免税", "海南", "同比", "环比", "增长", "下降",
            "客流", "人次", "件数",
        ],
        "signals": {
            "环比|月度|逐月": ("🗓️ 月度节奏", "月度环比变化反映短期景气波动"),
            "客单价|人均": ("💰 客单信号", "客单价波动影响香化品类结构"),
            "件数|件单价": ("📦 件数信号", "件数变化反映消费者购买件数与促销力度"),
            "增长|上升": ("📈 上行月份", "新闻显示该月景气上行"),
            "下降|下滑": ("📉 下行月份", "新闻显示该月景气承压"),
        },
    },
    "airport_overview": {
        "label": "12大机场",
        "filter_kw": [
            "机场", "旅客", "吞吐量", "航班", "航线", "国际航线", "复航",
            "浦东", "首都", "大兴", "白云", "宝安", "天府", "江北", "长水",
            "咸阳", "萧山", "美兰", "凤凰",
        ],
        "signals": {
            "国际航线|国际航班|复航|通航|加密": ("✈️ 国际恢复", "国际航线恢复/加密利好机场免税与境外客流"),
            "吞吐量|旅客量|客流量": ("📊 吞吐变化", "机场吞吐量直接影响免税潜在客流"),
            "T3|T4|T5|航站楼|新航站楼": ("🏗️ 基建扩容", "新航站楼/卫星厅投运可能扩大免税面积"),
            "增长|上升|恢复": ("📈 机场景气", "机场客流上行，利好机场免税销售"),
            "下降|下滑|减少": ("📉 机场承压", "机场客流下滑，需关注机场渠道备货"),
            "暑运|春运|旺季": ("🎒 季节性", "旺季机场客流通常显著抬升"),
        },
    },
    "airport_monthly": {
        "label": "机场月度客流",
        "filter_kw": [
            "机场", "月", "客流", "航班", "暑运", "春运", "国庆", "旺季",
            "浦东", "首都", "大兴", "白云", "宝安", "天府", "江北", "长水",
            "咸阳", "萧山", "美兰", "凤凰",
        ],
        "signals": {
            "暑运|暑假|7月|8月": ("☀️ 暑运高峰", "7-8 月通常为机场客流高峰"),
            "春运|春节|1月|2月": ("🧧 春运高峰", "1-2 月春运为全年最高峰值之一"),
            "国庆|10月": ("🇨🇳 国庆高峰", "国庆假期带来短期客流冲高"),
            "淡季": ("🍂 淡季", "淡季客流相对平稳，适合维护与调整"),
        },
    },
    "retailer_overview": {
        "label": "零售商估算",
        "filter_kw": [
            "中免", "cdf", "王府井", "海控", "海旅", "深免", "中服",
            "免税", "海南", "销售额", "营收", "门店", "免税店",
        ],
        "signals": {
            "中免|cdf": ("🏆 中免动态", "中免作为龙头，其策略/数据直接影响全省格局"),
            "王府井|万宁": ("🛍️ 王府井动态", "王府井万宁店表现影响代理估算占比"),
            "海控|全球精品": ("🏢 海控动态", "海控客流/活动影响海口日月商圈竞争"),
            "海旅": ("🌴 海旅动态", "海旅三亚店动态反映市区文旅客流"),
            "深免": ("🛒 深免动态", "深免深圳/海南布局变化"),
            "中服": ("💊 中服动态", "中服健康/市内免税动态"),
            "开业|首店|入驻": ("🆕 新店/首店", "新店开业或品牌入驻可能带来短期客流"),
            "促销|活动|会员": ("🎁 营销活动", "促销/会员活动影响短期销售"),
        },
    },
    "store_overview": {
        "label": "门店估算",
        "filter_kw": [
            "三亚国际免税城", "海棠湾", "海口国际免税城", "新海港",
            "日月广场", "美兰机场", "凤凰机场", "博鳌", "万宁",
            "王府井国际免税港", "海旅免税城", "海控全球精品",
        ],
        "signals": {
            "三亚国际免税城|海棠湾": ("🏖️ cdf 三亚国际免税城", "旗舰店动态对全省/中免估算影响最大"),
            "海口国际免税城|新海港": ("🚢 cdf 海口国际免税城", "新海港门店受港口客流与政策影响显著"),
            "日月广场": ("🌙 海口日月广场", "中免与海控同商圈竞争，关注分流与活动"),
            "美兰机场|凤凰机场": ("✈️ 机场店", "机场店与航班恢复/离岛客流直接挂钩"),
            "万宁|王府井": ("🏄 万宁王府井", "万宁店表现与代理估算占比相关"),
            "海旅免税城|三亚市区": ("🌆 三亚市区店", "市区文旅客流变化影响门店表现"),
        },
    },
    "policy": {
        "label": "政策动态",
        "filter_kw": [
            "政策", "免税", "海南", "自贸港", "封关", "零关税", "额度",
            "限购", "提货", "入境", "免签", "签证", "离岛", "口岸",
        ],
        "signals": {
            "封关|零关税": ("🔒 封关运作", "封关政策进度影响长期市场预期"),
            "免签|签证|入境": ("🛂 入境政策", "免签范围扩大直接利好境外客流"),
            "额度|限购|提货": ("📝 购物政策", "额度/限购/提货方式调整影响消费行为"),
            "消费券|补贴": ("💸 刺激政策", "消费券/补贴短期提振销售"),
        },
    },
    "travel": {
        "label": "旅游客流",
        "filter_kw": [
            "海南", "三亚", "海口", "游客", "旅游", "接待", "入境", "免签",
            "客流", "人次", "暑期", "春运", "航班",
        ],
        "signals": {
            "接待游客|旅游人次": ("🏖️ 全省客流", "全省游客接待量决定免税潜在客流池"),
            "入境游客|免签": ("🌍 入境客流", "入境游客是免税增量客源"),
            "暑期|旺季": ("☀️ 旺季客流", "旺季客流高峰决定短期销售上限"),
            "航班|航线|机票": ("✈️ 运力", "航班/运力变化影响可达性"),
        },
    },
}


def _matches_filter(title: str, filter_kw: List[str]) -> bool:
    """标题是否命中该上下文的任一过滤关键词。"""
    t = title.lower()
    return any(kw.lower() in t for kw in filter_kw)


def _extract_signal(title: str, signals: dict) -> Optional[Tuple[str, str]]:
    """
    从标题中提取第一个匹配的信号。
    signals: { "regex_pattern": (icon_label, interpretation) }
    返回 (icon_label, interpretation) 或 None。
    """
    for pattern, (label, interp) in signals.items():
        if re.search(pattern, title, re.IGNORECASE):
            return label, interp
    return None


def analyze_news_for_context(
    news_items: List[Tuple[str, str]],
    context: str,
    max_bullets: int = 3,
    include_urls: bool = True,
) -> List[dict]:
    """
    为指定模块上下文生成新闻分析备注。

    参数：
        news_items: [(title, url), ...] 已爬取的新闻列表
        context: NEWS_CONTEXTS 中的上下文名
        max_bullets: 最多返回几条
        include_urls: 返回结果中是否保留原始 url

    返回：
        List[dict]，每个 dict 包含：
        {
            "label": str,      # 信号标签，如 "📈 增长信号"
            "text": str,       # 生成的判断备注
            "url": str,        # 原始新闻链接（若 include_urls=True）
            "title": str,      # 原始新闻标题
        }
    """
    cfg = NEWS_CONTEXTS.get(context)
    if not cfg:
        return []

    filter_kw = cfg["filter_kw"]
    signals = cfg["signals"]

    bullets = []
    seen_labels = set()

    for title, url in news_items:
        if not _matches_filter(title, filter_kw):
            continue

        sig = _extract_signal(title, signals)
        if not sig:
            # 没有命中信号词，但命中了过滤关键词，也保留一条泛化备注
            sig = ("📰 相关动态", "该新闻与当前模块相关，可作为判断参考")

        label, interp = sig
        # 同一标签只保留一次，避免重复
        if label in seen_labels:
            continue
        seen_labels.add(label)

        text = f"**{label}**：{interp}。" if interp else f"**{label}**"
        # 若标题含具体数字，追加到备注中增强可读性
        numbers = re.findall(r"\d+\.?\d*\s*[亿元万人次%]+", title)
        if numbers:
            text += f"（新闻提及：{' / '.join(numbers[:2])}）"

        rec = {"label": label, "text": text, "title": title}
        if include_urls:
            rec["url"] = url
        bullets.append(rec)

        if len(bullets) >= max_bullets:
            break

    return bullets


def render_insight_markdown(
    bullets: List[dict],
    header: str = "🤖 新闻自动分析备注",
    empty_msg: str = "暂无与当前模块高度相关的新闻，请刷新新闻或关注后续更新。",
) -> str:
    """
    把分析结果渲染成 markdown 字符串，供 Streamlit 直接显示。
    """
    if not bullets:
        return f"**{header}**\n\n> {empty_msg}"

    lines = [f"**{header}**", ""]
    for b in bullets:
        line = f"- {b['text']}"
        if b.get("url"):
            line += f" [🔗 原文]({b['url']})"
        lines.append(line)
    lines.append("")
    lines.append("> 备注：以上由关键词自动提取生成，仅供辅助判断，关键决策请结合官方数据。")
    return "\n".join(lines)


def st_insight_box(
    news_items: List[Tuple[str, str]],
    context: str,
    max_bullets: int = 3,
    expanded: bool = False,
):
    """
    在 Streamlit 页面直接渲染一个 insight expander。
    需要在已 import streamlit as st 的页面中调用。
    """
    import streamlit as st

    bullets = analyze_news_for_context(news_items, context, max_bullets)
    md = render_insight_markdown(
        bullets,
        header=f"🤖 {NEWS_CONTEXTS.get(context, {}).get('label', context)} · 新闻自动备注",
    )
    with st.expander(md.split("\n")[0].replace("**", ""), expanded=expanded):
        st.markdown("\n".join(md.split("\n")[1:]))


# ============================================================
# 共享缓存：在多个页面间复用同一批爬取结果，避免重复请求
# ============================================================

if _HAS_ST:
    @st.cache_data(ttl=86400, show_spinner="🔄 正在爬取最新新闻，请稍候...")
    def fetch_news_cached(force_refresh: bool = False):
        """
        调用 HainanScraper 爬取全部新闻，结果在 Streamlit 全应用内缓存 24h。
        参数 force_refresh 仅用于构造缓存 key，实际刷新请调用 st.cache_data.clear()。
        """
        from utils.hainan_scraper import HainanScraper

        return HainanScraper().scrape_all()
else:  # pragma: no cover
    def fetch_news_cached(force_refresh: bool = False):  # type: ignore
        from utils.hainan_scraper import HainanScraper

        return HainanScraper().scrape_all()
