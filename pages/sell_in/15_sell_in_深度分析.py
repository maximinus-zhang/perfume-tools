# -*- coding: utf-8 -*-
"""
SELL IN 深度分析 v1.0（SELL IN 采购端，加密）
============================================
用途: 在「SELL IN」模块下，对 NET SELL-IN (USD，reported to principal) 做品牌 / 主体维度的深度分析。
数据来源: 桌面知识库
  《2025 TR YTD Oct Sell in & Purchase. BE. 2026 Projection.xlsx》
  → 工作表 `sell in`（表头在第 3 行，品牌数据第 4 行起）
口径说明:
  - 本表为「净 SELL-IN（USD）」—— TR 对品牌方(principal)的出货口径，属 SELL IN（非 SELL OUT 零售）。
  - FY2022/23/24 = 实际年；2025 Budget = 2025 预算；2025 Best Estimate = 2025 最新预估(BE)；
    2026 Projection = 2026 预测；各类 vs% 为同比增长率（小数形式，如 0.24 = +24%）。
  - YTD 截止月份源表标注为 Aug（尽管文件名写 Oct），以源表为准。
  - 金额单位统一为 USD，跨品牌汇总有效。
加密: 与 NEWNESS / 品牌表现分析 页共用同一密码(Max12345)与 utils.newness_crypto 校验逻辑。
"""
import streamlit as st
import pandas as pd
import numpy as np
import warnings
import base64
from utils.newness_crypto import decrypt_data   # 与 NEWNESS 页共用同一加密/密码(Max12345)

warnings.filterwarnings("ignore")

# 桌面知识库里的 SELL IN / 采购 总表（本地路径，符合「本地优先、不上云」偏好）
KB_FILE = r"C:\Users\Maximinuszhang\Desktop\WorkBuddy\知识库\2025 TR YTD Oct Sell in & Purchase. BE. 2026 Projection.xlsx"
SELLIN_SHEET = "sell in"

# ===================== 密码门（同 NEWNESS / 品牌页） =====================
EMBEDDED_TOKEN = (
    "TkVXMT+unCbW9CIFN9b0bBNK7Fyv6bwJpA/K4WP5kQH1JvrIGS3NyFMr6jHWmIOmXwntik3cLQYIJRJH"
)
SESSION_AUTH = "sellin_authed"
SESSION_ERR = "sellin_err"


def _try_unlock():
    """用输入的密码解密内嵌校验串；失败给出友好提示。"""
    pw = st.session_state.get("sellin_pw", "")
    if not pw:
        st.session_state[SESSION_ERR] = "请输入访问密码"
        return
    try:
        decrypt_data(base64.b64decode(EMBEDDED_TOKEN), pw)   # 密码错 -> PermissionError
        st.session_state[SESSION_AUTH] = True
        st.session_state[SESSION_ERR] = ""
    except PermissionError:
        st.session_state[SESSION_AUTH] = False
        st.session_state[SESSION_ERR] = "🔒 密码错误，请重试"
    except Exception as e:
        st.session_state[SESSION_AUTH] = False
        st.session_state[SESSION_ERR] = f"解密失败：{e}"


if not st.session_state.get(SESSION_AUTH, False):
    st.markdown(
        "<div style='max-width:480px;margin:40px auto;text-align:center;"
        "padding:32px;border-radius:18px;background:rgba(120,120,160,0.08);"
        "border:1px solid rgba(120,120,160,0.25);'>"
        "<div style='font-size:48px'>🔐</div>"
        "<h3 style='margin:12px 0 4px'>该页面已加密</h3>"
        "<p style='opacity:.7;margin:0'>本页为 SELL IN 深度分析（NET SELL-IN USD），"
        "请输入访问密码后查看。</p></div>",
        unsafe_allow_html=True,
    )
    st.text_input("访问密码", type="password", key="sellin_pw",
                  placeholder="请输入密码", help="与 NEWNESS 页相同密码")
    if st.button("🔓 解锁查看", type="primary", key="sellin_unlock"):
        _try_unlock()
    if st.session_state.get(SESSION_ERR):
        st.error(st.session_state[SESSION_ERR])
    if not st.session_state.get(SESSION_AUTH, False):
        st.stop()

