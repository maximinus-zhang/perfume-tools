# -*- coding: utf-8 -*-
"""
SELL IN 深度分析 v2.0（重写·扩维·密码保护）
=======================================
在 v1 基础上，用足知识库工作簿里之前完全没碰的维度，覆盖六大分析主题。
数据来源: 桌面知识库《2025 TR YTD Oct Sell in & Purchase. BE. 2026 Projection.xlsx》
用到的工作表:
  - `2026 Act+Rolling Fcst` : 逐月 2025实际 / 2026预算 / 2026实际+滚动预测 + MTD/YTM 达成率 + 品牌组 + 品类
  - `sell in` / `sell in R2` / `sell in RMB` : 同结构异数值，用于口径与修订对比
  - `2026 GBB SELL IN` : 按品牌组 × 零售商 × 季度 的渠道 SELL IN
  - `2026 Budget 9.25 … R1 / 2026 Budget_v1` : 2026 计划的多次迭代，用于预测演进
密码保护: 与 NEWNESS / 品牌表现分析 / 采购深度分析 页共用同一密码(Max12345)与 utils.newness_crypto。
"""
import streamlit as st
import pandas as pd
import numpy as np
import warnings
import base64
import os
from utils.newness_crypto import decrypt_data

warnings.filterwarnings("ignore")

KB_FILE = r"C:\Users\Maximinuszhang\Desktop\WorkBuddy\知识库\2025 TR YTD Oct Sell in & Purchase. BE. 2026 Projection.xlsx"
MONTHS = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]

# 本地知识库守卫：云端(Streamlit Cloud, Linux)无本机桌面文件，按「数据不上云」策略不读取本地文件。
# 文件缺失时给出友好提示并优雅停止，避免原始 traceback。本地有文件则完全不受影响。
if not os.path.exists(KB_FILE):
    st.error(
        "⚠️ 未检测到本地知识库文件，本页无法在云端加载数据。\n\n"
        f"期望路径：{KB_FILE}\n\n"
        "该页面依赖您本机桌面「知识库」中的零售报表。遵循「数据不上云」策略，"
        "云端部署不读取本地文件。请在本机 / 本地环境运行此页查看完整数据。"
    )
    st.stop()

# ===================== 密码门（同 NEWNESS / 品牌页 / 采购页） =====================
EMBEDDED_TOKEN = (
    "TkVXMT+unCbW9CIFN9b0bBNK7Fyv6bwJpA/K4WP5kQH1JvrIGS3NyFMr6jHWmIOmXwntik3cLQYIJRJH"
)
SESSION_AUTH = "sellin_authed"
SESSION_ERR = "sellin_err"


def _try_unlock():
    pw = st.session_state.get("sellin_pw", "")
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
            key="sellin_pw",
            placeholder="请输入密码",
            label_visibility="collapsed",
            help="与 NEWNESS 页相同密码",
        )
        if st.button("🔓 解锁查看", type="primary", key="sellin_unlock"):
            _try_unlock()
        if st.session_state.get(SESSION_ERR):
            st.error(st.session_state[SESSION_ERR])
    if not st.session_state.get(SESSION_AUTH, False):
        st.stop()

if st.sidebar.button("🔒 重新上锁", key="sellin_relock"):
    st.session_state[SESSION_AUTH] = False
    st.session_state[SESSION_ERR] = ""
    st.rerun()


# ===================== 数据加载 =====================
@st.cache_data
def load_act_fcst():
    """解析 `2026 Act+Rolling Fcst`：逐月三套序列 + MTD/YTM 达成率。
    表头在第 2 行(0-based=1)；品牌数据第 3 行起。
    """
    raw = pd.read_excel(KB_FILE, sheet_name="2026 Act+Rolling Fcst", engine="openpyxl", header=None)
    HDR = 1
    rows = []
    for r in range(HDR + 1, len(raw)):
        brand = raw.iloc[r, 2]   # 品牌名称（管报）
        if pd.isna(brand):
            continue
        b = str(brand).strip()
        if b in {"", "None", "nan"} or b.upper() in {"TOTAL", "TTL", "GRAND TOTAL", "合计"}:
            continue
        def col(c):
            return raw.iloc[r, c]
        rows.append({
            "品牌组": (str(raw.iloc[r, 1]).strip() if not pd.isna(raw.iloc[r, 1]) else ""),
            "管报品牌": b,
            "品类": (str(raw.iloc[r, 3]).strip() if not pd.isna(raw.iloc[r, 3]) else ""),
            "品牌": (str(raw.iloc[r, 4]).strip() if not pd.isna(raw.iloc[r, 4]) else b),
            # 2025 实际逐月 21..32
            "a25": [col(c) for c in range(21, 33)],
            # 2026 预算逐月 6..17
            "b26": [col(c) for c in range(6, 18)],
            # 2026 实际+预测逐月 36..47
            "f26": [col(c) for c in range(36, 48)],
            "FY2025": col(34),
            "FY2026_bgt": col(19),
            "FY2026_af": col(49),
            "MTD_act": col(51), "MTD_bgt": col(52), "MTD_gap": col(53), "MTD_ach": col(54),
            "YTM_act": col(56), "YTM_bgt": col(57), "YTM_gap": col(58), "YTM_ach": col(59),
        })
    return pd.DataFrame(rows)


