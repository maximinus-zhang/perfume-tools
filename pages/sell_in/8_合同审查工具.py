import streamlit as st
import re
import difflib
from io import BytesIO
import tempfile
import os

st.set_page_config(page_title="合同审查工具", page_icon="📄", layout="wide")
st.title("📄 合同智能审查与对比工具（含OCR）")

tab1, tab2, tab3 = st.tabs(["🔍 风险审查", "🌐 中英文对比", "📊 新旧合同对比"])

# ============================================================
# OCR 功能（扫描版PDF识别）
# ============================================================
@st.cache_resource
def load_ocr_engine():
    """加载 OCR 引擎（首次会下载模型）"""
    try:
        import easyocr
        st.info("🔄 正在加载 OCR 模型（首次约需下载 100MB）...")
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
        return reader
    except ImportError:
        return None

def ocr_image(image):
    """对图片进行 OCR 识别"""
    reader = load_ocr_engine()
    if reader is None:
        return "❌ 请安装 easyocr：pip install easyocr"
    
    try:
        result = reader.readtext(image, detail=0, paragraph=True)
        return "\n".join(result)
    except Exception as e:
        return f"❌ OCR 识别失败：{e}"

# ============================================================
# 文件读取函数（支持 TXT / PDF / DOCX / 扫描PDF）
# ============================================================
def read_file(file):
    """读取上传的文件，支持 TXT、PDF（含扫描版）、DOCX"""
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
        # 先尝试用 pdfplumber 提取文字（电子版PDF）
        try:
            import pdfplumber
            text = ""
            with pdfplumber.open(BytesIO(content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # 如果提取到文字且长度足够，说明是电子版PDF
            if len(text.strip()) > 50:
                return text
            
            # 文字太少，可能是扫描版PDF，启动OCR
            st.info("🔍 检测到可能是扫描版PDF，正在启动OCR识别...")
            return read_scanned_pdf(content)
            
        except ImportError:
            # 没有 pdfplumber，尝试直接 OCR
            st.info("📦 正在安装PDF解析工具，同时启动OCR...")
            return read_scanned_pdf(content)
        except Exception as e:
            return f"❌ PDF 读取失败：{e}"
    
    else:
        return f"❌ 不支持的文件格式：{file_type}，请上传 TXT / PDF / DOCX"


def read_scanned_pdf(pdf_content):
    """读取扫描版PDF（通过OCR）"""
    try:
        from pdf2image import convert_from_bytes
        
        # 将PDF转为图片
        images = convert_from_bytes(pdf_content, dpi=300)
        st.info(f"📄 共 {len(images)} 页，正在进行OCR识别...")
        
        full_text = ""
        progress_bar = st.progress(0)
        
        for i, img in enumerate(images):
            # 更新进度
            progress_bar.progress((i + 1) / len(images))
            
            # OCR识别
            page_text = ocr_image(img)
            if page_text.startswith("❌"):
                return page_text
            
            full_text += f"\n=== 第 {i+1} 页 ===\n{page_text}\n"
        
        progress_bar.empty()
        
        if len(full_text.strip()) > 50:
            st.success(f"✅ OCR识别完成！共识别 {len(full_text)} 字")
            return full_text
        else:
            return "⚠️ OCR未能提取到有效文字，请确认PDF是否为清晰扫描件"
    
    except ImportError as e:
        missing_pkg = str(e).split("'")[1] if "'" in str(e) else "pdf2image"
        return f"❌ 请安装 {missing_pkg}：pip install {missing_pkg}"
    except Exception as e:
        return f"❌ OCR 处理失败：{e}"


# ============================================================
# Tab 1：风险审查
# ============================================================
with tab1:
    st.header("合同风险点审查")
    st.caption("支持电子版PDF / 扫描版PDF / Word / TXT")
    
    f = st.file_uploader(
        "上传合同文件",
        type=["txt", "pdf", "docx"],
        key="risk",
        help="支持电子版PDF、扫描版PDF（自动OCR识别）、Word文档、纯文本"
    )
    
    if f:
        with st.spinner("正在读取文件..."):
            text = read_file(f)
        
        if text.startswith("❌") or text.startswith("⚠️"):
            st.warning(text)
        else:
            # 显示文件信息
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"📄 文件：{f.name}")
            with col2:
                st.info(f"📝 字数：{len(text)}字")
            
            with st.expander("📖 预览合同原文", expanded=False):
                st.text_area("原文", text[:3000] + ("..." if len(text) > 3000 else ""), height=300)
            
            st.subheader("✅ 必备条款检查")
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
            
            # 总体评价
            st.markdown("---")
            ratio = found_count / len(checks)
            if ratio >= 0.8:
                st.success(f"✅ 总体评价：合同较完整（{found_count}/{len(checks)}）")
            elif ratio >= 0.5:
                st.warning(f"⚠️ 总体评价：合同基本完整，建议补充缺失条款（{found_count}/{len(checks)}）")
            else:
                st.error(f"❌ 总体评价：合同缺失较多必备条款，请谨慎签署（{found_count}/{len(checks)}）")

# ============================================================
# Tab 2：中英文对比
# ============================================================
with tab2:
    st.header("中英文合同对比")
    st.caption("支持电子版PDF / 扫描版PDF / Word / TXT")
    
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
    st.caption("支持电子版PDF / 扫描版PDF / Word / TXT")
    
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
                
                # 统计修改量
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
