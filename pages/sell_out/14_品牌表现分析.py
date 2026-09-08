# -*- coding: utf-8 -*-
"""
品牌表现分析 v1.0（SELL OUT 销售端）
====================================
用途: 在「SELL OUT」模块下，分析各个品牌的市场与销售表现。
      - 优先维度: 海南离岛免税 + 机场/航班免税（按用户要求）
      - 兜底维度: 国内有税（口岸/边境）市场
数据来源: 桌面知识库《01零售报表-品牌合计总表_6.2026.xlsx》（本地文件，不上云）

两张核心工作表:
  1) 26vs25  —— 当前品牌表现（2025 YTM vs 2026 YTM + 逐月），含「所有店铺」总盘段
  2) database —— 2019–2020 历史子集（品牌 × 门店 × 月），门店名含市场/渠道信息

说明（数据口径）:
  - 26vs25 的「所有店铺」段 = 品牌零售总盘，是当前最完整、最新的品牌表现数据
  - 26vs25 还有 3 个「未命名」分段（品牌组合不同），源表未标注市场名；本页暂以
    「总盘」为主，市场拆分改用 database 表的门店名归类（见 Tab2）
  - database 仅 7 个品牌、2019–2020，作为「历史市场结构」补充视角

用法: 本文件由 Streamlit 多页 app 自动加载（见 utils/nav_meta.py）。
密码保护: 页面入口加密码门，与「2026 NEWNESS」页共用同一密码(Max12345)与同一套
      utils.newness_crypto 校验逻辑；未解锁时 st.stop()，解锁后正常渲染。
"""

import streamlit as st
import pandas as pd
import numpy as np
import warnings
import base64
import os
import plotly.express as px
import plotly.graph_objects as go
from utils.newness_crypto import decrypt_data
from utils.oss_helper import read_kb_excel, kb_available, KB_OSS_KEY_BRAND, KB_LOCAL_BRAND   # 与 NEWNESS 页共用同一加密/密码(Max12345)

warnings.filterwarnings("ignore")

# 桌面知识库里的品牌零售总表（本地路径，符合「本地优先、不上云」偏好）
KB_FILE = r"C:\Users\Maximinuszhang\Desktop\WorkBuddy\知识库\01零售报表-品牌合计总表_6.2026.xlsx"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# 知识库（OSS 优先）守卫在下方数据加载处用 kb_available 统一处理，此处不再做本地路径守卫。


# ============================================================
# 0) 密码门（与「2026 NEWNESS」页共用同一密码 & 同一套 crypto）
# ============================================================
# 内嵌一段用 Max12345 加密的校验串；解锁时 decrypt 成功即代表密码正确。
# 与 NEWNESS 页完全一致：PBKDF2+XOR，密码 Max12345（由负责人掌握，不写死语义）。
EMBEDDED_TOKEN = (
    "TkVXMT+unCbW9CIFN9b0bBNK7Fyv6bwJpA/K4WP5kQH1JvrIGS3NyFMr6jHWmIOmXwntik3cLQYIJRJH"
)

SESSION_AUTH = "brand_authed"
SESSION_ERR = "brand_err"


def _try_unlock():
    """用输入的密码解密内嵌校验串；失败给出友好提示。"""
    pw = st.session_state.get("brand_pw", "")
    if not pw:
        st.session_state[SESSION_ERR] = "请输入访问密码"
        return
    try:
        blob = base64.b64decode(EMBEDDED_TOKEN)
        decrypt_data(blob, pw)            # 密码错 -> PermissionError
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
            key="brand_pw",
            placeholder="请输入密码",
            label_visibility="collapsed",
            help="与 NEWNESS 页相同密码",
        )
        if st.button("🔓 解锁查看", type="primary", key="brand_unlock"):
            _try_unlock()
        if st.session_state.get(SESSION_ERR):
            st.error(st.session_state[SESSION_ERR])
    # 只有「仍未解锁」才停在此页；解锁成功后继续往下渲染（同一次运行内）
    if not st.session_state.get(SESSION_AUTH, False):
        st.stop()

