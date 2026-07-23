# utils/oss_helper.py
import os
import streamlit as st
import oss2
import pandas as pd
from io import BytesIO
from datetime import datetime

# ===== 知识库工作簿（KB）统一读取：私有 OSS 优先，本地兜底 =====
# 文件本身存于用户自有阿里云 OSS（bucket=maximinus-flies），ACL=private，
# 仅持有密钥的 App（本地 / Streamlit Cloud）可读取；外部/他人无法直接下载。
# 采购/SELL IN 深度 页用 TR YTD 工作簿；品牌表现分析 页用 01零售报表 工作簿。
KB_OSS_KEY = "kb/2025 TR YTD Oct Sell in & Purchase. BE. 2026 Projection.xlsx"
KB_LOCAL = r"C:\Users\Maximinuszhang\Desktop\WorkBuddy\知识库\2025 TR YTD Oct Sell in & Purchase. BE. 2026 Projection.xlsx"
KB_OSS_KEY_BRAND = "kb/01零售报表-品牌合计总表_6.2026.xlsx"
KB_LOCAL_BRAND = r"C:\Users\Maximinuszhang\Desktop\WorkBuddy\知识库\01零售报表-品牌合计总表_6.2026.xlsx"

def get_bucket():
    """获取 OSS Bucket 对象"""
    auth = oss2.Auth(
        st.secrets["OSS_ACCESS_KEY"],
        st.secrets["OSS_SECRET_KEY"]
    )
    return oss2.Bucket(
        auth,
        "https://oss-cn-hangzhou.aliyuncs.com",
        "maximinus-flies"
    )

def upload_to_oss(file, remote_path: str):
    """上传文件到 OSS"""
    bucket = get_bucket()
    bucket.put_object(remote_path, file.read())
    st.cache_data.clear()

def read_excel_from_oss(remote_path: str, sheet_name: int = 1, prefix_filter: str = None) -> pd.DataFrame:
    """
    从 OSS 读取 Excel 文件，默认读取第二个 Sheet（索引 1），自动寻找数据表头
    参数：
        remote_path: OSS 中的文件路径
        sheet_name: Sheet 索引，1=第二个Sheet（数据通常在这里）
        prefix_filter: 可选，只保留该前缀开头的行（如 'ORD-' 或 'PO-'）
    """
    try:
        bucket = get_bucket()
        # 文件尚未上传 / 不存在 → 静默返回空，让调用方回落本地，避免弹红色错误
        if not bucket.object_exists(remote_path):
            return pd.DataFrame()
        obj = bucket.get_object(remote_path)
        
        # 先读取全部数据（不指定 header），扫描找到真正的表头行
        # 优先 calamine（忽略样式，兼容个别 openpyxl 解析失败的 xlsx），失败回落 openpyxl
        df_raw = _read_excel_robust(BytesIO(obj.read()), sheet_name=sheet_name, header=None)
        
        # 去除全空行
        df_raw = df_raw.dropna(how='all').reset_index(drop=True)
        
        if df_raw.empty:
            return df_raw
        
        # 查找包含订单号/采购单号/品牌等关键字的行作为表头
        header_row = None
        keywords = ['订单号', '采购单号', '品牌', '产品类别', '门店', '供应商']
        for i in range(len(df_raw)):
            row_values = df_raw.iloc[i].astype(str).tolist()
            for kw in keywords:
                if any(kw in str(v) for v in row_values):
                    header_row = i
                    break
            if header_row is not None:
                break
        
        if header_row is None:
            header_row = 0
        
        # 重新读取，指定正确的表头行
        obj2 = bucket.get_object(remote_path)
        df = _read_excel_robust(BytesIO(obj2.read()), sheet_name=sheet_name, header=header_row)
        
        # 去除全空行
        df = df.dropna(how='all').reset_index(drop=True)
        # 去除全空列
        df = df.dropna(axis=1, how='all')
        
        # 清理列名中的空格
        df.columns = [str(c).strip() for c in df.columns]
        
        # 如果指定了前缀过滤，只保留有效数据行
        if prefix_filter and not df.empty:
            first_col = df.columns[0]
            df = df[df[first_col].astype(str).str.startswith(prefix_filter, na=False)]
            df = df.reset_index(drop=True)
        
        return df
    except Exception as e:
        st.error(f"OSS 读取错误：{e}")
        return pd.DataFrame()