# 已解锁：提供重新上锁按钮
if st.sidebar.button("🔒 重新上锁", key="sellin_relock"):
    st.session_state[SESSION_AUTH] = False
    st.session_state[SESSION_ERR] = ""
    st.rerun()


# ===================== 数据加载 =====================
@st.cache_data
def load_sellin():
    """读取 `sell in` 表，返回品牌级 SELL IN 指标 DataFrame。
    表头在第 3 行(0-based=2)，品牌数据第 4 行(0-based=3)起。
    """
    raw = pd.read_excel(KB_FILE, sheet_name=SELLIN_SHEET, engine="calamine", header=None)
    HDR = 2
    SKIP = {"TTL", "TOTAL", "NAN", "", "合计", "GRAND TOTAL"}
    rows = []
    for r in range(HDR + 1, len(raw)):
        brand = raw.iloc[r, 4]
        if pd.isna(brand):
            continue
        b = str(brand).strip()
        if b.upper() in SKIP or "合计" in b or "TOTAL" in b.upper():
            continue
        prin = raw.iloc[r, 2]
        rows.append({
            "Principal": (str(prin).strip() if not pd.isna(prin) else ""),
            "Brand": b,
            "FY2022": raw.iloc[r, 5],
            "FY2023": raw.iloc[r, 6],
            "FY2024": raw.iloc[r, 7],
            "Budget2025": raw.iloc[r, 8],
            "G25v24": raw.iloc[r, 11],
            "YTD2024": raw.iloc[r, 12],
            "YTD2025": raw.iloc[r, 13],
            "YTDg": raw.iloc[r, 14],
            "BE2025": raw.iloc[r, 15],
            "BE_vs24FY": raw.iloc[r, 16],
            "BE_vs_budget": raw.iloc[r, 17],
            "Achieve": raw.iloc[r, 18],
            "Proj2026": raw.iloc[r, 20],
            "G26v25BE": raw.iloc[r, 21],
        })
    df = pd.DataFrame(rows)
    num = ["FY2022", "FY2023", "FY2024", "Budget2025", "G25v24", "YTD2024", "YTD2025",
           "YTDg", "BE2025", "BE_vs24FY", "BE_vs_budget", "Achieve", "Proj2026", "G26v25BE"]
    for c in num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # 去掉三个核心金额列全空的品牌行（多为合计/空行）
    df = df.dropna(subset=["FY2024", "BE2025", "Proj2026"], how="all").reset_index(drop=True)
    return df


# ===================== 页面主体 =====================
st.title("🔒 SELL IN 深度分析 v1.0")
st.caption("SELL IN · NET SELL-IN (USD) · 数据来源：2025 TR YTD…Sell in & Purchase…xlsx（sell in 表）"
           " ｜ 本地知识库，不上云 ｜ 🔒 密码保护与 NEWNESS / 品牌表现分析 页一致")

df = load_sellin()

if df.empty:
    st.error("未能从 `sell in` 工作表解析出品牌数据，请检查源文件。")
    st.stop()

tab1, tab2, tab3 = st.tabs([
    "📊 品牌总览与排名", "🌟 BCG 矩阵与趋势", "🏢 按主体(Principal)汇总"
])