# 已解锁：提供重新上锁按钮
if st.sidebar.button("🔒 重新上锁", key="brand_relock"):
    st.session_state[SESSION_AUTH] = False
    st.session_state[SESSION_ERR] = ""
    st.rerun()


# 知识库数据守卫：优先私有 OSS（本地 / Streamlit Cloud 均可读），其次本地文件。
if not kb_available(oss_key=KB_OSS_KEY_BRAND, local_path=KB_LOCAL_BRAND):
    st.error(
        "⚠️ 未能加载知识库数据（品牌合计总表）。\n\n"
        "数据存放于您自有阿里云 OSS（私有），本地与云端 App 均凭密钥读取；"
        "若两端都不可达，请确认本地知识库文件存在，或 OSS 密钥已在 Streamlit Cloud Secrets 中配置。"
    )
    st.stop()

# ============================================================
# 1) 数据加载
# ============================================================

@st.cache_data
def load_brand_yoy():
    """读取 26vs25 的「所有店铺」总盘段，返回品牌级 2025/2026 YTM + 逐月。

    返回:
        df       : DataFrame[品牌, y25, y26, yoy, 月序列...]
        months25 : dict 品牌 -> [12个2025月值]
        months26 : dict 品牌 -> [12个2026月值]
    """
    raw = read_kb_excel(sheet_name="26vs25", header=None,
                        oss_key=KB_OSS_KEY_BRAND, local_path=KB_LOCAL_BRAND)

    # 找到「所有店铺」标题行
    r0 = None
    for r in range(min(20, len(raw))):
        if str(raw.iloc[r, 0]).strip() == "所有店铺":
            r0 = r
            break
    if r0 is None:
        return pd.DataFrame(), {}, {}

    # 行0 的月份标签列 -> 2025 在 c、2026 在 c+1
    month_col = {}
    for c in range(raw.shape[1]):
        v = raw.iloc[0, c]
        if isinstance(v, str) and v.strip() in MONTHS:
            month_col[v.strip()] = c

    # 品牌行: 从 r0+2 开始（跳过标题行与 TTL 行），直到 col0 为空
    rows = []
    m25, m26 = {}, {}
    r = r0 + 2
    while r < len(raw) and pd.notna(raw.iloc[r, 0]):
        name = str(raw.iloc[r, 0]).strip()
        if name == "TTL":
            r += 1
            continue
        y25 = raw.iloc[r, 1]
        y26 = raw.iloc[r, 2]
        yoy = raw.iloc[r, 3]
        s25 = [raw.iloc[r, month_col[m]] for m in MONTHS]
        s26 = [raw.iloc[r, month_col[m] + 1] for m in MONTHS]
        rows.append({"品牌": name, "y25": y25, "y26": y26, "yoy": yoy})
        m25[name] = s25
        m26[name] = s26
        r += 1

    df = pd.DataFrame(rows)
    # 数值化（部分可能是字符串/NaN）
    for col in ["y25", "y26", "yoy"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["y26"]).reset_index(drop=True)
    return df, m25, m26


@st.cache_data
def load_market_data():
    """读取 database 表，按门店名归类为市场，返回 品牌×市场 销售额（2019–2020 合计）。

    返回:
        long : DataFrame[品牌, 市场, 销售额]
        brands_in_db : database 中出现的品牌列表
    """
    db = read_kb_excel(sheet_name="database", header=0,
                       oss_key=KB_OSS_KEY_BRAND, local_path=KB_LOCAL_BRAND,
                       usecols=["Stores", "品牌", "销售金额"])
    db["销售金额"] = pd.to_numeric(db["销售金额"], errors="coerce")
    db = db.dropna(subset=["销售金额", "品牌"])
    db["市场"] = db["Stores"].apply(classify_market)
    long = (db.groupby(["品牌", "市场"])["销售金额"].sum()
              .reset_index().rename(columns={"销售金额": "销售额"}))
    return long, sorted(db["品牌"].dropna().unique().tolist())


