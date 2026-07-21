# -*- coding: utf-8 -*-
"""
竞品价格监控看板 v2.0
======================
监控各免税零售商（中免 / 海旅 / 海控 / 中服）公开标价的竞品 SKU，覆盖
【香水 / 彩妆 / 护肤】三大品类主力品牌。

数据来源：utils.price_monitor.fetcher 采集的快照（CSV 落盘 + OSS）。
  · 价格全部为【实测公开标价】，绝不含任何代理估算（与商情看板的估算数据严格区分）。
  · 合规：仅抓取公开标价页，不碰登录墙 / 小程序加密 API / 个人隐私。

核心功能（v2.0 新增）
  · 品类切换：香水 / 彩妆 / 护肤 / 全部。
  · 品牌多选：按当前品类下的在监品牌筛选。
  · 折扣维度：有税参考价、折扣率(免税省%)、促销标签（秒杀/促销）。
  · 降价预警：对比上一轮快照，标出降幅 ≥ 阈值（默认 5%）的 SKU。
  · 历史趋势：选单个 SKU，画跨日价格走势（折线）。
  · 品牌货架速览：选品类 + 品牌，实时拉取中免在售商品及折扣（不留存历史）。
  · CSV 下载 / 立即抓取。

维度说明（重要）
  · 公开接口【无销量字段】，故「销量/销售」维度无法提供；以「折扣率 + 促销标签 +
    在售 SKU 数 + 价格趋势」替代"行情"。
  · 折扣率(免税省%) = (有税参考价 − 实际免税价) / 有税参考价。

防御性设计：模块导入 / 计算失败只影响本页，弹友好提示，不连累 app.py 导航整站。
"""

import streamlit as st
from datetime import datetime
import pandas as pd
import threading

st.set_page_config(page_title="竞品价格监控", page_icon="🛒", layout="wide")

# ============================================================
# 防御性导入（任何失败只影响本页）
# ============================================================
try:
    from utils.price_monitor.fetcher import (
        load_latest, load_history, LOCAL_DIR, run_monitor,
    )
    from utils.price_monitor.adapters import ADAPTER_REGISTRY
    from utils.price_monitor.config import RETAILERS_MONITOR, BRAND_SHELF
    from utils.price_monitor.adapters.cdf_api import search_shelf
    _IMPORT_OK = True
    _IMPORT_ERR = ""
except Exception as _e:
    _IMPORT_OK = False
    _IMPORT_ERR = str(_e)

st.title("🛒 竞品价格监控看板")
st.caption("免税零售商公开标价 · 竞品 香水/彩妆/护肤 主力品牌 · 全为实测价（非估算）· v2.0")

if not _IMPORT_OK:
    st.error(
        f"⚠️ 价格监控模块加载失败，本页无法显示（不影响其他页面）：{_IMPORT_ERR}\n"
        f"请检查 utils/price_monitor/ 下的 fetcher.py、adapters/、config.py 是否存在。"
    )
    st.stop()


# ============================================================
# 小工具
# ============================================================
PRICE_DROP_THRESHOLD = 0.05  # 降价预警阈值（5%）


def _status_label(rec) -> str:
    return {"ok": "✅ 有价", "not_found": "⚠️ 未上架", "blocked_login": "🔒 登录墙",
            "error": "❌ 异常", "verify_pending": "⏳ 待验证"}.get(rec.status, rec.status)


def _price_drop(recs_current, recs_prev) -> dict:
    """对比上一轮快照，返回 {sku_id: (降幅比例, 现价, 上次价)}，仅含降幅≥阈值。"""
    prev = {r.sku_id: r for r in recs_prev if r.price is not None}
    out = {}
    for r in recs_current:
        if r.price is None:
            continue
        p = prev.get(r.sku_id)
        if p and p.price and p.price > 0:
            drop = (p.price - r.price) / p.price
            if drop >= PRICE_DROP_THRESHOLD:
                out[r.sku_id] = (drop, r.price, p.price)
    return out


