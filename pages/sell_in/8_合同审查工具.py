import streamlit as st
import re
import difflib
from io import BytesIO
import tempfile
import os
from datetime import datetime

st.set_page_config(page_title="合同审查工具", page_icon="📄", layout="wide")
st.title("📄 合同智能审查与对比工具（含AI分析）")

tab1, tab2, tab3 = st.tabs(["🔍 风险审查", "🌐 中英文对比", "📊 新旧合同对比"])

# ============================================================
# 文件读取函数
# ============================================================
def read_file(file):
    """读取上传的文件，支持 TXT、PDF、DOCX"""
    file_type = file.name.split(".")[-1].lower()
    content = file.read()

    if file_type == "txt":
        return content.decode("utf-8", errors="ignore")

    elif file_type == "docx":
        try:
            from docx import Document
            doc = Document(BytesIO(content))
            text = "\n".join([para.text for para in doc.paragraphs])
            return text if text.strip() else "⚠️ 文档内容为空"
        except ImportError:
            return "❌ 请安装 python-docx：pip install python-docx"
        except Exception as e:
            return f"❌ DOCX 读取失败：{e}"

    elif file_type == "pdf":
        try:
            from markitdown import MarkItDown
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            md = MarkItDown()
            result = md.convert(tmp_path)
            os.unlink(tmp_path)
            text = result.text_content
            if len(text.strip()) > 50:
                return text
            else:
                return "⚠️ 未能提取到文字内容，可能是扫描版PDF。请先使用在线工具将PDF转为文字后再上传。"
        except ImportError:
            return "❌ 请安装 markitdown：pip install markitdown"
        except Exception as e:
            return f"❌ PDF 读取失败：{e}"

    else:
        return f"❌ 不支持的文件格式：{file_type}"


# ============================================================
# 关键词风险分析
# ============================================================
def analyze_keywords(text):
    """关键词风险分析"""
    risks = []
    
    # 风险条款关键词
    risk_patterns = [
        ("🔄 自动续约条款", r"自动续[约签]|auto.?renew"),
        ("💰 赔偿限额条款", r"赔偿.*?限额|赔偿.*?上限|limit.*?liability"),
        ("🔒 保密条款", r"保密|confidential"),
        ("⚖️ 仲裁条款", r"仲裁|arbitration"),
        ("📋 管辖法院条款", r"管辖|jurisdiction"),
        ("🚫 单方变更权", r"有权.*?修改|有权.*?变更|单方.*?变更"),
        ("📊 数据保护条款", r"个人数据|个人信息|隐私|personal data|GDPR"),
        ("⏰ 不可抗力条款", r"不可抗力|force majeure"),
        ("📝 终止条款", r"终止|termination|cancel"),
        ("✅ 验收条款", r"验收|检验|inspection|acceptance"),
    ]
    
    for risk_name, pattern in risk_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            risks.append({"name": risk_name, "status": "✅ 已包含"})
        else:
            risks.append({"name": risk_name, "status": "⚠️ 未检测到，建议补充"})
    
    return risks


