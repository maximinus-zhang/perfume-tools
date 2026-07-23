# -*- coding: utf-8 -*-
"""
采购深度分析 v2.0（重写·扩维·密码保护）
=======================================
在 v1 基础上深挖 `purchase` 表（42 列）全字段，覆盖采购执行、库存健康评分、品牌方支持度、币种暴露四大主题。
数据来源: 桌面知识库《2025 TR YTD Oct Sell in & Purchase. BE. 2026 Projection.xlsx》→ 工作表 `purchase`
口径: 采购(Purchase) 口径，属 SELL IN（向品牌方采购），非 SELL OUT 零售。
      **金额含 EUR/USD 币种差异，跨币种不可直接汇总**——顶部「币种筛选」控制金额合计；库存月数/比率为无量纲，跨币种可比。
密码保护: 与 NEWNESS / 品牌表现分析 / SELL IN 深度分析 页共用同一密码(Max12345)与 utils.newness_crypto。
"""
import streamlit as st
import pandas as pd
import numpy as np
import warnings
import base64
from utils.newness_crypto import decrypt_data

warnings.filterwarnings("ignore")

KB_FILE = r"C:\Users\Maximinuszhang\Desktop\WorkBuddy\知识库\2025 TR YTD Oct Sell in & Purchase. BE. 2026 Projection.xlsx"
PURCHASE_SHEET = "purchase"

EMBEDDED_TOKEN = (
    "TkVXMT+unCbW9CIFN9b0bBNK7Fyv6bwJpA/K4WP5kQH1JvrIGS3NyFMr6jHWmIOmXwntik3cLQYIJRJH"
)
SESSION_AUTH = "purchase_authed"
SESSION_ERR = "purchase_err"


def _try_unlock():
    pw = st.session_state.get("purchase_pw", "")
    if not pw:
        st.session_state[SESSION_ERR] = "请输入访问密码"
        return
    try:
        decrypt_data(base64.b64decode(EMBEDDED_TOKEN), pw)
        st.session_state[SESSION_AUTH] = True
        st.session_state[SESSION_ERR] = ""
    except PermissionError:
        st.session_state[SESSION_AUTH] = False
        st.session_state[SESSION_ERR] = "🔒 密码错误，请重试"
    except Exception as e:
        st.session_state[SESSION_AUTH] = False
        st.session_state[SESSION_ERR] = f"解密失败：{e}"


if not st.session_state.get(SESSION_AUTH, False):
    with st.container(border=True):
        st.markdown("🔒 此页面需要访问密码，输入密码后即可查看完整内容。")
        st.text_input(
            "访问密码",
            type="password",
            key="purchase_pw",
            placeholder="请输入密码",
            label_visibility="collapsed",
            help="与 NEWNESS 页相同密码",
        )
        if st.button("🔓 解锁查看", type="primary", key="purchase_unlock"):
            _try_unlock()
        if st.session_state.get(SESSION_ERR):
            st.error(st.session_state[SESSION_ERR])
    if not st.session_state.get(SESSION_AUTH, False):
        st.stop()

if st.sidebar.button("🔒 重新上锁", key="purchase_relock"):
    st.session_state[SESSION_AUTH] = False
    st.session_state[SESSION_ERR] = ""
    st.rerun()