def classify_market(store):
    """按门店名启发式归类市场（估算归类，非官方字段）。"""
    s = str(store).strip().lower()
    # 海南离岛免税（含海南的机场店/市内店/提货点）
    if any(k in s for k in ["sanya", "haikou", "boao", "hainan", "hu海南"]):
        return "海南离岛免税"
    # 机场 / 航班 / 邮轮 免税
    if any(k in s for k in [" ap", "airport", "arrival", "departure",
                              "airline", "国航", "南航", "东航", "spring",
                              "cruise", "costa"]):
        return "机场/航班免税"
    # 口岸 / 边境（国内有税为主）
    if any(k in s for k in ["heihe", "suifenhe", "manzhouli", "lo wu", "lok ma",
                              "hung hom", "zhuhai", "ruili", "hekou", "hunchun",
                              "dongning", "fangcheng", "daluo", "mengding",
                              "wanding", "tengchong", "raohe", "tongjiang",
                              "mishan", "fuyuan", "luobei", "erlian",
                              "ganqimaodu", "dongwujiayu", "nansan", "weihai",
                              "bian"]):
        return "口岸/边境(国内有税)"
    return "其他市内/内地"


# ============================================================
# 2) 页面主体
# ============================================================

st.title("🏷️ 品牌表现分析 v1.0")
st.caption("SELL OUT · 数据来源：零售报表-品牌合计总表(6.2026) ｜ 本地知识库，不上云 ｜ 🔒 密码保护与 NEWNESS 页一致")

df, months25, months26 = load_brand_yoy()

if df.empty:
    st.error("未能从 26vs25 工作表解析出「所有店铺」品牌段，请检查源文件。")
    st.stop()

# 排序指标：以 2026 YTM 为销售规模代理
df_sorted = df.sort_values("y26", ascending=False).reset_index(drop=True)
df_sorted["排名"] = df_sorted.index + 1
total_26 = df_sorted["y26"].sum()
df_sorted["占大盘%"] = (df_sorted["y26"] / total_26 * 100).round(1)

# ---------- Tab 1: 品牌总盘表现 ----------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 品牌总盘表现 (2025→2026)",
    "🌏 市场维度 (海南+机场优先)",
    "🔥 竞争格局与集中度",
    "📅 月度节奏与动能",
])