# ---------- Tab1: 品牌总览与排名 ----------
with tab1:
    st.subheader("① 品牌 SELL IN 总览（按 2026 预测降序）")
    st.markdown("指标说明：**FY2024**=2024 实际年；**BE2025**=2025 最新预估；"
                "**YTD2025**=YTD Aug 2025；**YTDg**=YTD25 vs 24 增长；"
                "**Achieve**=YTD 达成率(YTD/BE)；**Proj2026**=2026 预测；"
                "**G26v25BE**=26 vs 25 BE 增长。金额单位 USD。")

    df_s = df.sort_values("Proj2026", ascending=False).reset_index(drop=True)
    df_s["排名"] = df_s.index + 1
    total_26 = df_s["Proj2026"].sum()
    df_s["占26预测%"] = (df_s["Proj2026"] / total_26 * 100).round(1) if total_26 else 0

    view_n = st.number_input("展示品牌数量（Top N）", min_value=5, max_value=len(df_s),
                             value=min(20, len(df_s)), step=1)
    show = df_s.head(view_n)

    st.dataframe(
        show[["排名", "Brand", "Principal", "FY2024", "BE2025", "Proj2026",
              "占26预测%", "G25v24", "G26v25BE", "Achieve", "YTDg"]].rename(columns={
            "Brand": "品牌", "Principal": "主体", "FY2024": "FY2024", "BE2025": "2025 BE",
            "Proj2026": "2026 预测", "占26预测%": "占26预测%", "G25v24": "25v24",
            "G26v25BE": "26v25BE", "Achieve": "达成率", "YTDg": "YTD增长",
        }).style.format({
            "FY2024": "{:,.0f}", "2025 BE": "{:,.0f}", "2026 预测": "{:,.0f}",
            "占26预测%": "{:.1f}%", "25v24": "{:.1%}", "26v25BE": "{:.1%}",
            "达成率": "{:.1%}", "YTD增长": "{:.1%}",
        }).background_gradient(subset=["26v25BE"], cmap="RdYlGn")
        .background_gradient(subset=["达成率"], cmap="RdYlGn"),
        use_container_width=True,
        column_config={
            "26v25BE": st.column_config.NumberColumn("26v25BE", format="%.1%"),
            "达成率": st.column_config.NumberColumn("达成率", format="%.1%"),
            "25v24": st.column_config.NumberColumn("25v24", format="%.1%"),
            "YTD增长": st.column_config.NumberColumn("YTD增长", format="%.1%"),
        },
    )

    st.subheader("② 2026 预测 增长最快 / 下滑最多（Top 5）")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**增长最快 Top 5**（按 26v25BE）")
        top_g = df.dropna(subset=["Proj2026", "G26v25BE"]).sort_values("G26v25BE", ascending=False).head(5)
        st.dataframe(top_g[["Brand", "Proj2026", "G26v25BE"]].rename(
            columns={"Brand": "品牌", "Proj2026": "2026 预测", "G26v25BE": "26v25BE"}
        ).style.format({"2026 预测": "{:,.0f}", "26v25BE": "{:.1%}"}), use_container_width=True)
    with c2:
        st.markdown("**下滑最多 Top 5**（按 26v25BE）")
        bot_g = df.dropna(subset=["Proj2026", "G26v25BE"]).sort_values("G26v25BE", ascending=True).head(5)
        st.dataframe(bot_g[["Brand", "Proj2026", "G26v25BE"]].rename(
            columns={"Brand": "品牌", "Proj2026": "2026 预测", "G26v25BE": "26v25BE"}
        ).style.format({"2026 预测": "{:,.0f}", "26v25BE": "{:.1%}"}), use_container_width=True)

    st.subheader("③ 单品牌指标下钻")
    pick = st.selectbox("选择品牌查看完整指标", options=df_s["Brand"].tolist(), key="si_pick")
    if pick:
        row = df_s[df_s["Brand"] == pick].iloc[0]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("FY2024", f"{row['FY2024']:,.0f}" if pd.notna(row['FY2024']) else "—")
        m2.metric("2025 BE", f"{row['BE2025']:,.0f}" if pd.notna(row['BE2025']) else "—")
        m3.metric("2026 预测", f"{row['Proj2026']:,.0f}" if pd.notna(row['Proj2026']) else "—")
        m4.metric("达成率", f"{row['Achieve']:.1%}" if pd.notna(row['Achieve']) else "—")
        m5, m6, m7 = st.columns(3)
        m5.metric("25v24", f"{row['G25v24']:.1%}" if pd.notna(row['G25v24']) else "—")
        m6.metric("26v25BE", f"{row['G26v25BE']:.1%}" if pd.notna(row['G26v25BE']) else "—")
        m7.metric("YTD增长", f"{row['YTDg']:.1%}" if pd.notna(row['YTDg']) else "—")

