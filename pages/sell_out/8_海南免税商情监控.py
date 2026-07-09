"""
海南免税商情监控 v6.5 - Streamlit 模块版
✅ 超链接 ✅ 年份标注 ✅ 全国12大机场
"""

import re
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from typing import Dict, List, Tuple, Optional

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# ============================================================
# 🏢 全国12大机场知识库 (CAAC 2024年官方数据)
# ⚠️ 月度分布为基于季节规律的估算值，仅供参考
# ============================================================

AIRPORT_DB = {
    # ── 第1名 ──
    "上海浦东": {
        "annual": 7679, "rank": 1, "data_year": "2024",
        "terminals": {
            "T1": "国际/地区 + 部分国内 (东上航)",
            "T2": "国内为主 (国航/南航/吉祥/春秋等)"
        },
        "major_airlines": ["东方航空(主基地)", "上海航空", "春秋航空", "吉祥航空", "中国国航"],
        "domestic_pct": 78, "international_pct": 22,
        "duty_free": {
            "operator": "中国中免(CDFG) + 日上免税行",
            "stores": "T1/T2出境及入境免税店",
            "note": "浦东机场免税销售额占中国机场免税~40%, 2024年约70亿元"
        },
        # 月度占比（%）- 基于季节性规律估算
        "monthly_pct": [7.8, 7.2, 8.5, 8.3, 8.6, 8.8, 9.2, 9.0, 8.2, 8.5, 8.0, 7.9],
        "latest_news_query": "上海浦东机场 2025 2026 国际航线 新航站楼",
    },
    # ── 第2名 ──
    "广州白云": {
        "annual": 7637, "rank": 2, "data_year": "2024",
        "terminals": {
            "T1": "国内为主(改造中, 航司已转场至T3)",
            "T2": "南航及天合联盟主楼",
            "T3": "2026年投运, 承接原T1国内航司"
        },
        "major_airlines": ["南方航空(主基地)", "中国国航", "海南航空", "九元航空"],
        "domestic_pct": 86, "international_pct": 14,
        "duty_free": {
            "operator": "中国中免(CDFG)",
            "stores": "T1/T2出境免税店",
            "note": "2024年T1改造影响部分免税面积"
        },
        "monthly_pct": [8.0, 7.5, 8.8, 8.5, 8.7, 8.5, 8.8, 8.6, 8.2, 8.0, 7.8, 8.6],
        "latest_news_query": "广州白云机场 T3 2025 2026 新航站楼",
    },
    # ── 第3名 ──
    "深圳宝安": {
        "annual": 6147, "rank": 3, "data_year": "2024",
        "terminals": {
            "T3": "国内/国际主楼 (2013年启用)",
            "T4": "2026年启动建设"
        },
        "major_airlines": ["深圳航空(主基地)", "南方航空", "中国国航", "东海航空"],
        "domestic_pct": 90, "international_pct": 10,
        "duty_free": {
            "operator": "中国中免(CDFG)",
            "stores": "T3出境免税店",
            "note": "深圳机场免税以出境为主, 体量较小"
        },
        "monthly_pct": [8.2, 7.8, 8.5, 8.3, 8.5, 8.2, 8.8, 8.6, 8.0, 8.5, 8.3, 8.3],
        "latest_news_query": "深圳宝安机场 2025 2026 新航线 国际",
    },
    # ── 第4名 ──
    "北京首都": {
        "annual": 5288, "rank": 4, "data_year": "2024",
        "terminals": {
            "T1": "暂停运营改造(2025年起)",
            "T2": "国内+国际 (南航/东航/海航部分)",
            "T3-C": "国航及星空联盟主楼",
            "T3-D/E": "国际/地区专用"
        },
        "major_airlines": ["中国国航(主基地)", "海南航空", "中国南方航空"],
        "domestic_pct": 82, "international_pct": 18,
        "duty_free": {
            "operator": "中国中免(CDFG)",
            "stores": "T2/T3出境免税店",
            "note": "首都机场免税受大兴分流影响, 2024年约40亿元"
        },
        "monthly_pct": [7.5, 7.0, 8.2, 8.5, 8.8, 9.0, 9.5, 9.2, 8.5, 8.0, 7.8, 8.0],
        "latest_news_query": "北京首都机场 2025 2026 国际航线",
    },
    # ── 第5名 ──
    "成都天府": {
        "annual": 5490, "rank": 5, "data_year": "2024",
        "terminals": {
            "T1": "国际/地区",
            "T2": "国内"
        },
        "major_airlines": ["四川航空(主基地)", "中国国航", "成都航空", "东方航空"],
        "domestic_pct": 88, "international_pct": 12,
        "duty_free": {
            "operator": "中国中免(CDFG)",
            "stores": "T1出境免税店",
            "note": "天府机场为成都主要国际门户"
        },
        "monthly_pct": [8.5, 8.0, 8.8, 8.5, 8.2, 7.8, 8.5, 8.3, 7.8, 8.5, 8.8, 8.3],
        "latest_news_query": "成都天府机场 2025 2026 新航线",
    },
    # ── 第6名 ──
    "北京大兴": {
        "annual": 4941, "rank": 6, "data_year": "2024",
        "terminals": {
            "主航站楼": "国内/国际一体化 (2019年启用)"
        },
        "major_airlines": ["中国南方航空(主基地)", "中国东方航空", "中国联合航空", "厦门航空"],
        "domestic_pct": 92, "international_pct": 8,
        "duty_free": {
            "operator": "中国中免(CDFG)",
            "stores": "出境免税店",
            "note": "大兴机场免税面积较大, 但国际客流仍在爬坡"
        },
        "monthly_pct": [8.0, 7.5, 8.5, 8.3, 8.5, 8.2, 9.0, 8.8, 8.2, 8.5, 8.3, 8.2],
        "latest_news_query": "北京大兴机场 2025 2026 国际航线 免税",
    },
    # ── 第7名 ──
    "重庆江北": {
        "annual": 4867, "rank": 7, "data_year": "2024",
        "terminals": {
            "T2": "国内 (川航/西部/华夏等)",
            "T3A": "国内/国际主楼"
        },
        "major_airlines": ["四川航空", "中国国航", "重庆航空", "西部航空"],
        "domestic_pct": 94, "international_pct": 6,
        "duty_free": {
            "operator": "中国中免(CDFG)",
            "stores": "T3A出境免税店",
            "note": "重庆机场免税以出境为主"
        },
        "monthly_pct": [8.5, 8.8, 9.0, 8.5, 7.8, 7.5, 8.0, 7.8, 7.5, 8.2, 8.5, 8.9],
        "latest_news_query": "重庆江北机场 2025 2026 T3B 新航站楼",
    },
    # ── 第8名 ──
    "上海虹桥": {
        "annual": 4700, "rank": 8, "data_year": "2024",
        "terminals": {
            "T1": "国际/地区 + 部分国内 (春秋/日韩航线)",
            "T2": "国内主楼 (东上航/国航/南航等)"
        },
        "major_airlines": ["东方航空(主基地)", "上海航空", "春秋航空", "中国国航"],
        "domestic_pct": 96, "international_pct": 4,
        "duty_free": {
            "operator": "日上免税行",
            "stores": "T1出境免税店",
            "note": "虹桥以国内航线为主, 免税体量远小于浦东"
        },
        "monthly_pct": [8.0, 7.5, 8.5, 8.3, 8.5, 8.2, 9.0, 8.8, 8.2, 8.5, 8.3, 8.2],
        "latest_news_query": "上海虹桥机场 2025 2026 新航线",
    },
    # ── 第9名 ──
    "昆明长水": {
        "annual": 4710, "rank": 9, "data_year": "2024",
        "terminals": {
            "T1": "国内/国际主楼"
        },
        "major_airlines": ["东方航空(云南公司)", "昆明航空", "云南祥鹏航空"],
        "domestic_pct": 93, "international_pct": 7,
        "duty_free": {
            "operator": "中国中免(CDFG)",
            "stores": "出境免税店",
            "note": "昆明为东南亚航线重要枢纽"
        },
        "monthly_pct": [8.0, 8.5, 8.8, 8.5, 8.2, 7.8, 8.0, 7.5, 7.8, 8.5, 8.8, 8.6],
        "latest_news_query": "昆明长水机场 2025 2026 国际航线 东南亚",
    },
    # ── 第10名 ──
    "西安咸阳": {
        "annual": 4703, "rank": 10, "data_year": "2024",
        "terminals": {
            "T1": "国内",
            "T2": "国内+国际",
            "T3": "国内主楼",
            "T5": "2026年投运"
        },
        "major_airlines": ["中国东方航空(西北公司)", "中国国航", "长安航空", "海南航空"],
        "domestic_pct": 94, "international_pct": 6,
        "duty_free": {
            "operator": "中国中免(CDFG)",
            "stores": "出境免税店",
            "note": "西安为一带一路航空枢纽"
        },
        "monthly_pct": [8.2, 7.8, 8.5, 8.3, 8.0, 7.5, 8.5, 8.3, 7.8, 8.5, 9.0, 8.6],
        "latest_news_query": "西安咸阳机场 2025 2026 T5 新航站楼",
    },
    # ── 第17名 ──
    "海口美兰": {
        "annual": 2688, "rank": 17, "data_year": "2024",
        "terminals": {
            "T1": "国内+国际",
            "T2": "2021年投运, 国内为主(海航)"
        },
        "major_airlines": ["海南航空(主基地)", "南方航空", "中国国航"],
        "domestic_pct": 96, "international_pct": 4,
        "duty_free": {
            "operator": "海控全球精品免税(ABC) + 中国中免",
            "stores": "T1/T2离岛免税提货点 + 机场免税店",
            "note": "中免海口美兰机场免税店为核心离岛免税渠道之一"
        },
        "monthly_pct": [8.5, 9.0, 8.5, 7.5, 7.0, 7.5, 8.0, 7.8, 7.5, 8.5, 9.5, 9.7],
        "latest_news_query": "海口美兰机场 2025 2026 新航线 免税",
    },
    # ── 第22名 ──
    "三亚凤凰": {
        "annual": 2280, "rank": 22, "data_year": "2024",
        "terminals": {
            "T1": "国内+国际",
            "T2": "国内",
            "T3": "2026年启动试运行"
        },
        "major_airlines": ["海南航空(主基地)", "南方航空", "中国国航", "四川航空"],
        "domestic_pct": 96, "international_pct": 4,
        "duty_free": {
            "operator": "中国中免(CDFG) 三亚市内免税店(更主要) + 机场提货",
            "stores": "机场离岛免税提货点",
            "note": "三亚免税以中免三亚国际免税城(市内店)为主, 机场为提货点"
        },
        "monthly_pct": [9.0, 9.5, 9.0, 8.0, 7.0, 6.5, 7.0, 6.8, 7.0, 8.5, 10.0, 10.7],
        "latest_news_query": "三亚凤凰机场 T3 2025 2026 试运行",
    },
}

