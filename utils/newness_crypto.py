# -*- coding: utf-8 -*-
"""
newness_crypto.py —— 新品上市看板数据的轻量级加密工具

用途：把从「2026 TR NEWNESS.pptx」提取出的敏感内容加密后落盘，
      只有知道密码(Max12345)的人才能解密查看，与其它并行项目隔离。

加密方式：PBKDF2 派生 32 字节密钥 + XOR 流密码(密钥流由 SHA256 链式生成)。
说明：这是「访问控制级」加密，目的是避免明文泄露、隔离敏感内容，
      并非高安全级军事加密，请勿用于极高保密场景。

文件格式：MAGIC(4) + salt(16) + verify(32, sha256(密码)) + cipher(变长)
"""
import base64
import hashlib
import os

MAGIC = b"NEW1"
PBKDF2_ROUNDS = 100_000


def _derive_key(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS, dklen=32)


def _keystream(key: bytes, length: int) -> bytes:
    """用 SHA256 链式生成伪随机流，长度不足则续算。"""
    out = b""
    counter = 0
    while len(out) < length:
        out += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:length]


def encrypt_data(plaintext: str, password: str) -> bytes:
    """把明文字符串加密为字节 blob。"""
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    verify = hashlib.sha256(password.encode("utf-8")).digest()  # 32 字节，用于校验密码
    data = plaintext.encode("utf-8")
    cipher = bytes(a ^ b for a, b in zip(data, _keystream(key, len(data))))
    return MAGIC + salt + verify + cipher


def decrypt_data(blob: bytes, password: str) -> str:
    """用密码解密 blob；密码错误抛 PermissionError；格式错误抛 ValueError。"""
    if blob[:4] != MAGIC:
        raise ValueError("文件格式不正确或已被损坏")
    body = blob[4:]
    salt = body[:16]
    verify = body[16:48]
    cipher = body[48:]
    if hashlib.sha256(password.encode("utf-8")).digest() != verify:
        raise PermissionError("密码错误")
    key = _derive_key(password, salt)
    data = bytes(a ^ b for a, b in zip(cipher, _keystream(key, len(cipher))))
    return data.decode("utf-8")


# 方便在命令行快速生成加密文件（可选）
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) != 4:
        print("用法: python newness_crypto.py <输入json> <输出bin> <密码>")
        sys.exit(1)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        text = f.read()
    blob = encrypt_data(text, sys.argv[3])
    with open(sys.argv[2], "wb") as f:
        f.write(blob)
    print(f"已加密写入: {sys.argv[2]} ({len(blob)} 字节)")
