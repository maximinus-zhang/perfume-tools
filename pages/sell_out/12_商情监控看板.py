# -*- coding: utf-8 -*-
"""
海南免税 商情监控看板（门店级代理估算） v1.0
============================================
定位: 在「零售商 — 门店」维度展示海南离岛免税商情。

⚠️ 核心合规要求（来自 MAX）:
  1. 门店级销售/客流全部为【代理估算值】，必须带「估算」角标，禁止误判为实测。
  2. 各零售商均为合作方（COOPERATION_ALL = 合作），尽量列详细。
  3. 估算方法透明可追溯（每条记录带 method 字段，看板内可展开查看）。

防御性设计: 模块导入/计算失败只影响本页，弹友好提示，不连累 app.py 导航整站。
"""

import streamlit as st
from datetime import datetime

st.set_page_config(page_title="免税商情看板", page_icon="📊", layout="wide")

# ============================================================
# 防御性导入（任何失败只影响本页）
# ============================================================
try:
    from utils.hainan_2026_data import HA_DF_2026, SOURCE_NOTE
    from utils.hainan_retailers import (
        RETAILERS, iter_stores, store_count, COOPERATION_ALL,
    )
    from utils.hainan_estimator import (
        estimate_store_sales, estimate_by_retailer,
        ESTIMATE_BADGE, ESTIMATE_DISCLAIMER, RETAILER_SHARE,
    )
    from utils.news_analyzer import (
        fetch_news_cached, analyze_news_for_context, render_insight_markdown,
    )
    _IMPORT_OK = True
    _IMPORT_ERR = ""
except Exception as _e:  # 非裸 except，明确捕获
    _IMPORT_OK = False
    _IMPORT_ERR = str(_e)

st.title("📊 海南免税商情监控看板")
st.caption("零售商 / 门店维度 · 门店级为代理估算 · v1.0")

if not _IMPORT_OK:
    st.error(
        f"⚠️ 数据模块加载失败，本页无法显示（不影响其他页面）：{_IMPORT_ERR}\n"
        f"请检查 utils/hainan_estimator.py、hainan_retailers.py、hainan_2026_data.py 是否存在。"
    )
    st.stop()


# ============================================================
# 新闻自动分析（防御性：失败不影响主看板）
# ============================================================
try:
    _news_data = fetch_news_cached()
    _all_news = []
    for k in ["airport_news", "duty_free_news", "li_island_news", "policy_news", "travel_news"]:
        items = _news_data.get(k, [])
        for item in items:
            if isinstance(item, (tuple, list)):
                if len(item) >= 2:
                    _all_news.append((item[0], item[1]))
                else:
                    _all_news.append((str(item[0]), ""))
            else:
                _all_news.append((str(item), ""))
except Exception as _ne:
    _all_news = []
    st.caption(f"📰 新闻加载失败，自动备注暂不可用：{_ne}")


def show_insight(context, max_bullets=3):
    """在模块下方渲染新闻自动分析备注（基于官方 H1 指标做量化交叉验证）。"""
    try:
        if not _all_news:
            return
        bullets = analyze_news_for_context(
            _all_news, context, max_bullets=max_bullets, metrics=HAINAN_METRICS
        )
        st.markdown(render_insight_markdown(bullets))
    except Exception as e:
        st.caption(f"🤖 新闻备注生成失败：{e}")


# ============================================================
# 小工具：角标 + 估算强提醒
# ============================================================
def est_badge():
    """返回「估算」角标 HTML（门店级数值一律带它）。"""
    return (
        f'<span style="background:#d97706;color:#fff;padding:1px 8px;'
        f'border-radius:10px;font-size:12px;font-weight:600;">{ESTIMATE_BADGE}</span>'
    )


# ============================================================
# 顶部：全省官方大盘（这些是实测，非估算）
# ============================================================
ytd = HA_DF_2026["ytd"]
HAINAN_METRICS = {
    "h1_amount": float(ytd["amount_2026"]),
    "h1_pax": float(ytd["pax_2026"]),
    "h1_pieces": float(ytd["pieces_2026"]),
    "h1_months": 6,
    "amt_yoy": float(ytd["amt_yoy"]),
    "pax_yoy": float(ytd["pax_yoy"]),
    "pc_yoy": float(ytd["pc_yoy"]),
}
st.subheader("📌 全省大盘（官方口径 · 海口海关）")
c1, c2, c3 = st.columns(3)
c1.metric("H1 销售额", f"{ytd['amount_2026']} 亿", f"{ytd['amt_yoy']}% YoY",
          help=f"官方来源：{ytd['source']}")
c2.metric("H1 客流", f"{ytd['pax_2026']} 万人次", f"{ytd['pax_yoy']}% YoY",
          help="官方·海口海关")
c3.metric("H1 件数", f"{ytd['pieces_2026']} 万件", f"{ytd['pc_yoy']}% YoY",
          help="官方·海口海关")

# 门店级估算强提醒（MAX 重点要求）
st.warning(ESTIMATE_DISCLAIMER, icon="⚠️")
show_insight("hainan_overview", max_bullets=3)


# ============================================================
# 锚点调整（可选）：默认取官方 199.2 亿；改动按比例重算，仍为估算
# ============================================================
with st.expander("🔧 调整估算锚点（可选）", expanded=False):
    st.markdown(
        "门店级估算 = 锚点全省总量 × 零售商占比 × 门店权重。默认锚点取海口海关官方 "
        f"**{ytd['amount_2026']} 亿 / {ytd['pax_2026']} 万人次**。改动后按比例重算，"
        "**结果仍全部为估算值**，请勿当作实测。"
    )
    col_a, col_b = st.columns(2)
    h1_total = col_a.number_input(
        "H1 全省销售额（亿元）", value=float(ytd["amount_2026"]),
        step=1.0, key="h1_total",
    )
    h1_pax = col_b.number_input(
        "H1 全省客流（万人次）", value=float(ytd["pax_2026"]),
        step=1.0, key="h1_pax",
    )

