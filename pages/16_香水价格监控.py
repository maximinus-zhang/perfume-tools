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

st.set_page_config(page_title="香水价格监控", layout="wide")
st.title("🛒 香水价格监控 · 多平台比价")

# 热门香水监控清单
PERFUME_LIST = {
    "香奈儿5号": "香奈儿5号 香水",
    "迪奥小姐": "迪奥小姐 香水",
    "祖玛珑蓝风铃": "祖玛珑 蓝风铃",
    "爱马仕大地": "爱马仕 大地 香水",
    "TOM FORD乌木": "TOM FORD 乌木沉香",
    "YSL自由之水": "YSL 自由之水",
    "Loewe事后清晨": "Loewe 事后清晨",
    "Gucci花悦": "Gucci 花悦",
    "三宅一生一生之水": "三宅一生 一生之水",
    "宝格丽大吉岭茶": "宝格丽 大吉岭茶",
}

# ============================================================
# 爬虫引擎
# ============================================================
class PriceCrawler:

    @staticmethod
    def search_smzdm(keyword, max_items=10):
        """
        什么值得买搜索（推荐！最稳定）
        聚合京东/淘宝/天猫/拼多多等所有平台价格
        """
        results = []
        try:
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                'Cookie': 'device_id=xxx',
            }
            
            # 什么值得买搜索API
            url = f"https://search.smzdm.com/?cate=1&keyword={keyword}&v=a"
            resp = requests.get(url, headers=headers, timeout=15)
            
            if resp.status_code == 200:
                # 解析搜索结果
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                for item in soup.select('.feed-row-wide')[:max_items]:
                    try:
                        title_el = item.select_one('.feed-block-title a')
                        title = title_el.get_text(strip=True) if title_el else ''
                        
                        price_el = item.select_one('.red, .price')
                        price_text = price_el.get_text(strip=True) if price_el else '0'
                        
                        # 提取价格数字
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        price = float(price_match.group()) if price_match else 0
                        
                        # 提取平台来源
                        平台_el = item.select_one('.source')
                        平台 = 平台_el.get_text(strip=True) if 平台_el else '未知'
                        
                        link = title_el.get('href', '') if title_el else ''
                        
                        # 提取优惠信息
                        zhi_el = item.select_one('.zhi')
                        zhi = zhi_el.get_text(strip=True) if zhi_el else '0'
                        
                        if title and price > 0:
                            results.append({
                                '名称': title[:80],
                                '价格(元)': price,
                                '平台': 平台,
                                '链接': link,
                                '推荐值': zhi,
                                '来源': '什么值得买',
                                '时间': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            })
                    except Exception:
                        continue
                        
        except Exception as e:
            st.warning(f"什么值得买搜索失败: {str(e)[:50]}")
        
        return results

    @staticmethod
    def search_jd(keyword, max_items=10):
        """
        京东搜索（使用内部API，比网页版稳定）
        """
        results = []
        try:
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36'
                ),
                'Referer': 'https://search.jd.com/',
            }
            
            # 京东搜索API
            url = f"https://search.jd.com/Search?keyword={keyword}&enc=utf-8"
            resp = requests.get(url, headers=headers, timeout=15)
            
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                for item in soup.select('.gl-item')[:max_items]:
                    try:
                        title_el = item.select_one('.p-name a')
                        title = title_el.get_text(strip=True) if title_el else ''
                        
                        price_el = item.select_one('.p-price i')
                        price_text = price_el.get_text(strip=True) if price_el else '0'
                        price = float(price_text) if price_text.replace('.', '').isdigit() else 0
                        
                        shop_el = item.select_one('.p-shop a')
                        shop = shop_el.get_text(strip=True) if shop_el else '京东自营'
                        
                        link_el = item.select_one('.p-name a')
                        link = f"https:{link_el.get('href', '')}" if link_el else ''
                        
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
                    except Exception:
                        continue
                        
        except Exception as e:
            st.warning(f"京东搜索失败: {str(e)[:50]}")
        
        return results

    @classmethod
    def search_all(cls, keyword, max_items=10):
        """从多个来源搜索，合并结果"""
        all_results = []
        
        # 1. 什么值得买（主力，聚合多平台）
        smzdm_results = cls.search_smzdm(keyword, max_items)
        all_results.extend(smzdm_results)
        
        # 2. 京东（补充）
        jd_results = cls.search_jd(keyword, max_items)
        all_results.extend(jd_results)
        
        # 按价格排序
        all_results.sort(key=lambda x: x.get('价格(元)', 99999))
        
        return all_results

    @classmethod
    def batch_search(cls, perfume_dict):
        """批量搜索所有监控的香水"""
        all_data = []
        progress_bar = st.progress(0, text="正在搜索各平台价格...")
        
        for i, (name, keyword) in enumerate(perfume_dict.items()):
            progress_text = f"📡 正在搜索: {name} ({i+1}/{len(perfume_dict)})"
            progress_bar.progress((i + 1) / len(perfume_dict), text=progress_text)
            
            results = cls.search_all(keyword, max_items=3)
            for r in results:
                r['监控名称'] = name
                all_data.append(r)
            
            time.sleep(1)  # 避免请求过快
        
        progress_bar.empty()
        return all_data