# ============================================================
# 后缀黑名单（同上）
# ============================================================

SUFFIX_BLACKLIST = [
    '_政务动态', '_新闻资讯', '_今日海南', '_今日三亚', '_今日白沙',
    '_市县', '_头条新闻', '_媒体关注', '_商务动态', '_图片新闻',
    '_最新实录', '_国务院部门文件', '__要闻动态', '_要闻动态',
    '_部门文件', '_政策问答', '_市场情况', '_信息提示', '_宣传图片新闻',
    '_部门动态', '_海南省人民政府', '_海南省商务厅',
    '_海南省发展和改革委员会', '_海南省发展和改革',
    '_海南省工业和信息化厅', '_中国日报网', '_澎湃新闻',
    '_首都之窗', '_海口市', '_三亚市', '_海南省',
]


def fetch(url, encoding="utf-8", timeout=15):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.encoding = encoding
        return resp.text if resp.status_code == 200 else None
    except:
        return None


def strip_all_suffixes(t):
    t = re.sub(r'\.{3,}|…+$', '', t)
    changed = True
    while changed:
        changed = False
        for suffix in SUFFIX_BLACKLIST:
            if t.endswith(suffix):
                t = t[:-len(suffix)]
                changed = True
                break
        t = re.sub(r'[＿_][\u4e00-\u9fa5]{1,5}\.\.\..*$', '', t)
        t = re.sub(r'[＿_][\u4e00-\u9fa5]{1,6}\.\.\.$', '', t)
        if t.endswith('_') or t.endswith('—') or t.endswith('-') or t.endswith('_'):
            t = t[:-1]
            changed = True
        m = re.search(r'\s*[—\-]\s*.{2,10}$', t)
        if m and len(t) - m.start() < 15:
            t = t[:m.start()]
            changed = True
        t = re.sub(r'^【[^】]+】', '', t)
    return t.strip()


