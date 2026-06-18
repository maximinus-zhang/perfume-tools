# pages/16_香水价格监控.py
import streamlit as st
import requests
import json
import re
import time
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import random
from io import BytesIO

st.set_page_config(page_title="香水价格监控", layout="wide")
st.title("🛒 香水价格监控 · Playwright 增强版")

# ============================================================
# 尝试导入 Playwright
# ============================================================
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# 热门香水监控清单
PERFUME_LIST = {
    "香奈儿5号": "香奈儿5号 香水 100ml",
    "迪奥小姐": "迪奥小姐 香水 100ml",
    "祖玛珑蓝风铃": "祖玛珑 蓝风铃 100ml",
    "爱马仕大地": "爱马仕 大地 香水 100ml",
    "TOM FORD乌木沉香": "TOM FORD 乌木沉香 50ml",
    "YSL自由之水": "YSL 自由之水 100ml",
    "Loewe事后清晨": "Loewe 事后清晨 001",
    "Gucci花悦": "Gucci 花悦 香水 100ml",
    "宝格丽大吉岭茶": "宝格丽 大吉岭茶 100ml",
    "三宅一生一生之水": "三宅一生 一生之水 100ml",
    "阿玛尼寄情": "阿玛尼 寄情 香水 100ml",
    "范思哲同名": "范思哲 同名 香水 100ml",
}

# ============================================================
# 爬虫引擎（requests 版 - 快速轻量）
# ============================================================
class RequestsCrawler:
    """快速爬虫（requests + BeautifulSoup）"""

    @staticmethod
    def search_jd(keyword, max_items=5):
        """京东搜索（用移动端API，更稳定）"""
        results = []
        try:
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) '
                    'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 '
                    'Mobile/15E148 Safari/604.1'
                ),
                'Accept': 'text/html,application/xhtml+xml',
                'Referer': 'https://m.jd.com/',
            }
            
            # 京东移动端搜索（比PC端更容易爬取）
            url = f"https://search.jd.com/Search?keyword={keyword}&enc=utf-8&wq={keyword}"
            resp = requests.get(url, headers=headers, timeout=15)
            
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 提取商品列表
                items = soup.select('.gl-item')
                if not items:
                    # 尝试移动端格式
                    items = soup.select('.search_result_item')
                
                for item in items[:max_items]:
                    try:
                        # 标题
                        title_el = item.select_one('.p-name a') or item.select_one('.item_name')
                        title = title_el.get_text(strip=True) if title_el else ''
                        
                        # 价格
                        price_el = item.select_one('.p-price i') or item.select_one('.price')
                        price_text = price_el.get_text(strip=True) if price_el else '0'
                        # 提取数字
                        price_match = re.search(r'(\d+\.?\d*)', price_text.replace(',', ''))
                        price = float(price_match.group(1)) if price_match else 0
                        
                        # 店铺
                        shop_el = item.select_one('.p-shop a') or item.select_one('.shop_name')
                        shop = shop_el.get_text(strip=True) if shop_el else '京东自营'
                        
                        # 链接
                        link_el = title_el if title_el else item.select_one('a')
                        link = ''
                        if link_el and link_el.get('href'):
                            href = link_el.get('href', '')
                            link = f"https:{href}" if href.startswith('//') else href
                        
                        if title and price > 0:
                            results.append({
                                '名称': title[:80],
                                '价格(元)': price,
                                '平台': '京东',
                                '店铺': shop,
                                '链接': link,
                                '来源': '京东',
                                '时间': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            })
                    except Exception as e:
                        continue
        except Exception as e:
            st.sidebar.warning(f"京东搜索失败: {str(e)[:40]}")
        
        return results

    @staticmethod
    def search_smzdm(keyword, max_items=5):
        """什么值得买搜索（已更新最新HTML结构）"""
        results = []
        try:
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                'Accept': 'text/html,application/xhtml+xml',
            }
            
            # 什么值得买搜索
            url = f"https://search.smzdm.com/?cate=1&keyword={keyword}&v=a"
            resp = requests.get(url, headers=headers, timeout=15)
            
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 新版本HTML结构适配
                items = soup.select('.feed-row-wide')
                if not items:
                    items = soup.select('.list-item')
                if not items:
                    items = soup.select('[class*="feed"]')
                
                for item in items[:max_items]:
                    try:
                        # 标题
                        title_el = item.select_one('.feed-block-title a') or item.select_one('.title a') or item.select_one('a')
                        title = title_el.get_text(strip=True) if title_el else ''
                        
                        # 价格（多种可能的选择器）
                        price_el = (
                            item.select_one('.red') or 
                            item.select_one('.price') or 
                            item.select_one('[class*="price"]') or
                            item.select_one('.buy-link')
                        )
                        price_text = price_el.get_text(strip=True) if price_el else ''
                        price_match = re.search(r'(\d+\.?\d*)', price_text.replace(',', ''))
                        price = float(price_match.group(1)) if price_match else 0
                        
                        # 来源平台
                        source_el = item.select_one('.source') or item.select_one('.mall')
                        platform = source_el.get_text(strip=True) if source_el else '什么值得买'
                        
                        link = title_el.get('href', '') if title_el else ''
                        
                        if title and price > 0:
                            results.append({
                                '名称': title[:80],
                                '价格(元)': price,
                                '平台': platform,
                                '链接': link,
                                '来源': '什么值得买',
                                '时间': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            })
                    except Exception:
                        continue
        except Exception as e:
            st.sidebar.warning(f"值得买搜索失败: {str(e)[:40]}")
        
        return results