with tab1:
    st.subheader("① 品牌销售表现总览（2026 YTM 降序）")
    st.markdown("指标说明：**YTM**=年初至今累计；**YOY**=2026 vs 2025 同比增长率；"
                "**占大盘%**=该品牌 2026 销售额占全部品牌比重。")

    view_n = st.number_input("展示品牌数量（Top N）", min_value=5, max_value=len(df_sorted),
                             value=min(15, len(df_sorted)), step=1)
    show = df_sorted.head(view_n)

    st.dataframe(
        show[["排名", "品牌", "y25", "y26", "yoy", "占大盘%"]].rename(columns={
            "y25": "2025 YTM", "y26": "2026 YTM", "yoy": "YOY"
        }).style.format({
            "2025 YTM": "{:,.0f}", "2026 YTM": "{:,.0f}",
            "YOY": "{:.1%}", "占大盘%": "{:.1f}%"
        }).background_gradient(subset=["YOY"], cmap="RdYlGn"),
        use_container_width=True,
        column_config={"YOY": st.column_config.NumberColumn("YOY", format="%.1%")},
    )

    st.subheader("② 2026 销售额排行（Top / Bottom）")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**增长最快 Top 5**（按 YOY）")
        top_g = df_sorted.sort_values("yoy", ascending=False).head(5)
        st.dataframe(top_g[["品牌", "y26", "yoy"]].rename(columns={"y26": "2026 YTM", "yoy": "YOY"})
                     .style.format({"2026 YTM": "{:,.0f}", "YOY": "{:.1%}"}),
                     use_container_width=True)
    with c2:
        st.markdown("**下滑最多 Bottom 5**（按 YOY）")
        bot_g = df_sorted.sort_values("yoy", ascending=True).head(5)
        st.dataframe(bot_g[["品牌", "y26", "yoy"]].rename(columns={"y26": "2026 YTM", "yoy": "YOY"})
                     .style.format({"2026 YTM": "{:,.0f}", "YOY": "{:.1%}"}),
                     use_container_width=True)

    st.subheader("③ BCG 矩阵：销售规模 × 增速")
    st.markdown("横轴=2026 销售额（规模），纵轴=YOY 增速；中位线分四象限："
                "🌟明星(高销高增) / 💰现金牛(高销低增) / 💡问题(低销高增) / ⚠️瘦狗(低销低增)。")

    med_sales = df_sorted["y26"].median()
    med_growth = df_sorted["yoy"].median()

    def _quad(row):
        hi_s = row["y26"] >= med_sales
        hi_g = row["yoy"] >= med_growth
        if hi_s and hi_g:
            return "🌟明星"
        if hi_s and not hi_g:
            return "💰现金牛"
        if not hi_s and hi_g:
            return "💡问题"
        return "⚠️瘦狗"

    bcg = df_sorted.copy()
    bcg["象限"] = bcg.apply(_quad, axis=1)
    # 先按 2026 销售额降序排序，再重命名列（避免重命名后列名找不到）
    bcg_show = (bcg[["品牌", "y26", "yoy", "象限"]]
                .sort_values("y26", ascending=False)
                .rename(columns={"y26": "2026 YTM", "yoy": "YOY"}))
    st.dataframe(
        bcg_show.style.format({"2026 YTM": "{:,.0f}", "YOY": "{:.1%}"}),
        use_container_width=True,
    )
    # 散点图（用 streamlit 原生 chart，无需额外依赖）
    chart_df = df_sorted[["品牌", "y26", "yoy"]].rename(columns={"y26": "2026销售额", "yoy": "YOY增速"})
    st.scatter_chart(chart_df.set_index("品牌"), x="2026销售额", y="YOY增速")

    st.subheader("④ 单品牌月度趋势（2025 vs 2026）")
    pick = st.selectbox("选择品牌查看月度走势", options=df_sorted["品牌"].tolist())
    if pick:
        ts = pd.DataFrame({
            "月份": MONTHS,
            "2025": [pd.to_numeric(v, errors="coerce") for v in months25.get(pick, [0] * 12)],
            "2026": [pd.to_numeric(v, errors="coerce") for v in months26.get(pick, [0] * 12)],
        }).set_index("月份")
        st.line_chart(ts)

    # ⑤ 增长贡献瀑布图：谁在拉动大盘、谁在拖累
    st.subheader("⑤ 大盘增长贡献分解（瀑布图）")
    st.markdown("每个品牌对**大盘净增长**（2026−2025）的贡献 = 品牌销售额变化量。"
                "绿色=拉动增长，红色=拖累大盘；按贡献绝对值排序，只展示主要品牌。")

    _contrib = df_sorted.copy()
    _contrib["delta"] = _contrib["y26"] - _contrib["y25"]
    _contrib = _contrib.dropna(subset=["delta"]).sort_values("delta", key=abs, ascending=False)
    total_delta = _contrib["delta"].sum()

    n_show = min(12, len(_contrib))
    head = _contrib.head(n_show)
    others_delta = _contrib.iloc[n_show:]["delta"].sum() if len(_contrib) > n_show else 0
    if len(_contrib) > n_show:
        head = pd.concat([head, pd.DataFrame([{
            "品牌": f"其他{len(_contrib)-n_show}个品牌", "delta": others_delta, "y26": np.nan, "yoy": np.nan}])],
            ignore_index=True)

    wf_labels = head["品牌"].tolist() + ["**2026 净变化**"]
    wf_values = head["delta"].tolist() + [total_delta]
    fig_wf = go.Figure(go.Waterfall(
        orientation="v",
        measure=["relative"] * len(head) + ["total"],
        x=wf_labels, y=wf_values,
        text=[f"{v:+,.0f}" for v in wf_values],
        textposition="outside",
        connector={"line": {"color": "#bdc3c7"}},
        increasing={"marker": {"color": "#2ecc71"}},
        decreasing={"marker": {"color": "#e74c3c"}},
        totals={"marker": {"color": "#34495e"}},
    ))
    fig_wf.update_layout(
        height=460, template="plotly_white",
        yaxis_title="销售额变化量", xaxis_tickangle=-30,
        title=f"2025 → 2026 大盘净增长 {total_delta:+,.0f} 的品牌贡献分解",
    )
    st.plotly_chart(fig_wf, use_container_width=True)