# ===================== 数据加载 =====================
@st.cache_data
def load_purchase():
    """读取 `purchase` 表（表头第 4 行，数据第 5 行起，共 42 列）。"""
    raw = pd.read_excel(KB_FILE, sheet_name=PURCHASE_SHEET, engine="openpyxl", header=None)
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
        rows.append({
            "Principal": (str(raw.iloc[r, 0]).strip() if not pd.isna(raw.iloc[r, 0]) else ""),
            "Brand": b,
            "Currency": (str(raw.iloc[r, 2]).strip().upper() if not pd.isna(raw.iloc[r, 2]) else ""),
            "FY2024": raw.iloc[r, 5],
            "Budget2025": raw.iloc[r, 6],
            "BE2025": raw.iloc[r, 18],
            "YTD2025inv": raw.iloc[r, 11],
            "PO2025": raw.iloc[r, 14],
            "InvRate": raw.iloc[r, 16],
            "AchInv": raw.iloc[r, 21],
            "AchPO": raw.iloc[r, 22],
            "Proj2026": raw.iloc[r, 23],
            "G26v25BE": raw.iloc[r, 24],
            "S_inv25": raw.iloc[r, 25],
            "S_inv25p": raw.iloc[r, 26],
            "FOC25": raw.iloc[r, 29],
            "FOC25p": raw.iloc[r, 30],
            "SM_TTL": raw.iloc[r, 35],
            "SM_yearend": raw.iloc[r, 36],
            "InvHKWH": raw.iloc[r, 37],
            "IC3": raw.iloc[r, 38],
            "IC_Trade": raw.iloc[r, 39],
            "IC8": raw.iloc[r, 40],
            "YTG_comment": (str(raw.iloc[r, 41]).strip() if not pd.isna(raw.iloc[r, 41]) else ""),
        })
    df = pd.DataFrame(rows)
    num = ["FY2024", "Budget2025", "BE2025", "YTD2025inv", "PO2025", "InvRate", "AchInv",
           "AchPO", "Proj2026", "G26v25BE", "S_inv25", "S_inv25p", "FOC25", "FOC25p",
           "SM_TTL", "SM_yearend", "InvHKWH", "IC3", "IC_Trade", "IC8"]
    for c in num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["FY2024", "BE2025", "Proj2026"], how="all").reset_index(drop=True)
    return df


def _inventory_health_score(ic3, ic8):
    """库存健康评分 0-100，基于 HK 仓库存月数(IC3，3月基准)。
    理想区间 3-9 个月=满分；<3 缺货风险、>9 积压风险各扣分；0/缺失=无数据。
    （注：健康区间按 HK WH 以 3 月历史 sell-in 为基准的惯例设定，可调。）"""
    x = ic3 if pd.notna(ic3) else (ic8 if pd.notna(ic8) else np.nan)
    if pd.isna(x) or x <= 0:
        return np.nan
    if 3 <= x <= 9:
        return 100.0
    if x < 3:
        return max(0.0, 100 - (3 - x) * 35)
    return max(0.0, 100 - (x - 9) * 6)


def _risk_level(score):
    if pd.isna(score):
        return "⚪ 无数据"
    if score >= 80:
        return "🟢 健康"
    if score >= 55:
        return "🟡 关注"
    if score >= 35:
        return "🟠 偏高"
    return "🔴 高风险"


# ===================== 页面主体 =====================
st.title("采购深度分析 v2.0")
st.caption("SELL IN · 采购(Purchase) · 数据来源：2025 TR YTD…Sell in & Purchase…xlsx（purchase 表）"
           " ｜ 本地知识库，不上云 ｜ 密码保护与 NEWNESS / 品牌表现分析 / SELL IN 深度 页一致")

df = load_purchase()
if df.empty:
    st.error("未能从 `purchase` 工作表解析出品牌数据，请检查源文件。")
    st.stop()

df["健康评分"] = df.apply(lambda r: _inventory_health_score(r["IC3"], r["IC8"]), axis=1)
df["风险"] = df["健康评分"].apply(_risk_level)
# 品牌方支持力度指数：S-invoice% 与 FOC% 合计（占采购比例越高=支持越大）
df["支持力度"] = df[["S_inv25p", "FOC25p"]].sum(axis=1)

cur_opts = ["全部（分币种显示）"] + sorted(df["Currency"].dropna().unique().tolist())
cur = st.selectbox("币种筛选（仅影响金额合计；库存月数/比率为无量纲，跨币种可比）",
                   options=cur_opts, index=0,
                   help="采购金额含 EUR / USD，跨币种不可直接汇总；选单一币种后金额合计才可比。")
df_v = df if cur == "全部（分币种显示）" else df[df["Currency"] == cur].reset_index(drop=True)
single_cur = (cur != "全部（分币种显示）")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🧾 采购执行深钻", "📦 库存健康评分", "🤝 品牌方支持度", "💱 币种暴露", "📋 YTG 备注"
])

