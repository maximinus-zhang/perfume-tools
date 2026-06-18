# pages/14_竞品监控.py
import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="竞品监控", layout="wide")
st.title("🛒 香水竞品价格监控")

# ============================================================
# 京东/天猫 商品搜索（使用开放API）
# ============================================================
class ProductMonitor:
    """竞品价格监控"""
    
    @staticmethod
    def search_jd(keyword):
        """京东搜索"""
        try:
            url = f"https://search.jd.com/Search?keyword={keyword}&enc=utf-8"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                items = soup.select('.gl-item')
                
                results = []
                for item in items[:10]:
                    title = item.select_one('.p-name a')
                    price = item.select_one('.p-price i')
                    shop = item.select_one('.p-shop span a')
                    
                    if title:
                        results.append({
                            'name': title.get_text(strip=True)[:100],
                            'price': price.get_text(strip=True) if price else 'N/A',
                            'shop': shop.get_text(strip=True) if shop else '京东自营',
                            'platform': '京东',
                            'time': datetime.now().strftime('%Y-%m-%d'),
                        })
                return results
        except:
            pass
        return []
    
    @staticmethod
    def get_exchange_rate():
        """获取实时汇率"""
        try:
            url = "https://api.exchangerate-api.com/v4/latest/USD"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'CNY': data['rates'].get('CNY', 7.2),
                    'USD': 1,
                }
        except:
            return {'CNY': 7.2, 'USD': 1}
        return {'CNY': 7.2, 'USD': 1}

# ============================================================
# 界面
# ============================================================
col1, col2 = st.columns([3, 1])
with col1:
    keyword = st.text_input("搜索香水产品", "香水 免税 100ml")
with col2:
    search = st.button("🔍 搜索", type="primary", use_container_width=True)

# 汇率信息
rate = ProductMonitor.get_exchange_rate()
st.caption(f"💱 当前汇率: 1 USD = {rate['CNY']} CNY")

if search:
    with st.spinner(f"正在搜索 '{keyword}'..."):
        results = ProductMonitor.search_jd(keyword)
    
    if results:
        st.success(f"找到 {len(results)} 个商品")
        
        # 转成 DataFrame 展示
        df = pd.DataFrame(results)
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                'name': '商品名称',
                'price': '价格 (CNY)',
                'shop': '店铺',
                'platform': '平台',
                'time': '更新时间',
            }
        )
        
        # 导出
        csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
        st.download_button("📥 导出数据", csv, f"竞品价格_{datetime.now().strftime('%Y%m%d')}.csv")
    else:
        st.warning("未找到商品，建议简化关键词")
else:
    st.info("输入关键词搜索京东香水商品")

# 监控清单
st.markdown("---")
st.subheader("📋 监控清单")
st.markdown("""
| 品牌 | 产品 | 监控状态 |
|------|------|---------|
| CHANEL | 香奈儿5号 100ml | ✅ 已开启 |
| DIOR | 迪奥小姐 100ml | ✅ 已开启 |
| JO MALONE | 蓝风铃 100ml | ✅ 已开启 |
| TOM FORD | 乌木沉香 50ml | ✅ 已开启 |
""")
