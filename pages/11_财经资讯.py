# pages/11_财经资讯.py
import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="财经资讯", layout="wide")
st.title("💰 财经资讯 · 免税行业情报")

# ============================================================
# 华尔街见闻 API（免费开放接口）
# ============================================================
class WallStreetNews:
    """华尔街见闻快讯爬虫"""
    
    API_URL = "https://api.wallstreetcn.com/v2/livenews"
    
    @staticmethod
    def get_live_news(limit=30):
        """获取实时快讯"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json',
            }
            params = {
                'limit': limit,
                'channel': 'global',
            }
            resp = requests.get(
                WallStreetNews.API_URL,
                headers=headers,
                params=params,
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('data', {}).get('items', [])
                results = []
                for item in items:
                    content = item.get('content_text', '')
                    # 过滤与免税/消费相关的新闻
                    keywords = ['免税', '消费', '零售', '海南', '海关', 
                               '奢侈品', '旅游', '离岛', '中免']
                    if any(kw in content for kw in keywords):
                        results.append({
                            'title': content[:150],
                            'time': item.get('display_time', ''),
                            'source': '华尔街见闻',
                            'type': '快讯',
                            'id': item.get('id', ''),
                        })
                return results[:20]
        except Exception as e:
            st.warning(f"华尔街见闻: {str(e)[:30]}")
        return []

    @staticmethod
    def search_news(keyword):
        """搜索新闻"""
        try:
            url = f"https://api.wallstreetcn.com/v2/search?q={keyword}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('data', {}).get('items', [])
                return [{
                    'title': item.get('title', '')[:120],
                    'summary': item.get('content_text', '')[:200],
                    'time': item.get('display_time', ''),
                    'source': '华尔街见闻',
                    'type': '搜索',
                } for item in items[:15]]
        except:
            pass
        return []

# ============================================================
# 界面
# ============================================================
tab1, tab2 = st.tabs(["📡 实时快讯", "🔍 关键词搜索"])

with tab1:
    st.subheader("📡 免税/消费相关实时快讯")
    
    if st.button("🔄 刷新快讯", type="primary"):
        with st.spinner("正在获取..."):
            news = WallStreetNews.get_live_news()
            st.session_state.wsc_news = news
    
    if 'wsc_news' not in st.session_state:
        st.session_state.wsc_news = []
    
    if st.session_state.wsc_news:
        st.success(f"共 {len(st.session_state.wsc_news)} 条相关快讯")
        for i, item in enumerate(st.session_state.wsc_news, 1):
            with st.container(border=True):
                st.markdown(f"**{i}. {item['title']}**")
                st.caption(f"🕐 {item['time']} | 📰 {item['source']}")
    else:
        st.info("点击"刷新快讯"获取最新资讯")

with tab2:
    st.subheader("🔍 搜索行业关键词")
    keyword = st.text_input("输入关键词", "海南 免税")
    
    if st.button("搜索"):
        with st.spinner(f"正在搜索 '{keyword}'..."):
            results = WallStreetNews.search_news(keyword)
        
        if results:
            for i, item in enumerate(results, 1):
                with st.container(border=True):
                    st.markdown(f"**{i}. {item['title']}**")
                    if item.get('summary'):
                        st.caption(item['summary'][:200])
                    st.caption(f"🕐 {item['time']} | 📰 {item['source']}")
        else:
            st.info("未找到相关结果")

st.caption(f"📊 数据来源: 华尔街见闻公开API | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