def _discount_pct(rec) -> float | None:
    return rec.discount_rate


# ============================================================
# 侧栏：抓取控制
# ============================================================
with st.sidebar:
    st.subheader("⚙️ 抓取控制")
    st.markdown("仅对**纯 HTTP 零售商**（中免）即时抓取，无需浏览器。"
                "海旅等需浏览器的零售商在此环境暂不触发。")
    if st.button("🔄 立即抓取一次（中免）", use_container_width=True, type="primary"):
        def _run():
            try:
                from utils.price_monitor.config import RETAILERS_MONITOR as _RM
                cdfg = [r for r in _RM if r["id"] == "cdfg"]
                run_monitor(retailers=cdfg, headless=True, persist=True)  # 默认抓全品类
                st.session_state["_pm_fetch_done"] = datetime.now().isoformat()
            except Exception as _e:
                st.session_state["_pm_fetch_err"] = str(_e)

        if "_pm_fetch_thread" not in st.session_state or not st.session_state["_pm_fetch_thread"].is_alive():
            st.session_state["_pm_fetch_done"] = ""
            st.session_state["_pm_fetch_err"] = ""
            t = threading.Thread(target=_run, daemon=True)
            t.start()
            st.session_state["_pm_fetch_thread"] = t
            st.rerun()

    if st.session_state.get("_pm_fetch_err"):
        st.error(f"抓取失败：{st.session_state['_pm_fetch_err']}")
    elif st.session_state.get("_pm_fetch_done"):
        st.success(f"✅ 抓取完成：{st.session_state['_pm_fetch_done'][:19]}")
        st.session_state["_pm_fetch_done"] = ""  # 清掉，避免重复提示
        st.rerun()


# ============================================================
# Tab 1：监控看板   /   Tab 2：品牌货架速览
# ============================================================
tab_board, tab_shelf = st.tabs(["📊 监控看板", "🛒 品牌货架速览"])