@st.cache_data
def load_sellin_variant(sheet, hdr=2, brand_col=4, prin_col=2):
    """通用解析 sell in / sell in R2 / sell in RMB（同结构）。"""
    raw = pd.read_excel(KB_FILE, sheet_name=sheet, engine="openpyxl", header=None)
    rows = []
    for r in range(hdr + 1, len(raw)):
        brand = raw.iloc[r, brand_col]
        if pd.isna(brand):
            continue
        b = str(brand).strip()
        if b.upper() in {"TTL", "TOTAL", "NAN", ""} or "合计" in b or "TOTAL" in b.upper():
            continue
        rows.append({
            "Brand": b,
            "Principal": (str(raw.iloc[r, prin_col]).strip() if not pd.isna(raw.iloc[r, prin_col]) else ""),
            "FY2024": raw.iloc[r, 7],
            "Budget2025": raw.iloc[r, 8],
            "YTD2025": raw.iloc[r, 13],
            "BE2025": raw.iloc[r, 15],
            "Achieve": raw.iloc[r, 18],
            "Proj2026": raw.iloc[r, 20],
            "G26v25BE": raw.iloc[r, 21],
        })
    df = pd.DataFrame(rows)
    for c in ["FY2024", "Budget2025", "YTD2025", "BE2025", "Achieve", "Proj2026", "G26v25BE"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["FY2024", "BE2025", "Proj2026"], how="all")
    # 用品牌名主名(去序号)做对齐键
    df["key"] = df["Brand"].str.replace(r"^\d+\.\s*", "", regex=True).str.strip()
    return df


@st.cache_data
def load_gbb():
    """解析 `2026 GBB SELL IN`：按品牌组分块，零售商 × 季度。"""
    raw = pd.read_excel(KB_FILE, sheet_name="2026 GBB SELL IN", engine="openpyxl", header=None)
    blocks = []
    r = 0
    while r < len(raw):
        # 块头行：col1 == 'Q1'
        if str(raw.iloc[r, 1]).strip().upper() == "Q1":
            bg = str(raw.iloc[r, 0]).strip()   # 品牌组（Tommy / Turssardi）
            r += 1
            while r < len(raw):
                lab = raw.iloc[r, 0]
                if pd.isna(lab):
                    r += 1
                    continue
                lab = str(lab).strip()
                if lab.upper() in {"TOTAL", "TTL", "GRAND TOTAL", "合计"}:
                    break
                if str(raw.iloc[r, 1]).strip().upper() == "Q1":   # 下一个块
                    break
                try:
                    blocks.append({
                        "品牌组": bg,
                        "零售商": lab,
                        "Q1": float(raw.iloc[r, 1]), "Q2": float(raw.iloc[r, 2]),
                        "Q3": float(raw.iloc[r, 3]), "Q4": float(raw.iloc[r, 4]),
                        "Total": float(raw.iloc[r, 5]),
                    })
                except (ValueError, TypeError):
                    pass
                r += 1
            continue
        r += 1
    return pd.DataFrame(blocks)


