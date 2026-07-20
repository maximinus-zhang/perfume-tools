# pages/sell_out/6_海南免税市场分析.py
# ============================================================
# 海南免税市场分析（真实公开数据版）
# 优化于 2026-07-20 —— 派派
#
# 改了什么（相对旧版）：
#   1. 旧版的“各门店数据”是用「全省总量 × 固定份额 × 季节系数」算出来的，
#      纯合成、不是真实门店数据，而且连全省总量都夸大了约 2.6 倍。
#   2. 新版【只使用公开来源的真实数据】（海口海关 / 海南省商务厅 /
#      中国中免年报），每个数字都带来源链接，可在文末“数据来源”核对。
#   3. 查不到的（如海旅/中服等门店年度营收、月度门店数据）一律标注
#      “无公开数据”，【绝不编造】。
#   4. 以“年度”为主：全省用年度真实趋势；门店用中免年报年度营业收入。
#
# 你怎么补充新数据（非技术也能改）：
#   打开本文件，找到下面【真实数据区】三个字典（PROVINCE / STORES /
#   SOURCES），按相同格式加一行即可，年份用数字、金额用亿元。
#   例如新增 2026 全省数据：在 PROVINCE 里加一行  2026: {"sales": 500.0, "guests": 700.0}
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ============================================================
# 【真实数据区】—— 仅公开来源，请勿编造
# ============================================================

# 全省离岛免税：海口海关监管的“离岛免税购物金额”
# 2025 年为海南省商务厅“12 家离岛免税店总销售额”口径（含免税+有税），客流未公开填 None
PROVINCE = {
    2019: {"sales": 134.9, "guests": 386.0},
    2020: {"sales": 274.8, "guests": 448.4},
    2021: {"sales": 495.0, "guests": 672.0},
    2022: {"sales": 349.0, "guests": 422.4},
    2023: {"sales": 437.6, "guests": 675.6},
    2024: {"sales": 309.4, "guests": 568.3},
    2025: {"sales": 475.2, "guests": None},  # 商务厅 12 家总销售额口径
}

# 中免旗下门店 / 子公司年度营业收入（中国中免年报，单位：亿元，含免税+有税）
# 这是公开渠道能拿到的“最接近门店真实数据”的数字。
# 键为门店/主体名，值为 {年份: 营收(亿元)}
STORES = {
    "三亚国际免税城（中免·三亚市内免税店）": {
        2022: 302.44, 2023: 283.64, 2024: 204.18,
    },
    "海口国际免税城（中免·海口免税城公司）": {
        2023: 68.38, 2024: 55.74,  # 2022 年 10 月才开业，无完整年报数据
    },
    "海免公司（日月广场/美兰/凤凰机场/博鳌）": {
        2022: 56.38, 2023: 49.18, 2024: 35.54,
    },
}

# 其他免税经营主体：公开渠道【没有】年度门店营收数据，仅列出名称，不展示数字
OTHER_OPERATORS = [
    "海旅免税城", "中服免税店", "深免海口观澜湖店",
    "万宁王府井免税港", "海发控全球精品免税城",
]

# 数据来源（带链接，方便核对）—— 新增数据请同步在这里补一条
SOURCES = [
    ("海口海关 · 2024 年海南离岛免税 309.4 亿元 / 568.3 万人次",
     "https://news.cctv.com/2025/01/02/ARTI91tTeDriSGYEBRNDIZGp250102.shtml"),
    ("海口海关 · 2023 年 437.6 亿元 / 675.6 万人次",
     "https://www.cnr.cn/hn/jrhn/20240102/t20240102_526543913.shtml"),
    ("海口海关 · 2022 年免税销售额 349 亿元 / 422.4 万人次",
     "https://www.toutiao.com/article/7216307163017413152/"),
    ("海口海关 · 2021 年 495 亿元 / 672 万人次",
     "http://xian.customs.gov.cn/customs/xwfb34/mtjj35/4124581/index.html"),
    ("海口海关 · 2020 年 274.8 亿元 / 448.4 万人次",
     "http://m.hkwb.net/content/2021-01/29/content_3941176.htm"),
    ("海口海关/海南省商务厅 · 2019 年 134.9 亿元 / 386 万人次",
     "https://www.hinews.cn/news/system/2020/10/13/032433734.shtml"),
    ("海南省商务厅 · 2025 年 12 家离岛免税店总销售额 475.2 亿元",
     "https://dzswgf.mofcom.gov.cn/news/123/2026/3/1774588279585.html"),
    ("中国中免 2024 年报 · 三亚市内店 204.18 亿 / 海口城 55.74 亿 / 海免 35.54 亿",
     "https://www.9fzt.com/detail/sh_601888_10_796956811591.html"),
    ("中国中免 2023 年报 · 三亚市内店 283.64 亿 / 海口城 68.38 亿 / 海免 49.18 亿",
     "https://m.toutiao.com/article/7351263542664004133/"),
    ("中国中免 2022 年报 · 三亚市内店 302.44 亿 / 海免 56.38 亿",
     "https://www.toutiao.com/article/7216690799612789303/"),
    ("三亚国际免税城 2024 全年销售额约 187 亿元（mall 实体报道口径，与年报 204 亿口径不同）",
     "https://www.comnews.cn/content/2026-01/20/content_60874.html"),
    ("海口海关 · 2026 年 1-6 月离岛免税 199.2 亿元 / 279.3 万人次（+18.8% / +12.6%）",
     "https://db.hainan.gov.cn/xwdt/yszx/202607/t20260709_4107904.html"),
    ("海口海关 · 封关后首段（2025-12-18~2026-04-30）离岛免税 222.2 亿元 / 297.3 万人次",
     "https://df.youth.cn/dfyw/202605/t20260513_16656698.htm"),
]