# ---------- Tab1: 采购执行深钻 ----------
with tab1:
    st.subheader("① 采购执行总览（开票率 / PO达成）")
    st.markdown("**开票率**=YTD 开票/PO；**开票达成**=YTD 开票/预算；**PO达成**=YTD PO/预算。")
    ex = df_v.copy()
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
        }        ).background_gradient(subset=["开票率"], cmap="RdYlGn")
        .background_gradient(subset=["开票达成"], cmap="RdYlGn"),
        use_container_width=True,
        column_config={
            "开票率": st.column_config.NumberColumn("开票率", format="%.1%"),
            "开票达成": st.column_config.NumberColumn("开票达成", format="%.1%"),
            "PO达成": st.column_config.NumberColumn("PO达成", format="%.1%"),
        },
    )
    st.subheader("② 交付风险：开票率最低 Top 8")
    low = ex.dropna(subset=["InvRate"]).sort_values("InvRate").head(8)
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

# ---------- Tab2: 库存健康评分 ----------
with tab2:
    st.subheader("① 库存健康评分矩阵（基于 HK 仓库存月数 IC3/IC8）")
    st.markdown("评分逻辑：以 `IC3`（End Aug IC HK WH，按 3 月历史 sell-in 基准的库存月数）为主；"
                "**3–9 个月=满分 100**；<3 月=缺货风险、>9 月=积压风险各扣分；0/缺失=⚪ 无数据。"
                "注：`SM_TTL`(总库存月) 与 `IC_Trade`(在途) 在本工作簿中为空，故以 IC3/IC8/Inv$ 为准。")
    ih = df_v.copy().sort_values("健康评分", na_position="last")
    st.dataframe(
        ih[["Brand", "Currency", "IC3", "IC8", "InvHKWH", "健康评分", "风险"]].rename(columns={
            "Brand": "品牌", "Currency": "币种", "IC3": "HK仓库存月(3月基准)", "IC8": "HK仓库存月(8月基准)",
            "InvHKWH": "HK仓库存$", "健康评分": "健康评分", "风险": "风险"}),
        use_container_width=True,
        column_config={
            "健康评分": st.column_config.NumberColumn("健康评分", format="%.0f"),
            "HK仓库存月(3月基准)": st.column_config.NumberColumn("HK仓库存月(3月基准)", format="%.1f"),
            "HK仓库存月(8月基准)": st.column_config.NumberColumn("HK仓库存月(8月基准)", format="%.1f"),
            "HK仓库存$": st.column_config.NumberColumn("HK仓库存$", format="%,.0f"),
        },
    )
    st.subheader("② 风险分布")
    dist = ih["风险"].value_counts()
    for lvl in ["🔴 高风险", "🟠 偏高", "🟡 关注", "🟢 健康", "⚪ 无数据"]:
        if lvl in dist.index:
            st.markdown(f"- {lvl}：**{dist[lvl]}** 个品牌")
    hi = ih[ih["健康评分"] < 55]
    if not hi.empty:
        st.subheader("③ 高风险/偏高品牌明细（评分<55）")
        st.dataframe(
            hi[["Brand", "Currency", "IC3", "IC8", "InvHKWH", "健康评分", "风险"]].rename(
                columns={"Brand": "品牌", "Currency": "币种", "IC3": "HK仓库存月(3月基准)",
                         "IC8": "HK仓库存月(8月基准)", "InvHKWH": "HK仓库存$", "健康评分": "健康评分", "风险": "风险"}
            ).style.format({"HK仓库存月(3月基准)": "{:.1f}", "HK仓库存月(8月基准)": "{:.1f}",
                            "HK仓库存$": "{:,.0f}", "健康评分": "{:.0f}"}),
            use_container_width=True,
        )

