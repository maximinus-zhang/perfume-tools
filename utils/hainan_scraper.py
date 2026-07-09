"""
海南免税商情监控 v6.3 - Streamlit 模块版
用法: from utils.hainan_scraper import HainanScraper
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
# 🏢 机场深度知识库
# ============================================================

AIRPORT_DB = {
    "上海浦东": {
        "annual": 7679, "rank": 1,
        "terminals": {
            "T1": "国际/地区 + 部分国内 (东上航)",
            "T2": "国内为主 (国航/南航/吉祥/春秋等)"
        },
        "major_airlines": ["东方航空(主基地)", "上海航空", "春秋航空", "吉祥航空", "中国国航"],
        "domestic_pct": 78,
        "international_pct": 22,
        "duty_free": {
            "operator": "中国中免(CDFG) + 日上免税行",
            "stores": "T1/T2出境及入境免税店",
            "note": "浦东机场免税销售额占中国机场免税~40%, 2024年约70亿元"
        },
        "monthly_distribution": [7.8, 7.2, 8.5, 8.3, 8.6, 8.8, 9.2, 9.0, 8.2, 8.5, 8.0, 7.9],
    },
    "广州白云": {
        "annual": 7637, "rank": 2,
        "terminals": {
            "T1": "国内为主(改造中, 航司已转场至T3)",
            "T2": "南航及天合联盟主楼",
            "T3": "2026年投运, 承接原T1国内航司"
        },
        "major_airlines": ["南方航空(主基地)", "中国国航", "海南航空", "九元航空"],
        "domestic_pct": 86,
        "international_pct": 14,
        "duty_free": {
            "operator": "中国中免(CDFG)",
            "stores": "T1/T2出境免税店",
            "note": "2024年T1改造影响部分免税面积"
        },
        "monthly_distribution": [8.0, 7.5, 8.8, 8.5, 8.7, 8.5, 8.8, 8.6, 8.2, 8.0, 7.8, 8.6],
    },
    "北京首都": {
        "annual": 5288, "rank": 3,
        "terminals": {
            "T1": "暂停运营改造(2025年起)",
            "T2": "国内+国际 (南航/东航/海航部分)",
            "T3-C": "国航及星空联盟主楼",
            "T3-D/E": "国际/地区专用"
        },
        "major_airlines": ["中国国航(主基地)", "海南航空", "中国南方航空"],
        "domestic_pct": 82,
        "international_pct": 18,
        "duty_free": {
            "operator": "中国中免(CDFG)",
            "stores": "T2/T3出境免税店",
            "note": "首都机场免税受大兴分流影响, 2024年约40亿元"
        },
        "monthly_distribution": [7.5, 7.0, 8.2, 8.5, 8.8, 9.0, 9.5, 9.2, 8.5, 8.0, 7.8, 8.0],
    },
    "海口美兰": {
        "annual": 2688, "rank": 17,
        "terminals": {
            "T1": "国内+国际",
            "T2": "2021年投运, 国内为主(海航)"
        },
        "major_airlines": ["海南航空(主基地)", "南方航空", "中国国航"],
        "domestic_pct": 96,
        "international_pct": 4,
        "duty_free": {
            "operator": "海控全球精品免税(ABC) + 中国中免",
            "stores": "T1/T2离岛免税提货点 + 机场免税店",
            "note": "中免海口美兰机场免税店为核心离岛免税渠道之一"
        },
        "monthly_distribution": [8.5, 9.0, 8.5, 7.5, 7.0, 7.5, 8.0, 7.8, 7.5, 8.5, 9.5, 9.7],
    },
    "三亚凤凰": {
        "annual": 2280, "rank": 22,
        "terminals": {
            "T1": "国内+国际",
            "T2": "国内",
            "T3": "2026年启动试运行"
        },
        "major_airlines": ["海南航空(主基地)", "南方航空", "中国国航", "四川航空"],
        "domestic_pct": 96,
        "international_pct": 4,
        "duty_free": {
            "operator": "中国中免(CDFG) 三亚市内免税店(更主要) + 机场提货",
            "stores": "机场离岛免税提货点",
            "note": "三亚免税以中免三亚国际免税城(市内店)为主, 机场为提货点"
        },
        "monthly_distribution": [9.0, 9.5, 9.0, 8.0, 7.0, 6.5, 7.0, 6.8, 7.0, 8.5, 10.0, 10.7],
    },
}

# ============================================================
# 后缀黑名单
# ============================================================

SUFFIX_BLACKLIST = [
    '_政务动态', '_新闻资讯', '_今日海南', '_今日三亚', '_今日白沙',
    '_市县', '_头条新闻', '_媒体关注', '_商务动态', '_图片新闻',
    '_最新实录', '_国务院部门文件',
    '__要闻动态', '_要闻动态', '_部门文件', '_政策问答',
    '_市场情况', '_信息提示', '_宣传图片新闻',
    '_部门动态', '_海南省人民政府', '_海南省商务厅',
    '_海南省发展和改革委员会', '_海南省发展和改革',
    '_海南省工业和信息化厅', '_中国日报网', '_澎湃新闻',
    '_首都之窗', '_海口市', '_三亚市', '_海南省',
]

# ============================================================
# 工具函数
# ============================================================

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
    if any(kw in t for kw in ["商城", "官方商城", "app下载", "APP下载", "手机版", "下载 v"]):
        return False
    if "官网" in t or "官方网站" in t:
        return False
    if t.count("|") >= 2:
        return False
    if "大众点评" in t or "小红书" in t or "抖音" in t:
        return False
    if "剁手" in t or "薅到" in t or "羊毛" in t:
        return False
    if re.search(r'[（(].*有限公司[）)]', t):
        return False
    if t.endswith("有限公司") or t.endswith("集团有限公司"):
        return False
    if re.match(r'^旅客服务[—\-]', t) or re.match(r'^首页[—\-|]', t) or re.match(r'^欢迎访问', t):
        return False
    nav_keywords = ["相关新闻", "最新解读", "政策问答", "回应关切", "解读回应",
                    "机场介绍", "欢迎访问", "信息公开", "阳光海南网",
                    "国家税务总局", "海南省商务厅", "海口市商务局"]
    for kw in nav_keywords:
        if kw in t:
            return False
    if "微博" in t:
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


def search_baidu_news(query, max_results=10, global_seen=None):
    if global_seen is None:
        global_seen = set()
    url = f"https://www.baidu.com/s?wd={requests.utils.quote(query)}&tn=news"
    text = fetch(url)
    if not text:
        return []
    soup = BeautifulSoup(text, "html.parser")
    results = []
    for h3 in soup.find_all("h3"):
        title = h3.get_text().strip()
        if not is_valid_article(title):
            continue
        cleaned = clean_title(title)
        if not cleaned:
            continue
        key = make_dedup_key(cleaned)
        if key not in global_seen:
            global_seen.add(key)
            results.append(cleaned)
    for div in soup.find_all("div", class_=lambda c: c and "title" in c):
        title = div.get_text().strip()
        if not is_valid_article(title):
            continue
        cleaned = clean_title(title)
        if not cleaned:
            continue
        key = make_dedup_key(cleaned)
        if key not in global_seen:
            global_seen.add(key)
            results.append(cleaned)
    return results[:max_results]


def smart_search(query, max_results=10, global_seen=None):
    return search_baidu_news(query, max_results, global_seen)


# ============================================================
# 🏪 主爬虫类
# ============================================================

class HainanScraper:
    """海南免税商情爬虫 - 返回结构化数据供 Streamlit 使用"""

    def __init__(self):
        self.global_seen = set()
        self.all_texts = []

    def calc_monthly(self, annual, dist):
        total = sum(dist)
        return [round(annual * p / total, 1) for p in dist]

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
                elif 390 <= val <= 410:
                    ctx = "2023年离岛免税"
                key = ("💰 销售额", f"{val}亿元", ctx)
                if key not in seen and ctx:
                    seen.add(key)
                    summary.append(key)

            for m in re.finditer(r'(\d+\.?\d*)\s*万人次', t):
                val = m.group(1)
                ctx = ""
                airport = ""
                if "美兰" in t:
                    airport = "海口美兰"
                elif "凤凰" in t or "三亚机场" in t:
                    airport = "三亚凤凰"
                elif "海南" in t and ("接待" in t or "游客" in t or "入境" in t):
                    airport = "海南全省"
                if "暑运" in t:
                    ctx = f"{airport}2026暑运预计".strip()
                elif "春运" in t:
                    ctx = f"{airport}2026春运".strip()
                elif "春节" in t:
                    ctx = "春节假期海南接待游客"
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

            m = re.search(r'(\d+年第一季度).*?入境游客[近约]?(\d+\.?\d*)\s*万人次', t)
            if m:
                key = ("🌍 入境", f"{m.group(2)}万人次", m.group(1))
                if key not in seen:
                    seen.add(key)
                    summary.append(key)

        return summary

    def scrape_all(self):
        """运行全部爬取，返回结构化数据"""
        today = datetime.now().strftime("%Y-%m-%d")

        print(f"🚀 海南免税商情爬虫启动 - {today}")
        print("=" * 50)

        results = {
            "date": today,
            "airport_db": AIRPORT_DB,
            "airport_news": [],
            "duty_free_news": [],
            "li_island_news": [],  # 离岛免税
            "policy_news": [],
            "travel_news": [],
            "summary": [],
        }

        # ====== 机场最新动态 ======
        print("\n🔍 搜索机场最新动态...")
        airport_queries = [
            "上海浦东机场 国际航线 2026",
            "北京首都机场 旅客 2026",
            "广州白云机场 T3 2026",
            "海口美兰机场 旅客 暑运 2026",
            "三亚凤凰机场 T3 试运行 2026",
        ]
        for q in airport_queries:
            r = smart_search(q, 4, self.global_seen)
            results["airport_news"].extend(r)
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
            self.all_texts.extend(r)
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
            self.all_texts.extend(r)
            time.sleep(0.8)

        # ====== 数据摘要 ======
        print("📊 生成数据摘要...")
        summary = []
        for code, info in AIRPORT_DB.items():
            summary.append(("✈️ 年吞吐", f"{info['annual']}万人次", f"{code}(全国第{info['rank']})"))
            dom = round(info['annual'] * info['domestic_pct'] / 100, 0)
            intl = round(info['annual'] * info['international_pct'] / 100, 0)
            summary.append(("🇨🇳 国内", f"{dom:.0f}万", code))
            summary.append(("🌍 国际", f"{intl:.0f}万", code))
        summary.extend(self.extract_numbers(self.all_texts))
        results["summary"] = summary

        print(f"\n✅ 爬取完成！共获取新闻 {len(self.global_seen)} 条")
        return results