# 最新动态（2026 封关后，非完整年度，仅作“最新”参考，不参与年度同比）
LATEST = {
    "2026 上半年（1-6 月）": {
        "sales": 199.2, "guests": 279.3,
        "sales_yoy": 18.8, "guests_yoy": 12.6,
        "note": "海口海关监管离岛免税购物金额；购物件数 1596.6 万件（+7.3%）",
    },
}


# ============================================================
# 数据加工（全部来自上面的真实数据，不做任何虚构推算）
# ============================================================
@st.cache_data
def build_province_df():
    rows = []
    for y, d in PROVINCE.items():
        rows.append({
            "year": y,
            "sales": d["sales"],
            "guests": d["guests"],
        })
    df = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
    # 同比增长（与上一年对比，使用全省销售额）
    df["sales_yoy"] = df["sales"].pct_change() * 100
    df["guests_yoy"] = df["guests"].pct_change() * 100
    return df


@st.cache_data
def build_store_df():
    rows = []
    for store, series in STORES.items():
        years = sorted(series.keys())
        for i, y in enumerate(years):
            prev = series.get(years[i - 1]) if i > 0 else None
            yoy = ((series[y] - prev) / prev * 100) if prev else None
            rows.append({
                "store": store,
                "year": y,
                "revenue": series[y],
                "yoy": yoy,
            })
    return pd.DataFrame(rows)


