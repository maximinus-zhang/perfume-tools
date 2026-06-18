import streamlit as st
import pandas as pd
from io import BytesIO
import os

st.title("📊 每日报表合并")
st.markdown("上传多个 Excel 文件，按「门店」或「品牌」列自动合并成一张总表。")

# 缓存函数：读取 Excel（避免重复读）
@st.cache_data
def load_excel(uploaded_file):
    return pd.read_excel(uploaded_file)

uploaded_files = st.file_uploader(
    "上传 Excel 文件（支持 .xlsx / .xls）",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"已上传 {len(uploaded_files)} 个文件")

    # 读取所有文件并添加来源文件名
    all_dfs = []
    for f in uploaded_files:
        df = load_excel(f)
        df['来源文件'] = f.name
        all_dfs.append(df)

    combined = pd.concat(all_dfs, ignore_index=True)

    st.subheader("合并预览（前 20 行）")
    st.dataframe(combined.head(20))

    # 可选：按某列排序
    sort_col = st.selectbox("排序依据列（可选）", options=combined.columns.tolist())
    if sort_col:
        combined = combined.sort_values(by=sort_col)

    # 导出为 Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        combined.to_excel(writer, index=False, sheet_name='合并报表')
    output.seek(0)

    st.download_button(
        label="📥 下载合并报表.xlsx",
        data=output,
        file_name="合并报表.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("请上传至少一个 Excel 文件")
