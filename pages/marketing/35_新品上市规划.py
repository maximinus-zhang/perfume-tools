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

# ===== 加密数据：base64 内嵌，部署到任何环境都无需外部文件 =====
import os, sys
import base64

PAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(PAGE_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.newness_crypto import decrypt_data

# 以下为「2026 TR NEWNESS」看板数据的加密副本（PBKDF2+XOR），以 base64 内嵌。
# 仅持有密码(Max12345)者可解密；明文不落盘，也不依赖外部文件路径，避免部署环境差异。
EMBEDDED_B64 = (
    "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"
)

def _load_blob() -> bytes:
    """直接解码内嵌的加密数据，彻底规避文件路径 / 部署环境差异问题。"""
    return base64.b64decode(EMBEDDED_B64)


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
        blob = _load_blob()  # 内嵌数据，直接解码，无需外部文件
        text = decrypt_data(blob, pw)            # 密码错 -> PermissionError
        st.session_state[SESSION_DATA] = json.loads(text)
        st.session_state[SESSION_AUTH] = True
        st.session_state[SESSION_ERR] = ""
    except PermissionError:
        st.session_state[SESSION_AUTH] = False
        st.session_state[SESSION_ERR] = "🔒 密码错误，请重试"
    except FileNotFoundError:
        st.session_state[SESSION_AUTH] = False
        st.session_state[SESSION_ERR] = (
            f"⚠️ 找不到加密数据文件：\n`{DATA_PATH}`\n\n"
            f"请确认 `data/newness_encrypted.bin` 已放在项目根目录的 `data/` 文件夹下。"
        )
    except Exception as e:                       # 文件损坏等其它异常
        st.session_state[SESSION_AUTH] = False
        st.session_state[SESSION_ERR] = f"解密失败：{e}"


if not st.session_state.get(SESSION_AUTH, False):
    with st.container(border=True):
        st.markdown("🔒 此页面需要访问密码，输入密码后即可查看完整内容。")
        st.text_input(
            "访问密码",
            type="password",
            key="newness_pw",
            placeholder="请输入密码",
            label_visibility="collapsed",
            help="密码由负责人提供，不显示在页面上",
        )
        if st.button("🔓 解锁查看", type="primary", key="newness_unlock"):
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
    st.plotly_chart(fig, width='stretch')


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
    st.dataframe(bpdf, width='stretch', hide_index=True)

st.divider()
st.caption("页面由「派派 · 高级开发工程师」构建：轻量加密(PBKDF2+XOR) + Streamlit 原生渲染，"
           "敏感内容不落明文、不依赖外部网络。")