# ============================================================
# 价格历史追踪（保存在 session_state 中）
# ============================================================
class PriceTracker:
    @staticmethod
    def init_history():
        if 'price_history' not in st.session_state:
            st.session_state.price_history = pd.DataFrame(columns=[
                '监控名称', '名称', '价格(元)', '平台', '时间'
            ])
    
    @staticmethod
    def add_record(df):
        new_df = df[['监控名称', '名称', '价格(元)', '平台', '时间']].copy()
        st.session_state.price_history = pd.concat([
            st.session_state.price_history, new_df
        ], ignore_index=True).tail(1000)  # 最多保留1000条
    
    @staticmethod
    def get_lowest_price(perfume_name, platform=None):
        """获取某款香水的最低价"""
        df = st.session_state.price_history
        mask = df['监控名称'] == perfume_name
        if platform:
            mask &= df['平台'] == platform
        filtered = df[mask]
        if len(filtered) > 0:
            return filtered.loc[filtered['价格(元)'].idxmin()]
        return None

# ============================================================
# 界面
# ============================================================

# 初始化历史记录
PriceTracker.init_history()

# 侧边栏
with st.sidebar:
    st.header("⚙️ 设置")
    
    # 监控的香水列表
    st.subheader("📋 监控清单")
    selected_perfumes = {}
    for name, keyword in PERFUME_LIST.items():
        if st.checkbox(name, value=True, key=f"p_{name}"):
            selected_perfumes[name] = keyword
    
    # 自定义添加
    st.subheader("➕ 自定义添加")
    custom_name = st.text_input("香水名称")
    custom_keyword = st.text_input("搜索关键词")
    if st.button("添加到监控") and custom_name and custom_keyword:
        PERFUME_LIST[custom_name] = custom_keyword
        st.success(f"已添加 {custom_name}")
        st.rerun()
    
    # 操作按钮
    st.markdown("---")
    scan_btn = st.button("🔍 扫描价格", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.caption("📌 数据来源")
    st.caption("- 什么值得买 (smzdm.com)")
    st.caption("- 京东 (jd.com)")
    st.caption("自动聚合所有平台价格")

# ============================================================
# 主界面
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 当前价格", "📈 价格趋势", "🔔 降价提醒", "📋 历史记录"
])