stores = estimate_store_sales(h1_total=h1_total, h1_pax=h1_pax)
retailers_est = estimate_by_retailer(h1_total=h1_total)


# ============================================================
# 视图一：按零售商汇总（估算）
# ============================================================
st.subheader("🏢 各零售商 H1 销售估算（全部为估算）")
import pandas as pd

r_rows = []
for r in retailers_est:
    r_rows.append({
        "零售商": r["retailer"],
        "上市代码": r["ticker"] or "—",
        "合作": r["cooperation"],
        "估算占比": f"{r['share_est']:.0%}",
        "H1销售估算(亿)": r["sales_h1_est"],
        "门店数": r["stores"],
        "口径": ESTIMATE_BADGE,
    })
r_df = pd.DataFrame(r_rows)
st.dataframe(r_df, width='stretch', hide_index=True)
st.caption("说明：占比为代理假设（RETAILER_SHARE），非逐店实测；数值随上方锚点联动。")
show_insight("retailer_overview", max_bullets=3)


# ============================================================
# 视图二：门店级明细（估算 + 分摊方法可追溯）
# ============================================================
st.subheader("🏪 门店级销售 / 客流估算（全部为估算，附分摊方法）")

s_rows = []
for s in stores:
    s_rows.append({
        "零售商": s["retailer"],
        "门店": s["store"],
        "城市": s.get("city"),
        "业态": s.get("type"),
        "销售估算(亿)": s["sales_h1_est"],
        "客流估算(万)": s["pax_h1_est"],
        "口径": ESTIMATE_BADGE,
        "分摊方法": s["method"],
    })
s_df = pd.DataFrame(s_rows)
# 门店级数值加角标（用 markdown 渲染，口径列已标注）
st.dataframe(s_df, width='stretch', hide_index=True)
st.markdown(
    f"以上 {len(s_df)} 条门店级记录，每一条的「口径」列均为 {est_badge()}，"
    f"「分摊方法」列可追溯计算来源；**请勿当作各店实测值**。",
    unsafe_allow_html=True,
)
show_insight("store_overview", max_bullets=3)

# 下载 CSV（便于交接给同事，且字段已带 is_estimate / source）
csv_df = pd.DataFrame([{
    "retailer": x["retailer"], "store": x["store"], "city": x.get("city"),
    "type": x.get("type"), "sales_h1_est": x["sales_h1_est"],
    "pax_h1_est": x["pax_h1_est"], "is_estimate": x["is_estimate"],
    "source": x["source"], "method": x["method"],
} for x in stores])
st.download_button(
    "⬇️ 下载门店估算 CSV（含 is_estimate 标记）",
    csv_df.to_csv(index=False).encode("utf-8-sig"),
    file_name="hainan_store_estimate.csv", mime="text/csv",
)


# ============================================================
# 视图三：门店销售估算柱状图
# ============================================================
st.subheader("📈 门店 H1 销售估算对比（全部为估算）")
chart_df = pd.DataFrame(stores)
chart_df = chart_df.set_index("store")["sales_h1_est"].sort_values()
st.bar_chart(chart_df)
st.caption("柱越高代表按权重分摊出的体量越大；仅为估算分布，非实测排名。")
show_insight("store_overview", max_bullets=2)


# ============================================================
# 视图四：零售商 / 门店主数据（尽量详细，合作方全列出）
# ============================================================
with st.expander("📋 零售商 / 门店主数据（合作方全清单）", expanded=False):
    st.markdown(f"合作状态口径：**{COOPERATION_ALL}**（各零售商均与 MAX 团队合作）。")
    for r in RETAILERS:
        st.markdown(f"### {r['name']}")
        meta = (
            f"- 上市代码：{r.get('ticker') or '非上市'}\n"
            f"- 合作：{r.get('cooperation')}\n"
            f"- 数据来源：{r.get('data_source')}\n"
            f"- 备注：{r.get('note')}\n"
        )
        if r.get("hainan_q1_2026_rev") is not None:
            meta += f"- 公开 Q1 海南营收：{r['hainan_q1_2026_rev']} 亿\n"
        st.markdown(meta)
        for s in r.get("stores", []):
            st.markdown(
                f"  - **{s['name']}**（{s.get('city')} / {s.get('type')}）"
                f" 权重 {s.get('weight'):.0%} — {s.get('note')}"
            )
show_insight("retailer_overview", max_bullets=3)


# ============================================================
# 数据校准提示（重要，需 MAX / 合作方核对）
# ============================================================
st.info(
    "📌 **数据校准提示**：王府井 Q1 公开营收仅 1.39 亿，但按当前 RETAILER_SHARE 3% "
    "推算 H1 约 5.98 亿，与 Q1 量级不匹配，占比可能偏高约 1 倍。"
    "建议以合作方实际口径校准 RETAILER_SHARE 后再对外使用门店估算。其余未上市零售商"
    "无公开逐季数据，占比为代理假设，同样建议合作方复核。",
    icon="ℹ️",
)


# ============================================================
# 页脚：来源说明
# ============================================================
st.divider()
st.markdown("### 📚 数据来源与口径")
st.markdown(f"- **官方**：{'; '.join(SOURCE_NOTE.get('official', []))}")
st.markdown(f"- **估算**：{'; '.join(SOURCE_NOTE.get('estimated', []))}")
st.markdown(f"- **抓取**：{'; '.join(SOURCE_NOTE.get('scraped', []))}")
st.caption(
    f"看板生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} · "
    f"门店级数值全部为代理估算（is_estimate=True）"
)
