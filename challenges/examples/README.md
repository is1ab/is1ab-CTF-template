# 📚 CTF Challenge Examples

這個目錄包含不同類型的 CTF 題目範例，展示如何使用此 template 創建各種類型的題目。

## 🎯 範例清單

### 1. PWN - Buffer Overflow 101
**路徑**: `pwn/buffer_overflow/`

- **類型**: NC Challenge (需要 socat)
- **難度**: Easy
- **分數**: 150
- **技術**: Stack Buffer Overflow, RIP Control
- **連線方式**: `nc <host> 9999`

**特色**：
- ✅ 完整的 C 源碼 (`src/chall.c`)
- ✅ Dockerfile 和 docker-compose 配置
- ✅ 使用 socat 提供 NC 服務
- ✅ 包含完整的 exploit 腳本 (pwntools)
- ✅ 建構腳本 (`docker/build.sh`)

**快速開始**：
```bash
cd pwn/buffer_overflow/docker
./build.sh
docker compose up -d
nc localhost 9999
```

---

### 2. WEB - SQL Injection 101
**路徑**: `web/sql_injection/`

- **類型**: Static Container (Web Service)
- **難度**: Easy
- **分數**: 100
- **技術**: SQL Injection, Authentication Bypass
- **訪問方式**: `http://localhost:8080`

**特色**：
- ✅ Flask Web 應用程式
- ✅ 漂亮的 HTML/CSS 介面
- ✅ SQLite 資料庫
- ✅ Docker 容器化部署
- ✅ Python exploit 腳本

**快速開始**：
```bash
cd web/sql_injection/docker
docker compose up -d
# 訪問 http://localhost:8080
```

---

### 3. CRYPTO - RSA for Beginners
**路徑**: `crypto/rsa_beginner/`

- **類型**: Static Attachment (純附件題)
- **難度**: Easy
- **分數**: 120
- **技術**: Weak RSA Key, Integer Factorization
- **附件**: public_key.pem, encrypted_flag.txt

**特色**：
- ✅ RSA 弱密鑰攻擊
- ✅ 題目生成腳本 (`src/generate.py`)
- ✅ 解題腳本 (`solution/solve.py`)
- ✅ 不需要 Docker（純靜態附件）
- ✅ 使用 pycryptodome

**快速開始**：
```bash
cd crypto/rsa_beginner/src
python3 generate.py  # 生成題目附件
cd ../solution
python3 solve.py     # 解題
```

---

### 4. REVERSE - Simple Crackme
**路徑**: `reverse/simple_crackme/`

- **類型**: Static Attachment (執行檔)
- **難度**: Easy
- **分數**: 130
- **技術**: Static Analysis, Password Check
- **附件**: crackme (ELF binary)

**特色**：
- ✅ 簡單的密碼驗證程式
- ✅ 適合逆向工程入門
- ✅ 可用 strings / ltrace 解決
- ✅ 不需要 Docker

---

### 5. MISC - Hidden Message
**路徑**: `misc/forensics_basic/`

- **類型**: Static Attachment (圖片檔)
- **難度**: Baby
- **分數**: 50
- **技術**: Forensics, File Analysis
- **附件**: image.png

**特色**：
- ✅ 基礎 forensics 入門
- ✅ 使用 strings 即可解決
- ✅ 適合完全新手
- ✅ 不需要 Docker

---

## 📋 範例比較表

| 類型 | 範例名稱 | 難度 | 需要 Docker | NC 服務 | Web 服務 | 附件檔案 |
|------|---------|------|------------|---------|---------|---------|
| PWN | Buffer Overflow | Easy | ✅ | ✅ | ❌ | ✅ (chall, libc) |
| WEB | SQL Injection | Easy | ✅ | ❌ | ✅ | ❌ |
| CRYPTO | RSA Beginner | Easy | ❌ | ❌ | ❌ | ✅ (pem, txt) |
| REVERSE | Simple Crackme | Easy | ❌ | ❌ | ❌ | ✅ (binary) |
| MISC | Hidden Message | Baby | ❌ | ❌ | ❌ | ✅ (png) |