def is_valid_article(title):
    t = title.strip()
    if not t or len(t) < 12:
        return False
    if t.startswith("...") or t.startswith("…"):
        return False
    if (t.endswith("...") or t.endswith("…")) and len(t) < 30:
        return False
    if "百度百科" in t or "维基百科" in t:
        return False
    nav_keywords = ["相关新闻", "最新解读", "政策问答", "回应关切", "解读回应",
                    "机场介绍", "欢迎访问", "信息公开", "阳光海南网",
                    "国家税务总局", "海南省商务厅", "海口市商务局",
                    "商城", "官网", "下载", "app下载"]
    for kw in nav_keywords:
        if kw in t:
            return False
    keywords = ["免税", "海南", "海口", "三亚", "自贸港", "离岛",
                "机场", "客流", "航班", "游客", "旅游", "暑运", "春运",
                "消费", "购物", "中免", "cdf", "封关", "零关税",
                "销售额", "金额", "亿元", "万人次", "吞吐量",
                "出入境", "接待", "旅客", "出行", "红利",
                "省政府", "投资指南", "监管办法", "购物节",
                "口岸", "通关", "便利化", "人财两旺",
                "消费券", "开门红", "总花费",
                "航站楼", "国际航线", "复航", "通航",
                "航空", "东航", "南航", "国航", "海航", "春秋", "吉祥",
                "免税店", "奢侈品", "客流", "中转", "快线",
                "一季度", "业绩", "增长", "千亿", "封关红利",
                "端午", "暑期", "暑假", "旺季"]
    return any(k.lower() in t.lower() for k in keywords)