with tab1:
    st.subheader("📊 香水价格实时扫描")
    
    if scan_btn or 'current_prices' not in st.session_state:
        with st.spinner("正在扫描各平台价格..."):
            results = PriceCrawler.batch_search(selected_perfumes)
            st.session_state.current_prices = results
            # 保存到历史
            if results:
                PriceTracker.add_record(pd.DataFrame(results))
    
    results = st.session_state.get('current_prices', [])
    
    if results:
        df = pd.DataFrame(results)
        
        # 显示统计
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📦 商品数", len(df['名称'].unique()))
        col2.metric("🏪 覆盖平台", len(df['平台'].unique()))
        col3.metric("💰 均价", f"¥{df['价格(元)'].mean():.0f}")
        col4.metric("💎 最低价", f"¥{df['价格(元)'].min():.0f}")
        
        # 按监控名称分组展示
        for perfume_name in selected_perfumes:
            perfume_data = df[df['监控名称'] == perfume_name]
            if len(perfume_data) > 0:
                with st.expander(f"🧴 {perfume_name} ({len(perfume_data)}条)", expanded=True):
                    # 最低价高亮
                    min_price_row = perfume_data.loc[perfume_data['价格(元)'].idxmin()]
                    
                    st.markdown(f"""
                    <div style="
                        background: #e8f5e9;
                        padding: 10px 15px;
                        border-radius: 8px;
                        margin-bottom: 10px;
                        border-left: 4px solid #4caf50;
                    ">
                        <strong>🏆 最低价</strong>: 
                        ¥{min_price_row['价格(元)']:.0f} 
                        来自 <strong>{min_price_row['平台']}</strong>
                        <a href="{min_price_row.get('链接', '#')}" target="_blank"> 🔗 查看</a>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 表格显示
                    display_cols = ['名称', '价格(元)', '平台', '时间']
                    if '店铺' in perfume_data.columns:
                        display_cols.insert(2, '店铺')
                    st.dataframe(
                        perfume_data[display_cols].sort_values('价格(元)'),
                        use_container_width=True,
                        column_config={
                            '价格(元)': st.column_config.NumberColumn(format="¥%.0f"),
                            '名称': st.column_config.TextColumn(width='large'),
                        }
                    )
        
        # 导出
        st.markdown("---")
        if st.button("📥 导出当前价格"):
            csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
            st.download_button(
                "下载 CSV",
                csv,
                f"香水价格_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            )
    else:
        st.info("💡 点击「扫描价格」按钮开始搜索，或稍后重试")
        st.markdown("""
        **首次使用？**
        - 确保左侧勾选了要监控的香水
        - 点击「扫描价格」按钮
        - 系统会从什么值得买和京东搜索价格
        """)

with tab2:
    st.subheader("📈 价格趋势")
    
    if not st.session_state.price_history.empty:
        history = st.session_state.price_history
        
        # 选择要查看的香水
        perfumes_in_history = history['监控名称'].unique()
        selected = st.selectbox("选择香水", perfumes_in_history)
        
        perfume_history = history[history['监控名称'] == selected].copy()
        perfume_history['时间'] = pd.to_datetime(perfume_history['时间'])
        perfume_history = perfume_history.sort_values('时间')
        
        if len(perfume_history) > 1:
            # 折线图
            fig = px.line(
                perfume_history,
                x='时间', y='价格(元)', color='平台',
                title=f"{selected} 价格趋势",
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 统计
            col1, col2, col3 = st.columns(3)
            col1.metric("📊 扫描次数", len(perfume_history))
            col2.metric("💰 最低价", f"¥{perfume_history['价格(元)'].min():.0f}")
            col3.metric("📈 当前价", f"¥{perfume_history['价格(元)'].iloc[-1]:.0f}")
        else:
            st.info("数据不足，需要多次扫描才能生成趋势")
    else:
        st.info("暂无历史数据，请先在「当前价格」标签页扫描")

with tab3:
    st.subheader("🔔 降价提醒")
    
    # 设置降价提醒阈值
    st.markdown("设置降价提醒，当价格低于某个值时通知你")
    
    alert_settings = {}
    for name in selected_perfumes:
        target_price = st.number_input(
            f"{name} 目标价格 (元)",
            min_value=0, value=500, step=50,
            key=f"alert_{name}"
        )
        alert_settings[name] = target_price
    
    if st.button("检查降价", type="primary"):
        results = st.session_state.get('current_prices', [])
        if not results:
            st.warning("请先在「当前价格」标签页扫描价格")
        else:
            df = pd.DataFrame(results)
            alerts = []
            for name, target in alert_settings.items():
                perfume_data = df[df['监控名称'] == name]
                if len(perfume_data) > 0:
                    min_price = perfume_data['价格(元)'].min()
                    if min_price <= target:
                        alerts.append(f"✅ {name}: ¥{min_price:.0f} ≤ ¥{target:.0f} (已达到目标)")
                    else:
                        alerts.append(f"⏳ {name}: ¥{min_price:.0f} > ¥{target:.0f} (差¥{min_price-target:.0f})")
            
            for alert in alerts:
                st.write(alert)

with tab4:
    st.subheader("📋 历史记录")
    
    if not st.session_state.price_history.empty:
        st.dataframe(
            st.session_state.price_history.sort_values('时间', ascending=False),
            use_container_width=True
        )
        
        # 清空历史
        if st.button("清空历史"):
            st.session_state.price_history = pd.DataFrame(columns=[
                '监控名称', '名称', '价格(元)', '平台', '时间'
            ])
            st.rerun()
    else:
        st.info("暂无历史记录")

st.caption(
    f"📊 数据来源: 什么值得买 / 京东 | "
    f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
    f"注意: 价格仅供参考，实际以平台为准"
)
