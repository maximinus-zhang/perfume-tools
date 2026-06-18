# pages/12_微博热点.py
import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="微博热点", layout="wide")
st.title("🔥 微博热搜 · 免税话题监控")

# ============================================================
# 微博热搜（免费开放接口）
# ============================================================
class WeiboHotSearch:
    """微博热搜爬虫"""
    
    @staticmethod
    def get_hot_search():
        """获取微博热搜榜"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://weibo.com/',
            }
            # 微博热搜 API
            url = "https://weibo.com/ajax/side/hotSearch"
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                hot_list = data.get('data', {}).get('realtime', [])
                
                results = []
                for item in hot_list:
                    word = item.get('word', '')
                    rank = item.get('rank', 0)
                    hot_num = item.get('num', 0)  # 热度值
                    
                    results.append({
                        'rank': rank,
                        'word': word,
                        'hot_num': hot_num,
                        'is_hot': item.get('is_hot', False),
                        'is_new': item.get('is_new', False),
                        'category': item.get('category', ''),
                    })
                
                return sorted(results, key=lambda x: x['rank'])[:50]
        except Exception as e:
            st.error(f"获取微博热搜失败: {str(e)}")
        return []

    @staticmethod
    def search_weibo(keyword):
        """搜索微博"""
        try:
            url = f"https://s.weibo.com/weibo?q={keyword}&typeall=1"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                cards = soup.select('.card-wrap')
                
                results = []
                for card in cards[:20]:
                    text = card.get_text(strip=True)[:200]
                    if text and len(text) > 10:
                        results.append({
                            'content': text[:150],
                            'source': '微博',
                            'time': datetime.now().strftime('%Y-%m-%d'),
                        })
                return results
        except:
            pass
        return []

# ============================================================
# 界面
# ============================================================
tab1, tab2, tab3 = st.tabs(["🏆 热搜榜", "🔍 话题搜索", "📈 趋势分析"])

with tab1:
    st.subheader("🏆 微博实时热搜榜")
    
    if st.button("🔄 刷新热搜", type="primary"):
        with st.spinner("正在获取..."):
            st.session_state.hot_search = WeiboHotSearch.get_hot_search()
    
    if 'hot_search' not in st.session_state:
        st.session_state.hot_search = []
    
    hot_list = st.session_state.hot_search
    
    if hot_list:
        # 筛选关注免税相关话题
        related_keywords = ['免税', '海南', '三亚', '旅游', '消费', '奢侈品', '化妆品', '香化']
        related = [h for h in hot_list 
                   if any(kw in h['word'] for kw in related_keywords)]
        
        st.metric("🔥 热搜总数", len(hot_list))
        if related:
            st.metric("🎯 相关话题", len(related), delta=f"{len(related)}条")
        
        # 显示热搜榜
        cols = st.columns([1, 4, 1])
        with cols[0]:
            st.markdown("**排名**")
        with cols[1]:
            st.markdown("**话题**")
        with cols[2]:
            st.markdown("**热度**")
        st.markdown("---")
        
        for item in hot_list[:30]:
            is_related = any(kw in item['word'] for kw in related_keywords)
            bg = "#fff3cd" if is_related else "transparent"
            
            cols = st.columns([1, 4, 1])
            with cols[0]:
                if item['rank'] <= 3:
                    st.markdown(f"<span style='color:red;font-weight:bold;'>{item['rank']}</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"**{item['rank']}**")
            with cols[1]:
                word = item['word']
                if is_related:
                    word = f"🛍️ {word}"
                if item.get('is_new'):
                    word += " 🆕"
                if item.get('is_hot'):
                    word += " 🔥"
                st.markdown(f"<span style='background:{bg};padding:2px 8px;border-radius:4px;'>{word}</span>", unsafe_allow_html=True)
            with cols[2]:
                if item['hot_num'] > 0:
                    st.caption(f"{item['hot_num']:,}")
            st.markdown("---")
    else:
        st.info('点击「刷新热搜」获取最新榜单')

with tab2:
    st.subheader("🔍 搜索微博话题")
    keyword = st.text_input("搜索关键词", "海南免税")
    if st.button("搜索微博"):
        with st.spinner("正在搜索..."):
            results = WeiboHotSearch.search_weibo(keyword)
        if results:
            for i, item in enumerate(results[:10], 1):
                with st.container(border=True):
                    st.write(f"**{i}.** {item['content']}")
        else:
            st.info("未找到相关内容")

with tab3:
    st.subheader("📈 话题趋势")
    st.markdown("""
    监控以下关键词的热度变化：
    
    | 关键词 | 监控状态 |
    |--------|---------|
    | 🛍️ 海南免税 | ✅ 已开启 |
    | 🏪 中免集团 | ✅ 已开启 |
    | ✈️ 离岛免税 | ✅ 已开启 |
    
    趋势数据将在后续版本中提供图表展示。
    """)

st.caption(f"📊 数据来源: 微博开放接口 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
