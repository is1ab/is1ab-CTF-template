# RSA for Beginners

> RSA 弱密鑰攻擊入門題

## 📝 題目描述

我用 RSA 加密了 flag，但我的公鑰有點小...

## 🎯 學習目標

- 理解 RSA 加密的基本原理
- 學習如何攻擊弱密鑰
- 掌握模運算和整數分解

## 🔧 環境需求

- **難度**: Easy
- **分類**: CRYPTO
- **分數**: 120
- **預估解題時間**: 25 分鐘

## 📦 附件

- `public_key.pem` - RSA 公鑰
- `encrypted_flag.txt` - 加密後的 flag

## 💡 提示

### 提示 1 (免費)
檢查一下公鑰的大小。
RSA 的安全性與密鑰長度有關。

### 提示 2 (10分)
n 的值很小，可以直接分解。
試試看線上的整數分解工具，例如 factordb.com

### 提示 3 (25分)
分解 n 得到 p 和 q 後：
1. 計算 φ(n) = (p-1)(q-1)
2. 計算私鑰 d = e^(-1) mod φ(n)
3. 解密: m = c^d mod n

## 🛠️ 推薦工具

- Python (pycryptodome)
- FactorDB
- RsaCtfTool
- openssl

## 📚 參考資料

- [RSA 加密演算法](https://en.wikipedia.org/wiki/RSA_(cryptosystem))
- [FactorDB](http://factordb.com/)

---

**作者**: admin
**創建時間**: 2026-01-18
**最後更新**: 2026-01-18
