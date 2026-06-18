import streamlit as st
import pandas as pd
from io import BytesIO

st.title("📦 库存匹配与分配")
st.markdown("上传「库存表」和「订单表」，设置安全库存天数，一键匹配并手动调整。")

# 功能：库存匹配算法（可编辑）
def match_inventory(inv_df, order_df, safety_days=30):
    """
    简单匹配逻辑：按金额/门店等级分配，这里示例为按订单数量与库存比例分配
    实际业务逻辑请自行替换
    """
    # 模拟合并：假设两表都有 'SKU' 列
    merged = order_df.merge(inv_df, on='SKU', how='left', suffixes=('_订单', '_库存'))
    # 假设库存数量列名为 '库存数量'，订单数量列名为 '数量'
    if '数量' in merged.columns and '库存数量' in merged.columns:
        # 根据安全库存天数调整分配 (demo)
        merged['建议分配'] = merged['数量'] * (safety_days / 30)
        merged['实际分配'] = merged[['库存数量', '建议分配']].min(axis=1)
    else:
        st.error("请确保订单表有 '数量' 列，库存表有 '库存数量' 列")
    return merged

col1, col2 = st.columns(2)
with col1:
    inv_file = st.file_uploader("上传库存表（Excel）", type=["xlsx", "xls"], key="inv")
with col2:
    order_file = st.file_uploader("上传订单表（Excel）", type=["xlsx", "xls"], key="order")

if inv_file and order_file:
    inv_df = pd.read_excel(inv_file)
    order_df = pd.read_excel(order_file)

    st.subheader("库存表预览")
    st.dataframe(inv_df.head())
    st.subheader("订单表预览")
    st.dataframe(order_df.head())

    safety_days = st.slider("安全库存天数", min_value=7, max_value=90, value=30, step=1)

    if st.button("开始匹配"):
        result = match_inventory(inv_df, order_df, safety_days)
        st.session_state['match_result'] = result  # 存入 session
        st.success("匹配完成！")

if 'match_result' in st.session_state:
    st.subheader("匹配结果（可编辑）")
    edited = st.data_editor(st.session_state['match_result'], num_rows="dynamic")

    # 导出编辑后的结果
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        edited.to_excel(writer, index=False, sheet_name='匹配结果')
    output.seek(0)
    st.download_button(
        label="📥 下载匹配结果.xlsx",
        data=output,
        file_name="匹配结果.xlsx"
    )
else:
    st.info("上传两份文件后点击「开始匹配」")