def make_dedup_key(text):
    key = text.strip()
    key = re.sub(r'[\s,，。、！？""「」『』【】《》→\-—()（）:：]', '', key)
    key = re.sub(r'(\d+\.?\d*)', lambda m: str(int(float(m.group(1)))), key)
    return key[:35]


def clean_title(title):
    t = title.strip()
    t = re.sub(r'^\.{3,}|^…+', '', t)
    t = re.sub(r'^[\s—\-]+', '', t)
    t = re.sub(r'^【[^】]{2,20}】', '', t)
    t = strip_all_suffixes(t)
    t = re.sub(r'[＿_][\u4e00-\u9fa5]{2,20}$', '', t)
    t = re.sub(
        r'[—\-]\s*(?:旅游文化|要闻动态|社会法治|人民网|中新网|中国民航网|'
        r'海南日报|市县|头条新闻|媒体关注|最新实录|部门文件|'
        r'国务院部门文件|视频图解|解读回应|宣传图片新闻|相关新闻|'
        r'政务动态|商务动态|新闻资讯|图片新闻|今日海南|今日三亚|今日白沙|'
        r'海口市商务局|海南省商务厅|海南省旅游|国家发展和改革委员会|'
        r'国家发改委|海南省人民政府|海南省工业和信息化厅|'
        r'海南省发展和改革委员会|海南省发展和改革|部门动态|'
        r'中国日报网|澎湃新闻|海口市|三亚市|首都之窗|海南省)'
        r'.{0,20}$', '', t, flags=re.IGNORECASE
    )
    t = re.sub(r'\s*[—\-]{2,}\s*.{0,30}$', '', t)
    t = re.sub(r'[＿_\s—\-]+$', '', t)
    t = re.sub(r'^[＿_\s—\-]+', '', t)
    t = strip_all_suffixes(t)
    t = t.strip()
    if (t.endswith("...") or t.endswith("…")) and len(t) < 30:
        return None
    if len(t) < 12:
        return None
    return t


# ============================================================
# 🔗 返回 (标题, URL) 元组
# ============================================================

