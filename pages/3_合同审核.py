import streamlit as st
import pandas as pd
import docx
import pdfplumber
from io import BytesIO
import re

st.title("📄 合同条款提取与风险提示")
st.markdown("上传 Word 或 PDF 合同，自动提取关键条款并标注风险关键词。")

# 风险关键词列表（可根据业务扩展）
RISK_KEYWORDS = [
    "违约金", "滞纳金", "赔偿", "罚款", "不承担责任", "免责",
    "单方变更", "终止合同", "仲裁", "诉讼", "保密期限", "不可抗力"
]

def extract_text_from_docx(file):
    """从 Word 文档提取文本"""
    doc = docx.Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_text_from_pdf(file):
    """从 PDF 提取文本"""
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

uploaded_file = st.file_uploader(
    "上传合同文件（.docx / .pdf）",
    type=["docx", "pdf"]
)

if uploaded_file:
    # 提取文本
    if uploaded_file.name.endswith('.docx'):
        text = extract_text_from_docx(uploaded_file)
    elif uploaded_file.name.endswith('.pdf'):
        text = extract_text_from_pdf(uploaded_file)
    else:
        st.error("不支持的文件格式")
        st.stop()

    st.subheader("合同全文预览（前 2000 字）")
    st.text_area("原文", text[:2000], height=300)

    # 查找风险关键词
    found = []
    for kw in RISK_KEYWORDS:
        occurrences = [(m.start(), m.end()) for m in re.finditer(re.escape(kw), text)]
        if occurrences:
            # 取关键词附近上下文（前后50字符）
            for start, end in occurrences:
                ctx_start = max(0, start - 50)
                ctx_end = min(len(text), end + 50)
                snippet = text[ctx_start:ctx_end].replace('\n', ' ')
                found.append({
                    '关键词': kw,
                    '上下文': snippet
                })

    if found:
        st.subheader("⚠️ 风险提示")
        risk_df = pd.DataFrame(found)
        st.dataframe(risk_df)
        st.warning(f"共发现 {len(found)} 处风险关键词，请重点审查对应条款。")
    else:
        st.success("✅ 未发现预设风险关键词（仅供参考，仍需人工审核）")

    # 导出风险报告
    if found:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            risk_df.to_excel(writer, index=False, sheet_name='风险条款')
        output.seek(0)
        st.download_button(
            label="📥 下载风险报告.xlsx",
            data=output,
            file_name="风险报告.xlsx"
        )