# ------------------------------------------------------------
# Tab 1 · 监控看板
# ------------------------------------------------------------
with tab_board:
    current = load_latest()
    if not current:
        st.warning("📭 暂无抓取数据。点左侧「立即抓取一次（中免）」生成首份快照。", icon="ℹ️")
    else:
        # ---- 筛选：品类 + 品牌 + 零售商 ----
        cats = ["全部"] + sorted({r.category for r in current})
        cat = st.selectbox("🏷️ 品类", cats, index=0)
        view = current if cat == "全部" else [r for r in current if r.category == cat]

        brands = sorted({r.brand for r in view})
        sel_brands = st.multiselect("🏢 品牌（多选）", options=brands, default=brands)
        view = [r for r in view if r.brand in sel_brands]

        retailers_present = sorted({r.retailer_name for r in view})
        with st.expander("🔎 按零售商筛选", expanded=False):
            sel_ret = st.multiselect("只看这些零售商", options=retailers_present, default=retailers_present)
            if sel_ret:
                view = [r for r in view if r.retailer_name in sel_ret]

        sub = view

        # ---- 历史（用于降价对比 / 趋势），仅取当前视图的 SKU ----
        hist_all = []
        try:
            sku_ids = sorted({r.sku_id for r in sub})
            for sid in sku_ids:
                hist_all.extend(load_history(sid))
            hist_all.sort(key=lambda x: x.captured_at)
        except Exception:
            hist_all = []

        prev_map = {}
        for r in hist_all:
            prev_map.setdefault(r.sku_id, []).append(r)
        prev_run = [v[-2] for v in prev_map.values() if len(v) >= 2]

        # ---- 组装表格行 ----
        rows = []
        for r in sub:
            dr = _discount_pct(r)
            rows.append({
                "零售商": r.retailer_name,
                "品牌": r.brand,
                "产品": r.name_cn,
                "规格": r.size_ml,
                "价格(CNY)": r.price if r.price is not None else "—",
                "有税参考价": r.sales_price if r.sales_price is not None else "—",
                "折扣率(省%)": f"{dr*100:.1f}%" if dr is not None else "—",
                "促销": r.promo_label or "—",
                "状态": _status_label(r),
                "抓取时间": r.captured_at[:16].replace("T", " "),
                "来源": r.source,
                "备注": r.note,
                "_status": r.status,
            })
        df = pd.DataFrame(rows)

        # ---- 降价预警 ----
        drops = _price_drop(sub, prev_run)
        current_map = {r.sku_id: r for r in sub}
        drop_keys = {(r.retailer_name, r.brand, r.name_cn) for r in sub if r.sku_id in drops}

        # ---- 顶部指标 ----
        n_ok = sum(1 for r in sub if r.status == "ok")
        n_total = len(sub)
        c1, c2, c3 = st.columns(3)
        c1.metric("在监控 SKU", f"{n_total}", f"{n_ok} 条有价（{cat}）")
        c2.metric("覆盖零售商", "、".join(retailers_present) or "—")
        c3.metric(f"降价预警(≥{int(PRICE_DROP_THRESHOLD*100)}%)", f"{len(drops)} 个",
                  help="对比上一次快照，降幅达阈值的 SKU 数")

        if drops:
            items = []
            for sid, (drop, cur, prev) in drops.items():
                rec = current_map.get(sid)
                if rec:
                    items.append(f"{rec.brand}{rec.name_cn} ¥{prev}→¥{cur}（↓{drop*100:.1f}%）")
            st.warning(f"📉 **降价预警（{len(drops)} 个）**：" + "；".join(items), icon="⚠️")
        else:
            if prev_run:
                st.success(f"✅ 较上轮快照无 ≥{int(PRICE_DROP_THRESHOLD*100)}% 降价。", icon="✅")
            else:
                st.info("ℹ️ 仅有单轮快照，降价对比需再抓一轮后生效。", icon="ℹ️")

        # ---- 快照表（高亮降价 + 高折扣）----
        st.subheader("📋 当前价格快照")

        def _style(row):
            out = []
            for c in row.index:
                if c == "价格(CNY)" and row["_status"] == "ok" and \
                        (row["零售商"], row["品牌"], row["产品"]) in drop_keys:
                    out.append("background-color:#fee2e2; color:#991b1b; font-weight:600")
                elif c == "折扣率(省%)":
                    try:
                        pct = float(str(row[c]).replace("%", ""))
                    except Exception:
                        pct = 0
                    out.append("color:#047857; font-weight:700" if pct >= 30 else "")
                elif row["_status"] != "ok":
                    out.append("opacity:0.55")
                else:
                    out.append("")
            return out

        styled = df.style.apply(_style, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)
        st.caption("说明：红字=较上轮降价≥5%；绿字=免税省≥30%；灰色=无价（未上架/登录墙/异常）。"
                   "折扣率= (有税参考价−免税价)/有税参考价。价格均为实测公开标价。")

        # ---- 历史趋势 ----
        st.subheader("📈 单 SKU 历史价格趋势")
        if hist_all:
            opts = {}
            for r in hist_all:
                if r.price is None:
                    continue
                label = f"{r.retailer_name} · {r.brand}{r.name_cn}"
                opts.setdefault(label, r.sku_id)
            choice = st.selectbox("选择 SKU", options=list(opts.keys()))
            if choice:
                sid = opts[choice]
                s = [r for r in hist_all if r.sku_id == sid and r.price is not None]
                s.sort(key=lambda x: x.captured_at)
                tdf = pd.DataFrame({
                    "时间": [x.captured_at[:16].replace("T", " ") for x in s],
                    "价格": [x.price for x in s],
                }).set_index("时间")
                st.line_chart(tdf)
                st.caption(f"共 {len(tdf)} 个观测点；最新 ¥{s[-1].price}（{s[-1].captured_at[:16].replace('T',' ')}）。")
        else:
            st.info("ℹ️ 暂无历史数据，抓取两轮后即可看趋势。", icon="ℹ️")

        # ---- 下载 ----
        st.subheader("⬇️ 导出")
        import csv as _csv
        csv_path = f"{LOCAL_DIR}/latest.csv"
        try:
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                csv_bytes = f.read().encode("utf-8-sig")
            st.download_button(
                "⬇️ 下载当前快照 CSV（含来源/状态/备注）",
                csv_bytes, file_name=f"竞品价格快照_{datetime.now():%Y%m%d}.csv", mime="text/csv",
            )
        except Exception as _e:
            st.error(f"读取 CSV 失败：{_e}")


