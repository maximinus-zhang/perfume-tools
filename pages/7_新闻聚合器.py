import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import feedparser
import re
from datetime import datetime, timedelta
import hashlib

st.set_page_config(page_title="新闻聚合器", layout="wide")
st.title("📰 海南免税·多源新闻聚合器")

# ============================================================
# 多源爬虫
# ============================================================
class NewsCollector:
    @staticmethod
    def _dedup(items):
        seen = set()
        result = []
        for item in items:
            key = hashlib.md5(item['title'].encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    @staticmethod
    def crawl_360(query="海南 免税"):
        """360新闻"""
        items = []
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            resp = requests.get(
                f"https://news.so.com/ns?q={query}&rank=rank",
                headers=headers, timeout=10
            )
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for li in soup.find_all('li', class_='item'):
                    a = li.find('a')
                    if a and a.get_text(strip=True):
                        items.append({
                            'title': a.get_text(strip=True)[:120],
                            'link': a.get('href', ''),
                            'source': '360新闻',
                            'date': datetime.now().strftime('%Y-%m-%d')
                        })
        except Exception as e:
            st.warning(f"360新闻抓取失败: {e}")
        return items[:15]

    @staticmethod
    def crawl_baidu(query="海南 免税"):
        """百度新闻 RSS"""
        items = []
        try:
            # 使用百度新闻的 RSS 源
            url = f"https://news.baidu.com/ns?word={query}&tn=news&rtt=1"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for h3 in soup.find_all('h3', class_='c-title'):
                    a = h3.find('a')
                    if a:
                        items.append({
                            'title': a.get_text(strip=True)[:120],
                            'link': a.get('href', ''),
                            'source': '百度新闻',
                            'date': datetime.now().strftime('%Y-%m-%d')
                        })
        except Exception as e:
            st.warning(f"百度新闻抓取失败: {e}")
        return items[:15]

    @staticmethod
    def crawl_163(query="海南"):
        """网易新闻搜索"""
        items = []
        try:
            url = f"https://so.news.163.com/search?q={query}&type=1"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for item in soup.select('.item'):
                    a = item.find('a')
                    if a:
                        items.append({
                            'title': a.get_text(strip=True)[:120],
                            'link': a.get('href', ''),
                            'source': '网易新闻',
                            'date': datetime.now().strftime('%Y-%m-%d')
                        })
        except:
            pass
        return items[:10]

    @staticmethod
    def crawl_weibo_hot():
        """微博热搜（免费接口）"""
        items = []
        try:
            resp = requests.get(
                "https://weibo.com/ajax/side/hotSearch",
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get('data', {}).get('realtime', [])[:20]:
                    word = item.get('word', '')
                    if '免税' in word or '海南' in word:
                        items.append({
                            'title': word,
                            'link': f"https://s.weibo.com/weibo?q={word}",
                            'source': '微博热搜',
                            'date': datetime.now().strftime('%Y-%m-%d')
                        })
        except:
            pass
        return items

    @classmethod
    def collect_all(cls, keyword="海南 免税"):
        """聚合所有源"""
        all_items = []
        with st.status("正在抓取多源新闻...", expanded=False) as status:
            for name, func in [
                ("360新闻", cls.crawl_360),
                ("百度新闻", cls.crawl_baidu),
                ("网易新闻", cls.crawl_163),
                ("微博热搜", cls.crawl_weibo_hot),
            ]:
                status.write(f"📡 正在抓取 {name}...")
                try:
                    result = func(keyword)
                    all_items.extend(result)
                    status.write(f"   ✅ {name}: {len(result)} 条")
                except Exception as e:
                    status.write(f"   ❌ {name}: {str(e)[:30]}")
            status.update(label="✅ 抓取完成", state="complete")

        # 去重
        return cls._dedup(all_items)

# ============================================================
# 主界面
# ============================================================
col1, col2 = st.columns([3, 1])
with col1:
    keyword = st.text_input("搜索关键词", "海南 免税")
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 刷新新闻", type="primary", use_container_width=True):
        st.session_state.news_data = None

# 初始化或刷新
if 'news_data' not in st.session_state or st.session_state.news_data is None:
    with st.spinner("正在聚合多源新闻..."):
        st.session_state.news_data = NewsCollector.collect_all(keyword)

news = st.session_state.news_data

if not news:
    st.info("暂无新闻数据，请点击刷新按钮重新抓取")
    st.stop()

# ============================================================
# 展示
# ============================================================
st.subheader(f"📊 共 {len(news)} 条相关资讯")

# 过滤和搜索
sources = list(set(n['source'] for n in news))
selected_sources = st.multiselect("按来源筛选", sources, default=sources)

filtered = [n for n in news if n['source'] in selected_sources]

# 分页
page_size = 10
total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
page = st.number_input("页码", 1, total_pages, 1)

start = (page - 1) * page_size
end = start + page_size

for i, n in enumerate(filtered[start:end], start + 1):
    with st.container():
        cols = st.columns([1, 5, 1])
        with cols[0]:
            st.markdown(f"**#{i}**")
        with cols[1]:
            st.markdown(f"**{n['title']}**")
            st.caption(f"📰 {n['source']} | 📅 {n['date']}")
        with cols[2]:
            if n['link']:
                st.markdown(f"[🔗 查看]({n['link']})")
        st.markdown("---")

# 导出
if st.button("📥 导出为 CSV"):
    df = pd.DataFrame(filtered)
    csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
    st.download_button("下载 CSV", csv, f"新闻数据_{datetime.now().strftime('%Y%m%d')}.csv")