# ---------- Tab 2: 市场维度 ----------
with tab2:
    st.subheader("市场结构（海南 + 机场 + 国内有税 优先视角）")
    st.markdown("数据来自 `database` 表（2019–2020 历史子集，仅 7 品牌），"
                "按**门店名启发式归类**为 4 类市场。此视角用于补足「各品牌市场分布」，"
                "口径较旧，仅作结构参考。")
    long, db_brands = load_market_data()

    if long.empty:
        st.warning("database 表无可用市场数据。")
    else:
        # 市场汇总
        mkt = (long.groupby("市场")["销售额"].sum().sort_values(ascending=False)
               .reset_index())
        mkt["占比%"] = (mkt["销售额"] / mkt["销售额"].sum() * 100).round(1)
        st.markdown("**各市场销售额合计与占比**")
        st.dataframe(mkt.style.format({"销售额": "{:,.0f}", "占比%": "{:.1f}%"})
                     .background_gradient(subset=["占比%"], cmap="Blues"),
                     use_container_width=True)
        st.bar_chart(mkt.set_index("市场")["销售额"])

        # 各市场 Top 品牌
        st.markdown("**各市场 Top 品牌**（按销售额）")
        for m in mkt["市场"].tolist():
            sub = (long[long["市场"] == m].sort_values("销售额", ascending=False)
                   .head(5).reset_index(drop=True))
            st.markdown(f"**{m}**")
            st.dataframe(sub.rename(columns={"销售额": "销售额(2019-2020累计)"})
                         .style.format({"销售额(2019-2020累计)": "{:,.0f}"}),
                         use_container_width=True)

        # 品牌 × 市场 透视
        st.markdown("**品牌 × 市场 销售额透视**（历史子集）")
        pivot = long.pivot_table(index="品牌", columns="市场", values="销售额",
                                 aggfunc="sum", fill_value=0)
        pivot["合计"] = pivot.sum(axis=1)
        pivot = pivot.sort_values("合计", ascending=False)
        st.dataframe(pivot.style.format("{:,.0f}").background_gradient(cmap="Greens"),
                     use_container_width=True)

