# -*- coding: utf-8 -*-
"""
把「海南免税香水深度竞品分析」HTML 报告上传到阿里云 OSS，生成可分享链接。

用法（在 perfume-tools-main 目录下，Windows）：
    python upload_report_to_oss.py            # 默认【私有 + 365天签名链接】（你的 Bucket 禁止公共读）
    python upload_report_to_oss.py --public   # 尝试公共读（Bucket 禁止则自动回落签名链接）
    python upload_report_to_oss.py --days 30  # 自定义签名链接有效期天数

凭证来源（按顺序，不会在屏幕上打印密钥）：
    1. 环境变量  OSS_ACCESS_KEY / OSS_SECRET_KEY
    2. 本地文件  .streamlit/secrets.toml  里的 OSS_ACCESS_KEY / OSS_SECRET_KEY
       （应用读取知识库 xlsx 用的也是这对凭证，已配好即可直接用）

说明：
    - 上传的是「竞品分析报告 HTML」，不含你的原始销售数据。
    - 你的 Bucket（maximinus-flies）已开启「阻止公共访问」，对象无法设为公共读，
      因此默认用【私有 + 签名链接】分享——链接带时效与签名，只有持链接者能打开，更安全。
    - 若以后 Bucket 允许公共读，可加 --public 生成无签名的长链。
"""

import os
import sys
import argparse
import urllib.parse

try:
    import oss2
except ImportError:
    print("❌ 缺少 oss2 库，请先安装：pip install oss2")
    sys.exit(1)

# ===== 配置（与 utils/oss_helper.py 保持一致）=====
OSS_ENDPOINT = "https://oss-cn-hangzhou.aliyuncs.com"
OSS_BUCKET = "maximinus-flies"
# 报告在本地项目里的位置（相对本脚本）
LOCAL_HTML = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "reports", "海南免税香水竞品分析.html"
)
# 上传到 OSS 的对象路径
OSS_KEY = "reports/海南免税香水竞品分析.html"


def load_credentials():
    """从环境变量 或 .streamlit/secrets.toml 读取 OSS 凭证（密钥不外印）。"""
    ak = os.environ.get("OSS_ACCESS_KEY")
    sk = os.environ.get("OSS_SECRET_KEY")
    if ak and sk:
        return ak, sk
    # 回落：读 .streamlit/secrets.toml
    secrets_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml"
    )
    if os.path.exists(secrets_path):
        try:
            import tomllib
            with open(secrets_path, "rb") as f:
                data = tomllib.load(f)
            ak = data.get("OSS_ACCESS_KEY")
            sk = data.get("OSS_SECRET_KEY")
            if ak and sk:
                return ak, sk
        except Exception as e:
            print(f"⚠️ 读取 .streamlit/secrets.toml 失败：{e}")
    print(
        "❌ 未找到 OSS 凭证。请二选一：\n"
        "  1) 设置环境变量 OSS_ACCESS_KEY / OSS_SECRET_KEY\n"
        "  2) 在 .streamlit/secrets.toml 配置 OSS_ACCESS_KEY / OSS_SECRET_KEY"
    )
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="上传深度竞品分析 HTML 到 OSS")
    parser.add_argument(
        "--public", action="store_true",
        help="尝试设为公共读（若 Bucket 禁止公共访问则自动回落为签名链接）"
    )
    parser.add_argument(
        "--days", type=int, default=365,
        help="签名链接有效期天数（默认 365 天）"
    )
    args = parser.parse_args()

    if not os.path.exists(LOCAL_HTML):
        print(f"❌ 本地报告文件未找到：{LOCAL_HTML}")
        sys.exit(1)

    ak, sk = load_credentials()
    auth = oss2.Auth(ak, sk)
    bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET)

    # 上传 HTML（指定内容类型，浏览器直接渲染而不是下载）
    with open(LOCAL_HTML, "rb") as f:
        bucket.put_object(
            OSS_KEY, f,
            headers={"Content-Type": "text/html; charset=utf-8"}
        )

    if args.public:
        # 用户主动要求公共读；若 Bucket 开启了「阻止公共访问」会失败，自动回落签名
        try:
            bucket.put_object_acl(OSS_KEY, oss2.OBJECT_ACL_PUBLIC_READ)
            base = f"https://{OSS_BUCKET}.oss-cn-hangzhou.aliyuncs.com"
            encoded_key = urllib.parse.quote(OSS_KEY, safe="/")
            url = f"{base}/{encoded_key}"
            print("✅ 已设为【公开读】，下面是可分享链接")
            print("   （任何人拿到链接都能打开，请勿在报告里放机密数据）：")
        except Exception:
            url = bucket.sign_url("GET", OSS_KEY, args.days * 24 * 3600)
            print("⚠️ 该 Bucket 已开启「阻止公共访问」，无法设为公共读。")
            print(f"   已自动改为【私有 + {args.days} 天签名链接】（更安全的分享方式）：")
    else:
        # 默认：私有 + 签名链接（你的 Bucket 禁止公共读，这样最稳，也更符合数据敏感偏好）
        url = bucket.sign_url("GET", OSS_KEY, args.days * 24 * 3600)
        print(f"✅ 已上传为【私有】，生成 {args.days} 天有效的签名分享链接：")
        print("   （链接带时效与签名，只有持链接者能打开，安全性更高）")

    print("\n   " + url + "\n")
    print("💡 报告内容更新后，重新生成 HTML 覆盖 reports/ 下文件，再跑一次本脚本即可覆盖。")


if __name__ == "__main__":
    main()