---

## 🛠️ 使用這些範例

### 複製範例作為新題目

```bash
# 複製 PWN 範例
cp -r challenges/examples/pwn/buffer_overflow challenges/pwn/my_new_pwn

# 修改配置
cd challenges/pwn/my_new_pwn
# 編輯 public.yml, private.yml, README.md
# 修改源碼和 Docker 配置
```

### 學習範例結構

每個範例都包含：

```
challenge_name/
├── public.yml          # 公開配置（分數、描述、提示）
├── private.yml         # 私密配置（flag、解法、測試）
├── README.md           # 題目說明
├── src/               # 源碼
├── docker/            # Docker 配置（如需要）
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── build.sh       # 建構腳本
├── solution/          # 官方解答
│   ├── exploit.py     # Exploit 腳本
│   └── README.md      # 解題步驟
├── files/             # 提供給選手的附件
└── writeup/           # Writeup（可選）
```

---

## 🔧 必要工具

### PWN 題目
```bash
# Python 環境
pip install pwntools

# Docker（for deployment）
docker --version
docker compose --version
```

### WEB 題目
```bash
# Python 環境
pip install flask

# 測試工具
sudo apt install curl
```

### CRYPTO 題目
```bash
# Python cryptography
pip install pycryptodome

# OpenSSL
openssl version
```

### REVERSE 題目
```bash
# 編譯工具
sudo apt install gcc build-essential

# 分析工具
sudo apt install binutils gdb
# IDA Pro / Ghidra（可選）
```

### MISC 題目
```bash
# 基本工具
sudo apt install binutils exiftool

# Python 環境
pip install pillow
```

---

## 📖 延伸閱讀

### 創建新題目

1. 參考對應類型的範例
2. 使用 `challenge-template/` 作為起點
3. 閱讀 `wiki/Challenge-Development.md`
4. 遵循 `docs/security-checklist.md`

### 測試題目

```bash
# 本地測試（PWN 範例）
cd challenges/examples/pwn/buffer_overflow/docker
./build.sh
docker compose up -d
nc localhost 9999

# 運行官方解答
cd ../solution
python3 exploit.py
```

### 部署到 Public Release

```bash
# 確保 ready_for_release: true
vim public.yml

# 執行 build script
./scripts/build.sh challenges/examples/pwn/buffer_overflow public-release

# 檢查 public-release 目錄
ls -la public-release/
```

---

## 🎓 學習路徑建議

### 初學者
1. 先看 **MISC - Hidden Message** (最簡單)
2. 嘗試 **CRYPTO - RSA Beginner** (純邏輯)
3. 挑戰 **REVERSE - Simple Crackme** (基礎逆向)

### 進階者
1. **WEB - SQL Injection** (Web 安全)
2. **PWN - Buffer Overflow** (Binary Exploitation)

### 出題者
- 研究每個範例的完整結構
- 了解 public.yml vs private.yml 的分離原則
- 學習如何撰寫好的提示和 writeup

---

## 🤝 貢獻範例

如果您創建了新的範例題目，歡迎提交 PR！

**要求**：
- 完整的 public.yml 和 private.yml
- 可運行的源碼和 solution
- 清楚的 README 說明
- 通過 security scan（無 flag 洩漏）

---

## ⚠️ 注意事項

1. **這些範例都是故意設計的脆弱程式**
   - 請勿在生產環境使用
   - 僅供 CTF 教學用途

2. **Flag 安全**
   - 範例的 flag 都寫在 private.yml 中
   - 發布前務必執行 `scripts/scan-secrets.py`

3. **Docker 安全**
   - 範例的 Docker 配置已包含基本安全設定
   - 生產環境請加強 resource limits 和 security_opt

---

**最後更新**: 2026-01-18
**維護者**: IS1AB Team