# ============================================================
# 爬虫引擎（Playwright 版 - 完整浏览器，抗反爬）
# ============================================================
class PlaywrightCrawler:
    """Playwright 浏览器爬虫（可爬取淘宝/天猫等反爬严格的平台）"""

    @staticmethod
    def search_jd_playwright(keyword, max_items=10):
        """京东 - 使用 Playwright 真实浏览器"""
        results = []
        if not HAS_PLAYWRIGHT:
            return results
        
        try:
            with sync_playwright() as p:
                # 启动浏览器（隐藏自动化特征）
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                    ]
                )
                context = browser.new_context(
                    user_agent=(
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/120.0.0.0 Safari/537.36'
                    ),
                    viewport={'width': 1920, 'height': 1080},
                    locale='zh-CN',
                )
                
                # 注入反检测脚本
                page = context.new_page()
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                # 访问京东搜索
                url = f"https://search.jd.com/Search?keyword={keyword}&enc=utf-8"
                page.goto(url, wait_until='networkidle', timeout=30000)
                
                # 等待商品加载
                page.wait_for_selector('.gl-item', timeout=10000)
                
                # 提取商品信息
                items = page.query_selector_all('.gl-item')
                for item in items[:max_items]:
                    try:
                        # 标题
                        title_el = item.query_selector('.p-name a')
                        title = title_el.inner_text().strip() if title_el else ''
                        
                        # 价格
                        price_el = item.query_selector('.p-price i')
                        price_text = price_el.inner_text().strip() if price_el else '0'
                        price_match = re.search(r'(\d+\.?\d*)', price_text)
                        price = float(price_match.group(1)) if price_match else 0
                        
                        # 店铺
                        shop_el = item.query_selector('.p-shop a')
                        shop = shop_el.inner_text().strip() if shop_el else '京东自营'
                        
                        # 链接
                        link = ''
                        if title_el:
                            href = title_el.get_attribute('href') or ''
                            link = f"https:{href}" if href.startswith('//') else href
                        
                        if title and price > 0:
                            results.append({
                                '名称': title[:80],
                                '价格(元)': price,
                                '平台': '京东',
                                '店铺': shop,
                                '链接': link,
                                '来源': '京东(浏览器)',
                                '时间': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            })
                    except Exception:
                        continue
                
                browser.close()
                
        except Exception as e:
            st.sidebar.warning(f"京东(Playwright)失败: {str(e)[:40]}")
        
        return results

    @staticmethod
    def search_taobao_playwright(keyword, max_items=10):
        """淘宝搜索 - Playwright 版"""
        results = []
        if not HAS_PLAYWRIGHT:
            return results
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )
                context = browser.new_context(
                    user_agent=(
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/120.0.0.0 Safari/537.36'
                    ),
                    viewport={'width': 1920, 'height': 1080},
                )
                
                page = context.new_page()
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                # 淘宝搜索
                url = f"https://s.taobao.com/search?q={keyword}"
                page.goto(url, wait_until='networkidle', timeout=30000)
                
                # 等待商品加载
                try:
                    page.wait_for_selector('.item.J_MouserOnverReq', timeout=15000)
                except:
                    page.wait_for_selector('[class*="item"]', timeout=15000)
                
                # 提取商品
                items = page.query_selector_all('.item.J_MouserOnverReq')
                if not items:
                    items = page.query_selector_all('[class*="item"]')
                
                for item in items[:max_items]:
                    try:
                        # 标题
                        title_el = item.query_selector('.title a') or item.query_selector('[class*="title"] a')
                        title = title_el.inner_text().strip() if title_el else ''
                        
                        # 价格
                        price_el = item.query_selector('.price') or item.query_selector('[class*="price"]')
                        price_text = price_el.inner_text().strip() if price_el else '0'
                        price_match = re.search(r'(\d+\.?\d*)', price_text)
                        price = float(price_match.group(1)) if price_match else 0
                        
                        # 店铺
                        shop_el = item.query_selector('.shop a') or item.query_selector('[class*="shop"]')
                        shop = shop_el.inner_text().strip() if shop_el else '淘宝店铺'
                        
                        # 链接
                        link = ''
                        if title_el:
                            href = title_el.get_attribute('href') or ''
                            if href.startswith('//'):
                                link = f"https:{href}"
                            elif href.startswith('/'):
                                link = f"https://s.taobao.com{href}"
                            else:
                                link = href
                        
                        if title and price > 0:
                            results.append({
                                '名称': title[:80],
                                '价格(元)': price,
                                '平台': '淘宝',
                                '店铺': shop,
                                '链接': link,
                                '来源': '淘宝(浏览器)',
                                '时间': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            })
                    except Exception:
                        continue
                
                browser.close()
                
        except Exception as e:
            st.sidebar.warning(f"淘宝(Playwright)失败: {str(e)[:40]}")
        
        return results

    @staticmethod
    def search_tmall_playwright(keyword, max_items=10):
        """天猫搜索 - Playwright 版"""
        results = []
        if not HAS_PLAYWRIGHT:
            return results
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )
                context = browser.new_context(
                    user_agent=(
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/120.0.0.0 Safari/537.36'
                    ),
                    viewport={'width': 1920, 'height': 1080},
                )
                
                page = context.new_page()
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                # 天猫搜索
                url = f"https://list.tmall.com/search_product.htm?q={keyword}"
                page.goto(url, wait_until='networkidle', timeout=30000)
                
                try:
                    page.wait_for_selector('.product-item', timeout=15000)
                except:
                    page.wait_for_timeout(3000)
                
                items = page.query_selector_all('.product-item')
                
                for item in items[:max_items]:
                    try:
                        title_el = item.query_selector('.product-title a') or item.query_selector('[class*="title"] a')
                        title = title_el.inner_text().strip() if title_el else ''
                        
                        price_el = item.query_selector('.product-price') or item.query_selector('[class*="price"]')
                        price_text = price_el.inner_text().strip() if price_el else '0'
                        price_match = re.search(r'(\d+\.?\d*)', price_text)
                        price = float(price_match.group(1)) if price_match else 0
                        
                        shop_el = item.query_selector('.product-shop a') or item.query_selector('[class*="shop"]')
                        shop = shop_el.inner_text().strip() if shop_el else '天猫店铺'
                        
                        link = ''
                        if title_el:
                            href = title_el.get_attribute('href') or ''
                            if href.startswith('//'):
                                link = f"https:{href}"
                            else:
                                link = href
                        
                        if title and price > 0:
                            results.append({
                                '名称': title[:80],
                                '价格(元)': price,
                                '平台': '天猫',
                                '店铺': shop,
                                '链接': link,
                                '来源': '天猫(浏览器)',
                                '时间': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            })
                    except Exception:
                        continue
                
                browser.close()
                
        except Exception as e:
            st.sidebar.warning(f"天猫(Playwright)失败: {str(e)[:40]}")
        
        return results