# ---------- Tab2: BCG 矩阵与趋势 ----------
with tab2:
    st.subheader("① BCG 矩阵：2026 预测规模 × 26v25BE 增速")
    st.markdown("横轴=2026 预测（规模），纵轴=26v25BE 增速；中位线分四象限："
                "🌟明星(高规高增) / 💰现金牛(高规低增) / 💡问题(低规高增) / ⚠️瘦狗(低规低增)。")

    bcg = df.dropna(subset=["Proj2026", "G26v25BE"]).copy()
    bcg = bcg[bcg["Proj2026"] > 0]
    if bcg.empty:
        st.warning("无足够数据绘制 BCG（需同时有 2026 预测与 26v25BE）。")
    else:
        med_s = bcg["Proj2026"].median()
        med_g = bcg["G26v25BE"].median()

        def _quad(row):
            hi_s = row["Proj2026"] >= med_s
            hi_g = row["G26v25BE"] >= med_g
            if hi_s and hi_g:
                return "🌟明星"
            if hi_s and not hi_g:
                return "💰现金牛"
            if not hi_s and hi_g:
                return "💡问题"
            return "⚠️瘦狗"

        bcg["象限"] = bcg.apply(_quad, axis=1)
        bcg_show = (bcg[["Brand", "Proj2026", "G26v25BE", "象限"]]
                    .sort_values("Proj2026", ascending=False))
        st.dataframe(
            bcg_show.rename(columns={"Brand": "品牌", "Proj2026": "2026 预测",
                                    "G26v25BE": "26v25BE", "象限": "象限"})
            .style.format({"2026 预测": "{:,.0f}", "26v25BE": "{:.1%}"}),
            use_container_width=True,
        )
        chart_df = bcg[["Brand", "Proj2026", "G26v25BE"]].rename(
            columns={"Brand": "品牌", "Proj2026": "2026预测", "G26v25BE": "26v25BE增速"})
        st.scatter_chart(chart_df.set_index("品牌"), x="2026预测", y="26v25BE增速")

    st.subheader("② SELL IN 三年实际 + 2025 BE + 2026 预测（合计趋势）")
    st.markdown("全品牌汇总：FY2022/23/24 实际 + 2025 BE 预估 + 2026 预测。"
                "注意 2025/2026 为预估口径，与前期实际不可直接等同增速。")
    trend = pd.DataFrame({
        "年度": ["FY2022", "FY2023", "FY2024", "2025 BE", "2026 预测"],
        "SELL IN": [
            df["FY2022"].sum(), df["FY2023"].sum(), df["FY2024"].sum(),
            df["BE2025"].sum(), df["Proj2026"].sum(),
        ],
    }).set_index("年度")
    st.line_chart(trend)
    st.caption(f"合计：FY2024={df['FY2024'].sum():,.0f} ｜ 2025 BE={df['BE2025'].sum():,.0f}"
               f" ｜ 2026 预测={df['Proj2026'].sum():,.0f}（USD）")

# ---------- Tab3: 按主体汇总 ----------
with tab3:
    st.subheader("① 按 Principal 汇总 SELL IN")
    agg = (df.groupby("Principal").agg(
        品牌数=("Brand", "count"),
        FY2024=("FY2024", "sum"),
        BE2025=("BE2025", "sum"),
        Proj2026=("Proj2026", "sum"),
    ).reset_index().sort_values("Proj2026", ascending=False))
    agg["占26预测%"] = (agg["Proj2026"] / agg["Proj2026"].sum() * 100).round(1)
    st.markdown("**各主体 SELL IN 合计（USD）**")
    st.dataframe(agg.rename(columns={"Principal": "主体"}).style.format({
        "FY2024": "{:,.0f}", "BE2025": "{:,.0f}", "Proj2026": "{:,.0f}", "占26预测%": "{:.1f}%"
    }).background_gradient(subset=["占26预测%"], cmap="Blues"), use_container_width=True)
    st.bar_chart(agg.set_index("Principal")["Proj2026"])

    st.subheader("② 主体 × 品牌 明细")
    piv = df.pivot_table(index="Principal", columns="Brand", values="Proj2026",
                          aggfunc="sum", fill_value=0)
    st.dataframe(piv.style.format("{:,.0f}"), use_container_width=True)

# ===================== 页脚 =====================
st.divider()
st.caption(
    "数据口径：① 本页 = 零售报表知识库《2025 TR YTD Oct Sell in & Purchase. BE. 2026 Projection.xlsx》"
    "的 `sell in` 工作表，NET SELL-IN (USD) 口径，属 SELL IN（对品牌方出货），非 SELL OUT 零售；"
    "② 表头第 3 行、品牌数据第 4 行起；YTD 截止月份源表标注 Aug；"
    "③ 金额单位统一 USD，跨品牌/主体汇总有效；④ 2025 BE / 2026 预测为预估，勿与前期实际混算增速。"
    "🔒 本页已加密，与 NEWNESS / 品牌表现分析 页共用同一密码(Max12345)。"
)
