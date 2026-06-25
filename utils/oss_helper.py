# utils/oss_helper.py
import streamlit as st
import oss2
import pandas as pd
from io import BytesIO
from datetime import datetime

def get_bucket():
    """获取 OSS Bucket 对象"""
    auth = oss2.Auth(
        st.secrets["OSS_ACCESS_KEY"],
        st.secrets["OSS_SECRET_KEY"]
    )
    return oss2.Bucket(
        auth,
        "https://oss-cn-shanghai.aliyuncs.com",
        "files-maximinus"
    )

def upload_to_oss(file, remote_path: str):
    """上传文件到 OSS"""
    bucket = get_bucket()
    bucket.put_object(remote_path, file.read())
    st.cache_data.clear()

def read_excel_from_oss(remote_path: str, sheet_name: int = 0, prefix_filter: str = None) -> pd.DataFrame:
    """
    从 OSS 读取 Excel 文件
    
    参数：
        remote_path: OSS 中的文件路径
        sheet_name: Sheet 索引，0=第一个Sheet
        prefix_filter: 可选，只保留该前缀开头的行（如 'ORD-' 或 'PO-'）
    """
    try:
        bucket = get_bucket()
        obj = bucket.get_object(remote_path)
        df = pd.read_excel(BytesIO(obj.read()), sheet_name=sheet_name)

        # 1. 去除全空行
        df = df.dropna(how='all').reset_index(drop=True)
        # 2. 去除全空列
        df = df.dropna(axis=1, how='all')

        if df.empty:
            return df

        # 3. 如果指定了前缀过滤，只保留有效数据行
        if prefix_filter:
            first_col = df.columns[0]
            df = df[df[first_col].astype(str).str.startswith(prefix_filter, na=False)]
            df = df.reset_index(drop=True)

        return df
    except Exception:
        return pd.DataFrame()

def read_csv_from_oss(remote_path: str) -> pd.DataFrame:
    try:
        bucket = get_bucket()
        obj = bucket.get_object(remote_path)
        return pd.read_csv(BytesIO(obj.read()))
    except Exception:
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