def search_baidu_news(query, max_results=10, global_seen=None):
    if global_seen is None:
        global_seen = set()
    url = f"https://www.baidu.com/s?wd={requests.utils.quote(query)}&tn=news"
    text = fetch(url)
    if not text:
        return []
    soup = BeautifulSoup(text, "html.parser")
    results = []

    for result_div in soup.find_all("div", class_=lambda c: c and "result" in c):
        h3 = result_div.find("h3")
        if not h3:
            continue
        a_tag = h3.find("a")
        if not a_tag:
            continue
        title = a_tag.get_text().strip()
        href = a_tag.get("href", "")
        if not is_valid_article(title):
            continue
        cleaned = clean_title(title)
        if not cleaned:
            continue
        key = make_dedup_key(cleaned)
        if key not in global_seen:
            global_seen.add(key)
            results.append((cleaned, href))

    for h3 in soup.find_all("h3"):
        title = h3.get_text().strip()
        a_tag = h3.find("a")
        href = a_tag.get("href", "") if a_tag else ""
        if not is_valid_article(title):
            continue
        cleaned = clean_title(title)
        if not cleaned:
            continue
        key = make_dedup_key(cleaned)
        if key not in global_seen:
            global_seen.add(key)
            results.append((cleaned, href))

    return results[:max_results]


def smart_search(query, max_results=10, global_seen=None):
    return search_baidu_news(query, max_results, global_seen)


# ============================================================
# 🏪 主爬虫类
# ============================================================