@st.cache_data
def load_budget_evolution():
    """解析全部 `2026 Budget*` 版本，提取每个版本的 2026 计划总额与品牌数。
    稳健做法：优先用逐月 2026 列(202601..202612)求和；否则用年度 2026 列。
    返回 DataFrame[版本, 2026计划总额, 品牌数]，按版本日期排序。
    注意：各版本统计口径/品牌范围可能不同（如 R1 为全口径锁定版），绝对额不可直接横比。
    """
    import re
    xl = pd.ExcelFile(KB_FILE, engine="openpyxl")
    vers = [s for s in xl.sheet_names if s.startswith("2026 Budget")]
    out = {}
    brand_count = {}
    for s in vers:
        try:
            raw = pd.read_excel(KB_FILE, sheet_name=s, engine="openpyxl", header=None)
            month_cols = []
            annual_col = None
            for rr in range(0, min(6, raw.shape[0])):
                for c in range(0, raw.shape[1]):
                    v = raw.iloc[rr, c]
                    if pd.isna(v):
                        continue
                    sv = str(v).replace(" ", "")
                    if sv in {str(m) for m in range(202601, 202613)}:
                        month_cols.append(c)
                    if "FY2026" in sv or "FY 2026" in sv or ("2026" in sv and "Budget" in sv and "Projection" not in sv):
                        if annual_col is None and "Projection" not in sv:
                            annual_col = c
            total = 0.0
            n = 0
            if month_cols:
                month_cols = sorted(set(month_cols))
                for rr in range(0, raw.shape[0]):
                    lab = raw.iloc[rr, 0]
                    if pd.notna(lab) and str(lab).strip().upper() in {"TOTAL", "TTL", "GRAND TOTAL", "合计"}:
                        continue
                    added = False
                    for c in month_cols:
                        val = raw.iloc[rr, c]
                        if pd.notna(val):
                            try:
                                total += float(val)
                                added = True
                            except (ValueError, TypeError):
                                pass
                    if added:
                        n += 1
                out[s] = total
                brand_count[s] = n
            elif annual_col is not None:
                for rr in range(0, raw.shape[0]):
                    lab = raw.iloc[rr, 0]
                    if pd.notna(lab) and str(lab).strip().upper() in {"TOTAL", "TTL", "GRAND TOTAL", "合计"}:
                        continue
                    val = raw.iloc[rr, annual_col]
                    if pd.notna(val):
                        try:
                            total += float(val)
                            n += 1
                        except (ValueError, TypeError):
                            pass
                out[s] = total
                brand_count[s] = n
        except Exception:
            continue

    def _key(name):
        m = re.findall(r"(\d{1,2})\.(\d{2})", name)
        if m:
            return (int(m[0][0]) * 100 + int(m[0][1]), name)
        if "v1" in name:
            return (0, name)
        if "R1" in name:
            return (99, name)
        return (50, name)

    ordered = dict(sorted(out.items(), key=lambda kv: _key(kv[0])))
    evo_df = pd.DataFrame({
        "版本": list(ordered.keys()),
        "2026计划总额": list(ordered.values()),
        "品牌数": [brand_count.get(s, 0) for s in ordered],
    })
    return evo_df


# ===================== 页面主体 =====================
st.title("SELL IN 深度分析 v2.0")
st.caption("SELL IN · 扩维多维度 · 数据来源：2025 TR YTD…Sell in & Purchase…xlsx（多工作表）"
           " ｜ 本地知识库，不上云 ｜ 密码保护与 NEWNESS / 品牌表现 / 采购深度 页一致")

af = load_act_fcst()
si = load_sellin_variant("sell in")
si_r2 = load_sellin_variant("sell in R2")
si_rmb = load_sellin_variant("sell in RMB")
gbb = load_gbb()
evo = load_budget_evolution()

if af.empty:
    st.error("未能解析 `2026 Act+Rolling Fcst`，请检查源文件。")
    st.stop()

# 把逐月序列转数值
for c in ["a25", "b26", "f26"]:
    af[c] = af[c].apply(lambda lst: [pd.to_numeric(x, errors="coerce") for x in lst])
af["FY2025"] = pd.to_numeric(af["FY2025"], errors="coerce")
af["FY2026_bgt"] = pd.to_numeric(af["FY2026_bgt"], errors="coerce")
af["FY2026_af"] = pd.to_numeric(af["FY2026_af"], errors="coerce")
for c in ["MTD_act", "MTD_bgt", "MTD_gap", "MTD_ach", "YTM_act", "YTM_bgt", "YTM_gap", "YTM_ach"]:
    af[c] = pd.to_numeric(af[c], errors="coerce")

# 组合合计（逐月）
port_a25 = [sum(x) for x in zip(*[[v for v in af["a25"].tolist()][i] for i in range(len(af))])] if False else None
def _month_sum(arr_series):
    acc = [0.0] * 12
    for lst in arr_series:
        for i, v in enumerate(lst):
            if pd.notna(v):
                acc[i] += float(v)
    return acc
