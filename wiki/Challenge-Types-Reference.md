# 📋 CTF 題目類型快速參考

> 快速查找不同類型題目的配置方式

## 🎯 題目類型概覽

| 類型 | challenge_type | 需要 Docker | 需要端口 | 範例 |
|------|---------------|------------|---------|------|
| **PWN (NC)** | `nc_challenge` | ✅ | ✅ | buffer_overflow |
| **WEB** | `static_container` | ✅ | ✅ | sql_injection |
| **CRYPTO** | `static_attachment` | ❌ | ❌ | rsa_beginner |
| **REVERSE** | `static_attachment` | ❌ | ❌ | simple_crackme |
| **MISC** | `static_attachment` | ❌ | ❌ | forensics_basic |

---

## 1️⃣ PWN - NC Challenge

### 特徵
- 需要 **socat** 提供 NC 服務
- 使用 **Docker** 容器化
- 提供二進制檔案給選手下載

### public.yml 配置
```yaml
challenge_type: "nc_challenge"

deploy_info:
  nc_port: 9999           # NC 服務端口
  timeout: 60             # 連線超時（秒）
  requires_build: true

  resources:
    memory: "128Mi"
    cpu: "50m"
```

### Docker 結構
```dockerfile
# Dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y socat
COPY chall /home/ctf/chall
CMD ["socat", "TCP-LISTEN:9999,reuseaddr,fork", "EXEC:./chall,stderr"]
```

### 必要文件
- `src/chall.c` - C 源碼
- `src/Makefile` - 編譯腳本
- `docker/Dockerfile` - Docker 配置
- `docker/docker-compose.yml` - 服務配置
- `docker/build.sh` - 建構腳本
- `solution/exploit.py` - Pwntools 腳本

### 連線方式
```bash
nc <host> 9999
```

---

## 2️⃣ WEB - Static Container

### 特徵
- 需要 **Web 服務**（Flask/Node.js/PHP 等）
- 使用 **Docker** 容器化
- 通常包含資料庫

### public.yml 配置
```yaml
challenge_type: "static_container"

deploy_info:
  port: 8080              # Web 服務端口
  url: ""                 # 部署後的 URL（比賽時填入）
  requires_build: true

  resources:
    memory: "256Mi"
    cpu: "100m"
```

### Docker 結構
```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY src/ /app/
RUN pip install -r requirements.txt
ENV FLAG=FLAG{...}
CMD ["python", "app.py"]
```

### 必要文件
- `src/app.py` - Web 應用程式
- `src/requirements.txt` - Python 依賴
- `src/templates/*.html` - HTML 模板
- `docker/Dockerfile` - Docker 配置
- `docker/docker-compose.yml` - 服務配置
- `solution/exploit.py` - Exploit 腳本

### 訪問方式
```bash
http://localhost:8080
```

---

## 3️⃣ CRYPTO - Static Attachment

### 特徵
- **不需要** Docker
- 只提供加密檔案
- 選手本地解題

### public.yml 配置
```yaml
challenge_type: "static_attachment"

files:
  - "public_key.pem"
  - "encrypted_flag.txt"

deploy_info:
  requires_build: false
```

### 必要文件
- `src/generate.py` - 生成題目的腳本
- `files/public_key.pem` - 公鑰檔案
- `files/encrypted_flag.txt` - 加密的 flag
- `solution/solve.py` - 解密腳本

### 常見類型
- RSA 弱密鑰
- 古典密碼
- Hash 破解
- 編碼問題

---

## 4️⃣ REVERSE - Static Attachment

### 特徵
- **不需要** Docker
- 提供二進制檔案
- 選手本地分析

### public.yml 配置
```yaml
challenge_type: "static_attachment"

files:
  - "crackme"

source_code_provided: false

deploy_info:
  requires_build: false
```

### 必要文件
- `src/crackme.c` - 源碼（不提供給選手）
- `src/Makefile` - 編譯腳本
- `files/crackme` - 編譯後的執行檔
- `solution/README.md` - 解題步驟

### 常見類型
- Crackme
- 反混淆
- Anti-debugging
- 虛擬機保護

