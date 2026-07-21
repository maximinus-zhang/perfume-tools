# -*- coding: utf-8 -*-
"""
全国免税商情监控 v9.0 - Streamlit 可视化仪表盘
✅ 海南离岛免税 2026 官方月度/YTD/政策  ✅ 12大机场双年对比
✅ 机场境外客流（国际航线/免签覆盖/入境游联动）  ✅ 百度新闻实时聚合
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import re
from datetime import datetime
from utils.hainan_scraper import HainanScraper, AIRPORT_DB
from utils.hainan_2026_data import HA_DF_2026, AIRPORT_INTL, SOURCE_NOTE
from utils.customs_parser import build_monthly_from_xlsx, try_cdp_fetch, XLSX_DIR, customs_folder_stats
from utils.news_analyzer import (
    fetch_news_cached, analyze_news_for_context, render_insight_markdown,
)

st.set_page_config(page_title="全国免税商情监控 2026", page_icon="🏝️", layout="wide")

# ============================================================
# 全局指标：用于新闻量化交叉验证 & 深度分析
# ============================================================
_yd = HA_DF_2026["ytd"]
HAINAN_METRICS = {
    "h1_amount": float(_yd["amount_2026"]),
    "h1_pax": float(_yd["pax_2026"]),
    "h1_pieces": float(_yd["pieces_2026"]),
    "h1_months": 6,
    "amt_yoy": float(_yd["amt_yoy"]),
    "pax_yoy": float(_yd["pax_yoy"]),
    "pc_yoy": float(_yd["pc_yoy"]),
}

# ============================================================
# 顶部
# ============================================================

st.title("🏝️ 全国免税商情监控 2026")
st.caption("📊 海南离岛免税：海口海关/新华社/央视/海南特区报 ｜ 12大机场：CAAC民航局公报 ｜ 入境游：海南自贸港封关发布会")

col1, col2 = st.columns([3, 1])
with col2:
    st.markdown("**🔄 数据刷新**")
    if st.button("重新解析本地月报", use_container_width=True, key="btn_parse"):
        by_ym, recs = build_monthly_from_xlsx()
        st.session_state["customs_by_ym"] = by_ym
        st.session_state["customs_recs"] = recs
        st.session_state["customs_msg"] = f"已重新解析本地 xlsx/：{len(recs)} 个月报"
        st.rerun()
    if st.button("⬇️ 在线抓取最新(需调试Chrome)", use_container_width=True, key="btn_fetch"):
        ok, msg = try_cdp_fetch()
        by_ym, recs = build_monthly_from_xlsx()
        st.session_state["customs_by_ym"] = by_ym
        st.session_state["customs_recs"] = recs
        st.session_state["customs_msg"] = ("✅ " if ok else "⚠️ ") + msg
        st.rerun()
    if st.button("📰 刷新新闻", use_container_width=True, key="btn_news"):
        st.cache_data.clear()
        st.rerun()

# ---- 海关月报解析结果（session 级，供『重新解析』刷新）----
if "customs_by_ym" not in st.session_state:
    _by, _recs = build_monthly_from_xlsx()
    st.session_state["customs_by_ym"] = _by
    st.session_state["customs_recs"] = _recs
    st.session_state["customs_msg"] = (
        f"已加载本地 xlsx/：{len(_recs)} 个月报（点右上『重新解析本地月报』可刷新）"
    )

data = fetch_news_cached()
today = data.get("date", datetime.now().strftime("%Y-%m-%d"))

total_news = sum(len(data.get(k, [])) for k in
                 ["airport_news", "duty_free_news", "li_island_news", "policy_news", "travel_news"])
st.success(f"📅 新闻更新于: {today}  |  共 {total_news} 条新闻")
_cn, _mt = customs_folder_stats()
_fresh = f" ｜ 📁 本地月报 {_cn} 个，最新更新 {_mt}" if _cn else " ｜ ⚠️ 未找到本地月报 xlsx/"
st.info(f"💰 海关月报：{st.session_state.get('customs_msg', '')}{_fresh}")

# ============================================================
# 安全取值函数
# ============================================================

def safe_info(code, key, default=None):
    info = AIRPORT_DB.get(code, {})
    return info.get(key, default)

def safe_news(data, key):
    items = data.get(key, [])
    result = []
    for item in items:
        if isinstance(item, (tuple, list)):
            if len(item) >= 2:
                result.append((item[0], item[1]))
            else:
                result.append((str(item[0]), ""))
        else:
            result.append((str(item), ""))
    return result


def all_news_items(data):
    """把所有类别的新闻合并成一个 (title, url) 列表，用于模块级自动分析。"""
    items = []
    for k in ["airport_news", "duty_free_news", "li_island_news", "policy_news", "travel_news"]:
        items.extend(safe_news(data, k))
    return items


def show_insight(context, max_bullets=3):
    """在模块下方渲染新闻自动分析备注（带官方 H1 量化交叉验证）"""
    try:
        bullets = analyze_news_for_context(
            all_news_items(data), context, max_bullets=max_bullets, metrics=HAINAN_METRICS
        )
        md = render_insight_markdown(bullets)
        st.markdown(md)
    except Exception as e:
        st.caption(f"🤖 新闻备注生成失败：{e}")

def fmt_growth(val_25, val_24):
    if val_24 and val_24 > 0:
        pct = (val_25 - val_24) / val_24 * 100
        return f"+{pct:.1f}%" if pct > 0 else f"{pct:.1f}%"
    return "N/A"

def badge(src):
    if src == "XLSX+推算":
        return "🟡 XLSX+推算"
    elif src in ("官方", "XLSX实时") or "XLSX" in str(src):
        return "🟢 官方/XLSX"
    elif src == "推算":
        return "🟡 推算"
    elif src == "累计进度":
        return "🟠 累计进度"
    return "⚪ 待补"

# ============================================================
# 海关月报解析 → 与硬编码数据合并 / 分析
# ============================================================

def merge_customs_monthly(hardcoded, by_ym):
    """用本地 XLSX 解析值覆盖硬编码月度序列（2026 M1-M5），并标来源。"""
    out = []
    for row in hardcoded:
        m = dict(row)
        label = m.get("m", "")
        mm = re.match(r"(\d+)月", label)
        if mm and "小计" not in label and "合计" not in label:
            rec = by_ym.get((2026, int(mm.group(1))))
            if rec:
                if rec["amt"] is not None:
                    m["amt26"] = rec["amt"]
                if rec["amt_yoy"] is not None:
                    m["yoy"] = round(rec["amt_yoy"], 1)
                if rec["pax"] is not None:
                    m["pax26"] = rec["pax"]
                if rec["pieces"] is not None:
                    m["pieces26"] = rec["pieces"]
                m["src"] = "XLSX实时"
        out.append(m)
    return out


def build_analysis_months(hardcoded, by_ym):
    """构造分析用月度行（含金额/人次/件数/同比，优先 XLSX 真实值）。"""
    rows = []
    for row in hardcoded:
        label = row.get("m", "")
        mm = re.match(r"(\d+)月", label)
        if not mm or "小计" in label or "合计" in label:
            continue
        mo = int(mm.group(1))
        rec = by_ym.get((2026, mo))
        amt26 = rec["amt"] if (rec and rec["amt"] is not None) else row.get("amt26")
        amt25 = row.get("amt25")
        pax26 = rec["pax"] if (rec and rec["pax"] is not None) else row.get("pax26")
        pax25 = row.get("pax25")
        pc26 = rec["pieces"] if (rec and rec["pieces"] is not None) else None
        yoy = rec["amt_yoy"] if (rec and rec["amt_yoy"] is not None) else row.get("yoy")
        src = "XLSX实时" if rec else row.get("src", "官方")
        rows.append({"m": label, "mo": mo, "amt26": amt26, "amt25": amt25,
                     "pax26": pax26, "pax25": pax25, "pieces26": pc26,
                     "yoy": yoy, "src": src})
    return rows


def merge_customs_quarterly(hardcoded_quarter, by_ym):
    """优先用 XLSX 月度数据重算 Q2；M6 缺失时，用 H1−ΣM1-M5 反推。"""
    h1 = HA_DF_2026["ytd"]
    out = []
    for row in hardcoded_quarter:
        r = dict(row)
        if not r.get("q", "").startswith("Q2"):
            out.append(r)
            continue
        m4 = by_ym.get((2026, 4))
        m5 = by_ym.get((2026, 5))
        m6 = by_ym.get((2026, 6))
        # 只有当 M4/M5 至少有一个来自 XLSX 时才用月度口径
        if not (m4 or m5):
            out.append(r)
            continue
        # 收集 M1-M5 的 XLSX 金额与人次
        m1_m5_amt = 0
        m1_m5_pax = 0
        for mo in range(1, 6):
            rec = by_ym.get((2026, mo))
            if rec and rec["amt"] is not None:
                m1_m5_amt += rec["amt"]
            if rec and rec["pax"] is not None:
                m1_m5_pax += rec["pax"]
        q2_amt = (m4["amt"] if m4 and m4["amt"] is not None else 0) + \
                 (m5["amt"] if m5 and m5["amt"] is not None else 0)
        q2_pax = (m4["pax"] if m4 and m4["pax"] is not None else 0) + \
                 (m5["pax"] if m5 and m5["pax"] is not None else 0)
        if m6 and m6["amt"] is not None:
            q2_amt += m6["amt"]
            q2_pax += m6["pax"] if m6["pax"] is not None else 0
            r["amt_src"] = "XLSX实时"
            r["pax_src"] = "XLSX实时"
            r["note"] = "Q2=M4+M5+M6 XLSX真实值"
        else:
            m6_amt = h1["amount_2026"] - m1_m5_amt
            m6_pax = h1["pax_2026"] - m1_m5_pax
            q2_amt += m6_amt
            q2_pax += m6_pax
            r["amt_src"] = "XLSX+推算"
            r["pax_src"] = "XLSX+推算"
            r["note"] = "M4/M5来自XLSX真实值，M6=H1−Σ1-5反推"
        # 重算同比
        if r["amt25"] and r["amt25"] > 0:
            r["yoy"] = round((q2_amt - r["amt25"]) / r["amt25"] * 100, 1)
        if r["pax25"] and r["pax25"] > 0:
            r["yoy_pax"] = round((q2_pax - r["pax25"]) / r["pax25"] * 100, 1)
        r["amt26"] = round(q2_amt, 4)
        r["pax26"] = round(q2_pax, 4) if q2_pax > 0 else None
        out.append(r)
    return out


def customs_folder_stats(folder=None):
    """返回 (xlsx文件数, 最新文件修改时间字符串)，用于页面显示数据时效。"""
    folder = os.path.abspath(folder or XLSX_DIR)
    if not os.path.isdir(folder):
        return 0, None
    xs = [f for f in os.listdir(folder)
          if f.lower().endswith(".xlsx") and not f.startswith("~")]
    if not xs:
        return 0, None
    latest = max(xs, key=lambda f: os.path.getmtime(os.path.join(folder, f)))
    mt = os.path.getmtime(os.path.join(folder, latest))
    return len(xs), datetime.fromtimestamp(mt).strftime("%Y-%m-%d %H:%M")

# ============================================================
# 模块一：海南离岛免税商情（2026 官方维度）
# ============================================================

st.markdown("---")
st.subheader("💰 海南离岛免税商情（2026 · 官方口径）")

yd = HA_DF_2026["ytd"]
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("免税购物金额", f"{yd['amount_2026']} 亿",
              delta=f"vs25年 {yd['amount_2025']}亿 · {yd['amt_yoy']:+.1f}%",
              help=f"来源：{yd['source']}")
with c2:
    st.metric("购物人数", f"{yd['pax_2026']} 万",
              delta=f"vs25年 {yd['pax_2025']}万 · {yd['pax_yoy']:+.1f}%")
with c3:
    st.metric("购物件数", f"{yd['pieces_2026']} 万",
              delta=f"vs25年 {yd['pieces_2025']}万 · {yd['pc_yoy']:+.1f}%")
st.caption(f"📌 YTD 口径：{yd['date_label']} ｜ 数据来源：{yd['source']}")
show_insight("hainan_overview", max_bullets=3)

# 季度 + 月度YTD
st.markdown("**📈 季度对比（金额 亿元 · 2026 vs 2025）**")
q_rows = merge_customs_quarterly(HA_DF_2026["quarter"], st.session_state["customs_by_ym"])
qd = pd.DataFrame(q_rows)
q_show = qd[["q", "amt26", "amt25", "yoy", "pax26", "pax25", "yoy_pax", "amt_src", "note"]].copy()
q_show.columns = ["季度", "2026金额", "2025金额", "金额同比%", "2026人数", "2025人数", "人数同比%",
                   "数据来源", "说明"]
st.dataframe(q_show, use_container_width=True, hide_index=True)
show_insight("quarterly", max_bullets=3)

st.markdown("**📅 月度 YTD 进度（亿元 / 万人次）**")
_merged = merge_customs_monthly(HA_DF_2026["monthly_ytd"], st.session_state["customs_by_ym"])
_mdf = pd.DataFrame(_merged)
# 26 vs 25 月度金额对比图（仅自然月）
_chart = _mdf[_mdf["m"].str.match(r"\d+月")][["m", "amt26", "amt25"]].set_index("m")
st.bar_chart(_chart, color=["#E63946", "#1E90FF"], height=320)
m_show = _mdf.copy()
if "src" in m_show:
    m_show["来源"] = m_show["src"].map(lambda s: badge(s))
m_show = m_show[["m", "amt26", "amt25", "pax26", "pax25", "来源"]]
m_show.columns = ["月份", "2026金额", "2025金额", "2026人数", "2025人数", "来源标注"]
st.dataframe(m_show, use_container_width=True, hide_index=True)
st.caption("💡 1–5月为海关《离岛免税销售情况表》XLSX 真实值（🟢XLSX实时）；6月=H1−Σ1-5 反推；H1/Q1为官方累计口径。点右上『重新解析本地月报』可刷新。")
show_insight("monthly", max_bullets=3)

# 节点专项
st.markdown("**🎪 重要消费节点（2026 · 官方）**")
ed = pd.DataFrame(HA_DF_2026["events_2026"])
ed_show = ed[["name", "period", "amt", "pax", "pieces", "yoy", "src"]].copy()
ed_show.columns = ["节点", "时间", "金额(亿)", "人次(万)", "件数(万)", "金额同比%", "来源"]
st.dataframe(ed_show, use_container_width=True, hide_index=True)

# 政策动销
with st.expander("📜 政策动销（2025-11-01 新政 + 封关）"):
    p = HA_DF_2026["policy"]
    st.markdown(f"- **生效**：{p['effective']}")
    st.markdown(f"- **额度**：{p['quota']}")
    st.markdown(f"- **品类**：{p['categories']}")
    st.markdown(f"- **提货方式**：{p['pickup']}")
    st.markdown(f"- **享惠面扩大**：")
    for e in p["enjoy"]:
        st.markdown(f"  - {e}")
    st.markdown(f"- **限购**：{p['limits']}")
    st.caption(f"来源：{p['source']}")
show_insight("policy", max_bullets=3)

# 省级入境游（境外游客客流）
st.markdown("**🌍 海南入境游（境外游客客流 · 省级口径）**")
ib = HA_DF_2026["inbound"]
i1, i2, i3, i4 = st.columns(4)
with i1:
    st.metric("进出境旅客", f"{ib['entry_exit_total']} 万", delta=f"{ib['entry_exit_yoy']:+.1f}%")
with i2:
    st.metric("免签入境", f"{ib['visa_free_entry']} 万", delta=f"{ib['visa_free_yoy']:+.1f}%")
with i3:
    st.metric("免签国家", f"{ib['visa_free_countries']} 国")
with i4:
    st.metric("境外航线", f"{ib['intl_routes']} 条 / {ib['route_countries']} 国地")
st.caption(f"📌 {ib['asof']} ｜ 来源：{ib['source']} ｜ {ib['note']}")
show_insight("travel", max_bullets=3)

# ============================================================
# 模块一·附：月度数据深度分析（海关 XLSX 真实值）
# ============================================================

st.markdown("---")
st.subheader("💡 月度数据深度分析（海关 XLSX 真实值）")

am = build_analysis_months(HA_DF_2026["monthly_ytd"], st.session_state["customs_by_ym"])
amdf = pd.DataFrame(am)

# (1) 26vs25 金额 + 同比走势
c1, c2 = st.columns(2)
with c1:
    st.markdown("**📊 月度免税金额：2026 vs 2025（亿元）**")
    ch = amdf[["m", "amt26", "amt25"]].set_index("m")
    st.bar_chart(ch, color=["#E63946", "#1E90FF"], height=320)
with c2:
    st.markdown("**📉 月度金额同比（%）— Q1冲高→Q2走平**")
    yoy_ch = amdf[["m", "yoy"]].set_index("m")
    st.line_chart(yoy_ch, height=320)

# (2) 客单价 / 件单价 / 人均件数
st.markdown("**🛒 客单价与件单价走势（香化渠道重点关注）**")
asp_rows = []
for _, r in amdf.iterrows():
    if r["pax26"] and r["pieces26"] and r["amt26"]:
        asp = r["amt26"] / r["pax26"] * 10000       # 元/人
        pp = r["amt26"] / r["pieces26"] * 10000     # 元/件
        ppi = r["pieces26"] / r["pax26"]            # 件/人
        asp_rows.append({"月份": r["m"], "客单价(元/人)": round(asp, 0),
                         "件单价(元/件)": round(pp, 0), "人均件数": round(ppi, 2),
                         "金额同比%": r["yoy"]})
aspdf = pd.DataFrame(asp_rows)
if not aspdf.empty:
    st.line_chart(aspdf.set_index("月份")[["客单价(元/人)", "件单价(元/件)"]], height=320)
    st.dataframe(aspdf, use_container_width=True, hide_index=True)
    st.caption("⚠️ 2月/6月缺人次数据，未计入。客单价=金额÷人次；件单价=金额÷件数。")
else:
    st.info("暂无可计算客单价的月份（需同时有人次与件数）")

# (3) 增长贡献 + 全年情景测算
st.markdown("**📈 增长贡献与全年情景测算**")
q1 = next(x for x in q_rows if x["q"].startswith("Q1"))
q2 = next(x for x in q_rows if x["q"].startswith("Q2"))
recs = st.session_state.get("customs_recs", [])
full_2025 = None
for rr in recs:
    if rr["year"] == 2025 and rr["month"] == 12 and rr["ytd_amt"]:
        full_2025 = rr["ytd_amt"]
h1_2025 = HA_DF_2026["ytd"]["amount_2025"]
h2_2025 = (full_2025 - h1_2025) if full_2025 else None
h1_2026 = HA_DF_2026["ytd"]["amount_2026"]

proj_rows = []
if h2_2025:
    for g, lbl in [(0.0, "保守 H2同比0%"), (0.05, "中性 H2同比+5%"), (0.10, "乐观 H2同比+10%")]:
        full = h1_2026 + h2_2025 * (1 + g)
        proj_rows.append({"情景": lbl, "H2 2026(亿)": round(h2_2025 * (1 + g), 1),
                          "全年 2026(亿)": round(full, 1),
                          "全年同比%": round((full / full_2025 - 1) * 100, 1) if full_2025 else None})
projdf = pd.DataFrame(proj_rows)
st.markdown(f"- **季度拆解**：Q1 金额 +{q1['yoy']}% → Q2 骤降至 +{q2['yoy']}%（{q2['note']}）；"
             f"5月金额同比仅 +0.4% 且件数 −4.9%，增长明显走平。")
if full_2025:
    st.markdown(f"- **2025 全年基数**：{full_2025:.1f} 亿（取自 2025M12 海关累计）；H1 {h1_2025} + H2 {h2_2025:.1f}。")
    st.dataframe(projdf, use_container_width=True, hide_index=True)
    st.caption("📌 情景测算基于『H2 2026 相对 H2 2025 给定增速』，仅作计划参考；实际受新政红利衰减、暑期/国庆旺季及补库节奏影响。")
else:
    st.warning("未解析到 2025M12 累计，无法测算全年情景（请确认 xlsx/ 含 2025M12.xlsx）")

# (4) 香化渠道提示
st.markdown("**🧴 对香化补货 / 计划的提示**")
st.info(
    "① Q2 客单价与件单价双降（Q2 客单价约 5,800–6,000 元/人，较 Q1 的 1月 8,090 / 2月 8,423 元明显回落），"
    "说明 Q2 增长主要靠流量而非客单，且流量亦在放缓。\n"
    "② 下半年同比基数已被新政抬高，H2 大概率仅低个位数增长甚至转负；"
    "补货计划勿按 Q1 斜率外推，建议按『中性情景』(全年约 +12.6%) 做滚动预测并防库存堆积。\n"
    "③ 6月(反推)~15亿为上半年低点，7–8月暑运通常回升，可结合实时月报动态调整。"
)
show_insight("monthly", max_bullets=3)

# ============================================================
# 模块一·附二：数据诊断与行动建议（DataAnalyticsReporter 增强）
# ============================================================

st.markdown("---")
st.subheader("🎯 数据诊断与行动建议")

# ---------- 1) H1 增长量价拆解 ----------
amt26, amt25 = _yd["amount_2026"], _yd["amount_2025"]
pax26, pax25 = _yd["pax_2026"], _yd["pax_2025"]
pc26, pc25 = _yd["pieces_2026"], _yd["pieces_2025"]

asp26 = amt26 * 10000 / pax26 if pax26 else None
asp25 = amt25 * 10000 / pax25 if pax25 else None
asp_yoy = (asp26 / asp25 - 1) * 100 if asp25 else None

ppc26 = pc26 / pax26 if pax26 else None
ppc25 = pc25 / pax25 if pax25 else None
ppc_yoy = (ppc26 / ppc25 - 1) * 100 if ppc25 else None

app26 = amt26 * 10000 / pc26 if pc26 else None
app25 = amt25 * 10000 / pc25 if pc25 else None
app_yoy = (app26 / app25 - 1) * 100 if app25 else None

st.markdown("**📊 H1 增长量价拆解**")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("H1 销售额同比", f"+{_yd['amt_yoy']:.1f}%")
with c2:
    st.metric("客流贡献", f"+{_yd['pax_yoy']:.1f}pp",
              help="客流增长对销售额增长的直接拉动（忽略结构变化）")
with c3:
    st.metric("客单价贡献", f"+{asp_yoy:.1f}pp",
              help=f"客单价 {asp25:.0f}元 → {asp26:.0f}元，与客流相乘近似解释总增长")
with c4:
    st.metric("人均件数变化", f"{ppc_yoy:+.1f}%",
              help=f"人均购买件数 {ppc25:.2f}件 → {ppc26:.2f}件；件单价 {app25:.0f}元 → {app26:.0f}元(+{app_yoy:.1f}%)")

st.markdown(
    f"- **核心结论**：H1 +{_yd['amt_yoy']:.1f}% 主要由客流 (+{_yd['pax_yoy']:.1f}%) 与客单价 (+{asp_yoy:.1f}%) 双轮驱动；"
    f"但人均件数下降 {abs(ppc_yoy):.1f}%，意味着增长并非来自‘买更多件’，而是来自**件单价提升 {app_yoy:.1f}%**（品类上移或折扣收窄）。"
)

# ---------- 2) 月度趋势诊断 ----------
st.markdown("**📉 月度趋势诊断**")
# 计算逐月同比、环比
_diag_rows = []
for i, r in amdf.iterrows():
    if r["amt26"] is None:
        continue
    yoy_amt = r["yoy"] if pd.notna(r["yoy"]) else None
    mom_amt = None
    if i > 0:
        prev = amdf.iloc[i - 1]
        if prev["amt26"] and prev["amt26"] > 0:
            mom_amt = (r["amt26"] - prev["amt26"]) / prev["amt26"] * 100
    _diag_rows.append({
        "月份": r["m"], "金额26": r["amt26"], "同比%": yoy_amt, "环比%": mom_amt,
        "来源": r["src"],
    })
diag_df = pd.DataFrame(_diag_rows)

# 异常判定：金额同比 < 5% 或 环比连续两月负
low_yoy = diag_df[(diag_df["同比%"].notna()) & (diag_df["同比%"] < 5.0)]
neg_mom_streak = 0
for v in diag_df["环比%"].dropna():
    neg_mom_streak = neg_mom_streak + 1 if v < 0 else 0

with st.expander("查看月度诊断明细", expanded=False):
    st.dataframe(
        diag_df.style
            .background_gradient(subset=["同比%"], cmap="RdYlGn", vmin=-10, vmax=50)
            .background_gradient(subset=["环比%"], cmap="RdYlGn", vmin=-40, vmax=40),
        hide_index=True, use_container_width=True,
    )

if not low_yoy.empty:
    st.warning(
        f"⚠️ **增速放缓信号**：{', '.join(low_yoy['月份'].tolist())} 金额同比增速低于 5%，"
        f"其中 {low_yoy.iloc[-1]['月份']} 同比仅 {low_yoy.iloc[-1]['同比%']:+.1f}%。"
        "Q2 增长动能明显弱于 Q1。"
    )

# ---------- 3) Q2 放缓归因 ----------
st.markdown("**🔍 Q2 放缓归因**")
q1_amt, q2_amt = q1["amt26"], q2["amt26"]
q1_yoy, q2_yoy = q1["yoy"], q2["yoy"]
q1_share = q1_amt / (q1_amt + q2_amt) * 100 if (q1_amt + q2_amt) else None
q2_share = 100 - q1_share if q1_share else None

st.markdown(
    f"- **季度结构**：Q1 占 H1 金额 {q1_share:.1f}%（{q1_amt:.1f}亿，同比 +{q1_yoy:.1f}%），"
    f"Q2 占 {q2_share:.1f}%（{q2_amt:.1f}亿，同比 +{q2_yoy:.1f}%）。"
    f"Q1 的增量贡献约为 {(q1_amt - q1['amt25']):.1f}亿，Q2 增量仅约 {(q2_amt - q2['amt25']):.1f}亿。"
)
st.markdown(
    f"- **归因判断**：Q2 放缓主要受**高基数 + 淡季效应 + 新政红利衰减**三重影响；"
    f"5 月金额同比 +0.4% 但件数同比 −4.9%，件单价同比约 +5.6%，说明价格/结构因素部分对冲了量缩。"
)

# ---------- 4) 行动建议卡片 ----------
st.markdown("**🎯 对香化采购 / 补货的建议**")
rec_cols = st.columns(3)
with rec_cols[0]:
    st.info(
        "**库存节奏**：Q2 已现量缩价升，H2 同比基数更高，建议按『中性情景』全年约 +12.6% 做滚动预测，"
        "避免按 Q1 斜率线性外推导致库存积压。",
        icon="📦",
    )
with rec_cols[1]:
    st.info(
        "**品类侧重**：人均件数下降、件单价上升，提示消费者更偏好高单价/高客单产品；"
        "香化备货可适当向高价值 SKU 倾斜，减少低毛利走量款占比。",
        icon="💄",
    )
with rec_cols[2]:
    st.info(
        "**观测窗口**：6 月为上半年低点，7–8 月暑运为关键验证期；"
        "若 7 月金额同比仍低于 10%，需进一步下调 H2 预期并收紧补货。",
        icon="📅",
    )

st.caption(
    "📌 以上诊断基于海口海关 H1 官方数据与 XLSX 月度真实值；"
    "件数/件单价因 2 月、6 月缺人次数据可能存在估算偏差。"
)

# ============================================================
# 模块二：12大机场核心指标（2025 vs 2024）
# ============================================================

st.markdown("---")
st.subheader("🛫 全国12大机场核心指标 (2025年 CAAC数据)  —  2025 VS 2024 对比")

airport_keys = list(AIRPORT_DB.keys())

cols = st.columns(4)
for i, code in enumerate(airport_keys[:6]):
    a25 = safe_info(code, "annual_2025", 0)
    a24 = safe_info(code, "annual_2024", 0)
    rank = safe_info(code, "rank", "?")
    growth = safe_info(code, "growth_pct", 0)
    dom = safe_info(code, "domestic_pct", "?")
    intl = safe_info(code, "international_pct", "?")
    with cols[i % 4]:
        st.metric(
            label=f"{code}",
            value=f"{a25} 万",
            delta=f"+{growth}% #{rank}",
            help=f"2025: {a25}万 | 2024: {a24}万 | 增量: +{a25-a24}万 | 国内{dom}% 国际{intl}%"
        )

# 第二行：剩余机场（第7-12个）
remaining = airport_keys[6:]
if remaining:
    cols2 = st.columns(len(remaining))
    for i, code in enumerate(remaining):
        a25 = safe_info(code, "annual_2025", 0)
        a24 = safe_info(code, "annual_2024", 0)
        rank = safe_info(code, "rank", "?")
        growth = safe_info(code, "growth_pct", 0)
        dom = safe_info(code, "domestic_pct", "?")
        intl = safe_info(code, "international_pct", "?")
        with cols2[i]:
            st.metric(
                label=f"{code}",
                value=f"{a25} 万",
                delta=f"+{growth}% #{rank}",
                help=f"2025: {a25}万 | 2024: {a24}万 | 增量: +{a25-a24}万 | 国内{dom}% 国际{intl}%"
            )
show_insight("airport_overview", max_bullets=3)

# ============================================================
# 模块三：机场吞吐量对比图（2025 vs 2024）
# ============================================================

st.markdown("---")
st.subheader("📈 机场年吞吐量对比: 2025(蓝) VS 2024(橙)  —  增量百分比")

chart_data = pd.DataFrame({
    "机场": airport_keys,
    "2025": [safe_info(k, "annual_2025", 0) for k in airport_keys],
    "2024": [safe_info(k, "annual_2024", 0) for k in airport_keys],
    "增量": [safe_info(k, "annual_2025", 0) - safe_info(k, "annual_2024", 0) for k in airport_keys],
    "增长率(%)": [safe_info(k, "growth_pct", 0) for k in airport_keys],
})

# 图表独占一行，保证柱状图宽度充足
st.bar_chart(chart_data, x="机场", y=["2025", "2024"],
             color=["#1E90FF", "#FF8C00"], height=400)

st.caption("**数据明细表**（单位：万人次）")

growth_df = chart_data[["机场", "2025", "2024", "增量", "增长率(%)"]].copy()
growth_df["增长率"] = growth_df["增长率(%)"].apply(lambda x: f"+{x}%" if x > 0 else f"{x}%")
st.dataframe(
    growth_df.style
        .highlight_max(subset=["增长率(%)"], color="#90EE90")
        .highlight_min(subset=["增长率(%)"], color="#FFB3B3"),
    use_container_width=True, hide_index=True,
    column_config={
        "2025": st.column_config.NumberColumn("2025年", format="%.0f", width="small"),
        "2024": st.column_config.NumberColumn("2024年", format="%.0f", width="small"),
        "增量": st.column_config.NumberColumn("增量(万)", format="+%.0f", width="small"),
        "增长率(%)": st.column_config.NumberColumn("增长率", format="%.1f%%", width="small"),
        "增长率": st.column_config.NumberColumn("增长", width="small"),
    }
)

# ============================================================
# 模块四：增长率排名
# ============================================================

st.markdown("---")
st.subheader("📊 增长率排名")

growth_ranked = chart_data.sort_values("增长率(%)", ascending=False).reset_index(drop=True)

col1, col2 = st.columns([2, 3])
with col1:
    st.dataframe(
        growth_ranked[["机场", "增长率(%)"]].style
            .bar(subset=["增长率(%)"], color="#1E90FF"),
        use_container_width=True, hide_index=True
    )
with col2:
    st.bar_chart(growth_ranked, x="机场", y="增长率(%)",
                 color="#1E90FF", height=350)

# ============================================================
# 模块五：月度客流分布（2025 vs 2024）
# ============================================================

st.markdown("---")
st.subheader("📅 月度旅客流量对比: 2025(蓝) VS 2024(橙)")
st.caption("✅ 年总量为 CAAC 官方数据  |  ⚠️ 月度分布为模拟值(基于历史季节规律)，非官方月度数据")

months = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]

selected_airport = st.selectbox("选择机场查看月度对比", airport_keys, index=0)

info = AIRPORT_DB.get(selected_airport, {})
annual_2025 = info.get("annual_2025", 0)
annual_2024 = info.get("annual_2024", 0)
monthly_pct = info.get("monthly_pct", None)
dom_pct = info.get("domestic_pct", 50)
intl_pct = info.get("international_pct", 50)
growth_pct = info.get("growth_pct", 0)
monthly_source = info.get("monthly_source", "模拟值")

if monthly_pct and len(monthly_pct) == 12:
    total_pct = sum(monthly_pct)
    if total_pct > 0:
        m2025 = [round(annual_2025 * p / total_pct, 1) for p in monthly_pct]
        m2024 = [round(annual_2024 * p / total_pct, 1) for p in monthly_pct]
    else:
        m2025 = [round(annual_2025 / 12, 1)] * 12
        m2024 = [round(annual_2024 / 12, 1)] * 12
else:
    m2025 = [round(annual_2025 / 12, 1)] * 12
    m2024 = [round(annual_2024 / 12, 1)] * 12

monthly_df = pd.DataFrame({
    "月份": months,
    "2025(万人次)": m2025,
    "2024(万人次)": m2024,
})

col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    chart_data_month = monthly_df.set_index("月份")
    st.line_chart(chart_data_month, color=["#1E90FF", "#FF8C00"], height=400)

with col2:
    st.metric(f"🛫 {selected_airport} (2025)", f"{annual_2025} 万/年")
    st.metric(f"🛫 {selected_airport} (2024)", f"{annual_2024} 万/年")
    st.metric("📈 同比增长", f"+{growth_pct}%")

with col3:
    st.metric("国内占比", f"{dom_pct}%")
    st.metric("国际占比", f"{intl_pct}%")
    st.metric("月度数据", monthly_source)
    if m2025:
        peak = max(m2025)
        peak_month = months[m2025.index(peak)]
        low = min(m2025)
        low_month = months[m2025.index(low)]
        st.metric(f"📈 旺季 ({peak_month})", f"{peak:.0f} 万")
        st.metric(f"📉 淡季 ({low_month})", f"{low:.0f} 万")

with st.expander("📊 查看月度明细对比数据"):
    monthly_detail = monthly_df.copy()
    monthly_detail["同比增减(万)"] = [m2025[i] - m2024[i] for i in range(12)]
    monthly_detail["同比(%)"] = [
        f"+{((m2025[i]-m2024[i])/m2024[i]*100):.1f}%" if m2024[i] > 0 else "N/A"
        for i in range(12)
    ]
    st.dataframe(monthly_detail, use_container_width=True, hide_index=True)
show_insight("airport_monthly", max_bullets=3)

# ============================================================
# 模块六：航站楼 & 航线总览（含机场境外客流 Tab）
# ============================================================

st.markdown("---")
st.subheader("🏗️ 航站楼 & 航线总览（12大机场 · 含境外客流）")

for code in airport_keys:
    info = AIRPORT_DB.get(code, {})
    annual_25 = info.get("annual_2025", 0)
    annual_24 = info.get("annual_2024", 0)
    rank = info.get("rank", "?")
    growth = info.get("growth_pct", 0)
    terminals = info.get("terminals", {})
    airlines = info.get("major_airlines", [])
    duty_free = info.get("duty_free", {"operator": "暂无", "stores": "暂无", "note": "暂无"})
    code_en = info.get("code_en", code)
    cargo_25 = info.get("cargo_2025", 0)
    mov_25 = info.get("movements_2025", 0)
    intl_pct = info.get("international_pct", 0)
    dom_pct = info.get("domestic_pct", 0)
    intl_info = AIRPORT_INTL.get(code, {})

    airport_news = safe_news(data, "airport_news")
    airport_filtered = [(t, u) for t, u in airport_news if code[:2] in t or code_en in t]

    with st.expander(f"🛫 **{code} ({code_en})** — {annual_25}万/年 (全国第{rank})  |  +{growth}%  |  国际占比 {intl_pct}%"):
        tabs = st.tabs(["🏗️ 航站楼", "✈️ 航司(境内+境外)", "🛍️ 免税业务",
                        "🌍 境外客流", "📊 双年对比", "📰 最新动态"])

        with tabs[0]:
            if terminals:
                for t_code, t_desc in terminals.items():
                    st.markdown(f"- **{t_code}**: {t_desc}")
            else:
                st.info("暂无航站楼信息")

        with tabs[1]:
            # --- 境内航司（国内基地航司）---
            if airlines:
                st.markdown("**🇨🇳 境内主力航司**")
                for airline in airlines:
                    st.markdown(f"- ✈️ {airline}")
            else:
                st.info("暂无境内主力航司信息")

            # --- 境外航司（国际/地区航司，免税业务核心客源）---
            intl_airlines = intl_info.get("intl_airlines", [])
            if intl_airlines:
                st.markdown("---")
                st.markdown(f"**🌏 境外/地区航司（{len(intl_airlines)}家）** — *免税核心客源承运方*")
                # 分 2 列展示，避免列表过长
                col_a, col_b = st.columns(2)
                half = (len(intl_airlines) + 1) // 2
                with col_a:
                    for al in intl_airlines[:half]:
                        st.markdown(f"- 🌐 {al}")
                with col_b:
                    for al in intl_airlines[half:]:
                        st.markdown(f"- 🌐 {al}")
            else:
                st.info("暂无境外航司信息")

        with tabs[2]:
            st.markdown(f"- **运营商**: {duty_free.get('operator', '暂无')}")
            st.markdown(f"- **门店**: {duty_free.get('stores', '暂无')}")
            st.markdown(f"- **备注**: {duty_free.get('note', '暂无')}")

        with tabs[3]:
            st.markdown(f"**🌐 国际旅客占比（CAAC官方）**：{intl_pct}%（国内 {dom_pct}%）")
            if intl_info:
                st.markdown(f"_{intl_info.get('intl_pct_note','')}_")
                st.markdown("**✈️ 主要国际/地区航线城市**（公开整理）：")
                for r in intl_info.get("key_intl_routes", []):
                    st.markdown(f"- {r}")
                st.markdown(f"**🛂 免签覆盖**：{intl_info.get('visa_free_cover','')}")
                if intl_info.get("note"):
                    st.caption(intl_info["note"])
            else:
                st.info("暂无境外客流明细")
            if code in ("海口美兰", "三亚凤凰"):
                st.success("🏝️ 该机场为海南离岛免税直接口岸，境外客流经86国免签落地入岛购物（见上方『海南入境游』面板）")

        with tabs[4]:
            st.metric("2025年旅客量", f"{annual_25} 万")
            st.metric("2024年旅客量", f"{annual_24} 万")
            st.metric("同比增长", f"+{growth}%")
            st.metric("货邮吞吐量(2025)", f"{cargo_25} 万吨")
            st.metric("起降架次(2025)", f"{mov_25} 万架次")

        with tabs[5]:
            shown = airport_filtered[:5] if airport_filtered else airport_news[:5]
            if shown:
                for i, (title, url) in enumerate(shown):
                    if url:
                        st.markdown(f"{i+1}. [{title}]({url})")
                    else:
                        st.markdown(f"{i+1}. {title}")
            else:
                st.info("暂无最新动态")

# ============================================================
# 模块七：全国机场对比表
# ============================================================

st.markdown("---")
st.subheader("📋 全国12大机场核心指标对比 — 2025 VS 2024 (CAAC官方数据)")

compare_data = []
for code in airport_keys:
    a25 = safe_info(code, "annual_2025", 0)
    a24 = safe_info(code, "annual_2024", 0)
    dom_pct = safe_info(code, "domestic_pct", 0)
    intl_pct = safe_info(code, "international_pct", 0)
    growth = safe_info(code, "growth_pct", 0)
    rank = safe_info(code, "rank", "?")
    code_en = safe_info(code, "code_en", "")
    cargo_25 = safe_info(code, "cargo_2025", 0)
    mov_25 = safe_info(code, "movements_2025", 0)
    terminals = safe_info(code, "terminals", {})
    airlines = safe_info(code, "major_airlines", [])

    dom = round(a25 * dom_pct / 100, 0)
    intl = round(a25 * intl_pct / 100, 0)
    compare_data.append({
        "机场": code,
        "代码": code_en,
        "2025(万)": a25,
        "2024(万)": a24,
        "增量(万)": a25 - a24,
        "增长(%)": growth,
        "全国排名": rank,
        "货邮(万吨)": cargo_25,
        "起降(万架次)": mov_25,
        "国内(万)": f"{dom:.0f}({dom_pct}%)",
        "国际(万)": f"{intl:.0f}({intl_pct}%)",
        "航站楼数": len(terminals),
        "主力航司数": len(airlines),
    })

compare_df = pd.DataFrame(compare_data)
st.dataframe(
    compare_df.style
        .highlight_max(subset=["2025(万)", "增长(%)"], color="#90EE90")
        .highlight_min(subset=["增长(%)"], color="#FFB3B3"),
    use_container_width=True, hide_index=True,
    column_config={
        "2025(万)": st.column_config.NumberColumn(format="%.0f"),
        "2024(万)": st.column_config.NumberColumn(format="%.0f"),
        "增量(万)": st.column_config.NumberColumn(format="+%.0f"),
        "增长(%)": st.column_config.NumberColumn(format="+.1f%%"),
    }
)

# ============================================================
# 模块八：最新动态
# ============================================================

st.markdown("---")
st.subheader("📰 最新动态 (点击标题打开原文)")

news_tabs = st.tabs(["✈️ 机场动态", "🛍️ 机场免税", "💰 离岛免税", "📜 政策动态", "🏖️ 旅游客流"])

news_categories = [
    ("airport_news", "✈️ 机场动态"),
    ("duty_free_news", "🛍️ 机场免税"),
    ("li_island_news", "💰 离岛免税"),
    ("policy_news", "📜 政策动态"),
    ("travel_news", "🏖️ 旅游客流"),
]

for key, label in news_categories:
    tab_idx = news_categories.index((key, label))
    with news_tabs[tab_idx]:
        items = safe_news(data, key)
        if items:
            for i, (title, url) in enumerate(items):
                if url:
                    st.markdown(f"{i+1}. [{title}]({url})")
                else:
                    st.markdown(f"{i+1}. {title}")
        else:
            st.info(f"暂无{label}相关新闻")

# ============================================================
# 模块九：关键数据摘要
# ============================================================

st.markdown("---")
st.subheader("📊 关键数据摘要")

summary = data.get("summary", [])
if summary:
    seen_summary = set()
    summary_rows = []
    for item in summary:
        if isinstance(item, (tuple, list)):
            if len(item) >= 3:
                icon, val, ctx = item[0], item[1], item[2]
            elif len(item) == 2:
                icon, val = item[0], item[1]
                ctx = ""
            else:
                icon, val, ctx = str(item), "", ""
        else:
            icon, val, ctx = str(item), "", ""
        key = f"{icon}|{val}|{ctx[:30]}"
        if key not in seen_summary and ctx.strip():
            seen_summary.add(key)
            summary_rows.append({"类别": icon, "数据": val, "说明": ctx})
    if summary_rows:
        summary_df = pd.DataFrame(summary_rows)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无摘要数据")
else:
    st.info("暂无摘要数据")

# ============================================================
# 页脚：数据来源说明
# ============================================================

st.markdown("---")
st.markdown("### 📌 数据来源说明")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**🟢 官方数据**")
    for s in SOURCE_NOTE["official"]:
        st.markdown(f"- {s}")
with col2:
    st.markdown("**🟡 估算 / 公开整理**")
    for s in SOURCE_NOTE["estimated"]:
        st.markdown(f"- {s}")
with col3:
    st.markdown("**📰 实时抓取**")
    for s in SOURCE_NOTE["scraped"]:
        st.markdown(f"- {s}")
    st.markdown("—")
    st.markdown("⚠️ **机场境外游客客流定位**：CAAC公报仅公布机场『国际占比%』，分机场/分国别境外旅客明细为边检涉密级数据、公开源未披露；本页『境外客流』Tab 提供**国际航线城市 + 免签国覆盖（公开整理）**，并结合**海南省级入境游口径**（86国免签/138.5万进出境）做联动分析。")

st.caption(f"本报告由海南免税商情监控 v9.0 自动生成 | {today}")
