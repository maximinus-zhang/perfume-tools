# -*- coding: utf-8 -*-
"""
采购深度分析 v1.0（SELL IN 采购端，加密）
=======================================
用途: 在「SELL IN」模块下，对采购(Purchase，reported to principal)做品牌 / 主体 / 库存风险维度的深度分析。
数据来源: 桌面知识库
  《2025 TR YTD Oct Sell in & Purchase. BE. 2026 Projection.xlsx》
  → 工作表 `purchase`（表头在第 4 行，品牌数据第 5 行起）
口径说明:
  - 本表为「采购(Purchase)」—— TR 向品牌方(principal)的采购口径，属 SELL IN（非 SELL OUT 零售）。
  - 金额存在 **币种差异**：列 [2] Currency 为 EUR 或 USD，跨币种不可直接汇总。
    本页提供「币种筛选」：选单一币种时所有合计/BCG 才可比；选「全部」时按币种分开展示。
  - FY2022/23/24 = 实际年；2025 Purchase Budget = 2025 采购预算；2025 Best Estimate = 2025 最新预估(BE)；
    2026 Projection = 2026 预测；各类 vs% 为同比增长率（小数形式，如 0.24 = +24%）。
  - YTD 截止月份源表标注为 Aug（尽管文件名写 Oct），以源表为准。
  - 库存月数(Stock month)、HK WH 库存金额、IC 在途等均来自源表对应列。
加密: 与 NEWNESS / 品牌表现分析 / SELL IN 深度分析 页共用同一密码(Max12345)与 utils.newness_crypto 校验逻辑。
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
PURCHASE_SHEET = "purchase"

# ===================== 密码门（同 NEWNESS / 品牌页 / SELL IN 深度分析） =====================
EMBEDDED_TOKEN = (
    "TkVXMT+unCbW9CIFN9b0bBNK7Fyv6bwJpA/K4WP5kQH1JvrIGS3NyFMr6jHWmIOmXwntik3cLQYIJRJH"
)
SESSION_AUTH = "purchase_authed"
SESSION_ERR = "purchase_err"


def _try_unlock():
    """用输入的密码解密内嵌校验串；失败给出友好提示。"""
    pw = st.session_state.get("purchase_pw", "")
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
        "<p style='opacity:.7;margin:0'>本页为采购深度分析（Purchase / NET SELL-IN USD），"
        "请输入访问密码后查看。</p></div>",
        unsafe_allow_html=True,
    )
    st.text_input("访问密码", type="password", key="purchase_pw",
                  placeholder="请输入密码", help="与 NEWNESS 页相同密码")
    if st.button("🔓 解锁查看", type="primary", key="purchase_unlock"):
        _try_unlock()
    if st.session_state.get(SESSION_ERR):
        st.error(st.session_state[SESSION_ERR])
    if not st.session_state.get(SESSION_AUTH, False):
        st.stop()

# 已解锁：提供重新上锁按钮
if st.sidebar.button("🔒 重新上锁", key="purchase_relock"):
    st.session_state[SESSION_AUTH] = False
    st.session_state[SESSION_ERR] = ""
    st.rerun()


# ===================== 数据加载 =====================
@st.cache_data
def load_purchase():
    """读取 `purchase` 表，返回品牌级采购指标 DataFrame。
    表头在第 4 行(0-based=3)，品牌数据第 5 行(0-based=4)起。
    """
    raw = pd.read_excel(KB_FILE, sheet_name=PURCHASE_SHEET, engine="calamine", header=None)
    HDR = 3
    SKIP = {"TTL", "TOTAL", "NAN", "", "合计", "GRAND TOTAL"}
    rows = []
    for r in range(HDR + 1, len(raw)):
        brand = raw.iloc[r, 1]
        if pd.isna(brand):
            continue
        b = str(brand).strip()
        if b.upper() in SKIP or "合计" in b or "TOTAL" in b.upper():
            continue
        cur = raw.iloc[r, 2]
        rows.append({
            "Principal": (str(raw.iloc[r, 0]).strip() if not pd.isna(raw.iloc[r, 0]) else ""),
            "Brand": b,
            "Currency": (str(cur).strip().upper() if not pd.isna(cur) else ""),
            "FY2022": raw.iloc[r, 3],
            "FY2023": raw.iloc[r, 4],
            "FY2024": raw.iloc[r, 5],
            "Budget2025": raw.iloc[r, 6],
            "G23v22": raw.iloc[r, 7],
            "G24v23": raw.iloc[r, 8],
            "G25v24": raw.iloc[r, 9],
            "YTD2024inv": raw.iloc[r, 10],
            "YTD2025inv": raw.iloc[r, 11],
            "YTDg": raw.iloc[r, 13],
            "PO2025": raw.iloc[r, 14],
            "InvRate": raw.iloc[r, 16],
            "YTG2025": raw.iloc[r, 17],
            "BE2025": raw.iloc[r, 18],
            "BE_vs24FY": raw.iloc[r, 19],
            "BE_vs_budget": raw.iloc[r, 20],
            "AchInv": raw.iloc[r, 21],
            "AchPO": raw.iloc[r, 22],
            "Proj2026": raw.iloc[r, 23],
            "G26v25BE": raw.iloc[r, 24],
            "S_inv25": raw.iloc[r, 25],
            "S_inv25p": raw.iloc[r, 26],
            "S_inv26": raw.iloc[r, 27],
            "S_inv26p": raw.iloc[r, 28],
            "FOC25": raw.iloc[r, 29],
            "FOC25p": raw.iloc[r, 30],
            "FOC26": raw.iloc[r, 31],
            "FOC26p": raw.iloc[r, 32],
            "SM_YTD": raw.iloc[r, 33],
            "SM_coming": raw.iloc[r, 34],
            "SM_TTL": raw.iloc[r, 35],
            "SM_yearend": raw.iloc[r, 36],
            "InvHKWH": raw.iloc[r, 37],
            "IC_HKWH3": raw.iloc[r, 38],
            "IC_Trade": raw.iloc[r, 39],
            "IC_HKWH8": raw.iloc[r, 40],
            "YTG_comment": (str(raw.iloc[r, 41]).strip() if not pd.isna(raw.iloc[r, 41]) else ""),
        })
    df = pd.DataFrame(rows)
    num = ["FY2022", "FY2023", "FY2024", "Budget2025", "G23v22", "G24v23", "G25v24",
           "YTD2024inv", "YTD2025inv", "YTDg", "PO2025", "InvRate", "YTG2025", "BE2025",
           "BE_vs24FY", "BE_vs_budget", "AchInv", "AchPO", "Proj2026", "G26v25BE",
           "S_inv25", "S_inv25p", "S_inv26", "S_inv26p", "FOC25", "FOC25p", "FOC26", "FOC26p",
           "SM_YTD", "SM_coming", "SM_TTL", "SM_yearend", "InvHKWH", "IC_HKWH3", "IC_Trade", "IC_HKWH8"]
    for c in num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # 去掉三个核心金额列全空的品牌行（多为合计/空行）
    df = df.dropna(subset=["FY2024", "BE2025", "Proj2026"], how="all").reset_index(drop=True)
    return df


# ===================== 页面主体 =====================
st.title("🔒 采购深度分析 v1.0")
st.caption("SELL IN · 采购(Purchase) · 数据来源：2025 TR YTD…Sell in & Purchase…xlsx（purchase 表）"
           " ｜ 本地知识库，不上云 ｜ 🔒 密码保护与 NEWNESS / 品牌表现 / SELL IN 深度 页一致")

df = load_purchase()

if df.empty:
    st.error("未能从 `purchase` 工作表解析出品牌数据，请检查源文件。")
    st.stop()

# 币种筛选：跨币种不可直接汇总，故提供筛选
cur_opts = ["全部（分币种显示）"] + sorted(df["Currency"].dropna().unique().tolist())
cur = st.selectbox("币种筛选", options=cur_opts, index=0,
                   help="采购金额含 EUR / USD，跨币种不可直接汇总；选单一币种后合计/BCG 才可比。")
df_v = df if cur == "全部（分币种显示）" else df[df["Currency"] == cur].reset_index(drop=True)
single_cur = (cur != "全部（分币种显示）")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 指标总览(按币种)", "🌟 BCG 矩阵(单一币种)", "🧾 采购执行(开票率/PO达成)", "📦 库存风险(月数/IC在途/YTG)"
])

# ---------- Tab1: 指标总览(按币种) ----------
with tab1:
    st.subheader("① 币种汇总（同币种才可相加）")
    if single_cur:
        st.info(f"当前筛选币种：**{cur}**（单一币种，合计可比）")
        tot = df_v
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("FY2024", f"{tot['FY2024'].sum():,.0f}")
        c2.metric("2025 预算", f"{tot['Budget2025'].sum():,.0f}")
        c3.metric("2025 BE", f"{tot['BE2025'].sum():,.0f}")
        c4.metric("2026 预测", f"{tot['Proj2026'].sum():,.0f}")
        c5.metric("2025 PO", f"{tot['PO2025'].sum():,.0f}")
    else:
        st.warning("「全部」模式：跨币种不可直接相加，下方按币种分别列示合计。")
        for cc in sorted(df["Currency"].dropna().unique().tolist()):
            sub = df[df["Currency"] == cc]
            st.markdown(f"**{cc} 币种合计**（{len(sub)} 个品牌）")
            cc1, cc2, cc3, cc4 = st.columns(4)
            cc1.metric("FY2024", f"{sub['FY2024'].sum():,.0f}")
            cc2.metric("2025 BE", f"{sub['BE2025'].sum():,.0f}")
            cc3.metric("2026 预测", f"{sub['Proj2026'].sum():,.0f}")
            cc4.metric("2025 PO", f"{sub['PO2025'].sum():,.0f}")

    st.subheader("② 品牌级采购指标（按 2026 预测降序）")
    st.markdown("指标说明：**FY2024**=2024 实际年；**Budget2025**=2025 采购预算；**BE2025**=2025 最新预估；"
                "**YTD2025inv**=YTD Aug 2025 开票(invoiced)；**PO2025**=YTD Aug 2025 总采购单；"
                "**InvRate**=开票率(invoiced/PO)；**AchInv/AchPO**=开票/PO 达成率(YTD/预算)；"
                "**Proj2026**=2026 预测；**G26v25BE**=26 vs 25 BE 增长。")
    df_s = df_v.sort_values("Proj2026", ascending=False).reset_index(drop=True)
    df_s["排名"] = df_s.index + 1
    view_n = st.number_input("展示品牌数量（Top N）", min_value=5, max_value=len(df_s),
                             value=min(20, len(df_s)), step=1, key="pu_n")
    show = df_s.head(view_n)
    st.dataframe(
        show[["排名", "Brand", "Currency", "Principal", "FY2024", "Budget2025", "BE2025",
              "Proj2026", "G26v25BE", "InvRate", "AchInv", "AchPO"]].rename(columns={
            "Brand": "品牌", "Currency": "币种", "Principal": "主体", "FY2024": "FY2024",
            "Budget2025": "2025预算", "BE2025": "2025 BE", "Proj2026": "2026预测",
            "G26v25BE": "26v25BE", "InvRate": "开票率", "AchInv": "开票达成", "AchPO": "PO达成",
        }).style.format({
            "FY2024": "{:,.0f}", "2025预算": "{:,.0f}", "2025 BE": "{:,.0f}", "2026预测": "{:,.0f}",
            "26v25BE": "{:.1%}", "开票率": "{:.1%}", "开票达成": "{:.1%}", "PO达成": "{:.1%}",
        }).background_gradient(subset=["26v25BE"], cmap="RdYlGn")
        .background_gradient(subset=["开票率"], cmap="RdYlGn"),
        use_container_width=True,
        column_config={
            "26v25BE": st.column_config.NumberColumn("26v25BE", format="%.1%"),
            "开票率": st.column_config.NumberColumn("开票率", format="%.1%"),
            "开票达成": st.column_config.NumberColumn("开票达成", format="%.1%"),
            "PO达成": st.column_config.NumberColumn("PO达成", format="%.1%"),
        },
    )

    st.subheader("③ 单品牌指标下钻")
    pick = st.selectbox("选择品牌查看完整采购指标", options=df_s["Brand"].tolist(), key="pu_pick")
    if pick:
        row = df_s[df_s["Brand"] == pick].iloc[0]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("FY2024", f"{row['FY2024']:,.0f}" if pd.notna(row['FY2024']) else "—")
        m2.metric("2025 BE", f"{row['BE2025']:,.0f}" if pd.notna(row['BE2025']) else "—")
        m3.metric("2026 预测", f"{row['Proj2026']:,.0f}" if pd.notna(row['Proj2026']) else "—")
        m4.metric("开票率", f"{row['InvRate']:.1%}" if pd.notna(row['InvRate']) else "—")
        m5, m6, m7, m8 = st.columns(4)
        m5.metric("2025 PO", f"{row['PO2025']:,.0f}" if pd.notna(row['PO2025']) else "—")
        m6.metric("开票达成", f"{row['AchInv']:.1%}" if pd.notna(row['AchInv']) else "—")
        m7.metric("PO达成", f"{row['AchPO']:.1%}" if pd.notna(row['AchPO']) else "—")
        m8.metric("26v25BE", f"{row['G26v25BE']:.1%}" if pd.notna(row['G26v25BE']) else "—")

# ---------- Tab2: BCG 矩阵(单一币种) ----------
with tab2:
    if not single_cur:
        st.warning("⚠️ 请先在左上角选择**单一币种**再绘制 BCG（跨币种金额不可比）。")
    else:
        st.subheader("① BCG 矩阵：2026 预测规模 × 26v25BE 增速")
        st.markdown("横轴=2026 预测（规模），纵轴=26v25BE 增速；中位线分四象限："
                    "🌟明星(高规高增) / 💰现金牛(高规低增) / 💡问题(低规高增) / ⚠️瘦狗(低规低增)。"
                    f"（币种={cur}）")
        bcg = df_v.dropna(subset=["Proj2026", "G26v25BE"]).copy()
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

        st.subheader("② 采购三年实际 + 2025 BE + 2026 预测（合计趋势）")
        st.markdown(f"所选币种({cur})全品牌汇总：FY2022/23/24 实际 + 2025 BE 预估 + 2026 预测。"
                    "注意 2025/2026 为预估口径，与前期实际不可直接等同增速。")
        trend = pd.DataFrame({
            "年度": ["FY2022", "FY2023", "FY2024", "2025 BE", "2026 预测"],
            "采购": [
                df_v["FY2022"].sum(), df_v["FY2023"].sum(), df_v["FY2024"].sum(),
                df_v["BE2025"].sum(), df_v["Proj2026"].sum(),
            ],
        }).set_index("年度")
        st.line_chart(trend)
        st.caption(f"合计({cur})：FY2024={df_v['FY2024'].sum():,.0f} ｜ 2025 BE={df_v['BE2025'].sum():,.0f}"
                   f" ｜ 2026 预测={df_v['Proj2026'].sum():,.0f}")

# ---------- Tab3: 采购执行(开票率 vs PO达成) ----------
with tab3:
    st.subheader("① 开票率(invoiced/PO) 与达成率")
    st.markdown("**开票率**=YTD 开票金额 / YTD 总采购单(PO)；**开票达成**=YTD 开票 / 预算；"
                "**PO达成**=YTD 总PO / 预算。开票率偏低说明下了单但货未到/未开票，需关注供应链交付。")
    ex = df_v.copy()
    ex = ex[ex["Proj2026"].notna() | ex["BE2025"].notna()]
    view = ex[["Brand", "Currency", "YTD2025inv", "PO2025", "InvRate", "AchInv", "AchPO",
               "BE2025", "Proj2026"]].sort_values("BE2025", ascending=False)
    st.dataframe(
        view.rename(columns={
            "Brand": "品牌", "Currency": "币种", "YTD2025inv": "YTD开票", "PO2025": "YTD PO",
            "InvRate": "开票率", "AchInv": "开票达成", "AchPO": "PO达成",
            "BE2025": "2025 BE", "Proj2026": "2026预测",
        }).style.format({
            "YTD开票": "{:,.0f}", "YTD PO": "{:,.0f}", "2025 BE": "{:,.0f}", "2026预测": "{:,.0f}",
            "开票率": "{:.1%}", "开票达成": "{:.1%}", "PO达成": "{:.1%}",
        }).background_gradient(subset=["开票率"], cmap="RdYlGn")
        .background_gradient(subset=["开票达成"], cmap="RdYlGn"),
        use_container_width=True,
        column_config={
            "开票率": st.column_config.NumberColumn("开票率", format="%.1%"),
            "开票达成": st.column_config.NumberColumn("开票达成", format="%.1%"),
            "PO达成": st.column_config.NumberColumn("PO达成", format="%.1%"),
        },
    )

    st.subheader("② 开票率最低 Top 8（交付风险预警）")
    low = ex.dropna(subset=["InvRate"]).sort_values("InvRate", ascending=True).head(8)
    if low.empty:
        st.info("无开票率数据。")
    else:
        st.dataframe(
            low[["Brand", "Currency", "YTD2025inv", "PO2025", "InvRate", "AchPO"]].rename(
                columns={"Brand": "品牌", "Currency": "币种", "YTD2025inv": "YTD开票",
                         "PO2025": "YTD PO", "InvRate": "开票率", "AchPO": "PO达成"}
            ).style.format({"YTD开票": "{:,.0f}", "YTD PO": "{:,.0f}",
                            "开票率": "{:.1%}", "PO达成": "{:.1%}"}),
            use_container_width=True,
        )

    st.subheader("③ Principal support：S-invoice / FOC 占比")
    st.markdown("**S-invoice**(供应商发票) 与 **FOC**(免费货) 占采购比例，反映品牌方支持力度。"
                "比例高 = 品牌方投入多。")
    sup = ex.dropna(subset=["S_inv25p", "FOC25p"], how="all")[
        ["Brand", "Currency", "S_inv25", "S_inv25p", "FOC25", "FOC25p", "Proj2026"]
    ].sort_values("Proj2026", ascending=False)
    st.dataframe(
        sup.rename(columns={
            "Brand": "品牌", "Currency": "币种", "S_inv25": "25 S-invoice", "S_inv25p": "S-inv占比",
            "FOC25": "25 FOC", "FOC25p": "FOC占比", "Proj2026": "2026预测",
        }).style.format({
            "25 S-invoice": "{:,.0f}", "25 FOC": "{:,.0f}", "2026预测": "{:,.0f}",
            "S-inv占比": "{:.1%}", "FOC占比": "{:.1%}",
        }),
        use_container_width=True,
        column_config={
            "S-inv占比": st.column_config.NumberColumn("S-inv占比", format="%.1%"),
            "FOC占比": st.column_config.NumberColumn("FOC占比", format="%.1%"),
        },
    )

# ---------- Tab4: 库存风险(月数/IC在途/YTG) ----------
with tab4:
    st.subheader("① 库存月数(Stock month) 风险")
    st.markdown("**SM_TTL**=截至 YTD 202505 总库存月数；**SM_yearend**=年底预计库存月数；"
                "**SM_coming**=在途货的库存月数。一般 >6 个月视为偏高，需关注积压。")
    sm = df_v.dropna(subset=["SM_TTL", "SM_yearend"], how="all")[
        ["Brand", "Currency", "SM_YTD", "SM_coming", "SM_TTL", "SM_yearend",
         "InvHKWH", "IC_HKWH3", "IC_Trade", "IC_HKWH8"]
    ].sort_values("SM_TTL", ascending=False)
    st.dataframe(
        sm.rename(columns={
            "Brand": "品牌", "Currency": "币种", "SM_YTD": "YTD库存月", "SM_coming": "在途库存月",
            "SM_TTL": "总库存月", "SM_yearend": "年底库存月", "InvHKWH": "HK仓库存$",
            "IC_HKWH3": "IC HK仓(3月)", "IC_Trade": "IC在途", "IC_HKWH8": "IC HK仓(8月)",
        }).style.format({
            "YTD库存月": "{:.1f}", "在途库存月": "{:.1f}", "总库存月": "{:.1f}", "年底库存月": "{:.1f}",
            "HK仓库存$": "{:,.0f}", "IC HK仓(3月)": "{:,.0f}", "IC在途": "{:,.0f}", "IC HK仓(8月)": "{:,.0f}",
        }).background_gradient(subset=["总库存月"], cmap="OrRd")
        .background_gradient(subset=["年底库存月"], cmap="OrRd"),
        use_container_width=True,
    )

    st.subheader("② 库存月数偏高预警（SM_TTL > 6）")
    hi = sm.dropna(subset=["SM_TTL"]).query("SM_TTL > 6")
    if hi.empty:
        st.success("当前筛选下无库存月数 > 6 的品牌。")
    else:
        st.dataframe(
            hi[["Brand", "Currency", "SM_TTL", "SM_yearend", "InvHKWH"]].rename(
                columns={"Brand": "品牌", "Currency": "币种", "SM_TTL": "总库存月",
                         "SM_yearend": "年底库存月", "InvHKWH": "HK仓库存$"}
            ).style.format({"总库存月": "{:.1f}", "年底库存月": "{:.1f}", "HK仓库存$": "{:,.0f}"}),
            use_container_width=True,
        )

    st.subheader("③ YTG 备注(Comments on YTG)")
    st.markdown("源表「Comments on YTG」逐品牌备注，通常用于记录下单单号、交付状态、特殊说明等。")
    ytg = df_v[df_v["YTG_comment"].notna() & (df_v["YTG_comment"].astype(str).str.len() > 0)][
        ["Brand", "Currency", "YTG_comment"]
    ]
    if ytg.empty:
        st.info("当前筛选下无 YTG 备注。")
    else:
        for _, r in ytg.iterrows():
            st.markdown(f"- **{r['Brand']}** ({r['Currency']})：{r['YTG_comment']}")

# ===================== 页脚 =====================
st.divider()
st.caption(
    "数据口径：① 本页 = 零售报表知识库《2025 TR YTD Oct Sell in & Purchase. BE. 2026 Projection.xlsx》"
    "的 `purchase` 工作表，采购(Purchase)口径，属 SELL IN（向品牌方采购），非 SELL OUT 零售；"
    "② 表头第 4 行、品牌数据第 5 行起；YTD 截止月份源表标注 Aug；"
    "③ **金额含 EUR/USD 币种差异，跨币种不可直接汇总**，请用顶部「币种筛选」；"
    "④ 2025 BE / 2026 预测为预估，勿与前期实际混算增速；库存月数为源表口径。"
    "🔒 本页已加密，与 NEWNESS / 品牌表现分析 / SELL IN 深度分析 页共用同一密码(Max12345)。"
)