# ============================================================
# 智能引擎调度器
# ============================================================
class SmartCrawler:
    """智能选择爬虫引擎，多源互补"""

    @staticmethod
    def search_all(keyword, max_items=5):
        """多引擎搜索"""
        all_results = []
        engines = []
        
        # 1. 快速引擎（无浏览器）
        engines.append(('京东(快速)', RequestsCrawler.search_jd))
        engines.append(('值得买', RequestsCrawler.search_smzdm))
        
        # 2. 浏览器引擎（如果有 Playwright）
        if HAS_PLAYWRIGHT:
            engines.append(('京东(浏览器)', PlaywrightCrawler.search_jd_playwright))
            engines.append(('淘宝(浏览器)', PlaywrightCrawler.search_taobao_playwright))
            engines.append(('天猫(浏览器)', PlaywrightCrawler.search_tmall_playwright))
        
        # 依次执行
        for name, func in engines:
            try:
                results = func(keyword, max_items)
                all_results.extend(results)
                if results:
                    st.sidebar.success(f"✅ {name}: {len(results)}条")
                else:
                    st.sidebar.info(f"⏳ {name}: 0条")
            except Exception as e:
                st.sidebar.error(f"❌ {name}: {str(e)[:30]}")
        
        # 去重（按标题去重）
        seen = set()
        unique_results = []
        for item in all_results:
            key = item['名称'][:30]
            if key not in seen:
                seen.add(key)
                unique_results.append(item)
        
        # 按价格排序
        unique_results.sort(key=lambda x: x.get('价格(元)', 99999))
        
        return unique_results

    @staticmethod
    def batch_search(perfume_dict):
        """批量搜索所有监控香水"""
        all_data = []
        
        total = len(perfume_dict)
        progress_bar = st.progress(0, text="准备搜索...")
        status_text = st.empty()
        
        for i, (name, keyword) in enumerate(perfume_dict.items()):
            progress = (i + 1) / total
            status_text.text(f"📡 正在搜索: {name} ({i+1}/{total})")
            progress_bar.progress(progress)
            
            results = SmartCrawler.search_all(keyword, max_items=4)
            for r in results:
                r['监控名称'] = name
                all_data.append(r)
            
            time.sleep(0.5)  # 短暂间隔
        
        progress_bar.empty()
        status_text.empty()
        
        return all_data

