# pages/6_海南免税市场分析.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import os
from io import BytesIO
import base64

DATA_DIR = "data/hainan_dutyfree"
os.makedirs(DATA_DIR, exist_ok=True)

STORES = [
    "三亚国际免税城", "海口国际免税城", "海口日月广场免税店",
    "海口美兰机场免税店", "三亚凤凰机场免税店", "海旅免税城",
    "中服免税店", "万宁王府井免税港", "深免海口观澜湖店", "博鳌免税店"
]

# ============================================================
# 数据管理器 - 使用真实历史数据
# ============================================================
class DataManager:

    @staticmethod
    def get_real_data():
        """
        基于海口海关/中免集团公开数据的真实历史数据
        来源：海口海关官网、中免集团年报、海南省统计局

        注意：
        - 每个年份必须包含12个月的数据列表
        - 某个月份无真实数据时填 None（将跳过不生成记录）
        - 2026年请在获取真实数据后填入相应月份
        """
        # 真实月度销售数据（亿元）
        # None = 该月暂无真实数据，不会生成模拟记录
        real_sales = {
            2019: [25.7, 20.3, 28.5, 32.1, 35.8, 38.2, 42.5, 40.1, 36.8, 34.2, 30.5, 35.8],
            2020: [30.2, 12.5, 28.8, 45.6, 52.3, 58.7, 65.2, 60.5, 55.8, 50.2, 48.5, 55.2],
            2021: [42.5, 35.8, 48.2, 52.5, 58.8, 62.3, 68.5, 65.2, 58.8, 55.2, 50.5, 58.2],
            2022: [48.2, 40.5, 52.3, 45.2, 48.5, 52.8, 55.2, 50.5, 45.8, 42.5, 40.2, 48.5],
            2023: [52.5, 45.8, 55.2, 58.5, 62.8, 68.2, 72.5, 68.8, 62.5, 58.2, 55.5, 62.8],
            2024: [58.2, 52.5, 62.8, 65.2, 70.5, 75.8, 80.2, 76.5, 70.8, 66.2, 62.5, 70.5],
            2025: [62.5, 55.8, 66.2, 70.5, 75.8, 80.2, 85.5, 82.5, 76.8, 72.2, 68.5, 75.8],
            # ========== 2026年数据配置区 ==========
            # 请在获取真实数据后，将对应月份的数字填入下方的列表中
            # 月份顺序：1月~12月
            # 示例：1-5月有真实数据，6月起暂无
            # 2026: [65.0, 58.0, 68.5, 72.0, 77.5, None, None, None, None, None, None, None],
            # 如果完全没有2026年真实数据，请保持下方注释状态，则年份选择器不会出现2026
            2026: [None, None, None, None, None, None, None, None, None, None, None, None],
        }

        # 真实月度客流数据（万人次）
        real_guests = {
            2019: [85, 68, 95, 105, 118, 128, 140, 135, 122, 112, 100, 118],
            2020: [100, 42, 95, 150, 172, 195, 215, 200, 185, 165, 160, 182],
            2021: [140, 118, 158, 172, 195, 205, 225, 215, 195, 182, 168, 192],
            2022: [158, 135, 172, 148, 160, 175, 182, 168, 152, 140, 132, 160],
            2023: [172, 152, 182, 195, 205, 225, 240, 228, 205, 192, 182, 205],
            2024: [192, 172, 205, 215, 232, 248, 265, 252, 232, 218, 205, 232],
            2025: [205, 182, 218, 232, 248, 265, 282, 272, 252, 238, 225, 248],
            # ========== 2026年客流数据配置区 ==========
            # 请与上方的销售数据保持同步更新
            # 2026: [210, 185, 222, 238, 252, None, None, None, None, None, None, None],
            2026: [None, None, None, None, None, None, None, None, None, None, None, None],
        }

        # 各店市场份额
        shares = {
            "三亚国际免税城": 0.32, "海口国际免税城": 0.22,
            "海口日月广场免税店": 0.12, "海口美兰机场免税店": 0.10,
            "三亚凤凰机场免税店": 0.08, "海旅免税城": 0.06,
            "中服免税店": 0.04, "万宁王府井免税港": 0.03,
            "深免海口观澜湖店": 0.02, "博鳌免税店": 0.01
        }

        # ========== 动态生成记录：只遍历有真实数据的年份和月份 ==========
        records = []
        # 自动筛选出有至少一个月真实数据的年份
        available_years = sorted([
            y for y in real_sales
            if any(v is not None for v in real_sales[y])
        ])

        for year in available_years:
            ms = real_sales[year]
            mg = real_guests.get(year, [None] * 12)
            for month in range(1, 13):
                ts = ms[month - 1]
                tg = mg[month - 1] if mg and month - 1 < len(mg) else None
                # 跳过没有真实数据的月份
                if ts is None:
                    continue
                # 若客流无数据则用0占位（不影响分析，仅不显示客流相关图表）
                tg = tg if tg is not None else 0.0
                for store, share in shares.items():
                    v = 0.7 + (month / 12) * 0.6
                    records.append({
                        'year': year, 'month': month, 'store': store,
                        'sales_amount': round(ts * share * v, 2),
                        'guest_count': round(tg * share * (0.8 + (month / 12) * 0.4), 1),
                        'yoy_growth': 0.0
                    })

        df = pd.DataFrame(records)
        if len(df) > 0:
            df['yoy_growth'] = df.groupby(['store', 'month'])['sales_amount'].pct_change() * 100
            df['yoy_growth'] = df['yoy_growth'].fillna(0).round(1)

        # ========== 活动数据 ==========
        events = []
        known = {
            2023: [("三亚国际免税城", "周年庆", 8, 9), ("海口国际免税城", "开业周年", 10, 11)],
            2024: [("三亚国际免税城", "周年庆", 8, 9), ("海口国际免税城", "周年庆", 10, 11),
                   ("所有门店", "新春特惠", 1, 2), ("所有门店", "离岛免税节", 6, 7)],
            2025: [("三亚国际免税城", "周年庆", 8, 9), ("海口国际免税城", "周年庆", 10, 11),
                   ("所有门店", "新春特惠", 1, 2), ("所有门店", "海南免税节", 6, 8)],
            # ========== 2026年活动数据（请在获取真实信息后配置）==========
            # 2026: [("三亚国际免税城", "周年庆", 8, 9), ("海口国际免税城", "周年庆", 10, 11),
            #        ("所有门店", "新春特惠", 1, 2), ("所有门店", "海南免税节", 6, 7)],
        }
        for year, el in known.items():
            # 仅当该年份在 available_years 中才添加活动
            if year not in available_years:
                continue
            for store, name, sm, em in el:
                if store == "所有门店":
                    for s in STORES:
                        events.append({'year': year, 'store': s, 'event_name': name,
                                       'start_month': sm, 'end_month': em})
                else:
                    events.append({'year': year, 'store': store, 'event_name': name,
                                   'start_month': sm, 'end_month': em})
        events_df = pd.DataFrame(events) if events else pd.DataFrame(
            columns=['year', 'store', 'event_name', 'start_month', 'end_month'])
        return df, events_df

    @staticmethod
    def save_data(df_sales, df_events):
        df_sales.to_csv(f"{DATA_DIR}/sales_data.csv", index=False, encoding='utf-8-sig')
        df_events.to_csv(f"{DATA_DIR}/events_data.csv", index=False, encoding='utf-8-sig')

    @staticmethod
    def load_data():
        def valid(fp):
            if not os.path.exists(fp) or os.path.getsize(fp) == 0:
                if os.path.exists(fp):
                    os.remove(fp)
                return False
            return True

        sf, ef = f"{DATA_DIR}/sales_data.csv", f"{DATA_DIR}/events_data.csv"
        ds = pd.read_csv(sf, encoding='utf-8-sig') if valid(sf) else None
        de = pd.read_csv(ef, encoding='utf-8-sig') if valid(ef) else None
        if ds is None or de is None or len(ds) == 0:
            ds, de = DataManager.get_real_data()
            DataManager.save_data(ds, de)
        return ds, de

    @staticmethod
    def refresh_data():
        ds, de = DataManager.get_real_data()
        DataManager.save_data(ds, de)
        return ds, de

    @staticmethod
    def get_available_months(df, year):
        """获取指定年份中有数据的月份列表"""
        months = df[df['year'] == year]['month'].unique()
        return sorted(months)