port_a25 = _month_sum(af["a25"])
port_b26 = _month_sum(af["b26"])
port_f26 = _month_sum(af["f26"])

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 月度趋势与季节性", "🎯 达成率诊断", "🧩 品牌组/品类结构", "🔁 口径与修订对比", "🏬 渠道(GBB)", "📜 预测演进"
])

# ---------- Tab1: 月度趋势与季节性 ----------
with tab1:
    st.subheader("① 全组合逐月：2025 实际 vs 2026 预算 vs 2026 实际+预测")
    trend_df = pd.DataFrame({
        "月份": MONTHS,
        "2025实际": port_a25,
        "2026预算": port_b26,
        "2026实际+预测": port_f26,
    }).set_index("月份")
    st.line_chart(trend_df)
    c1, c2, c3 = st.columns(3)
    c1.metric("2025 实际 FY", f"{sum(port_a25):,.0f}")
    c2.metric("2026 预算 FY", f"{sum(port_b26):,.0f}")
    c3.metric("2026 实际+预测 FY", f"{sum(port_f26):,.0f}")

    st.subheader("② 单品牌月度下钻")
    pick = st.selectbox("选择品牌", options=af["管报品牌"].tolist(), key="t1_pick")
    if pick:
        row = af[af["管报品牌"] == pick].iloc[0]
        sd = pd.DataFrame({
            "月份": MONTHS,
            "2025实际": [v for v in row["a25"]],
            "2026预算": [v for v in row["b26"]],
            "2026实际+预测": [v for v in row["f26"]],
        }).set_index("月份")
        st.line_chart(sd)
        # 季节性：用 2026 实际+预测 的月度占比
        f26 = [v for v in row["f26"] if pd.notna(v)]
        if f26 and sum(f26) > 0:
            peak = MONTHS[int(np.argmax(f26))]
            st.caption(f"2026 实际+预测 峰值月：**{peak}**（占全年 {max(f26)/sum(f26)*100:.1f}%）；"
                       f"谷月：**{MONTHS[int(np.argmin(f26))]}**")

# ---------- Tab2: 达成率诊断 ----------
with tab2:
    st.subheader("① YTM 达成率排名（实际 vs 预算）")
    st.markdown("`YTM 达成率` = 2026 YTM 实际 / 2026 YTM 预算；>1 达标，<1 缺口。Gap = 实际−预算。")
    dd = af.dropna(subset=["YTM_ach"]).copy()
    dd = dd.sort_values("YTM_ach", ascending=False)
    dd_show = dd[["管报品牌", "品类", "品牌组", "YTM_act", "YTM_bgt", "YTM_gap", "YTM_ach",
                  "MTD_ach"]].rename(columns={
        "管报品牌": "品牌", "YTM_act": "YTM实际", "YTM_bgt": "YTM预算",
        "YTM_gap": "YTM Gap", "YTM_ach": "YTM达成率", "MTD_ach": "MTD达成率"})
    st.dataframe(
        dd_show.style.format({
            "YTM实际": "{:,.0f}", "YTM预算": "{:,.0f}", "YTM Gap": "{:,.0f}",
            "YTM达成率": "{:.1%}", "MTD达成率": "{:.1%}",
        }).background_gradient(subset=["YTM达成率"], cmap="RdYlGn"),
        use_container_width=True,
        column_config={
            "YTM达成率": st.column_config.NumberColumn("YTM达成率", format="%.1%"),
            "MTD达成率": st.column_config.NumberColumn("MTD达成率", format="%.1%"),
        },
    )

    st.subheader("② 缺口最大的品牌（YTM Gap 最小/最负 Top 8）")
    gap_sorted = af.dropna(subset=["YTM_gap"]).sort_values("YTM_gap")
    worst = gap_sorted.head(8)
    st.dataframe(
        worst[["管报品牌", "YTM_act", "YTM_bgt", "YTM_gap", "YTM_ach"]].rename(
            columns={"管报品牌": "品牌", "YTM_act": "YTM实际", "YTM_bgt": "YTM预算",
                     "YTM_gap": "YTM Gap", "YTM_ach": "YTM达成率"}
        ).style.format({"YTM实际": "{:,.0f}", "YTM预算": "{:,.0f}", "YTM Gap": "{:,.0f}",
                        "YTM达成率": "{:.1%}"}),
        use_container_width=True,
        column_config={"YTM达成率": st.column_config.NumberColumn("YTM达成率", format="%.1%")},
    )
    st.subheader("③ 达标 vs 缺口 概览")
    ok = (dd["YTM_ach"] >= 1).sum()
    st.markdown(f"YTM 达成率 ≥100% 的品牌：**{ok}** 个；<100% 的品牌：**{len(dd)-ok}** 个"
                f"（共 {len(dd)} 个有达成率数据的品牌）。")