# ---------- Tab 3: 竞争格局与集中度 ----------
with tab3:
    st.subheader("① 市场集中度指标（2025 vs 2026）")
    st.markdown("**CR3/CR5** = 前 3/5 大品牌合计份额；**HHI** = 各品牌份额平方和 ×10000"
                "（<1500 竞争型 / 1500–2500 中度集中 / >2500 高度集中）。集中度上升=大盘向头部收敛。")

    def _concentration(vals):
        s = pd.Series(vals).dropna()
        s = s[s > 0]
        tot = s.sum()
        if tot <= 0 or len(s) == 0:
            return None
        share = s / tot
        return dict(cr3=share.nlargest(3).sum(), cr5=share.nlargest(5).sum(),
                    cr10=share.nlargest(10).sum(), hhi=(share ** 2).sum() * 10000)

    c25, c26 = _concentration(df["y25"]), _concentration(df["y26"])
    if c25 and c26:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("CR3 前三品牌份额", f"{c26['cr3']:.1%}", f"{(c26['cr3']-c25['cr3'])*100:+.1f}pp")
        m2.metric("CR5 前五品牌份额", f"{c26['cr5']:.1%}", f"{(c26['cr5']-c25['cr5'])*100:+.1f}pp")
        m3.metric("HHI 集中度指数", f"{c26['hhi']:,.0f}",
                  f"{c26['hhi']-c25['hhi']:+,.0f}",
                  delta_color="inverse")  # HHI 上升是集中，标红
        lvl = "高度集中" if c26["hhi"] > 2500 else ("中度集中" if c26["hhi"] > 1500 else "竞争型")
        m4.metric("2026 格局判定", lvl, f"品牌数 {int((df['y26']>0).sum())}")

    st.markdown("---")
    st.subheader("② 市场份额变化（谁在抢份额）")
    st.markdown("份额变化 = 2026 份额 − 2025 份额（百分点 pp）。绿色=份额提升（进攻者），红色=份额下滑（防守者）。")

    sh = df_sorted.copy()
    tot25, tot26 = sh["y25"].sum(), sh["y26"].sum()
    sh["share25"] = sh["y25"] / tot25 * 100
    sh["share26"] = sh["y26"] / tot26 * 100
    sh["share_delta_pp"] = sh["share26"] - sh["share25"]
    sh = sh.dropna(subset=["share_delta_pp"]).sort_values("share_delta_pp")

    top_n_share = sh.tail(15)  # 前15个份额变化最大的品牌
    colors = ["#e74c3c" if v < 0 else "#2ecc71" for v in top_n_share["share_delta_pp"]]
    fig_sh = go.Figure(go.Bar(
        x=top_n_share["share_delta_pp"], y=top_n_share["品牌"], orientation="h",
        marker_color=colors,
        text=[f"{v:+.2f}pp" for v in top_n_share["share_delta_pp"]],
        textposition="outside",
    ))
    fig_sh.update_layout(height=max(420, len(top_n_share) * 28), template="plotly_white",
                         xaxis_title="份额变化 (pp)", yaxis_title="")
    st.plotly_chart(fig_sh, use_container_width=True)

    st.markdown("---")
    st.subheader("③ 品牌销售 Pareto（80/20 检验）")
    st.markdown("柱=各品牌 2026 销售额（降序），线=累计份额。虚线 80% 线与交叉点"
                "揭示『几个品牌撑起 80% 大盘』。")

    par = df_sorted.dropna(subset=["y26"]).copy()
    par = par[par["y26"] > 0]
    par["cum_share"] = par["y26"].cumsum() / par["y26"].sum() * 100
    n80 = int((par["cum_share"] < 80).sum()) + 1
    fig_par = go.Figure()
    fig_par.add_bar(x=par["品牌"], y=par["y26"], marker_color="#3498db", name="2026 销售额",
                    text=[f"{v:,.0f}" for v in par["y26"]], textposition="outside")
    fig_par.add_scatter(x=par["品牌"], y=par["cum_share"], name="累计份额%",
                        yaxis="y2", mode="lines+markers", line=dict(color="#e67e22", width=2.5))
    fig_par.add_hline(y=80, line_dash="dot", line_color="#e74c3c", annotation_text="80%",
                      yref="y2")
    fig_par.update_layout(
        template="plotly_white", height=480, xaxis_tickangle=-35,
        yaxis=dict(title="销售额"),
        yaxis2=dict(title="累计份额%", overlaying="y", side="right", range=[0, 105]),
        title=f"前 {n80} 个品牌贡献 80% 大盘（共 {len(par)} 个品牌）",
    )
    st.plotly_chart(fig_par, use_container_width=True)

    st.markdown("---")
    st.subheader("④ 增长质量矩阵（规模 × 增速 × 趋势）")
    st.markdown("在 BCG 基础上加入**近期动能**（4–6月同比 vs 1–3月同比）：气泡大小=2026 销售额，"
                "颜色=动能变化（绿=二季度在加速，红=在减速）。")

    def _m_growth(brand, months_dict, m_list):
        vals = [pd.to_numeric(months_dict.get(brand, [None]*12)[MONTHS.index(m)], errors="coerce")
                if m in MONTHS else None for m in m_list]
        s = pd.Series(vals, index=m_list, dtype="float64")
        return s

    qual_rows = []
    for _, row in df_sorted.iterrows():
        b = row["品牌"]
        g_q1 = _m_growth(b, months25, MONTHS[0:3]).sum()
        g26_q1 = _m_growth(b, months26, MONTHS[0:3]).sum()
        g_q2 = _m_growth(b, months25, MONTHS[3:6]).sum()
        g26_q2 = _m_growth(b, months26, MONTHS[3:6]).sum()
        if g_q1 and g_q1 > 0 and g_q2 and g_q2 > 0 and pd.notna(row["yoy"]):
            qual_rows.append({
                "品牌": b, "y26": row["y26"], "yoy": row["yoy"],
                "g_q1": (g26_q1 / g_q1 - 1) * 100 if g_q1 > 0 else None,
                "g_q2": (g26_q2 / g_q2 - 1) * 100 if g_q2 > 0 else None,
            })
    qdf = pd.DataFrame(qual_rows).dropna()
    if not qdf.empty:
        qdf["momentum"] = qdf["g_q2"] - qdf["g_q1"]
        fig_q = px.scatter(
            qdf, x="y26", y="yoy", size="y26", color="momentum",
            color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
            hover_name="品牌",
            labels={"y26": "2026 销售额", "yoy": "总增速 YOY", "momentum": "Q2动能-Q1动能"},
        )
        fig_q.add_hline(y=qdf["yoy"].median(), line_dash="dot", line_color="#95a5a6")
        fig_q.add_vline(x=qdf["y26"].median(), line_dash="dot", line_color="#95a5a6")
        fig_q.update_layout(template="plotly_white", height=520,
                            title="气泡=2026销售额 ｜ 右上=明星(大且高增) ｜ 颜色绿=Q2在加速")
        st.plotly_chart(fig_q, use_container_width=True)
        st.caption(f"⚠️ 动能仅统计 1-6 月可同比的品牌（{len(qdf)} 个）；4-6月为最新已出月份。")
    else:
        st.info("当前数据无可比的 Q1/Q2 同期值，无法计算动能矩阵。")