# ============================================================
# 价格历史追踪
# ============================================================
class PriceHistory:
    @staticmethod
    def init():
        if 'price_history' not in st.session_state:
            st.session_state.price_history = pd.DataFrame(columns=[
                '监控名称', '名称', '价格(元)', '平台', '来源', '时间'
            ])
    
    @staticmethod
    def add(df):
        df_to_add = df[['监控名称', '名称', '价格(元)', '平台', '来源', '时间']].copy()
        st.session_state.price_history = pd.concat([
            st.session_state.price_history, df_to_add
        ], ignore_index=True).tail(2000)

# ============================================================
# 界面
# ============================================================

PriceHistory.init()

with st.sidebar:
    st.header("⚙️ 设置")
    
    st.info(
        f"🖥️ Playwright: {'✅ 已安装' if HAS_PLAYWRIGHT else '❌ 未安装'}\n\n"
        f"{'可爬取: 京东/淘宝/天猫' if HAS_PLAYWRIGHT else '仅可爬取: 京东(快速版)'}"
    )
    
    if not HAS_PLAYWRIGHT:
        st.code("pip install playwright\nplaywright install chromium")
    
    st.markdown("---")
    st.subheader("📋 监控清单")
    
    selected_perfumes = {}
    for name, keyword in PERFUME_LIST.items():
        if st.checkbox(name, value=True, key=f"p_{name}"):
            selected_perfumes[name] = keyword
    
    st.markdown("---")
    scan_btn = st.button("🔍 开始扫描", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.caption("📌 数据来源")
    st.caption("快速模式: 京东/值得买")
    if HAS_PLAYWRIGHT:
        st.caption("浏览器模式: 京东/淘宝/天猫")

# ============================================================
# 主界面
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 当前价格", "📈 价格趋势", "🔔 降价提醒", "📋 历史记录"
])