# ============================================================
# UI
# ============================================================
def main():
    st.title("🌴 海南免税市场分析（真实公开数据版）")
    st.caption("数据来源：海口海关 / 海南省商务厅 / 中国中免年报 ｜ 仅展示公开可溯源的真实数据，查不到的一律标注「无公开数据」")

    pdf = build_province_df()
    sdf = build_store_df()

    # ---- 顶部概览指标 ----
    latest = pdf.iloc[-1]
    prev = pdf.iloc[-2] if len(pdf) > 1 else None
    st.subheader(f"📊 最新年度概览：{int(latest['year'])} 年")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("全省销售额", f"{latest['sales']:.1f} 亿",
              f"{latest['sales_yoy']:+.1f}%" if pd.notna(latest['sales_yoy']) else None)
    if pd.notna(latest['guests']):
        c2.metric("购物人数", f"{latest['guests']:.0f} 万",
                  f"{latest['guests_yoy']:+.1f}%" if pd.notna(latest['guests_yoy']) else None)
    else:
        c2.metric("购物人数", "未公开")
    if prev is not None:
        c3.metric("上一年销售额", f"{prev['sales']:.1f} 亿")
        peak = pdf.loc[pdf['sales'].idxmax()]
        c4.metric("历史峰值", f"{peak['sales']:.1f} 亿（{int(peak['year'])}）")
    st.markdown("---")

    t1, t2, t3, t4 = st.tabs([
        "📈 全省年度趋势", "🏪 中免门店年度实况", "🆕 最新动态（2026）", "📋 数据来源与缺口"
    ])

    # ---------- Tab 1：全省年度趋势 ----------
    with t1:
        st.subheader("全省离岛免税年度趋势（真实数据）")
        fig = go.Figure()
        fig.add_bar(
            x=pdf["year"], y=pdf["sales"],
            name="销售额（亿元）", marker_color="#3498db",
            text=pdf["sales"].round(1), textposition="outside",
        )
        fig.add_trace(go.Scatter(
            x=pdf["year"], y=pdf["guests"],
            name="购物人数（万人次）", yaxis="y2",
            mode="lines+markers", line=dict(color="#e67e22", width=3),
        ))
        fig.update_layout(
            yaxis=dict(title="销售额（亿元）"),
            yaxis2=dict(title="购物人数（万）", overlaying="y", side="right"),
            hovermode="x unified", legend=dict(orientation="h"),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("逐年明细（含同比）")
        show = pdf.copy()
        show["year"] = show["year"].astype(int)
        show["销售额(亿)"] = show["sales"].round(1)
        show["购物人数(万)"] = show["guests"].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "未公开")
        show["销售额同比"] = show["sales_yoy"].apply(lambda x: f"{x:+.1f}%" if pd.notna(x) else "—")
        show["人数同比"] = show["guests_yoy"].apply(lambda x: f"{x:+.1f}%" if pd.notna(x) else "—")
        st.dataframe(show[["year", "销售额(亿)", "销售额同比", "购物人数(万)", "人数同比"]],
                     use_container_width=True, hide_index=True)

        st.info(
            "📌 说明：2019–2024 为海口海关监管的“离岛免税购物金额”；"
            "2025 为海南省商务厅公布的“12 家离岛免税店总销售额”（含免税+有税，口径略宽），客流未公开。"
        )

    # ---------- Tab 2：中免门店年度实况 ----------
    with t2:
        st.subheader("中免旗下门店 / 子公司 年度营业收入（中国中免年报）")
        st.caption("⚠️ 这是集团年报口径的「营业收入」（含免税+有税），是公开渠道最贴近门店真实经营的数据；"
                   "非中免体系的其他免税店无公开年度数据，见“数据来源与缺口”页。")

        fig = px.bar(
            sdf, x="store", y="revenue", color="year",
            barmode="group", text_auto=".1f",
            labels={"store": "门店 / 主体", "revenue": "营业收入（亿元）", "year": "年份"},
            title="各门店年度营业收入对比",
        )
        fig.update_xaxes(tickangle=20)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("逐年明细与同比")
        sd = sdf.copy()
        sd["revenue"] = sd["revenue"].round(2)
        sd["yoy"] = sd["yoy"].apply(lambda x: f"{x:+.1f}%" if pd.notna(x) else "首年/无对比")
        st.dataframe(
            sd[["store", "year", "revenue", "yoy"]].rename(columns={"revenue": "营业收入(亿)"}),
            use_container_width=True, hide_index=True,
        )

        st.warning(
            "🚫 以下经营主体【无公开年度门店营收数据】，故不展示数字（不编造）：\n"
            + "、".join(OTHER_OPERATORS)
        )

    # ---------- Tab 3：最新动态（2026 封关后） ----------
    with t3:
        st.subheader("🆕 最新动态（2026 年，封关后）")
        st.caption("⚠️ 以下为最新公开数据，但属「年内累计 / 部分时段」，非完整年度，不参与年度同比。")
        for period, d in LATEST.items():
            c1, c2 = st.columns(2)
            c1.metric(period, f"{d['sales']:.1f} 亿",
                       f"{d['sales_yoy']:+.1f}%" if d.get('sales_yoy') is not None else None)
            c2.metric("购物人数", f"{d['guests']:.0f} 万",
                       f"{d['guests_yoy']:+.1f}%" if d.get('guests_yoy') is not None else None)
            st.info(f"📌 {d.get('note', '')}")

        st.info(
            "补充背景：自 2025-12-18 海南自贸港封关、离岛免税新政落地 至 2026-04-30，"
            "海口海关累计监管离岛免税购物金额 222.2 亿元、购物人数 297.3 万人次"
            "（同比 +22.6% / +9.4%），为封关后首段完整窗口数据。"
        )

    # ---------- Tab 4：数据来源与缺口 ----------
    with t4:
        st.subheader("📚 数据来源（点击可核对原文）")
        for name, url in SOURCES:
            st.markdown(f"- [{name}]({url})")

        st.subheader("⚪ 当前「无公开数据」的缺口")
        st.markdown(
            "以下维度在公开渠道查不到真实数据，本模块**不展示、不估算**：\n"
            "- **月度门店级数据**：海关只公布全省月度/年度总额，中免年报只到年度/区域，门店月度真实销售查不到。\n"
            "- **非中免门店年度营收**：海旅免税城、中服免税店、深免海口观澜湖店、万宁王府井免税港、海发控全球精品免税城 均无公开年度数字（仅有个别节假日增速，不足以复原全年）。\n"
            "- **2025 年购物人数**：商务厅只公布了总销售额 475.2 亿，未公布对应客流。\n"
            "- **2022 年海口国际免税城**：2022 年 10 月才开业，年报无完整年度营收。"
        )

        st.subheader("🛠️ 如何补充真实数据")
        st.markdown(
            "1. 打开本文件，找到顶部【真实数据区】。\n"
            "2. 全省数据加在 `PROVINCE` 字典：例如 `2026: {\"sales\": 500.0, \"guests\": 700.0}`。\n"
            "3. 门店数据加在 `STORES` 字典对应门店下，年份用数字、金额用亿元。\n"
            "4. 新增来源请同步加到 `SOURCES` 列表，保留链接以便核对。\n"
            "5. 保存后刷新 Streamlit 页面即可生效。**请勿填入未经核实的估算值。**"
        )


if __name__ == "__main__":
    main()