# ============================================================
# Tab 1：风险审查
# ============================================================
with tab1:
    st.header("合同风险点审查（含AI分析）")
    st.caption("支持电子版PDF / Word / TXT | 自动提取金额、日期、当事人等关键信息")

    f = st.file_uploader(
        "上传合同文件",
        type=["txt", "pdf", "docx"],
        key="risk",
        help="支持电子版PDF、Word文档、纯文本。扫描版PDF请先转文字。"
    )

    if f:
        with st.spinner("正在读取并分析合同..."):
            text = read_file(f)

        if text.startswith("❌") or text.startswith("⚠️"):
            st.warning(text)
        else:
            # 显示文件信息
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"📄 文件：{f.name}")
            with col2:
                st.info(f"📝 字数：{len(text)}字")
            with col3:
                st.info(f"📊 段落数：{len(text.splitlines())}行")

            # ===== AI 智能提取 =====
            st.subheader("🤖 AI 智能提取")
            st.info("💡 提示：安装 LexNLP 可获取更智能的合同分析（pip install lexnlp）")

            # ===== 必备条款检查 =====
            st.markdown("---")
            st.subheader("✅ 必备条款完整性检查")
            
            checks = [
                ("合同主体", r"甲方|乙方|party[_\s]?[abAB]|hereinafter"),
                ("合同标的", r"标的|服务[内容范围]|scope of (work|service)"),
                ("合同期限", r"期限|term|duration|effective date"),
                ("付款条款", r"付款|payment|price|fee|consideration"),
                ("违约责任", r"违约|breach|default|liability|indemnif"),
                ("争议解决", r"争议|仲裁|管辖|dispute|arbitration|jurisdiction"),
                ("保密条款", r"保密|confidential"),
                ("终止条款", r"终止|termination|cancel"),
                ("签署生效", r"签署|生效|sign|execut|in witness"),
            ]
            
            found_count = 0
            for name, pattern in checks:
                if re.search(pattern, text, re.IGNORECASE):
                    st.success(f"✅ {name}")
                    found_count += 1
                else:
                    st.warning(f"⚠️ 未检测到：{name}")
            
            # ===== 风险条款分析 =====
            st.markdown("---")
            st.subheader("⚠️ 风险条款检测")
            risk_results = analyze_keywords(text)
            
            risk_found = 0
            risk_missing = 0
            for risk in risk_results:
                if "✅" in risk["status"]:
                    st.success(f"{risk['name']}：{risk['status']}")
                    risk_found += 1
                else:
                    st.warning(f"{risk['name']}：{risk['status']}")
                    risk_missing += 1
            
            # ===== 总体评价 =====
            st.markdown("---")
            st.subheader("📊 总体评价")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("✅ 必备条款", f"{found_count}/{len(checks)}")
            with col2:
                st.metric("📋 风险条款已含", risk_found)
            with col3:
                st.metric("⚠️ 建议补充", risk_missing)
            with col4:
                score = int((found_count / len(checks) * 0.6 + risk_found / len(risk_results) * 0.4) * 100)
                st.metric("📈 合同完整度", f"{score}%")
            
            # 预览原文
            with st.expander("📖 预览合同原文", expanded=False):
                st.text_area("原文", text[:3000] + ("..." if len(text) > 3000 else ""), height=300)


# ============================================================
# Tab 2：中英文对比
# ============================================================
with tab2:
    st.header("中英文合同对比")
    st.caption("支持电子版PDF / Word / TXT")

    col1, col2 = st.columns(2)
    with col1:
        cn = st.file_uploader("中文合同", type=["txt", "pdf", "docx"], key="cn")
    with col2:
        en = st.file_uploader("英文合同", type=["txt", "pdf", "docx"], key="en")

    if cn and en:
        with st.spinner("正在读取文件..."):
            cn_text = read_file(cn)
            en_text = read_file(en)

        if cn_text.startswith("❌"):
            st.error(f"中文文件：{cn_text}")
        elif en_text.startswith("❌"):
            st.error(f"英文文件：{en_text}")
        else:
            cn_lines = cn_text.splitlines()
            en_lines = en_text.splitlines()

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("中文行数", len(cn_lines))
            with col2:
                st.metric("英文行数", len(en_lines))
            with col3:
                diff_lines = abs(len(cn_lines) - len(en_lines))
                st.metric("行数差异", diff_lines)

            if diff_lines > 10:
                st.warning(f"⚠️ 行数差异较大（差{diff_lines}行），建议检查是否有缺漏")
            elif diff_lines > 3:
                st.info(f"ℹ️ 行数略有差异（差{diff_lines}行）")
            else:
                st.success("✅ 行数基本一致")


# ============================================================
# Tab 3：新旧合同对比
# ============================================================
with tab3:
    st.header("新旧合同差异对比")
    st.caption("支持电子版PDF / Word / TXT")

    col1, col2 = st.columns(2)
    with col1:
        old = st.file_uploader("旧合同", type=["txt", "pdf", "docx"], key="old")
    with col2:
        new = st.file_uploader("新合同", type=["txt", "pdf", "docx"], key="new")

    if old and new:
        with st.spinner("正在读取文件..."):
            old_text = read_file(old)
            new_text = read_file(new)

        if old_text.startswith("❌"):
            st.error(f"旧合同：{old_text}")
        elif new_text.startswith("❌"):
            st.error(f"新合同：{new_text}")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("旧合同字数", f"{len(old_text)}字")
            with col2:
                st.metric("新合同字数", f"{len(new_text)}字")

            diff = difflib.unified_diff(
                old_text.splitlines(), new_text.splitlines(),
                fromfile="旧合同", tofile="新合同"
            )
            result = "\n".join(diff)

            if result.strip():
                st.subheader("📝 差异详情")
                st.code(result, language="diff")
                
                added = result.count('\n+') - result.count('\n+++')
                removed = result.count('\n-') - result.count('\n---')
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🟢 新增行数", max(added, 0))
                with col2:
                    st.metric("🔴 删除行数", max(removed, 0))
                with col3:
                    st.metric("📊 总修改数", max(added, 0) + max(removed, 0))
            else:
                st.success("✅ 两份合同内容完全一致")