# ---------- Tab3: 品牌组/品类结构 ----------
with tab3:
    st.subheader("① 按品类汇总（2026 实际+预测 FY）")
    by_cat = af.dropna(subset=["FY2026_af"]).groupby("品类").agg(
        品牌数=("管报品牌", "count"), FY2025=("FY2025", "sum"),
        FY2026_af=("FY2026_af", "sum")).reset_index()
    by_cat["占比"] = (by_cat["FY2026_af"] / by_cat["FY2026_af"].sum() * 100).round(1)
    by_cat["YoY"] = (by_cat["FY2026_af"] / by_cat["FY2025"] - 1)
    st.dataframe(by_cat.rename(columns={"品类": "品类", "FY2026_af": "2026实际+预测"})
                 .style.format({"FY2025": "{:,.0f}", "2026实际+预测": "{:,.0f}",
                                "占比": "{:.1f}%", "YoY": "{:.1%}"})
                 .background_gradient(subset=["占比"], cmap="Blues"), use_container_width=True)
    st.bar_chart(by_cat.set_index("品类")["FY2026_af"])

    st.subheader("② 按品牌组汇总")
    by_grp = af.dropna(subset=["FY2026_af"]).groupby("品牌组").agg(
        品牌数=("管报品牌", "count"), FY2025=("FY2025", "sum"),
        FY2026_af=("FY2026_af", "sum")).reset_index()
    by_grp["占比"] = (by_grp["FY2026_af"] / by_grp["FY2026_af"].sum() * 100).round(1)
    by_grp["YoY"] = (by_grp["FY2026_af"] / by_grp["FY2025"] - 1)
    st.dataframe(by_grp.rename(columns={"品牌组": "品牌组", "FY2026_af": "2026实际+预测"})
                 .style.format({"FY2025": "{:,.0f}", "2026实际+预测": "{:,.0f}",
                                "占比": "{:.1f}%", "YoY": "{:.1%}"})
                 .background_gradient(subset=["占比"], cmap="Blues"), use_container_width=True)

    st.subheader("③ 结构 mix：品类占比（2026 vs 2025）")
    mix = by_cat.set_index("品类")[["FY2025", "FY2026_af"]]
    mix_pct = mix.div(mix.sum(axis=0), axis=1) * 100
    st.dataframe(mix_pct.rename(columns={"FY2025": "2025占比%", "FY2026_af": "2026占比%"})
                 .style.format("{:.1f}%"), use_container_width=True)
    st.caption("占比变化反映结构 mix 漂移：某品类占比上升=该品类增长快于组合均值（量价/结构效应）。")

# ---------- Tab4: 口径与修订对比 ----------
with tab4:
    st.subheader("① 口径对比：sell in（管报） vs sell in RMB vs sell in R2")
    st.markdown("三张表结构相同但数值不同：`sell in`=管报快照、`sell in RMB`=RMB 口径、`sell in R2`=修订版 R2。"
                "按品牌主名对齐，对比 2025 BE 与 2026 预测的差异。")
    merged = si[["key", "Brand", "BE2025", "Proj2026"]].rename(
        columns={"BE2025": "BE2025_管报", "Proj2026": "Proj2026_管报"})
    for name, df in [("R2", si_r2), ("RMB", si_rmb)]:
        m = df[["key", "BE2025", "Proj2026"]].rename(
            columns={"BE2025": f"BE2025_{name}", "Proj2026": f"Proj2026_{name}"})
        merged = merged.merge(m, on="key", how="outer")
    merged = merged.dropna(subset=[c for c in merged.columns if c not in ("key", "Brand")], how="all")
    cmp = merged.head(30)
    st.dataframe(cmp.style.format({
        "BE2025_管报": "{:,.0f}", "Proj2026_管报": "{:,.0f}",
        "BE2025_R2": "{:,.0f}", "Proj2026_R2": "{:,.0f}",
        "BE2025_RMB": "{:,.0f}", "Proj2026_RMB": "{:,.0f}",
    }), use_container_width=True)
    st.caption("差异来源：R2 为修订后预估、RMB 为人民币口径，二者与管报 USD 不可直接等同；对比用于发现口径/修订漂移。")