---

## 5️⃣ MISC - Static Attachment

### 特徵
- **不需要** Docker
- 可以是任何檔案類型
- 通常是 Forensics / Steganography

### public.yml 配置
```yaml
challenge_type: "static_attachment"

files:
  - "image.png"

deploy_info:
  requires_build: false
```

### 必要文件
- `src/generate.py` - 生成題目的腳本（可選）
- `files/image.png` - 題目檔案
- `solution/README.md` - 解題步驟

### 常見類型
- 圖片隱寫
- 檔案分析
- 記憶體取證
- 網路封包分析
- OSINT

---

## 📦 附件提供方式

### PWN / REVERSE
提供二進制檔案 + libc（如需要）

```yaml
files:
  - "chall"
  - "libc.so.6"
```

### WEB
通常不提供附件（線上服務），除非：
- 提供源碼（source_code_provided: true）
- 提供特定檔案輔助解題

```yaml
files:
  - "source.zip"  # 如果提供源碼
```

### CRYPTO
提供加密相關檔案

```yaml
files:
  - "public_key.pem"
  - "encrypted_flag.txt"
  - "encrypt.py"  # 加密腳本（可選）
```

---

## 🐳 Docker 部署配置

### 資源限制建議

| 類型 | Memory | CPU | 說明 |
|------|--------|-----|------|
| PWN (NC) | 128-256Mi | 50-100m | 通常很輕量 |
| WEB (Simple) | 256-512Mi | 100-200m | 取決於框架 |
| WEB (Database) | 512Mi-1Gi | 200-500m | 需要資料庫 |

### docker-compose.yml 範例

```yaml
version: '3.8'

services:
  challenge:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "9999:9999"  # 或 "8080:8080"
    restart: unless-stopped

    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'

    environment:
      - FLAG=FLAG{...}

    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "9999"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## 🔒 安全最佳實踐

### 1. Flag 處理

❌ **錯誤**：Flag 寫死在程式碼中
```c
char flag[] = "FLAG{hardcoded}";
```

✅ **正確**：從環境變數讀取
```c
char *flag = getenv("FLAG");
```

### 2. Docker 安全

```yaml
# 安全選項
security_opt:
  - no-new-privileges:true
read_only: true

# 非 root 使用者
RUN useradd -m ctf
USER ctf
```

### 3. 資源限制

```yaml
# 防止 DoS
deploy:
  resources:
    limits:
      memory: 256M
      cpus: '0.5'

# PWN 題目超時
timeout: 60  # 秒
```

---

## 📝 快速創建新題目

### 方法 1: 複製範例

```bash
# 複製對應類型的範例
cp -r challenges/examples/pwn/buffer_overflow challenges/pwn/my_new_challenge

# 修改配置
cd challenges/pwn/my_new_challenge
vim public.yml private.yml README.md
```

### 方法 2: 使用 Template

```bash
# 使用基礎 template
cp -r challenge-template challenges/web/my_web_challenge
cd challenges/web/my_web_challenge

# 替換變數
sed -i 's/${CHALLENGE_TITLE}/My Web Challenge/g' public.yml.template
# ... 更多替換
```

---

## 🎓 學習建議

### 新手出題者

1. **從簡單開始**：MISC > CRYPTO > WEB > REVERSE > PWN
2. **參考範例**：查看 `challenges/examples/` 的完整實現
3. **測試流程**：本地測試 → Docker 測試 → Security Scan
4. **完整文檔**：public.yml + README.md + solution

### 進階出題者

1. **複雜部署**：Multi-container, Database, Redis
2. **動態 Flag**：每隊不同的 flag
3. **反作弊**：Rate limiting, IP tracking
4. **監控**：Logging, Metrics

---

## 🔗 相關文檔

- [完整範例](challenges/examples/README.md)
- [題目開發指南](Challenge-Development)
- [安全檢查清單](docs/security-checklist.md)
- [CTF 工作流程](docs/ctf-challenge-workflow.md)

---

**最後更新**: 2026-01-18
**維護者**: IS1AB Team