with tab1:
    st.subheader("📊 香水价格扫描")
    
    if not selected_perfumes:
        st.warning("⚠️ 请在左侧勾选要监控的香水")
        st.stop()
    
    # 扫描操作
    if scan_btn or 'current_prices' not in st.session_state:
        with st.spinner("正在扫描各平台价格（可能需要1-2分钟）..."):
            results = SmartCrawler.batch_search(selected_perfumes)
            st.session_state.current_prices = results
            if results:
                PriceHistory.add(pd.DataFrame(results))
    
    results = st.session_state.get('current_prices', [])
    
    if results:
        df = pd.DataFrame(results)
        
        # 核心指标
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("📦 商品数", len(df['名称'].unique()))
        col2.metric("🏪 覆盖平台", len(df['平台'].unique()))
        col3.metric("💰 最低价", f"¥{df['价格(元)'].min():.0f}")
        col4.metric("📊 均价", f"¥{df['价格(元)'].mean():.0f}")
        col5.metric("🔍 数据源", len(df['来源'].unique()))
        
        # 按香水分组展示
        for perfume_name in selected_perfumes:
            perfume_data = df[df['监控名称'] == perfume_name]
            if len(perfume_data) > 0:
                min_row = perfume_data.loc[perfume_data['价格(元)'].idxmin()]
                
                with st.expander(
                    f"🧴 {perfume_name} "
                    f"({len(perfume_data)}个价格 | "
                    f"最低 ¥{min_row['价格(元)']:.0f} @ {min_row['平台']})",
                    expanded=True
                ):
                    # 最低价卡片
                    st.markdown(f"""
                    <div style="
                        background: #e8f5e9;
                        padding: 12px 18px;
                        border-radius: 10px;
                        margin-bottom: 12px;
                        border-left: 5px solid #4caf50;
                    ">
                        <strong>🏆 全网最低价</strong>: 
                        <span style="font-size: 24px; color: #e53935; font-weight: bold;">
                            ¥{min_row['价格(元)']:.0f}
                        </span>
                        来自 <strong>{min_row['平台']}</strong>
                        ({min_row['来源']})
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 表格
                    display_df = perfume_data[[
                        '名称', '价格(元)', '平台', '店铺', '来源', '时间'
                    ]].sort_values('价格(元)')
                    
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        column_config={
                            '价格(元)': st.column_config.NumberColumn(format="¥%.0f"),
                            '名称': st.column_config.TextColumn(width='large'),
                        },
                        hide_index=True,
                    )
        
        # 导出
        st.markdown("---")
        csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
        st.download_button(
            "📥 导出当前价格",
            csv,
            f"香水价格_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        )
    else:
        st.warning("""
        ⚠️ 暂未搜索到价格数据，可能原因：
        1. **首次运行** - 点击左侧「开始扫描」按钮
        2. **网络问题** - 检查是否能访问京东/淘宝
        3. **反爬拦截** - 安装 Playwright 后使用浏览器模式
        
        💡 **推荐**: 
        ```cmd
        pip install playwright
        playwright install chromium
        ```
        """)

with tab2:
    st.subheader("📈 价格趋势")
    
    if not st.session_state.price_history.empty:
        history = st.session_state.price_history
        
        perfumes = history['监控名称'].unique()
        selected = st.selectbox("选择香水查看趋势", perfumes)
        
        ph = history[history['监控名称'] == selected].copy()
        ph['时间'] = pd.to_datetime(ph['时间'])
        ph = ph.sort_values('时间')
        
        if len(ph) > 1:
            fig = px.line(
                ph, x='时间', y='价格(元)', color='平台',
                title=f"{selected} 价格趋势",
                markers=True,
                line_shape='spline',
            )
            fig.update_layout(hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 记录数", len(ph))
        col2.metric("💰 最低价", f"¥{ph['价格(元)'].min():.0f}")
        col3.metric("📈 最高价", f"¥{ph['价格(元)'].max():.0f}")
        col4.metric("💹 平均价", f"¥{ph['价格(元)'].mean():.0f}")
    else:
        st.info("暂无历史数据，请先在「当前价格」标签页扫描")

with tab3:
    st.subheader("🔔 降价提醒设置")
    
    st.markdown("设置目标价格，当某款香水低于该价格时高亮提醒")
    
    alerts = []
    if results:
        df = pd.DataFrame(results)
        for name in selected_perfumes:
            target = st.number_input(
                f"{name} 目标价 (元)",
                min_value=0, value=500, step=50,
                key=f"alert_{name}"
            )
            
            perfume_data = df[df['监控名称'] == name]
            if len(perfume_data) > 0:
                min_price = perfume_data['价格(元)'].min()
                if min_price <= target:
                    st.success(f"✅ {name}: ¥{min_price:.0f} ≤ ¥{target:.0f} (已达到!)")
                else:
                    st.info(f"⏳ {name}: ¥{min_price:.0f} > ¥{target:.0f} (还差¥{min_price-target:.0f})")
    else:
        st.info("请先在「当前价格」标签页扫描数据")

with tab4:
    st.subheader("📋 价格历史记录")
    
    if not st.session_state.price_history.empty:
        st.dataframe(
            st.session_state.price_history.sort_values('时间', ascending=False),
            use_container_width=True,
            hide_index=True,
        )
        
        if st.button("🗑️ 清空历史"):
            st.session_state.price_history = pd.DataFrame(columns=[
                '监控名称', '名称', '价格(元)', '平台', '来源', '时间'
            ])
            st.rerun()
    else:
        st.info("暂无历史记录")

# 页脚
st.markdown("---")
st.caption(
    f"🤖 引擎: {'Playwright + Requests' if HAS_PLAYWRIGHT else 'Requests'} | "
    f"数据来源: 京东/淘宝/天猫/什么值得买 | "
    f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
)