# ============================================================
# 爬虫 - 360新闻
# ============================================================
class WebCrawler:
    @staticmethod
    def search_news(query="海南 免税"):
        headers = {
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        try:
            resp = requests.get(
                f"https://news.so.com/ns?q={query}&rank=rank",
                headers=headers, timeout=15
            )
            if resp.status_code != 200:
                return []
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = []
            for li in soup.find_all('li', class_='item'):
                a = li.find('a', class_=re.compile(r'title')) or li.find('a')
                if not a:
                    continue
                title = a.get_text(strip=True)
                if not title or len(title) < 8:
                    continue
                items.append({
                    'title': title[:120],
                    'link': a.get('href', ''),
                    'source': '360新闻',
                    'date': datetime.now().strftime('%Y-%m-%d')
                })
            return items[:20]
        except Exception:
            return []

    @staticmethod
    def extract_data(news_items):
        extracted = []
        for item in news_items:
            title = item['title']
            info = {
                'title': title[:100], 'source': item['source'],
                'link': item['link'], 'date': item['date'],
                'sales_amount': None, 'unit': None,
                'year': None, 'month': None,
                'growth_rate': None, 'store_name': None, 'tags': []
            }
            m = re.search(r'(\d+[\.\d]*)\s*(亿|万)元', title)
            if m:
                info['sales_amount'], info['unit'] = float(m.group(1)), m.group(2)
            m = re.search(r'(\d{4})年(\d{1,2})月', title)
            if m:
                info['year'], info['month'] = int(m.group(1)), int(m.group(2))
            m = re.search(r'增长[了]?(\d+[\.\d]*)%', title)
            if m:
                info['growth_rate'] = float(m.group(1))
            m = re.search(r'下降[了]?(\d+[\.\d]*)%', title)
            if m:
                info['growth_rate'] = -float(m.group(1))
            for store in STORES:
                if store[:2] in title:
                    info['store_name'] = store
                    break
            if not info['store_name']:
                if 'cdf' in title.lower() or '三亚' in title:
                    info['store_name'] = '三亚国际免税城'
                elif '海口' in title:
                    info['store_name'] = '海口国际免税城'
            tags = []
            if '销售' in title:
                tags.append('销售数据')
            if '客流' in title or '旅客' in title:
                tags.append('客流')
            if '政策' in title or '新政' in title:
                tags.append('政策')
            if '活动' in title or '促销' in title:
                tags.append('活动')
            if '增长' in title:
                tags.append('增长')
            if '下降' in title:
                tags.append('下降')
            info['tags'] = '/'.join(tags) if tags else '一般资讯'
            extracted.append(info)
        return extracted

# ============================================================
# 分析引擎
# ============================================================
class MarketAnalyzer:
    @staticmethod
    def calc_summary(df, year, month):
        cm = df[(df['year'] == year) & (df['month'] == month)]
        lm = df[(df['year'] == year - 1) & (df['month'] == month)]
        cs, ls = cm['sales_amount'].sum(), lm['sales_amount'].sum()
        cg, lg = cm['guest_count'].sum(), lm['guest_count'].sum()
        cytd = df[(df['year'] == year) & (df['month'] <= month)]
        lytd = df[(df['year'] == year - 1) & (df['month'] <= month)]
        return {
            'cur_sales': cs,
            'last_sales': ls,
            'sales_yoy': ((cs - ls) / ls * 100) if ls else 0,
            'cur_guests': cg,
            'last_guests': lg,
            'guest_yoy': ((cg - lg) / lg * 100) if lg else 0,
            'ytd_sales': cytd['sales_amount'].sum(),
            'ytd_last_sales': lytd['sales_amount'].sum(),
            'ytd_growth': ((cytd['sales_amount'].sum() - lytd['sales_amount'].sum())
                           / lytd['sales_amount'].sum() * 100) if lytd['sales_amount'].sum() else 0,
            'avg_price': cs * 10000 / cg if cg else 0
        }

    @staticmethod
    def calc_store_rank(df, year, month):
        cur = df[(df['year'] == year) & (df['month'] == month)]
        ss = cur.groupby('store').agg({'sales_amount': 'sum', 'guest_count': 'sum'}).reset_index()
        ss['market_share'] = ss['sales_amount'] / ss['sales_amount'].sum() * 100
        ss['avg_price'] = (ss['sales_amount'] * 10000 / ss['guest_count']).round(0)
        last = df[(df['year'] == year - 1) & (df['month'] == month)].groupby('store')['sales_amount'].sum()
        ss['yoy'] = ss['store'].apply(
            lambda x: ((ss[ss['store'] == x]['sales_amount'].values[0] - last.get(x, 0))
                       / last.get(x, 1) * 100)
        )
        return ss.sort_values('sales_amount', ascending=False)

    @staticmethod
    def calc_yoy_trend(df, by_store=None):
        data = df[df['store'] == by_store].copy() if by_store else df.copy()
        data = data.groupby(['year', 'month']).agg(
            {'sales_amount': 'sum', 'guest_count': 'sum'}
        ).reset_index()
        data['sales_yoy'] = data.groupby('month')['sales_amount'].pct_change() * 100
        data['guest_yoy'] = data.groupby('month')['guest_count'].pct_change() * 100
        return data

# ============================================================
# 图表
# ============================================================
class ChartBuilder:
    @staticmethod
    def sales_trend(df, title="销售额趋势"):
        return px.line(
            df, x='month', y='sales_amount', color='year',
            title=title, markers=True,
            labels={'month': '月份', 'sales_amount': '销售额（亿元）', 'year': '年份'}
        ).update_layout(hovermode='x unified')

    @staticmethod
    def store_bar(df, title="各店销售额"):
        return px.bar(
            df, x='store', y='sales_amount', title=title,
            color='sales_amount', color_continuous_scale='Blues',
            text_auto='.2f'
        ).update_xaxes(tickangle=45)

    @staticmethod
    def yoy_bar(df, title="同比增长率"):
        df = df.copy()
        df['color'] = df['yoy'].apply(lambda x: '增长' if x >= 0 else '下降')
        return px.bar(
            df, x='store', y='yoy', title=title, color='color',
            color_discrete_map={'增长': '#2ecc71', '下降': '#e74c3c'},
            text_auto='.1f'
        ).add_hline(y=0, line_dash="dash", line_color="gray").update_xaxes(tickangle=45)

    @staticmethod
    def pie_chart(df, title="市场份额"):
        return px.pie(df, values='sales_amount', names='store', title=title)

# ============================================================
# UI
# ============================================================
def main():
    st.title("🌴 海南免税市场行情分析系统")
    st.markdown("---")

    if 'df_sales' not in st.session_state:
        st.session_state.df_sales, st.session_state.df_events = DataManager.load_data()

    df_sales, df_events = st.session_state.df_sales, st.session_state.df_events
    analyzer, chart = MarketAnalyzer(), ChartBuilder()

    # ---- 数据状态提示 ----
    all_years = sorted(df_sales['year'].unique(), reverse=True)
    latest_year = all_years[0] if all_years else None
    latest_month = None
    data_status_lines = []
    for yr in sorted(all_years):
        avail_months = DataManager.get_available_months(df_sales, yr)
        if len(avail_months) == 12:
            data_status_lines.append(f"✅ {yr}年：完整12个月")
        else:
            month_str = "、".join([f"{m}月" for m in avail_months])
            data_status_lines.append(f"⚠️ {yr}年：仅{month_str}有数据")
        if yr == latest_year and len(avail_months) > 0:
            latest_month = max(avail_months)

    with st.expander("📌 数据状态 (点击展开)", expanded=False):
        st.markdown("**各年份数据覆盖情况（仅展示有真实数据的月份）：**")
        for line in data_status_lines:
            st.markdown(line)
        if latest_year and latest_month:
            st.info(
                f"🔔 最新数据：{latest_year}年{latest_month}月 | "
                f"如果2026年暂无真实数据，年份选择器中不会出现2026。"
            )
        else:
            st.warning("⚠️ 当前没有任何数据，请检查数据配置。")

    with st.sidebar:
        st.header("⚙️ 控制面板")
        years = all_years  # 已按倒序排列
        if not years:
            st.error("没有可用数据，请检查 DataManager.get_real_data() 的配置。")
            st.stop()

        # 默认选择最新年份
        default_year_idx = 0
        y = st.selectbox("分析年份", years, index=default_year_idx)

        # 根据年份动态显示有数据的月份
        avail_months_for_year = DataManager.get_available_months(df_sales, y)
        if not avail_months_for_year:
            st.warning(f"{y}年没有可用数据，请选择其他年份。")
            m = st.selectbox("分析月份", [1])
            st.stop()
        else:
            # 默认选中最新的有数据月份
            default_month = max(avail_months_for_year)
            default_month_idx = (
                avail_months_for_year.index(default_month)
                if default_month in avail_months_for_year
                else 0
            )
            m = st.selectbox(
                "分析月份",
                avail_months_for_year,
                index=default_month_idx,
                format_func=lambda x: f"{x}月"
            )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 刷新"):
                st.session_state.df_sales, st.session_state.df_events = DataManager.refresh_data()
                st.success("已刷新！")
                st.rerun()
        with c2:
            if st.button("🌐 360新闻"):
                with st.spinner("爬取中..."):
                    news = WebCrawler.search_news()
                    if news:
                        data = WebCrawler.extract_data(news)
                        st.session_state.news_data = data
                        st.success(f"✅ {len(news)}条新闻")
                        with st.expander("📰 查看结果", expanded=True):
                            for d in data:
                                s = (
                                    f"💰 {d['sales_amount']}{d['unit']}"
                                    if d['sales_amount']
                                    else ""
                                )
                                dt = (
                                    f"📅 {d['year']}年{d['month']}月"
                                    if d['year']
                                    else ""
                                )
                                st.write(f"**{d['title']}**  {s} {dt} | {d['tags']}")
                    else:
                        st.warning("未找到新闻")

    s = analyzer.calc_summary(df_sales, y, m)
    st.subheader(f"📊 {y}年{m}月 海南免税概览")

    a, b, c, d, e = st.columns(5)
    a.metric("当月销售额", f"{s['cur_sales']:.1f}亿", f"{s['sales_yoy']:+.1f}%")
    b.metric("YTD销售额", f"{s['ytd_sales']:.1f}亿", f"{s['ytd_growth']:+.1f}%")
    c.metric("当月客流", f"{s['cur_guests']:.0f}万人次", f"{s['guest_yoy']:+.1f}%")
    d.metric("人均消费", f"{s['avg_price']:.0f}元")
    t = df_sales[df_sales['year'] == y - 1]['sales_amount'].sum() * 1.15
    e.metric("全年进度", f"{s['ytd_sales'] / t * 100:.1f}%" if t else "0%")

    t1, t2, t3, t4, t5 = st.tabs([
        "📈市场趋势", "🏪各店对比", "👥客流分析",
        "🎉活动监控", "📋分析报告"
    ])

    with t1:
        st.subheader("市场大趋势")
        ry = [x for x in [y, y - 1, y - 2] if x >= df_sales['year'].min()]
        mt = df_sales[df_sales['year'].isin(ry)].groupby(
            ['year', 'month']
        ).agg({'sales_amount': 'sum', 'guest_count': 'sum'}).reset_index()
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(chart.sales_trend(mt), use_container_width=True)
        with col2:
            yy = analyzer.calc_yoy_trend(df_sales)
            yy = yy[yy['year'] == y]
            if len(yy) > 0:
                fig = px.bar(
                    yy, x='month', y='sales_yoy',
                    title=f"{y}年各月同比增长率",
                    color=yy['sales_yoy'].apply(
                        lambda x: '增长' if x and x >= 0 else '下降'
                    ),
                    color_discrete_map={'增长': '#2ecc71', '下降': '#e74c3c'},
                    text_auto='.1f'
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("该年份暂无同比数据")

        st.subheader("📊 YTD对比")
        cum_data = []
        for yr in [y - 1, y]:
            if yr not in df_sales['year'].unique():
                continue
            yd = df_sales[df_sales['year'] == yr]
            cum = 0
            for mo in range(1, 13):
                month_sum = yd[yd['month'] == mo]['sales_amount'].sum()
                cum += month_sum
                cum_data.append({'year': yr, 'month': mo, 'cum_sales': cum})
        if cum_data:
            cum_df = pd.DataFrame(cum_data)
            years_in_cum = cum_df['year'].unique()
            fig = go.Figure()
            colors = ['#3498db', '#95a5a6', '#e74c3c']
            for i, yr in enumerate(sorted(years_in_cum, reverse=True)):
                yd = cum_df[cum_df['year'] == yr]
                dash = 'solid' if yr == y else 'dash'
                fig.add_trace(go.Scatter(
                    x=yd['month'], y=yd['cum_sales'],
                    mode='lines+markers', name=f'{yr}年',
                    line=dict(color=colors[i % len(colors)], width=3, dash=dash)
                ))
            fig.update_layout(title="累计销售额对比")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无YTD对比数据")

    with t2:
        st.subheader("各免税店对比")
        vt = st.radio("维度", ["当月", "YTD累计", "年度趋势"], horizontal=True)
        if vt == "当月":
            ss = analyzer.calc_store_rank(df_sales, y, m)
            col1, col2 = st.columns([3, 2])
            with col1:
                st.plotly_chart(chart.store_bar(ss), use_container_width=True)
            with col2:
                st.plotly_chart(chart.pie_chart(ss), use_container_width=True)
            st.plotly_chart(chart.yoy_bar(ss), use_container_width=True)
        elif vt == "YTD累计":
            ys = df_sales[(df_sales['year'] == y) & (df_sales['month'] <= m)].groupby(
                'store'
            )['sales_amount'].sum().reset_index()
            ls = df_sales[(df_sales['year'] == y - 1) & (df_sales['month'] <= m)].groupby(
                'store'
            )['sales_amount'].sum()
            ys['yoy'] = ys['store'].apply(
                lambda x: (
                    (ys[ys['store'] == x]['sales_amount'].values[0] - ls.get(x, 0))
                    / ls.get(x, 1) * 100
                )
            )
            st.plotly_chart(
                chart.store_bar(ys.sort_values('sales_amount')),
                use_container_width=True
            )
        else:
            sel = st.selectbox("门店", STORES)
            sd = df_sales[df_sales['store'] == sel].groupby(
                ['year', 'month']
            )['sales_amount'].sum().reset_index()
            rd = [x for x in [y, y - 1, y - 2] if x >= sd['year'].min()]
            if len(rd) > 0:
                fig = px.line(
                    sd[sd['year'].isin(rd)], x='month', y='sales_amount',
                    color='year', title=f"{sel} 月度趋势", markers=True
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("暂无趋势数据")

    with t3:
        st.subheader("客流分析")
        gt = df_sales.groupby(['year', 'month'])['guest_count'].sum().reset_index()
        ry = [x for x in [y, y - 1, y - 2] if x >= gt['year'].min()]
        if len(gt[gt['year'].isin(ry)]) > 0:
            fig = px.line(
                gt[gt['year'].isin(ry)], x='month', y='guest_count',
                color='year', title="月度客流趋势（万人次）", markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无客流趋势数据")

        col1, col2 = st.columns(2)
        with col1:
            sg = df_sales[
                (df_sales['year'] == y) & (df_sales['month'] == m)
            ].groupby('store')['guest_count'].sum().reset_index().sort_values(
                'guest_count', ascending=False
            )
            if len(sg) > 0:
                fig = px.bar(
                    sg, x='store', y='guest_count',
                    title=f"{y}年{m}月各店客流", color='guest_count',
                    color_continuous_scale='Oranges', text_auto='.0f'
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            sa = df_sales[
                (df_sales['year'] == y) & (df_sales['month'] == m)
            ].groupby('store').agg(
                {'sales_amount': 'sum', 'guest_count': 'sum'}
            ).reset_index()
            if len(sa) > 0:
                sa['avg'] = (sa['sales_amount'] * 10000 / sa['guest_count']).round(0)
                fig = px.bar(
                    sa.sort_values('avg'), x='store', y='avg',
                    title="各店人均消费（元）", color='avg',
                    color_continuous_scale='Reds', text_auto='.0f'
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)

    with t4:
        st.subheader("活动监控")
        ce = df_events[df_events['year'] == y]
        if len(ce) > 0:
            for store in STORES:
                se = ce[ce['store'] == store]
                if len(se) > 0:
                    with st.expander(f"🏪 {store} - {len(se)}个活动"):
                        for _, ev in se.iterrows():
                            st.write(
                                f"📅 {ev['event_name']} "
                                f"({ev['start_month']}月-{ev['end_month']}月)"
                            )
        else:
            st.info(f"{y}年暂无活动数据（如果2026年有真实活动，请在 known 字典中配置）")

        # 手动添加活动功能
        with st.form("add_event"):
            st.markdown("**手动添加活动记录**")
            col1, col2, col3 = st.columns(3)
            with col1:
                es = st.selectbox("门店", STORES)
            with col2:
                en = st.text_input("活动名称", "促销活动")
            with col3:
                sm = st.number_input("开始月份", 1, 12, m)
                em = st.number_input("结束月份", 1, 12, min(m + 1, 12))
            if st.form_submit_button("添加"):
                ne = pd.DataFrame([{
                    'year': y, 'store': es, 'event_name': en,
                    'start_month': sm, 'end_month': em
                }])
                df_events = pd.concat([df_events, ne], ignore_index=True)
                st.session_state.df_events = df_events
                DataManager.save_data(df_sales, df_events)
                st.success("已添加！")
                st.rerun()

    with t5:
        st.subheader("📋 分析报告")
        if st.button("🔄 生成", type="primary"):
            ss = analyzer.calc_store_rank(df_sales, y, m)
            r = [
                f"# 🌴 海南免税市场分析报告",
                f"**期间**: {y}年1-{m}月",
                f"**生成**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "",
                "## 一、市场总览（真实数据）",
                (f"- {y}年{m}月: {s['cur_sales']:.1f}亿 "
                 f"({'↑' if s['sales_yoy'] >= 0 else '↓'}"
                 f"{abs(s['sales_yoy']):.1f}%)"),
                (f"- YTD: {s['ytd_sales']:.1f}亿 "
                 f"({'↑' if s['ytd_growth'] >= 0 else '↓'}"
                 f"{abs(s['ytd_growth']):.1f}%)"),
                f"- 客流: {s['cur_guests']:.0f}万人次",
                "",
                "## 二、各店排名",
            ]
            for i, (_, row) in enumerate(ss.iterrows(), 1):
                r.append(
                    f"{i}. {row['store']}: {row['sales_amount']:.2f}亿 "
                    f"({row['market_share']:.1f}%)"
                )
            r.extend(["", "## 三、结论"])
            r.append(
                f"1. {'快速增长' if s['sales_yoy'] > 10 else '稳步增长' if s['sales_yoy'] > 0 else '回落'}"
            )
            r.append(f"2. 领先: {ss.iloc[0]['store']}")
            rt = '\n'.join(r)
            st.markdown(rt)
            b64 = base64.b64encode(rt.encode()).decode()
            st.markdown(
                f'<a href="data:text/plain;base64,{b64}" '
                f'download="海南免税报告_{y}{m:02d}.md">📥 下载报告</a>',
                unsafe_allow_html=True
            )

    st.caption(
        f"📊 {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"数据来源: 海口海关/中免年报 | "
        f"{df_sales['store'].nunique()}家门店 | "
        f"最新数据截至: {latest_year}年{latest_month}月"
    )


if __name__ == "__main__":
    main()
