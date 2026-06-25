import streamlit as st
import re
import difflib

st.set_page_config(page_title="合同审查工具", page_icon="📄", layout="wide")
st.title("📄 合同智能审查与对比工具")

tab1, tab2, tab3 = st.tabs(["🔍 风险审查", "🌐 中英文对比", "📊 新旧合同对比"])

def read_file(file):
    return file.read().decode("utf-8", errors="ignore")

with tab1:
    st.header("合同风险点审查")
    f = st.file_uploader("上传合同（TXT格式）", type="txt", key="risk")
    if f:
        text = read_file(f)
        st.info(f"合同字数：{len(text)}字")
        st.subheader("必备条款检查")
        checks = [
            ("合同主体", r"甲方|乙方|party"),
            ("合同标的", r"标的|服务|scope"),
            ("合同期限", r"期限|term|duration"),
            ("付款条款", r"付款|payment|price|fee"),
            ("违约责任", r"违约|breach|liability"),
            ("争议解决", r"争议|仲裁|管辖|dispute"),
            ("保密条款", r"保密|confidential"),
            ("终止条款", r"终止|termination"),
            ("签署生效", r"签署|生效|sign|execut"),
        ]
        for name, pattern in checks:
            if re.search(pattern, text, re.IGNORECASE):
                st.success(f"✅ {name}")
            else:
                st.warning(f"⚠️ 未检测到：{name}")

with tab2:
    st.header("中英文合同对比")
    col1, col2 = st.columns(2)
    with col1:
        cn = st.file_uploader("中文合同", type="txt", key="cn")
    with col2:
        en = st.file_uploader("英文合同", type="txt", key="en")
    if cn and en:
        cn_text, en_text = read_file(cn), read_file(en)
        cn_lines, en_lines = cn_text.splitlines(), en_text.splitlines()
        st.metric("中文行数", len(cn_lines))
        st.metric("英文行数", len(en_lines))
        if abs(len(cn_lines) - len(en_lines)) > 3:
            st.warning(f"⚠️ 行数差异较大（差{abs(len(cn_lines)-len(en_lines))}行），建议检查是否有缺漏")
        else:
            st.success("✅ 行数基本一致")

with tab3:
    st.header("新旧合同差异对比")
    col1, col2 = st.columns(2)
    with col1:
        old = st.file_uploader("旧合同", type="txt", key="old")
    with col2:
        new = st.file_uploader("新合同", type="txt", key="new")
    if old and new:
        old_text, new_text = read_file(old), read_file(new)
        diff = difflib.unified_diff(
            old_text.splitlines(), new_text.splitlines(),
            fromfile="旧合同", tofile="新合同"
        )
        result = "\n".join(diff)
        if result.strip():
            st.code(result, language="diff")
        else:
            st.success("✅ 两份合同完全一致")