# ---------- Tab5: 渠道(GBB) ----------
with tab5:
    if gbb.empty:
        st.warning("未能解析 `2026 GBB SELL IN`。")
    else:
        st.subheader("① 各品牌组 × 零售商 季度 SELL IN")
        for bg in gbb["品牌组"].unique():
            sub = gbb[gbb["品牌组"] == bg]
            st.markdown(f"**品牌组：{bg}**（合计 {sub['Total'].sum():,.0f}）")
            st.dataframe(sub[["零售商", "Q1", "Q2", "Q3", "Q4", "Total"]].rename(
                columns={"零售商": "零售商", "Q1": "Q1", "Q2": "Q2", "Q3": "Q3", "Q4": "Q4", "Total": "全年"}
            ).style.format({"Q1": "{:,.0f}", "Q2": "{:,.0f}", "Q3": "{:,.0f}",
                            "Q4": "{:,.0f}", "全年": "{:,.0f}"})
            .background_gradient(subset=["全年"], cmap="OrRd"), use_container_width=True)
        st.subheader("② 渠道集中度（按零售商全年合计）")
        ch = gbb.groupby("零售商")["Total"].sum().sort_values(ascending=False).reset_index()
        ch["占比"] = (ch["Total"] / ch["Total"].sum() * 100).round(1)
        st.dataframe(ch.rename(columns={"零售商": "零售商", "Total": "全年SELL IN"})
                     .style.format({"全年SELL IN": "{:,.0f}", "占比": "{:.1f}%"})
                     .background_gradient(subset=["占比"], cmap="Blues"), use_container_width=True)
        st.bar_chart(ch.set_index("零售商")["Total"])

# ---------- Tab6: 预测演进 ----------
with tab6:
    st.subheader("① 2026 计划总额演进（各预算版本快照）")
    st.caption("注：工作簿含 10 个 `2026 Budget*` 版本，但仅纳入**含 2026 计划数（逐月或年度）**的版本；"
               "早期版本若仅含「2026 Projection」或结构不同，未纳入，以免混入不可比口径。")
    if evo is None or evo.empty:
        st.warning("未能解析任何预算版本。")
    else:
        evo2 = evo.copy()
        evo2["环比变化"] = evo2["2026计划总额"].pct_change()
        st.line_chart(evo2.set_index("版本")["2026计划总额"])
        st.dataframe(evo2.style.format({
            "2026计划总额": "{:,.0f}", "品牌数": "{:.0f}", "环比变化": "{:.1%}"}), use_container_width=True)
        # 口径可比性判断：若各版本品牌数差异过大，绝对额不可横比
        nb = evo2["品牌数"]
        comparable = (nb.max() <= nb.min() * 1.5) if nb.min() > 0 else False
        if comparable:
            first_v = evo2["2026计划总额"].iloc[0]
            last_v = evo2["2026计划总额"].iloc[-1]
            if first_v:
                st.caption(f"各版本品牌数接近（{int(nb.min())}–{int(nb.max())}），口径基本可比；"
                           f"从首版到最新版 2026 计划总额变动 **{(last_v/first_v-1)*100:+.1f}%**"
                           f"（{first_v:,.0f} → {last_v:,.0f}）。")
        else:
            st.warning("⚠️ 各预算版本品牌范围/口径不一致（品牌数 "
                       f"{int(nb.min())}–{int(nb.max())}），**绝对额不可直接横比**，"
                       "下表仅展示各版本计划总额的方向性变化，精确可比需按共同品牌集合重算。")

# ===================== 页脚 =====================
st.divider()
st.caption(
    "数据口径：① 本页综合知识库《2025 TR YTD Oct Sell in & Purchase. BE. 2026 Projection.xlsx》多张工作表；"
    "② `2026 Act+Rolling Fcst` 提供逐月 2025实际/2026预算/2026实际+预测 与 MTD/YTM 达成率（管报口径）；"
    "③ `sell in` / `sell in R2` / `sell in RMB` 为同结构异数值的口径与修订快照；"
    "④ `2026 GBB SELL IN` 为按品牌组×零售商×季度的渠道 SELL IN；"
    "⑤ `2026 Budget*` 共 10 个版本用于预测演进轨迹；"
    "⑥ 金额单位以源表为准（管报口径），跨口径(USD/RMB)对比仅看差异方向、不混算。与 NEWNESS / 品牌表现分析 / 采购深度 页共用同一密码(Max12345)。"
)