# ---------- Tab3: 品牌方支持度 ----------
with tab3:
    st.subheader("① 品牌方支持力度排名（S-invoice% + FOC% 合计）")
    st.markdown("**支持力度指数** = 2025 S-invoice 占采购比 + 2025 FOC 占采购比；越高=品牌方投入越多"
                "（免费货/供应商发票支持）。下表面向单一币种可比，全部模式仅作方向参考。")
    sup = df_v.dropna(subset=["支持力度"]).sort_values("支持力度", ascending=False).copy()
    st.dataframe(
        sup[["Brand", "Currency", "S_inv25", "S_inv25p", "FOC25", "FOC25p", "支持力度", "Proj2026"]].rename(
            columns={"Brand": "品牌", "Currency": "币种", "S_inv25": "25 S-invoice",
                     "S_inv25p": "S-inv占比", "FOC25": "25 FOC", "FOC25p": "FOC占比",
                     "支持力度": "支持力度指数", "Proj2026": "2026预测"}
        ).style.format({
            "25 S-invoice": "{:,.0f}", "25 FOC": "{:,.0f}", "2026预测": "{:,.0f}",
            "S-inv占比": "{:.1%}", "FOC占比": "{:.1%}", "支持力度指数": "{:.1%}",
        }).background_gradient(subset=["支持力度指数"], cmap="Greens"),
        use_container_width=True,
        column_config={
            "S-inv占比": st.column_config.NumberColumn("S-inv占比", format="%.1%"),
            "FOC占比": st.column_config.NumberColumn("FOC占比", format="%.1%"),
            "支持力度指数": st.column_config.NumberColumn("支持力度指数", format="%.1%"),
        },
    )
    st.subheader("② 支持度 Top 5 / 末 5")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**支持力度最强 Top 5**")
        st.dataframe(sup.head(5)[["Brand", "支持力度"]].rename(
            columns={"Brand": "品牌", "支持力度": "支持力度指数"}).style.format({"支持力度指数": "{:.1%}"}))
    with c2:
        st.markdown("**支持力度最弱 Top 5**")
        st.dataframe(sup.tail(5)[["Brand", "支持力度"]].rename(
            columns={"Brand": "品牌", "支持力度": "支持力度指数"}).style.format({"支持力度指数": "{:.1%"}))

# ---------- Tab4: 币种暴露 ----------
with tab4:
    st.subheader("① 币种暴露总览")
    st.markdown("采购金额分 EUR / USD；下方按币种列示采购规模与库存金额暴露。")
    exp = df.groupby("Currency").agg(
        品牌数=("Brand", "count"), FY2024=("FY2024", "sum"), BE2025=("BE2025", "sum"),
        Proj2026=("Proj2026", "sum"), PO2025=("PO2025", "sum"),
        InvHKWH=("InvHKWH", "sum"), IC_Trade=("IC_Trade", "sum")).reset_index()
    st.dataframe(exp.rename(columns={"Currency": "币种"}).style.format({
        "FY2024": "{:,.0f}", "BE2025": "{:,.0f}", "Proj2026": "{:,.0f}", "PO2025": "{:,.0f}",
        "InvHKWH": "{:,.0f}", "IC_Trade": "{:,.0f}"}), use_container_width=True)
    st.bar_chart(exp.set_index("Currency")["Proj2026"])
    st.subheader("② 采购额币种构成")
    if single_cur:
        st.info(f"当前筛选：**{cur}**。上方总额即该币种合计。")
    else:
        st.info("选单一币种可看该币种下各品牌明细；上方为分币种汇总。")

# ---------- Tab5: YTG 备注 ----------
with tab5:
    st.subheader("① YTG 备注（Comments on YTG）")
    ytg = df_v[df_v["YTG_comment"].notna() & (df_v["YTG_comment"].astype(str).str.len() > 0)][
        ["Brand", "Currency", "YTG_comment"]]
    if ytg.empty:
        st.info("当前筛选下无 YTG 备注。")
    else:
        for _, r in ytg.iterrows():
            st.markdown(f"- **{r['Brand']}** ({r['Currency']})：{r['YTG_comment']}")

# ===================== 页脚 =====================
st.divider()
st.caption(
    "数据口径：① 本页 = 知识库《2025 TR YTD Oct Sell in & Purchase. BE. 2026 Projection.xlsx》"
    "的 `purchase` 工作表（42 列，采购口径，属 SELL IN）；"
    "② 表头第 4 行、品牌数据第 5 行起；YTD 截止月份源表标注 Aug；"
    "③ **金额含 EUR/USD 币种差异，跨币种不可直接汇总**（顶部「币种筛选」控制金额合计）；"
    "④ 库存月数/开票率/支持度占比为无量纲比率，跨币种可比；"
    "⑤ 库存健康评分=基于总库存月数的经验规则（3–6 月满分），供排序参考非精算。与 NEWNESS / 品牌表现分析 / SELL IN 深度 页共用同一密码(Max12345)。"
)
