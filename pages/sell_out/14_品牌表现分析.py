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
from utils.newness_crypto import decrypt_data   # 与 NEWNESS 页共用同一加密/密码(Max12345)

warnings.filterwarnings("ignore")

# 桌面知识库里的品牌零售总表（本地路径，符合「本地优先、不上云」偏好）
KB_FILE = r"C:\Users\Maximinuszhang\Desktop\WorkBuddy\知识库\01零售报表-品牌合计总表_6.2026.xlsx"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


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
    raw = pd.read_excel(KB_FILE, sheet_name="26vs25", engine="openpyxl", header=None)

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
    db = pd.read_excel(KB_FILE, sheet_name="database", engine="openpyxl",
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
tab1, tab2 = st.tabs(["📊 品牌总盘表现 (2025→2026)", "🌏 市场维度 (海南+机场优先)"])

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
