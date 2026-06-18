# pages/7_新闻聚合器.py
import streamlit as st
import pandas as pd
import feedparser
import requests
from datetime import datetime, timedelta
import hashlib
import re
import time

# 可选：安装 newspaper3k 后可启用
try:
    from newspaper import Article, Config
    HAS_NEWSPAPER = True
except ImportError:
    HAS_NEWSPAPER = False

# 可选：安装 trafilatura 后可启用
try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

st.set_page_config(page_title="新闻聚合器", layout="wide")
st.title("📰 海南免税·新闻聚合器")

# ============================================================
# 稳定的 RSS 新闻源（不会反爬，100% 可用）
# ============================================================
RSS_FEEDS = {
    "百度热榜": "https://top.baidu.com/board?tab=realtime",
    "新浪新闻": "https://rss.news.sina.com.cn/",
    "网易新闻": "https://news.163.com/special/0001220O/news_json.js",
    "36氪": "https://36kr.com/feed",
    "虎嗅": "https://www.huxiu.com/rss/0.xml",
}

# 海南免税相关的关键词
KEYWORDS = ["海南", "免税", "离岛", "中免", "CDF", "三亚", "海口", "免税店"]

# ============================================================
# 新闻爬虫引擎
# ============================================================
class NewsEngine:
    """多引擎新闻爬虫，含降级策略"""

    @staticmethod
    def _dedup(items):
        """去重"""
        seen = set()
        result = []
        for item in items:
            key = hashlib.md5(item['title'].encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    @staticmethod
    def fetch_rss(feed_url, source_name, max_items=10):
        """从 RSS 订阅源获取新闻（最稳定方式）"""
        items = []
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:max_items]:
                title = entry.get('title', '')
                link = entry.get('link', '')
                published = entry.get('published', '')
                summary = entry.get('summary', '')[:200]

                # 检查是否包含关键词
                if any(kw in title for kw in KEYWORDS):
                    items.append({
                        'title': title[:120],
                        'link': link,
                        'summary': summary[:200],
                        'source': source_name,
                        'date': published[:10] if published else datetime.now().strftime('%Y-%m-%d'),
                        'method': 'RSS'
                    })
        except Exception as e:
            st.sidebar.warning(f"{source_name} RSS失败: {str(e)[:30]}")
        return items

    @staticmethod
    def fetch_baidu_hot():
        """百度热搜榜（使用模拟浏览器请求）"""
        items = []
        try:
            headers = {
                'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                               'AppleWebKit/537.36 (KHTML, like Gecko) '
                               'Chrome/120.0.0.0 Safari/537.36'),
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://top.baidu.com/',
            }
            # 百度热搜 API
            url = "https://top.baidu.com/api/board?tab=realtime"
            resp = requests.get(url, headers=headers, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                cards = data.get('data', {}).get('cards', [])
                for card in cards:
                    for item in card.get('content', []):
                        title = item.get('word', item.get('query', ''))
                        if any(kw in title for kw in KEYWORDS):
                            items.append({
                                'title': title[:120],
                                'link': f"https://www.baidu.com/s?wd={title}",
                                'summary': '',
                                'source': '百度热搜',
                                'date': datetime.now().strftime('%Y-%m-%d'),
                                'method': 'API'
                            })
        except Exception as e:
            st.sidebar.warning(f"百度热搜失败: {str(e)[:30]}")
        return items

    @staticmethod
    def fetch_weibo_hot():
        """微博热搜（免费接口）"""
        items = []
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            # 微博热搜 API
            url = "https://weibo.com/ajax/side/hotSearch"
            resp = requests.get(url, headers=headers, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                hot_list = (data.get('data', {})
                           .get('realtime', [])[:50])

                for item in hot_list:
                    title = item.get('word', '')
                    if any(kw in title for kw in KEYWORDS):
                        items.append({
                            'title': title[:120],
                            'link': f"https://s.weibo.com/weibo?q={title}",
                            'summary': f"热搜排名: {item.get('rank', 'N/A')}",
                            'source': '微博热搜',
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'method': 'API'
                        })
        except Exception as e:
            st.sidebar.warning(f"微博热搜失败: {str(e)[:30]}")
        return items

    @staticmethod
    def fetch_neteasy():
        """网易新闻 JSON 接口"""
        items = []
        try:
            url = "https://news.163.com/special/0001220O/news_json.js"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=10)

            if resp.status_code == 200:
                # 网易返回的是 JSONP，需要提取 JSON
                text = resp.text
                json_match = re.search(r'data\s*=\s*(\[.*?\])\s*;', text, re.DOTALL)
                if json_match:
                    import json
                    data = json.loads(json_match.group(1))
                    for item in data[:30]:
                        title = item.get('title', '') or item.get('name', '')
                        link = item.get('url', item.get('link', ''))
                        if any(kw in title for kw in KEYWORDS):
                            items.append({
                                'title': title[:120],
                                'link': link,
                                'summary': item.get('digest', '')[:200],
                                'source': '网易新闻',
                                'date': datetime.now().strftime('%Y-%m-%d'),
                                'method': 'API'
                            })
        except Exception as e:
            st.sidebar.warning(f"网易新闻失败: {str(e)[:30]}")
        return items

    @classmethod
    def search_with_newspaper(cls, keyword="海南 免税", max_articles=5):
        """使用 Newspaper3k 搜索（需要安装）"""
        items = []
        if not HAS_NEWSPAPER:
            return items

        try:
            # 使用 Google News RSS 进行搜索（稳定且免费）
            search_url = (
                f"https://news.google.com/rss/search?"
                f"q={keyword}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
            )
            feed = feedparser.parse(search_url)

            for entry in feed.entries[:max_articles]:
                title = entry.get('title', '')
                link = entry.get('link', '')
                if not title or not link:
                    continue

                # 使用 newspaper 提取文章详情
                try:
                    config = Config()
                    config.browser_user_agent = (
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36'
                    )
                    config.request_timeout = 10

                    article = Article(link, config=config)
                    article.download()
                    article.parse()

                    items.append({
                        'title': title[:120],
                        'link': link,
                        'summary': (article.text[:300] if article.text
                                   else entry.get('summary', '')[:200]),
                        'source': 'Google News',
                        'date': (entry.get('published', '')[:10]
                                or datetime.now().strftime('%Y-%m-%d')),
                        'method': 'Newspaper3k'
                    })
                except Exception:
                    # 降级：只保存标题和链接
                    items.append({
                        'title': title[:120],
                        'link': link,
                        'summary': entry.get('summary', '')[:200],
                        'source': 'Google News',
                        'date': (entry.get('published', '')[:10]
                                or datetime.now().strftime('%Y-%m-%d')),
                        'method': 'RSS'
                    })
        except Exception as e:
            st.sidebar.warning(f"Google News失败: {str(e)[:30]}")

        return items

    @classmethod
    def collect_all(cls, keyword="海南 免税"):
        """聚合所有数据源"""
        all_items = []

        progress_text = "正在抓取多源新闻..."
        progress_bar = st.progress(0, text=progress_text)

        # 数据源列表 (name, func, weight)
        sources = [
            ("百度热搜", cls.fetch_baidu_hot, 0.2),
            ("微博热搜", cls.fetch_weibo_hot, 0.2),
            ("网易新闻", cls.fetch_neteasy, 0.15),
            ("Google News", lambda: cls.search_with_newspaper(keyword), 0.15),
        ]

        for i, (name, func, _) in enumerate(sources):
            status_text = f"📡 正在抓取 {name}..."
            progress_bar.progress((i + 1) / len(sources), text=status_text)

            try:
                result = func()
                all_items.extend(result)
                st.sidebar.success(f"✅ {name}: {len(result)} 条")
            except Exception as e:
                st.sidebar.error(f"❌ {name}: {str(e)[:30]}")

            time.sleep(0.5)  # 避免请求过快

        progress_bar.empty()

        # 去重并排序
        all_items = cls._dedup(all_items)
        all_items.sort(key=lambda x: x.get('date', ''), reverse=True)

        return all_items

# ============================================================
# 主界面
# ============================================================

# 初始化
if 'news_data' not in st.session_state:
    st.session_state.news_data = []
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None

# 侧边栏控制
with st.sidebar:
    st.header("⚙️ 控制面板")

    keyword = st.text_input("搜索关键词", "海南 免税")

    col1, col2 = st.columns(2)
    with col1:
        refresh_btn = st.button("🔄 刷新", type="primary", use_container_width=True)
    with col2:
        auto_refresh = st.checkbox("自动刷新", value=False)

    st.markdown("---")
    st.markdown("### 📊 数据源状态")
    st.markdown(f"- Newspaper3k: {'✅ 已安装' if HAS_NEWSPAPER else '❌ 未安装'}")
    st.markdown(f"- Trafilatura: {'✅ 已安装' if HAS_TRAFILATURA else '❌ 未安装'}")

    if not HAS_NEWSPAPER:
        st.info("💡 安装 newspaper3k 可获取更多新闻:\n"
                "`pip install newspaper3k lxml_html_clean`")

# 刷新逻辑
if refresh_btn or (auto_refresh and (
    st.session_state.last_refresh is None or
    (datetime.now() - st.session_state.last_refresh).seconds > 300
)):
    with st.spinner("正在聚合多源新闻..."):
        st.session_state.news_data = NewsEngine.collect_all(keyword)
        st.session_state.last_refresh = datetime.now()

news = st.session_state.news_data

# 主内容
st.subheader(f"📊 共找到 {len(news)} 条相关资讯")

if not news:
    st.warning("""
    ⚠️ 暂未找到相关新闻，可能原因：

    1. **缺少依赖包** - 建议安装 newspaper3k:
       ```
       pip install newspaper3k lxml_html_clean
       ```

    2. **今日暂无相关热点** - 可以试试手动搜索

    3. **网络问题** - 检查是否能访问 Google News

    💡 **替代方案**: 点击下方按钮使用百度搜索
    """)

    # 手动搜索备选方案
    search_term = st.text_input("🔍 手动搜索", "海南 免税 2025")
    if st.button("使用百度搜索"):
        import urllib.parse
        encoded = urllib.parse.quote(search_term)
        url = f"https://www.baidu.com/s?wd={encoded}"
        st.markdown(f"[🔗 点击打开百度搜索结果]({url})")
else:
    # 统计
    methods = [n['method'] for n in news if 'method' in n]
    col1, col2, col3 = st.columns(3)
    col1.metric("总条数", len(news))
    col2.metric("数据源数", len(set(n['source'] for n in news)))
    col3.metric("最新", news[0]['date'] if news else '-')

    # 筛选
    sources = list(set(n['source'] for n in news))
    selected_sources = st.multiselect("按来源筛选", sources, default=sources)

    filtered = [n for n in news if n['source'] in selected_sources]

    # 分页显示
    page_size = 10
    total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
    page = st.number_input("页码", 1, total_pages, 1)

    start = (page - 1) * page_size
    end = start + page_size

    for i, n in enumerate(filtered[start:end], start + 1):
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{i}. {n['title']}**")
                if n.get('summary'):
                    st.caption(f"📝 {n['summary'][:150]}...")
            with col2:
                st.markdown(f"📰 {n['source']}")
                st.caption(f"📅 {n['date']}")
            with col3:
                if n.get('link'):
                    st.markdown(f"[🔗 查看原文]({n['link']})")
                if n.get('method'):
                    st.caption(f"方式: {n.get('method', '')}")

    # 导出功能
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 导出为 CSV", use_container_width=True):
            df = pd.DataFrame(filtered)
            csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
            st.download_button(
                "点击下载",
                csv,
                f"海南免税新闻_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            )
    with col2:
        if st.button("📋 复制到剪贴板", use_container_width=True):
            text = "\n\n".join([
                f"{i}. {n['title']}\n来源: {n['source']} | 日期: {n['date']}"
                for i, n in enumerate(filtered, 1)
            ])
            st.code(text, language="text")
            st.info("请手动复制上方内容")

# 页脚
st.markdown("---")
st.caption(
    f"🤖 数据来源: Google News RSS / 百度热搜 / 微博热搜 / 网易新闻 | "
    f"引擎: Newspaper3k{' ✅' if HAS_NEWSPAPER else ' ❌'} | "
    f"最后更新: {st.session_state.last_refresh.strftime('%H:%M:%S') if st.session_state.last_refresh else 'N/A'}"
)
