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
        "https://oss-cn-shanghai.aliyuncs.com",  # 你的 Endpoint
        "files-maximinus"                          # 你的 Bucket 名称
    )

def upload_to_oss(file, remote_path: str):
    """上传文件到 OSS，remote_path 如 'sell_in/purchase.xlsx'"""
    bucket = get_bucket()
    bucket.put_object(remote_path, file.read())
    st.cache_data.clear()  # 清除缓存，强制刷新

def read_excel_from_oss(remote_path: str) -> pd.DataFrame:
    """从 OSS 读取 Excel 文件"""
    try:
        bucket = get_bucket()
        obj = bucket.get_object(remote_path)
        return pd.read_excel(BytesIO(obj.read()))
    except Exception:
        return pd.DataFrame()  # 文件不存在时返回空 DataFrame

def read_csv_from_oss(remote_path: str) -> pd.DataFrame:
    """从 OSS 读取 CSV 文件"""
    try:
        bucket = get_bucket()
        obj = bucket.get_object(remote_path)
        return pd.read_csv(BytesIO(obj.read()))
    except Exception:
        return pd.DataFrame()

def upload_section(remote_path: str, label: str = "上传数据文件"):
    """通用上传组件，所有页面共用"""
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