def read_csv_from_oss(remote_path: str) -> pd.DataFrame:
    try:
        bucket = get_bucket()
        obj = bucket.get_object(remote_path)
        return pd.read_csv(BytesIO(obj.read()))
    except Exception as e:
        st.error(f"CSV 读取错误：{e}")
        return pd.DataFrame()

def upload_section(remote_path: str, label: str = "上传数据文件"):
    with st.sidebar.expander(f"📤 {label}", expanded=False):
        uploaded = st.file_uploader(
            "选择 Excel/CSV 文件",
            type=["xlsx", "xls", "csv"],
            key=f"upload_{remote_path}"
        )
        if uploaded:
            with st.spinner("正在上传到云端..."):
                upload_to_oss(uploaded, remote_path)
            st.success(f"✅ 上传成功！{datetime.now().strftime('%H:%M:%S')}")

# ===== 知识库（KB）Excel 读取：私有 OSS 优先，本地兜底 =====
def read_excel_raw_from_oss(remote_path: str):
    """返回 OSS 对象的 BytesIO；不存在或出错返回 None（调用方回落本地）。"""
    try:
        bucket = get_bucket()
        if not bucket.object_exists(remote_path):
            return None
        return BytesIO(bucket.get_object(remote_path).read())
    except Exception:
        return None

def _read_excel_robust(src, **kwargs):
    """读取 Excel：优先 calamine（Rust 解析、忽略样式，兼容个别 openpyxl 解析失败的 xlsx），
    失败回落 openpyxl。src 可为本地路径或 BytesIO。"""
    last_err = None
    for eng in ("calamine", "openpyxl"):
        try:
            return pd.read_excel(src, engine=eng, **kwargs)
        except Exception as e:
            last_err = e
    raise last_err

def _excelfile_robust(src, **kwargs):
    """同 _read_excel_robust，但返回 ExcelFile 对象（用于列举/解析多个 sheet）。"""
    last_err = None
    for eng in ("calamine", "openpyxl"):
        try:
            return pd.ExcelFile(src, engine=eng, **kwargs)
        except Exception as e:
            last_err = e
    raise last_err

def read_kb_excel(sheet_name, header=None, engine=None,
                  oss_key=KB_OSS_KEY, local_path=KB_LOCAL, **kwargs):
    """读取 KB 工作簿指定 sheet。优先私有 OSS，读不到回落本地路径。
    engine=None 时自动选用 calamine（优先）→ openpyxl（兜底）；也可显式指定单一引擎。
    其余关键字参数（如 usecols）透传给 pd.read_excel。"""
    data = read_excel_raw_from_oss(oss_key)
    src = data if data is not None else local_path
    if engine:
        return pd.read_excel(src, sheet_name=sheet_name, header=header, engine=engine, **kwargs)
    return _read_excel_robust(src, sheet_name=sheet_name, header=header, **kwargs)

def kb_excelfile(engine=None, oss_key=KB_OSS_KEY, local_path=KB_LOCAL):
    """返回 KB 工作簿的 ExcelFile 对象（用于列举 sheet_names）。优先 OSS，回落本地。
    engine=None 时自动 calamine→openpyxl 兜底。"""
    data = read_excel_raw_from_oss(oss_key)
    src = data if data is not None else local_path
    if engine:
        return pd.ExcelFile(src, engine=engine)
    return _excelfile_robust(src)

def kb_available(oss_key=KB_OSS_KEY, local_path=KB_LOCAL):
    """KB 数据是否可获取（本地文件存在 或 私有 OSS 对象可读取）。"""
    if os.path.exists(local_path):
        return True
    try:
        return read_excel_raw_from_oss(oss_key) is not None
    except Exception:
        return False
