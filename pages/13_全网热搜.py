# pages/13_全网热搜.py
import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="全网热搜", layout="wide")
st.title("🌐 全网热搜 · 免税行业监测")

# ============================================================
# 知托热榜 API（免费开放）
# ============================================================
class AllHotSearch:
    """聚合全网热搜"""
    
    @staticmethod
    def get_baidu_hot():
        """百度热搜"""
        try:
            url = "https://top.baidu.com/api/board?tab=realtime"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                cards = data.get('data', {}).get('cards', [])
                results = []
                for card in cards:
                    for item in card.get('content', [])[:20]:
                        results.append({
                            'title': item.get('word', item.get('query', '')),
                            'hot': item.get('hotScore', 0),
                            'source': '百度',
                            'url': f"https://www.baidu.com/s?wd={item.get('word', '')}",
                        })
                return results[:30]
        except:
            pass
        return []

    @staticmethod
    def get_weibo_hot():
        """微博热搜"""
        try:
            url = "https://weibo.com/ajax/side/hotSearch"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('data', {}).get('realtime', [])
                return [{
                    'title': item.get('word', ''),
                    'hot': item.get('num', 0),
                    'source': '微博',
                    'url': f"https://s.weibo.com/weibo?q={item.get('word', '')}",
                } for item in items[:30]]
        except:
            pass
        return []

    @staticmethod
    def get_zhihu_hot():
        """知乎热榜"""
        try:
            url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=30"
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('data', [])
                return [{
                    'title': item.get('target', {}).get('title', ''),
                    'hot': item.get('detail_text', '0').replace('万', '0000').replace('亿', '00000000'),
                    'source': '知乎',
                    'url': f"https://www.zhihu.com/question/{item.get('target', {}).get('id', '')}",
                } for item in items[:20]]
        except:
            pass
        return []

    @staticmethod
    def get_douyin_hot():
        """抖音热搜"""
        try:
            url = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('data', {}).get('word_list', [])
                return [{
                    'title': item.get('word', ''),
                    'hot': item.get('hot_value', 0),
                    'source': '抖音',
                    'url': f"https://www.douyin.com/search/{item.get('word', '')}",
                } for item in items[:20]]
        except:
            pass
        return []

# ============================================================
# 界面
# ============================================================
st.markdown("""
<style>
    .hot-item {
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 6px;
        transition: background 0.2s;
    }
    .hot-item:hover {
        background: #f5f5f5;
    }
    .badge-baidu { background: #4a90d9; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
    .badge-weibo { background: #e6162d; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
    .badge-zhihu { background: #056de8; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
    .badge-douyin { background: #000; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# 关键词过滤
filter_keywords = st.text_input("🔍 筛选关键词（如：免税、海南）", "免税")

col1, col2 = st.columns([3, 1])
with col1:
    refresh = st.button("🔄 刷新全部热搜", type="primary", use_container_width=True)
with col2:
    auto = st.checkbox("自动刷新", value=True)

if refresh or auto:
    with st.spinner("正在获取全网热搜..."):
        baidu = AllHotSearch.get_baidu_hot()
        weibo = AllHotSearch.get_weibo_hot()
        zhihu = AllHotSearch.get_zhihu_hot()
        douyin = AllHotSearch.get_douyin_hot()
        
        st.session_state.all_hot = {
            '百度': baidu,
            '微博': weibo,
            '知乎': zhihu,
            '抖音': douyin,
        }

if 'all_hot' in st.session_state:
    all_data = st.session_state.all_hot
    
    # 统计
    total = sum(len(v) for v in all_data.values())
    related = []
    for source, items in all_data.items():
        for item in items:
            if filter_keywords and filter_keywords in item['title']:
                related.append({**item, 'source': source})
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 总热搜数", total)
    col2.metric(f"🎯 相关' {filter_keywords} '", len(related))
    col3.metric("📰 数据源", f"{sum(1 for v in all_data.values() if v)}/4")
    
    # 显示各平台
    tabs = st.tabs(list(all_data.keys()))
    
    for i, (source, items) in enumerate(all_data.items()):
        with tabs[i]:
            if items:
                filtered = [item for item in items 
                           if not filter_keywords or filter_keywords in item['title']]
                
                for j, item in enumerate(filtered[:15], 1):
                    with st.container():
                        cols = st.columns([1, 5, 1])
                        with cols[0]:
                            st.markdown(f"**{j}**")
                        with cols[1]:
                            st.markdown(f"**{item['title']}**")
                            if item.get('hot'):
                                st.caption(f"🔥 热度: {item['hot']}")
                        with cols[2]:
                            if item.get('url'):
                                st.markdown(f"[🔗 查看]({item['url']})")
                        st.markdown("---")
            else:
                st.warning(f"{source} 暂无数据")
else:
    st.info("点击"刷新全部热搜"获取数据")

st.caption(f"📊 数据来源: 百度/微博/知乎/抖音开放接口 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
