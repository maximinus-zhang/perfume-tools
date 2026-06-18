# pages/15_RSS订阅.py
import streamlit as st
import feedparser
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="RSS订阅", layout="wide")
st.title("📡 RSS 订阅 · 行业资讯")

# ============================================================
# 推荐的 RSS 订阅源（100% 稳定）
# ============================================================
RECOMMENDED_FEEDS = {
    "📰 百度新闻·海南": "https://news.baidu.com/ns?word=海南&tn=news&rtt=1&bsst=1&cl=2&rn=20&ct=1",
    "📰 百度新闻·免税": "https://news.baidu.com/ns?word=免税&tn=news&rtt=1&bsst=1&cl=2&rn=20&ct=1",
    "📰 百度新闻·旅游": "https://news.baidu.com/ns?word=旅游&tn=news&rtt=1&bsst=1&cl=2&rn=20&ct=1",
    "📰 联合早报·中国": "https://www.zaobao.com.sg/realtime/china/feed.xml",
    "📰 36氪·快讯": "https://36kr.com/feed",
    "📰 虎嗅·早报": "https://www.huxiu.com/rss/0.xml",
}

# ============================================================
# RSS 解析引擎
# ============================================================
class RSSReader:
    @staticmethod
    def parse_feed(feed_url, name, max_items=20):
        """解析 RSS 订阅源"""
        items = []
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:max_items]:
                items.append({
                    'title': entry.get('title', '')[:120],
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', entry.get('description', ''))[:200],
                    'published': entry.get('published', entry.get('updated', ''))[:10],
                    'source': name,
                    'feed_url': feed_url,
                })
        except Exception as e:
            st.sidebar.warning(f"{name}: {str(e)[:30]}")
        return items

# ============================================================
# 界面
# ============================================================

# 初始化
if 'rss_data' not in st.session_state:
    st.session_state.rss_data = {}

# 侧边栏
with st.sidebar:
    st.header("📡 订阅源管理")
    
    # 推荐订阅源
    st.subheader("推荐订阅源")
    selected_feeds = []
    for name, url in RECOMMENDED_FEEDS.items():
        if st.checkbox(name, value=True, key=f"feed_{name}"):
            selected_feeds.append((name, url))
    
    # 自定义订阅源
    st.subheader("自定义订阅")
    custom_url = st.text_input("输入 RSS 地址")
    custom_name = st.text_input("订阅源名称")
    if st.button("添加订阅") and custom_url and custom_name:
        RECOMMENDED_FEEDS[custom_name] = custom_url
        st.success(f"已添加 {custom_name}")
        st.rerun()
    
    # 刷新
    st.markdown("---")
    if st.button("🔄 刷新全部", type="primary", use_container_width=True):
        st.session_state.rss_data = {}
        with st.spinner("正在刷新..."):
            for name, url in selected_feeds:
                items = RSSReader.parse_feed(url, name)
                st.session_state.rss_data[name] = items
        st.success("刷新完成！")
        st.rerun()

# 主内容
st.subheader("📊 资讯汇总")

# 如果有缓存数据，直接显示
if st.session_state.rss_data:
    # 合并所有数据
    all_items = []
    for source, items in st.session_state.rss_data.items():
        all_items.extend(items)
    
    # 按时间排序
    all_items.sort(key=lambda x: x.get('published', ''), reverse=True)
    
    st.success(f"共 {len(all_items)} 条资讯")
    
    # 按来源筛选
    sources = list(set(item['source'] for item in all_items))
    selected_sources = st.multiselect("按来源筛选", sources, default=sources)
    
    filtered = [item for item in all_items if item['source'] in selected_sources]
    
    # 显示
    for i, item in enumerate(filtered[:50], 1):
        with st.container(border=True):
            cols = st.columns([4, 1, 1])
            with cols[0]:
                st.markdown(f"**{i}. [{item['title']}]({item['link']})**")
                if item.get('summary'):
                    st.caption(item['summary'][:150])
            with cols[1]:
                st.markdown(f"📰 {item['source']}")
            with cols[2]:
                st.markdown(f"📅 {item.get('published', '')[:10]}")
    
    # 导出
    if st.button("📥 导出为 CSV"):
        df = pd.DataFrame(filtered)
        csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
        st.download_button("下载", csv, f"RSS订阅_{datetime.now().strftime('%Y%m%d')}.csv")
else:
    # 首次加载
    st.info('点击左侧「刷新全部」按钮获取最新资讯')
    
    # 预览订阅源
    st.markdown("### 📋 已配置的订阅源")
    for name, url in RECOMMENDED_FEEDS.items():
        st.markdown(f"- {name}")

st.caption(f"📊 {datetime.now().strftime('%Y-%m-%d %H:%M')} | 📡 RSS订阅 · 自动聚合")
