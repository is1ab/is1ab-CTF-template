#!/usr/bin/env python3
"""
生成 RSA 挑戰題目
使用極小的質數以便分解

分解方法（選手可用）：
1. factordb.com - 直接查詢 n 的因數
2. yafu - 本地分解工具: yafu "factor(n)"
3. SageMath - factor(n)
4. Fermat's factorization - 當 p 和 q 接近時有效
"""

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import os
from pathlib import Path

# 弱質數（故意使用容易分解的小質數）
# 這些質數已在 factordb.com 中收錄，選手可直接查詢
p = 1000000007  # 10^9 + 7，著名質數
q = 1000000009  # 10^9 + 9，著名質數

# 計算 RSA 參數
n = p * q
e = 65537

# 計算私鑰
phi_n = (p - 1) * (q - 1)
d = pow(e, -1, phi_n)

print(f"[*] Generating weak RSA keys...")
print(f"    p = {p}")
print(f"    q = {q}")
print(f"    n = {n}")
print(f"    e = {e}")
print(f"    Key size: ~{n.bit_length()} bits")

# 創建 RSA 密鑰
key = RSA.construct((n, e, d, p, q))

# 確保 files 目錄存在
files_dir = Path(__file__).parent.parent / "files"
files_dir.mkdir(parents=True, exist_ok=True)

# 儲存公鑰
public_key = key.publickey()
pubkey_path = files_dir / "public_key.pem"
with open(pubkey_path, 'wb') as f:
    f.write(public_key.export_key('PEM'))
print(f"[+] Public key saved to {pubkey_path}")

# 加密 flag
flag = b"FLAG{w34k_rsa_k3y_1s_vuln3r4bl3}"
cipher = PKCS1_OAEP.new(public_key)
ciphertext = cipher.encrypt(flag)

# 儲存加密後的 flag
encrypted_path = files_dir / "encrypted_flag.txt"
with open(encrypted_path, 'wb') as f:
    f.write(ciphertext)
print(f"[+] Encrypted flag saved to {encrypted_path}")

# 驗證解密
cipher_private = PKCS1_OAEP.new(key)
decrypted = cipher_private.decrypt(ciphertext)
assert decrypted == flag, "Decryption failed!"
print(f"[+] Verification successful: {decrypted.decode()}")

print(f"\n[*] Challenge files generated successfully!")