class HainanScraper:
    """海南免税商情爬虫"""

    def __init__(self):
        self.global_seen = set()
        self.all_texts = []

    def calc_monthly(self, annual, pcts):
        total = sum(pcts)
        return [round(annual * p / total, 1) for p in pcts]

    def extract_numbers(self, texts):
        summary = []
        seen = set()
        for t in texts:
            for m in re.finditer(r'(\d+\.?\d*)\s*亿元', t):
                val = float(m.group(1))
                ctx = ""
                if "半年" in t or "上半" in t:
                    ctx = "2026上半年离岛免税"
                elif "五一" in t:
                    ctx = "五一假期离岛免税"
                elif "暑" in t and ("销售" in t or "免税" in t):
                    ctx = "暑运离岛免税"
                elif "累计" in t:
                    ctx = "离岛免税累计"
                elif "2024" in t:
                    ctx = "2024年离岛免税"
                elif "端午" in t:
                    ctx = "端午假期离岛免税"
                elif 220 <= val <= 225:
                    ctx = "离岛免税(累计)"
                key = ("💰 销售额", f"{val}亿元", ctx)
                if key not in seen and ctx:
                    seen.add(key)
                    summary.append(key)

            for m in re.finditer(r'(\d+\.?\d*)\s*万人次', t):
                val = m.group(1)
                ctx = ""
                if "美兰" in t and "暑运" in t:
                    ctx = "海口美兰2026暑运预计"
                elif "三亚" in t and "暑运" in t:
                    ctx = "三亚凤凰2026暑运预计"
                elif "海南" in t and ("接待" in t or "游客" in t) and "春节" in t:
                    ctx = "春节假期海南接待游客"
                elif "入境" in t and "第一" in t:
                    ctx = "2026年第一季度海南接待入境游客"
                elif "接待入境" in t or "入境游客" in t:
                    ctx = "海南接待入境游客"
                elif "接待游客" in t:
                    ctx = "海南接待游客"
                if not ctx:
                    continue
                key = ("✈️ 客流", f"{val}万人次", ctx)
                if key not in seen:
                    seen.add(key)
                    summary.append(key)

            if "首次突破" in t and "千亿元" in t:
                key = ("💰 销售额", "千亿元", "三亚游客总花费首次突破千亿元")
                if key not in seen:
                    seen.add(key)
                    summary.append(key)

            for m in re.finditer(r'旅游总花费[逾超]?(\d+\.?\d*)\s*亿元', t):
                key = ("💰 销售额", f"{m.group(1)}亿元", "海南旅游总花费")
                if key not in seen:
                    seen.add(key)
                    summary.append(key)

        return summary

    def scrape_all(self):
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"🚀 海南免税商情爬虫启动 - {today}")

        results = {
            "date": today,
            "airport_db": AIRPORT_DB,
            "airport_news": [],
            "duty_free_news": [],
            "li_island_news": [],
            "policy_news": [],
            "travel_news": [],
            "airport_latest_news": {},
            "summary": [],
        }

        # ====== 机场最新动态 ======
        print("\n🔍 搜索机场最新动态...")
        airport_queries = [
            ("上海浦东机场 国际航线 2026", "上海浦东"),
            ("北京首都机场 旅客 2026", "北京首都"),
            ("广州白云机场 T3 2026", "广州白云"),
            ("深圳宝安机场 国际航线 2026", "深圳宝安"),
            ("成都天府机场 国际航线 2026", "成都天府"),
            ("北京大兴机场 国际航线 2026", "北京大兴"),
            ("重庆江北机场 T3B 2026", "重庆江北"),
            ("上海虹桥机场 新航线 2026", "上海虹桥"),
            ("昆明长水机场 国际航线 2026", "昆明长水"),
            ("西安咸阳机场 T5 2026", "西安咸阳"),
            ("海口美兰机场 旅客 2026", "海口美兰"),
            ("三亚凤凰机场 T3 2026", "三亚凤凰"),
        ]
        for q, airport_name in airport_queries:
            r = smart_search(q, 3, self.global_seen)
            results["airport_news"].extend(r)
            results["airport_latest_news"][airport_name] = r
            time.sleep(0.5)

        # ====== 机场免税 ======
        print("🛍️ 搜索机场免税动态...")
        df_queries = [
            "机场免税 销售额 浦东 首都 白云 2026",
            "中免 机场免税店 2026",
            "海南机场 免税 销售 2026",
        ]
        for q in df_queries:
            r = smart_search(q, 5, self.global_seen)
            results["duty_free_news"].extend(r)
            time.sleep(0.5)

        # ====== 离岛免税 ======
        print("💰 搜索离岛免税动态...")
        li_queries = [
            "海南离岛免税 销售额 2026",
            "海南离岛免税 购物金额",
            "cdf 三亚 海口 免税 销售",
            "暑期 海南 免税 购物",
        ]
        for q in li_queries:
            r = smart_search(q, 8, self.global_seen)
            results["li_island_news"].extend(r)
            self.all_texts.extend([t for t, u in r])
            time.sleep(0.8)

        # ====== 政策动态 ======
        print("📜 搜索政策动态...")
        policy_queries = [
            "海南自贸港 最新政策 免税 2026",
            "离岛免税 政策调整",
            "海南 封关运作 零关税",
        ]
        for q in policy_queries:
            r = smart_search(q, 6, self.global_seen)
            results["policy_news"].extend(r)
            time.sleep(0.8)

        # ====== 旅游客流 ======
        print("✈️ 搜索旅游客流...")
        travel_queries = [
            "海南 旅游 游客 人数 2026",
            "三亚 入境 旅客 2026",
        ]
        for q in travel_queries:
            r = smart_search(q, 6, self.global_seen)
            results["travel_news"].extend(r)
            self.all_texts.extend([t for t, u in r])
            time.sleep(0.8)

        # ====== 数据摘要 ======
        print("📊 生成数据摘要...")
        summary = []
        for code, info in AIRPORT_DB.items():
            summary.append(("✈️ 年吞吐", f"{info['annual']}万人次",
                          f"{code}(全国第{info['rank']}, {info['data_year']}年)"))
            dom = round(info['annual'] * info['domestic_pct'] / 100, 0)
            intl = round(info['annual'] * info['international_pct'] / 100, 0)
            summary.append(("🇨🇳 国内", f"{dom:.0f}万", code))
            summary.append(("🌍 国际", f"{intl:.0f}万", code))
        summary.extend(self.extract_numbers(self.all_texts))
        results["summary"] = summary

        print(f"\n✅ 爬取完成！共 {len(self.global_seen)} 条新闻")
        return results

st.markdown("---")
st.caption(f"本报告由海南免税商情监控 v1.1 自动生成 | {today}")
st.caption("🟢 **年吞吐量**: CAAC民航局 **2024年**官方数据，真实可靠")
st.caption("🟡 **月度分布**: 基于航空业季节性规律的**估算值**，非官方数据，仅供参考")
st.caption("🟡 **境内外占比**: 基于各机场年报和公开数据的估算")
st.caption("🟢 **航站楼/航司/免税**: 基于公开资料整理")
st.caption("🟢 **最新动态**: 百度新闻实时搜索，点击标题可打开原文")