# ------------------------------------------------------------
# Tab 2 · 品牌货架速览（实时拉取中免在售商品）
# ------------------------------------------------------------
with tab_shelf:
    st.subheader("🛒 中免 CDF 品牌货架速览（实时）")
    st.caption("选品类 + 品牌，实时拉取该品牌在售商品及折扣（不留存历史）。"
               "数据源：中免公开搜索接口；【销量维度接口未提供】。")

    shelf_cat = st.selectbox("🏷️ 品类", options=["香水", "彩妆", "护肤"], index=0)
    brands = BRAND_SHELF.get(shelf_cat, [])
    shelf_brand = st.selectbox("🏢 品牌", options=brands, index=0)

    if st.button("🔍 查询货架", type="primary", use_container_width=False):
        with st.spinner(f"实时查询中免「{shelf_brand}」货架…"):
            try:
                results = search_shelf(shelf_brand, category=shelf_cat)
                st.session_state["_shelf"] = results
                st.session_state["_shelf_brand"] = shelf_brand
                st.session_state["_shelf_cat"] = shelf_cat
            except Exception as _e:
                st.error(f"查询失败：{_e}")

    results = st.session_state.get("_shelf", [])
    shown_brand = st.session_state.get("_shelf_brand", "")
    shown_cat = st.session_state.get("_shelf_cat", "")
    if results:
        st.success(f"「{shown_brand}」({shown_cat}) 共 {len(results)} 件在售商品", icon="🛍️")
        rows = []
        for o in results:
            sp, pr = o.get("sales_price"), o.get("price")
            dr = (sp - pr) / sp if (sp and pr and sp > 0) else None
            rows.append({
                "商品": o.get("name") or "—",
                "品牌": o.get("brand") or "—",
                "免税价": pr if pr is not None else "—",
                "有税参考价": sp if sp is not None else "—",
                "折扣率(省%)": f"{dr*100:.1f}%" if dr is not None else "—",
                "促销": o.get("promo") or "—",
                "品类": o.get("category") or "—",
                "链接": o.get("url") or "",
            })
        sdf = pd.DataFrame(rows)
        st.dataframe(sdf, use_container_width=True, hide_index=True)
        st.caption("说明：折扣率= (有税参考价−免税价)/有税参考价；促销标签来自中免「秒杀价/促销」等。")
    else:
        st.info("ℹ️ 点上方「查询货架」查看该品牌在中免的在售商品与折扣。", icon="ℹ️")


# ============================================================
# 来源说明
# ============================================================
st.divider()
st.markdown("### 📚 数据来源与口径")
st.markdown("- **全部为实测公开标价**：抓取各零售商官网公开标价页，绝不含任何代理估算。")
st.markdown("- **合规边界**：仅抓公开标价，不碰登录墙 / 小程序加密 API / 个人隐私；命中登录墙的零售商自动跳过并标记。")
st.markdown(f"- **快照目录**：`{LOCAL_DIR}`（每日一份 + `latest.csv`；可选同步 OSS）。")
st.caption(f"看板生成于 {datetime.now():%Y-%m-%d %H:%M} · 当前覆盖品类：香水 / 彩妆 / 护肤")
