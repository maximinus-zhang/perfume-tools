# -*- coding: utf-8 -*-
"""
🎯 新品上市规划页面 —— 加密访问的「2026 TR NEWNESS」看板
========================================================================
数据来源：data/newness_encrypted.bin
    （由「2026 TR NEWNESS.pptx」提取内容后，用轻量加密落盘，
      只有持有密码的人才能解密查看，与其它并行项目隔离。）

访问方式：密码解锁（密码由负责人掌握，不写死在页面里）。
解密工具：from utils.newness_crypto import decrypt_data
渲染技术：Streamlit 原生组件 + Plotly（均本地依赖，不依赖外部 CDN，
          避免与同机运行的其它项目产生网络/资源耦合）。
========================================================================
"""
import os
import sys
import json
import streamlit as st
import pandas as pd
import plotly.express as px

# ===== 路径定位（无论 app 从哪启动都能找到项目根与数据文件）=====
PAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(PAGE_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DATA_PATH = os.path.join(PROJECT_ROOT, "data", "newness_encrypted.bin")

from utils.newness_crypto import decrypt_data

st.title("🎯 新品上市规划 · 2026 NEWNESS")


# ======================================================================
# 1) 密码门（session_state 记住解锁状态，刷新不重复输入）
# ======================================================================
SESSION_AUTH = "newness_authed"
SESSION_DATA = "newness_data"
SESSION_ERR = "newness_err"


def try_unlock():
    """读取加密文件并尝试用输入的密码解密；失败给出友好提示。"""
    pw = st.session_state.get("newness_pw", "")
    if not pw:
        st.session_state[SESSION_ERR] = "请输入访问密码"
        return
    try:
        with open(DATA_PATH, "rb") as f:
            blob = f.read()
        text = decrypt_data(blob, pw)            # 密码错 -> PermissionError
        st.session_state[SESSION_DATA] = json.loads(text)
        st.session_state[SESSION_AUTH] = True
        st.session_state[SESSION_ERR] = ""
    except PermissionError:
        st.session_state[SESSION_AUTH] = False
        st.session_state[SESSION_ERR] = "🔒 密码错误，请重试"
    except Exception as e:                       # 文件损坏等其它异常
        st.session_state[SESSION_AUTH] = False
        st.session_state[SESSION_ERR] = f"解密失败：{e}"


if not st.session_state.get(SESSION_AUTH, False):
    st.markdown(
        "<div style='max-width:480px;margin:40px auto;text-align:center;"
        "padding:32px;border-radius:18px;background:rgba(120,120,160,0.08);"
        "border:1px solid rgba(120,120,160,0.25);'>"
        "<div style='font-size:48px'>🔐</div>"
        "<h3 style='margin:12px 0 4px'>该页面已加密</h3>"
        "<p style='opacity:.7;margin:0'>本页内容来自内部新品上市资料，"
        "请输入访问密码后查看。</p></div>",
        unsafe_allow_html=True,
    )
    pw = st.text_input("访问密码", type="password", key="newness_pw",
                       placeholder="请输入密码", help="密码由负责人提供，不显示在页面上")
    if st.button("🔓 解锁查看", type="primary", use_container_width=True):
        try_unlock()
    if st.session_state.get(SESSION_ERR):
        st.error(st.session_state[SESSION_ERR])
    # 只有「仍未解锁」才停在此页；解锁成功后继续往下渲染看板（同一次运行内）
    if not st.session_state.get(SESSION_AUTH, False):
        st.stop()


# 已解锁：提供重新上锁按钮
if st.sidebar.button("🔒 重新上锁"):
    st.session_state[SESSION_AUTH] = False
    st.session_state[SESSION_DATA] = None
    st.session_state[SESSION_ERR] = ""
    st.rerun()

data = st.session_state[SESSION_DATA]


# ======================================================================
# 2) 概览指标卡
# ======================================================================
existing = data.get("existing_brands", [])
new_brands = data.get("new_brands", [])
quarters = data.get("quarters", {})
festivals = data.get("festivals", [])
meta = data.get("meta", {})

c1, c2, c3, c4 = st.columns(4)
c1.metric("看板总页数", meta.get("total_pages", len(data.get("brand_pages", []))))
c2.metric("现有品牌", len(existing))
c3.metric("新增品牌", len(new_brands))
c4.metric("关键节日节点", len(festivals))

st.caption("🔒 数据已本地加密（data/newness_encrypted.bin），本页为解密后视图，与同机其它项目隔离。")


# ======================================================================
# 3) 季度新品分布（Plotly 柱状图，本地渲染）
# ======================================================================
st.markdown("### 📊 季度新品上市分布")
if quarters:
    qdf = pd.DataFrame({
        "季度": quarters.get("labels", []),
        "新品数": quarters.get("data", []),
    })
    fig = px.bar(
        qdf, x="季度", y="新品数", text="新品数",
        color="季度",
        color_discrete_sequence=quarters.get("colors", px.colors.qualitative.Safe),
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title=None, yaxis_title="新品数量（款）",
        font=dict(size=13),
    )
    st.plotly_chart(fig, use_container_width=True)


# ======================================================================
# 4) 现有品牌矩阵（按 tier 着色的胶囊标签）
# ======================================================================
st.markdown("### 🏷️ 现有品牌矩阵")
TIER_COLOR = {"BT1": "#3B82F6", "BT2": "#22C55E", "BT3": "#A855F7"}


def tier_color(tier):
    return TIER_COLOR.get(tier, "#94A3B8")


chips_html = "<div style='line-height:2.2'>"
for b in existing:
    c = tier_color(b.get("tier", "-"))
    state = b.get("state", "")
    chips_html += (
        f'<span style="display:inline-block;margin:4px;padding:5px 12px;'
        f'border-radius:999px;background:{c}1A;border:1px solid {c}66;'
        f'color:{c};font-size:13px;font-weight:600;">'
        f'{b.get("cn","")}<span style="opacity:.55;font-weight:500">'
        f' · {b.get("tier","-")} · {state}</span></span>'
    )
chips_html += "</div>"
st.markdown(chips_html, unsafe_allow_html=True)

legend = (
    "<div style='margin-top:6px;font-size:12px;opacity:.75'>"
    "<span style='color:#3B82F6'>●</span> BT1 高端　"
    "<span style='color:#22C55E'>●</span> BT2 中端　"
    "<span style='color:#A855F7'>●</span> BT3 小众　"
    "<span style='color:#94A3B8'>●</span> 其它/护肤/彩妆线</div>"
)
st.markdown(legend, unsafe_allow_html=True)


# ======================================================================
# 5) 新增品牌（突出展示）
# ======================================================================
st.markdown("### ✨ 2026 新增品牌")
NB_COLOR = {"已确认": "#22C55E", "待定": "#F59E0B", "厂家未出": "#94A3B8"}
nb_cols = st.columns(len(new_brands) if len(new_brands) <= 4 else 4)
for i, b in enumerate(new_brands):
    col = nb_cols[i % 4]
    stt = b.get("state", "")
    c = NB_COLOR.get(stt, "#94A3B8")
    col.markdown(
        f"<div style='padding:14px;border-radius:14px;height:100%;"
        f"background:{c}14;border:1px solid {c}55;'>"
        f"<div style='font-weight:700;font-size:15px'>{b.get('cn','')}</div>"
        f"<div style='opacity:.6;font-size:12px;margin-bottom:6px'>"
        f"{b.get('en','')}</div>"
        f"<span style='display:inline-block;padding:2px 10px;border-radius:999px;"
        f"background:{c};color:#fff;font-size:12px;font-weight:600'>{stt}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ======================================================================
# 6) 关键节日节点
# ======================================================================
st.markdown("### 🎉 关键节日节点")
if festivals:
    fcols = st.columns(len(festivals))
    for col, f in zip(fcols, festivals):
        col.markdown(
            f"<div style='padding:16px;border-radius:14px;text-align:center;"
            f"background:{f.get('color','#888')}1A;"
            f"border:1px solid {f.get('color','#888')}55;'>"
            f"<div style='font-size:13px;opacity:.7'>{f.get('month','')}</div>"
            f"<div style='font-weight:800;font-size:18px;color:{f.get('color','#888')}'>"
            f"{f.get('name','')}</div>"
            f"<div style='font-size:13px'>{f.get('full','')}</div></div>",
            unsafe_allow_html=True,
        )


# ======================================================================
# 7) 品牌页码对照表
# ======================================================================
st.markdown("### 📖 品牌 → PPT 页码对照")
bp = data.get("brand_pages", [])
if bp:
    bpdf = pd.DataFrame(bp)
    bpdf.columns = ["品牌 Brand", "PPT 页码范围"]
    st.dataframe(bpdf, use_container_width=True, hide_index=True)

st.divider()
st.caption("页面由「派派 · 高级开发工程师」构建：轻量加密(PBKDF2+XOR) + Streamlit 原生渲染，"
           "敏感内容不落明文、不依赖外部网络。")