# ---------- Tab 4: 月度节奏与动能 ----------
with tab4:
    st.subheader("① 品牌 × 月份 同比热力图（2026 vs 2025 同月）")
    st.markdown("每格 = 该品牌该月 2026/2025 同比增速。绿=正增长，红=负增长，灰=无同期数据。"
                "用于快速定位**哪些品牌在哪个月掉队/爆发**。")

    heat_rows = []
    for _, row in df_sorted.iterrows():
        b = row["品牌"]
        r = {"品牌": b}
        for i, m in enumerate(MONTHS):
            v25 = pd.to_numeric(months25.get(b, [None]*12)[i], errors="coerce")
            v26 = pd.to_numeric(months26.get(b, [None]*12)[i], errors="coerce")
            if pd.notna(v25) and pd.notna(v26) and v25 > 0:
                r[m] = (v26 / v25 - 1) * 100
            else:
                r[m] = np.nan
        heat_rows.append(r)
    hdf = pd.DataFrame(heat_rows).set_index("品牌")

    z = hdf.values
    fig_h = go.Figure(go.Heatmap(
        z=z, x=hdf.columns.tolist(), y=hdf.index.tolist(),
        colorscale="RdYlGn", zmid=0,
        text=np.where(np.isnan(z), "", np.vectorize(lambda v: f"{v:+.0f}%" if not np.isnan(v) else "")(z)),
        texttemplate="%{text}", textfont=dict(size=9),
        colorbar=dict(title="同比%"),
        xgap=1, ygap=1,
    ))
    fig_h.update_layout(template="plotly_white", height=max(560, len(hdf) * 22 + 160),
                        title="逐月同比增速热力图（按 2026 销售额降序）")
    st.plotly_chart(fig_h, use_container_width=True)

    st.markdown("---")
    st.subheader("② 大盘月度节奏（2025 vs 2026 + 同比）")
    mkt_ts = pd.DataFrame({
        "月份": MONTHS,
        "2025": [sum(pd.to_numeric(months25.get(b, [0]*12)[i], errors="coerce") or 0
                     for b in df_sorted["品牌"]) for i in range(12)],
        "2026": [sum(pd.to_numeric(months26.get(b, [0]*12)[i], errors="coerce") or 0
                     for b in df_sorted["品牌"]) for i in range(12)],
    })
    mkt_ts["同比%"] = np.where(mkt_ts["2025"] > 0,
                                (mkt_ts["2026"] / mkt_ts["2025"] - 1) * 100, np.nan)
    c_a, c_b = st.columns([3, 2])
    with c_a:
        fig_m = go.Figure()
        fig_m.add_bar(x=mkt_ts["月份"], y=mkt_ts["2025"], name="2025", marker_color="#95a5a6")
        fig_m.add_bar(x=mkt_ts["月份"], y=mkt_ts["2026"], name="2026", marker_color="#3498db")
        fig_m.update_layout(barmode="group", template="plotly_white", height=380,
                            yaxis_title="大盘销售额", title="大盘月度销售额对比")
        st.plotly_chart(fig_m, use_container_width=True)
    with c_b:
        fig_g = go.Figure(go.Bar(
            x=mkt_ts["月份"], y=mkt_ts["同比%"],
            marker_color=["#2ecc71" if (v is not np.nan and v >= 0) else "#e74c3c"
                          for v in mkt_ts["同比%"]],
            text=[f"{v:+.1f}%" if not np.isnan(v) else "" for v in mkt_ts["同比%"]],
            textposition="outside",
        ))
        fig_g.update_layout(template="plotly_white", height=380,
                            yaxis_title="同比%", title="大盘月度同比")
        st.plotly_chart(fig_g, use_container_width=True)

    st.markdown("---")
    st.subheader("③ 集中度逐月演变（CR5 走势）")
    st.markdown("逐月计算前 5 大品牌份额合计：曲线**上升**=月份越近越向头部集中，"
                "**下降**=长尾品牌在后期发力。")
    cr5_series = []
    for i, m in enumerate(MONTHS):
        vals = {}
        for b in df_sorted["品牌"]:
            v25 = pd.to_numeric(months25.get(b, [0]*12)[i], errors="coerce") or 0
            v26 = pd.to_numeric(months26.get(b, [0]*12)[i], errors="coerce") or 0
            vals[b] = v25 + v26  # 合并两年口径看结构
        s = pd.Series(vals)
        s = s[s > 0]
        if len(s) >= 5:
            cr5_series.append({"月份": m, "CR5%": s.nlargest(5).sum() / s.sum() * 100})
        else:
            cr5_series.append({"月份": m, "CR5%": np.nan})
    cr5df = pd.DataFrame(cr5_series)
    fig_cr5 = go.Figure(go.Scatter(
        x=cr5df["月份"], y=cr5df["CR5%"], mode="lines+markers",
        line=dict(color="#8e44ad", width=3),
        text=[f"{v:.1f}%" if not np.isnan(v) else "" for v in cr5df["CR5%"]],
    ))
    fig_cr5.update_layout(template="plotly_white", height=340,
                          yaxis_title="CR5 %", yaxis_range=[0, 100],
                          title="前五大品牌份额合计（2025+2026 合并口径）")
    st.plotly_chart(fig_cr5, use_container_width=True)

# ============================================================
# 3) 页脚：数据口径说明
# ============================================================
st.divider()
st.caption(
    "数据口径：① 品牌总盘表现 = 零售报表 26vs25「所有店铺」段（2025/2026 YTM + 逐月），品牌零售口径；"
    "② 市场维度 = database 表 2019–2020，门店名启发式归类为 海南离岛免税 / 机场·航班免税 / 口岸·边境(国内有税) / 其他市内·内地，"
    "归类依据门店名，属估算。源文件：桌面知识库《01零售报表-品牌合计总表_6.2026.xlsx》。"
    "⚠️ 26vs25 另有 3 个未命名分段（品牌组合不同），源表未标注市场名；若你知道它们分别对应"
    "海南/机场/国内有税，告知后本页可升级为「按市场切换」的精准视图。"
)
