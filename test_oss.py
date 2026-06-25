import oss2
import pandas as pd
from io import BytesIO

auth = oss2.Auth('LTAI5t7pnRCMHbQboqKKASdo', 'kLnIaGp59TuWoHxzGiToTqQrEewTwP')
bucket = oss2.Bucket(auth, 'https://oss-cn-shanghai.aliyuncs.com', 'files-maximinus')

print("=== OSS 中的文件列表 ===")
for obj in oss2.ObjectIteratorV2(bucket):
    print(f"  📄 {obj.key}  ({obj.size} bytes)")

print("\n=== 尝试读取 order_data.xlsx ===")
try:
    obj = bucket.get_object("logistics/order_data.xlsx")
    df = pd.read_excel(BytesIO(obj.read()))
    print(f"读取成功！共 {len(df)} 行")
    print(f"列名：{list(df.columns)}")
    print(df.head(5))
except Exception as e:
    print(f"读取失败：{e}")
