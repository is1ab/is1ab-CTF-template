#!/usr/bin/env python3
"""
RSA Beginner - 解題腳本

分解 n 的方法：
1. factordb.com - 直接在網站查詢 n 的因數
2. yafu - 命令行工具: yafu "factor(1000000007000000063)"
3. SageMath - factor(1000000007000000063)
4. 在線工具 - alpertron.com.ar/ECM.HTM
"""

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from pathlib import Path
import os

print("[*] RSA Weak Key Attack")
print("="*50)

# 確定文件路徑
script_dir = Path(__file__).parent
files_dir = script_dir.parent / "files"

# 讀取公鑰
pubkey_path = files_dir / "public_key.pem"
if not pubkey_path.exists():
    print(f"[!] Public key not found at {pubkey_path}")
    print("[!] Please run generate.py first")
    exit(1)

with open(pubkey_path, 'rb') as f:
    public_key = RSA.import_key(f.read())

n = public_key.n
e = public_key.e

print(f"[*] Public key parameters:")
print(f"    n = {n}")
print(f"    e = {e}")
print(f"    Key size: {n.bit_length()} bits")

# 分解 n
print(f"\n[*] Factoring n...")
print(f"    方法 1: 訪問 factordb.com 查詢")
print(f"    方法 2: yafu \"factor({n})\"")
print(f"    方法 3: SageMath: factor({n})")

# 這些質數可以在 factordb.com 找到
p = 1000000007  # 10^9 + 7
q = 1000000009  # 10^9 + 9

# 驗證
assert p * q == n, "Factorization incorrect!"
print(f"[+] Found factors:")
print(f"    p = {p}")
print(f"    q = {q}")

# 計算私鑰
print(f"\n[*] Computing private key...")
phi_n = (p - 1) * (q - 1)
d = pow(e, -1, phi_n)
print(f"[+] Private exponent d = {d}")

# 重建完整密鑰
print(f"\n[*] Reconstructing private key...")
private_key = RSA.construct((n, e, d, p, q))

# 讀取加密的 flag
print(f"\n[*] Reading encrypted flag...")
encrypted_path = files_dir / "encrypted_flag.txt"
if not encrypted_path.exists():
    print(f"[!] Encrypted flag not found at {encrypted_path}")
    print("[!] Please run generate.py first")
    exit(1)

with open(encrypted_path, 'rb') as f:
    ciphertext = f.read()

# 解密
print(f"[*] Decrypting...")
cipher = PKCS1_OAEP.new(private_key)
flag = cipher.decrypt(ciphertext)

print(f"\n{'='*50}")
print(f"🏁 Flag: {flag.decode()}")
print(f"{'='*50}")
