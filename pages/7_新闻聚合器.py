# pages/7_新闻聚合器.py
import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="新闻搜索", layout="wide")
st.title("📰 海南免税·新闻搜索")

st.markdown("""
<style>
    .search-result {
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
        border: 1px solid #ddd;
        background: #fafafa;
    }
    .search-result:hover {
        background: #f0f0f0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 百度搜索 - 最简版
# ============================================================
def baidu_search(keyword):
    """直接请求百度搜索页面，提取标题和链接"""
    results = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        url = f"https://www.baidu.com/s?wd={keyword}"
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 百度搜索结果都在 class="result" 或 class="c-container" 里
            for item in soup.select('.result, .c-container'):
                h3 = item.find('h3')
                if h3 and h3.find('a'):
                    a = h3.find('a')
                    title = a.get_text(strip=True)
                    link = a.get('href', '')
                    # 提取摘要
                    abstract = ''
                    span = item.find('span', class_='content-right_8Zs40')
                    if not span:
                        div = item.find('div', class_='c-abstract')
                        if div:
                            abstract = div.get_text(strip=True)[:150]
                    
                    if title and len(title) > 5:
                        results.append({
                            'title': title[:120],
                            'link': link if link.startswith('http') else f'https://www.baidu.com{link}',
                            'abstract': abstract,
                            'source': '百度搜索',
                            'date': datetime.now().strftime('%Y-%m-%d'),
                        })
                        
                        if len(results) >= 20:
                            break
        else:
            st.warning(f"百度返回状态码: {resp.status_code}")
            
    except Exception as e:
        st.error(f"搜索出错: {str(e)}")
        
    return results

# ============================================================
# 界面
# ============================================================

# 搜索区域
col1, col2 = st.columns([3, 1])
with col1:
    keyword = st.text_input("", placeholder="输入关键词，如：海南 免税 2025", label_visibility="collapsed")
with col2:
    search = st.button("🔍 搜索", type="primary", use_container_width=True)

# 快速搜索标签
st.markdown("**快速搜索:**")
cols = st.columns(5)
quick = ["海南免税", "中免集团", "三亚免税店", "离岛免税", "海口免税"]
for i, q in enumerate(quick):
    with cols[i]:
        if st.button(f"🏷️ {q}", use_container_width=True, key=f"q_{i}"):
            keyword = q
            search = True

# 搜索结果
st.markdown("---")

if search or keyword:
    if not keyword:
        st.info("请输入搜索关键词")
    else:
        with st.spinner(f"🔍 正在搜索 '{keyword}'..."):
            results = baidu_search(keyword)
        
        if results:
            st.success(f"✅ 找到 {len(results)} 条结果")
            
            for i, item in enumerate(results, 1):
                with st.container():
                    cols = st.columns([1, 4, 1])
                    with cols[0]:
                        st.markdown(f"<h3 style='color:#1a73e8;'>{i}</h3>", unsafe_allow_html=True)
                    with cols[1]:
                        st.markdown(f"**<a href='{item['link']}' target='_blank' style='color:#1a0dab;font-size:16px;'>{item['title']}</a>**", unsafe_allow_html=True)
                        if item.get('abstract'):
                            st.caption(item['abstract'][:200])
                        st.caption(f"📰 {item['source']} | 📅 {item['date']}")
                    with cols[2]:
                        st.markdown(f"[🔗 打开]({item['link']})")
                    st.markdown("---")
            
            # 导出功能
            if st.button("📥 导出为 CSV"):
                df = pd.DataFrame(results)
                csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
                st.download_button("下载", csv, f"搜索结果_{datetime.now().strftime('%Y%m%d')}.csv")
        else:
            st.warning("""
            ⚠️ 没有找到结果，可能是：
            1. **网络问题** - 检查是否能访问百度
            2. **关键词太具体** - 试试更宽泛的关键词
            
            💡 **直接去百度搜索:**
            """)
            
            # 提供百度搜索链接
            baidu_url = f"https://www.baidu.com/s?wd={keyword}"
            st.markdown(f"""
            <a href="{baidu_url}" target="_blank" style="
                display: inline-block;
                padding: 12px 24px;
                background: #4a90d9;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                font-size: 16px;
            ">🔗 点击打开百度搜索结果</a>
            """, unsafe_allow_html=True)

else:
    # 默认展示热门搜索
    st.markdown("### 🔥 热门搜索")
    st.markdown("""
    - 点击上方的快速搜索标签
    - 或输入关键词后点击搜索按钮
    - 示例：`海南免税 2025`、`中免集团最新`、`三亚免税店促销`
    """)
