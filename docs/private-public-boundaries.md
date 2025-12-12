# 🔐 Private vs Public 內容邊界指南

> **文檔版本**: v1.0
> **建立日期**: 2025-12-12
> **用途**: 明確定義哪些內容應保留在 Private Repository，哪些可以發布到 Public Repository

---

## 📋 目錄

1. [概述](#概述)
2. [內容分類規範](#內容分類規範)
3. [目錄結構對照](#目錄結構對照)
4. [檔案檢查清單](#檔案檢查清單)
5. [自動化驗證](#自動化驗證)
6. [最佳實踐](#最佳實踐)
7. [常見錯誤](#常見錯誤)

---

## 🎯 概述

在 CTF 競賽管理中，正確區分 Private 和 Public 內容至關重要：

- ✅ **Private Content**: 包含敏感資訊（flag、解答、內部筆記）
- ✅ **Public Content**: 可以安全公開的內容（題目描述、附件、Docker 配置）

**❌ 常見風險**:
- Flag 洩漏到 Public Repository
- Writeup 或解題腳本意外公開
- 內部測試資料暴露
- 管理員憑證外洩

---

## 📊 內容分類規範

### 🔴 CRITICAL - 絕對不可公開

這些內容**絕對不能**出現在 Public Repository：

| 類別 | 檔案/內容 | 說明 |
|------|---------|------|
| **Flag** | `private.yml` 中的 flag 欄位 | 題目答案 |
| **Writeup** | `writeup/` 目錄 | 官方解答和詳細步驟 |
| **Solution** | `solution/`, `solve.py`, `exploit.py` | 解題腳本 |
| **內部筆記** | `private.yml` 中的 internal_notes | 開發筆記、測試記錄 |
| **測試憑證** | `test_credentials`, `admin_password` | 測試用的帳密 |
| **Private Keys** | `*.pem`, `id_rsa`, `*.key` | 私鑰檔案 |
| **環境變數** | `.env`, `.env.local`, `.env.production` | 敏感配置 |
| **資料庫備份** | `*.sql`, `*.db` (含真實資料) | 可能包含敏感資料 |

### 🟡 SENSITIVE - 謹慎處理

這些內容**可能**包含敏感資訊，需要審查：

| 類別 | 檔案/內容 | 處理方式 |
|------|---------|---------|
| **Source Code** | `src/` 目錄 | 審查是否包含硬編碼 flag 或 hint |
| **Docker ENV** | `docker-compose.yml` 環境變數 | 確保使用 `${FLAG}` 而非硬編碼 |
| **Config Files** | `config.json`, `settings.py` | 檢查是否包含密碼或 token |
| **測試腳本** | `test.py`, `check.py` | 可能洩漏解題思路 |
| **日誌檔案** | `*.log` | 可能包含 flag 或敏感資訊 |

### 🟢 SAFE - 可以公開

這些內容可以安全地發布到 Public Repository：

| 類別 | 檔案/內容 | 說明 |
|------|---------|------|
| **Public Metadata** | `public.yml` | 題目基本資訊（不含 flag） |
| **題目描述** | `description.md`, `README.md` | 題目說明 |
| **附件** | `files/` 目錄 | 提供給參賽者的檔案 |
| **Docker 配置** | `Dockerfile`, `docker-compose.yml` | 容器配置（移除敏感資料後） |
| **公開 Source** | `src/` (審查後) | 題目原始碼（不含 flag） |
| **Assets** | `assets/`, `static/` | 圖片、CSS、JS 等資源 |

---

## 📁 目錄結構對照

### Private Repository 結構

```
challenges/
└── web/
    └── sql-injection/
        ├── public.yml              # 🟢 SAFE - 公開資訊
        ├── private.yml             # 🔴 CRITICAL - 不可公開
        │   ├── flag: "is1abCTF{...}"        # 答案
        │   ├── internal_notes: "..."         # 內部筆記
        │   └── verified_solutions: [...]     # 驗證過的解法
        ├── src/                    # 🟡 SENSITIVE - 需審查
        │   ├── app.py              # 審查硬編碼
        │   └── database.sql        # 確保無敏感資料
        ├── docker/                 # 🟢 SAFE - 公開（移除敏感資料後）
        │   ├── Dockerfile
        │   └── docker-compose.yml  # 使用 ${FLAG} 而非硬編碼
        ├── files/                  # 🟢 SAFE - 提供給參賽者
        │   └── challenge.zip
        ├── writeup/                # 🔴 CRITICAL - 不可公開
        │   ├── solution.md         # 官方解答
        │   └── exploit.py          # 解題腳本
        └── tests/                  # 🟡 SENSITIVE - 需審查
            └── test.py             # 可能洩漏解題思路
```

### Public Repository 結構（發布後）

```
challenges/
└── sql-injection/                  # 題目名稱（無分類前綴）
    ├── public.yml                  # ✅ 從 private repo 複製
    ├── files/                      # ✅ 參賽者附件
    │   └── challenge.zip
    ├── docker/                     # ✅ 容器配置（已清理）
    │   ├── Dockerfile
    │   └── docker-compose.yml
    └── README.md                   # ✅ 題目說明（從 public.yml 生成）
```

**❌ 不應出現**:
- `private.yml`
- `writeup/`
- `solution/`, `solve.py`, `exploit.py`
- `.env`, `secrets.yml`
- 任何包含 flag 的檔案

---

## ✅ 檔案檢查清單

### 題目開發者檢查清單

在提交 PR 之前，請確認：

#### Private Repository（開發階段）

- [ ] `public.yml` 已完整填寫（不含 flag）
- [ ] `private.yml` 包含 flag 和敏感資訊
- [ ] `writeup/` 目錄包含詳細解答
- [ ] `src/` 中沒有硬編碼的 flag
- [ ] `docker-compose.yml` 使用 `${FLAG}` 環境變數
- [ ] `files/` 中的附件不含解答或 hint
- [ ] 執行 `scan-secrets.py` 無 CRITICAL 問題

#### Public Repository（發布階段）

- [ ] 只包含 `public.yml`（無 `private.yml`）
- [ ] 沒有 `writeup/` 目錄
- [ ] 沒有 `solution/` 或解題腳本
- [ ] Docker 配置已清理敏感資料
- [ ] 執行 flag 格式掃描無洩漏
- [ ] 所有檔案通過安全檢查

### 審核者檢查清單

在審核 PR 時，請確認：

- [ ] PR 不包含對 `private.yml` 的刪除或移動
- [ ] `public.yml` 不包含 flag 或敏感資訊
- [ ] Docker 配置使用環境變數而非硬編碼
- [ ] 新增的 `src/` 代碼沒有硬編碼 flag
- [ ] CI 安全掃描全部通過
- [ ] 題目可以正常部署和測試

---

## 🤖 自動化驗證

### 1. Pre-commit Hook

在本地配置 pre-commit hook：

創建 `.git/hooks/pre-commit`：

```bash
#!/bin/bash

echo "🔍 執行 pre-commit 安全掃描..."

# 掃描 staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|yml|yaml|js|json|sh)$')

if [ -n "$STAGED_FILES" ]; then
    # 檢查是否包含 flag 格式
    if echo "$STAGED_FILES" | xargs grep -l "is1abCTF{" 2>/dev/null; then
        echo "❌ 錯誤：發現 flag 格式字串！"
        echo "請確保 flag 只存在於 private.yml 中"
        exit 1
    fi

    # 檢查是否包含敏感檔案
    if echo "$STAGED_FILES" | grep -E "(private\.yml|solution|solve\.py|exploit\.py|writeup)" 2>/dev/null; then
        echo "⚠️  警告：發現敏感檔案"
        echo "請確認這些檔案不應該被提交到公開版本"
    fi
fi

echo "✅ Pre-commit 檢查通過"
exit 0
```

```bash
chmod +x .git/hooks/pre-commit
```

### 2. GitHub Actions 自動掃描

在 PR 階段自動執行（已包含在 [security-scan.yml](../.github/workflows/security-scan.yml)）：

```yaml
- name: 🔍 檢查 Private vs Public 邊界
  run: |
    # 檢查 public.yml 是否包含敏感欄位
    if grep -r "flag:" challenges/*/public.yml 2>/dev/null; then
      echo "::error::public.yml 中發現 flag 欄位！"
      exit 1
    fi

    # 檢查 public-release 目錄
    if [ -d "public-release" ]; then
      # 不應包含 private.yml
      if find public-release -name "private.yml" 2>/dev/null | grep -q .; then
        echo "::error::public-release 中發現 private.yml！"
        exit 1
      fi

      # 不應包含 writeup
      if find public-release -type d -name "writeup" 2>/dev/null | grep -q .; then
        echo "::error::public-release 中發現 writeup 目錄！"
        exit 1
      fi
    fi
```

### 3. 建置階段驗證

在 `auto-release.yml` 中已包含驗證步驟：

```yaml
- name: 🔍 Validate Public Release
  run: |
    # 檢查 flag 洩漏
    FLAG_PREFIX=$(grep -E "^\s*flag_prefix:" config.yml | awk -F'"' '{print $2}')
    FOUND_FLAGS=$(grep -r "${FLAG_PREFIX}{" public-release/ || true)

    if [ -n "$FOUND_FLAGS" ]; then
      echo "::error::公開版本中發現 Flag 洩漏！"
      exit 1
    fi

    # 檢查敏感檔案
    FOUND_PRIVATE=$(find public-release/ -name "private.yml" || true)
    if [ -n "$FOUND_PRIVATE" ]; then
      echo "::error::公開版本中發現 private.yml！"
      exit 1
    fi
```

---

## 💡 最佳實踐

### 1. 使用 Template 變數

**❌ 不好的做法**：硬編碼 flag
```yaml
# docker-compose.yml
environment:
  FLAG: "is1abCTF{secret_flag_here}"  # ❌ 絕對不要這樣做
```

**✅ 好的做法**：使用環境變數
```yaml
# docker-compose.yml
environment:
  FLAG: ${FLAG}  # ✅ 使用環境變數
```

```yaml
# private.yml
flag: "is1abCTF{secret_flag_here}"  # ✅ flag 只存在這裡
```

### 2. 分離式配置

**題目結構建議**：

```
challenge/
├── public.yml          # 只包含公開資訊
├── private.yml         # 只包含敏感資訊
├── src/
│   ├── app.py         # 使用 os.getenv('FLAG')
│   └── config.py      # 不含硬編碼
└── docker/
    └── docker-compose.yml  # 使用 ${FLAG}
```

### 3. Writeup 模板

**Writeup 結構建議**（存放在 `writeup/` 目錄）：

```markdown
# [題目名稱] Writeup

## 題目描述
[從 public.yml 複製]

## 解題思路
1. 觀察...
2. 分析...
3. 利用...

## 詳細步驟
[詳細的解題步驟]

## Flag
\`\`\`
is1abCTF{flag_here}
\`\`\`

## 學習重點
- 重點 1
- 重點 2

## 參考資料
- [連結 1]
- [連結 2]
```

### 4. 公開發布前檢查

使用提供的腳本進行最終檢查：

```bash
# 1. 建置公開版本
./scripts/build.sh challenges/web/sql-injection/ public-release

# 2. 執行安全掃描
uv run python scripts/scan-secrets.py --path public-release/

# 3. 手動檢查
ls -la public-release/challenges/sql-injection/
# 確認沒有 private.yml、writeup/ 等

# 4. 驗證 Docker 配置
cat public-release/challenges/sql-injection/docker/docker-compose.yml
# 確認使用 ${FLAG} 而非硬編碼
```

---

## ⚠️ 常見錯誤

### 錯誤 1: Flag 硬編碼在 Source Code

**❌ 錯誤範例**：
```python
# app.py
FLAG = "is1abCTF{secret_flag}"  # ❌ 硬編碼

if user_input == FLAG:
    return "Correct!"
```

**✅ 正確做法**：
```python
# app.py
import os
FLAG = os.getenv('FLAG', 'default_flag_for_dev')  # ✅ 從環境變數讀取

if user_input == FLAG:
    return "Correct!"
```

### 錯誤 2: Private.yml 被加入 Public Release

**原因**：建置腳本錯誤或手動複製時遺漏過濾

**檢測**：
```bash
find public-release/ -name "private.yml"
# 應該沒有任何輸出
```

**修復**：
```bash
# 從 public-release 移除
find public-release/ -name "private.yml" -delete
```

### 錯誤 3: Writeup 意外公開

**原因**：建置時未排除 `writeup/` 目錄

**檢測**：
```bash
find public-release/ -type d -name "writeup"
# 應該沒有任何輸出
```

**修復**：
```bash
# 從 public-release 移除
find public-release/ -type d -name "writeup" -exec rm -rf {} +
```

### 錯誤 4: Docker Compose 硬編碼 Flag

**❌ 錯誤範例**：
```yaml
# docker-compose.yml
services:
  web:
    environment:
      - FLAG=is1abCTF{real_flag_here}  # ❌ 硬編碼
```

**✅ 正確做法**：
```yaml
# docker-compose.yml
services:
  web:
    environment:
      - FLAG=${FLAG}  # ✅ 使用環境變數
```

**部署時設定**：
```bash
# 在部署環境設定
export FLAG="is1abCTF{real_flag_here}"
docker-compose up -d
```

### 錯誤 5: Git 歷史中的敏感資料

**問題**：即使檔案被刪除，Git 歷史中仍可能存在

**檢測**：
```bash
# 搜尋 Git 歷史中的 flag
git log -S "is1abCTF{" --all --pretty=format:"%h %s"
```

**修復**（慎用，會改寫歷史）：
```bash
# 使用 git-filter-repo 移除敏感資料
pip install git-filter-repo
git filter-repo --invert-paths --path-match 'private.yml' --force

# 或使用 BFG Repo-Cleaner
java -jar bfg.jar --delete-files private.yml
```

---

## 🔗 相關資源

### 內部文檔

- [自動化 Release 工作流程](../.github/workflows/auto-release.yml)
- [安全掃描工具](../scripts/scan-secrets.py)
- [改善實施指南](IMPROVEMENT_IMPLEMENTATION_GUIDE.md)
- [自動化 Release 測試指南](auto-release-testing.md)

### 外部資源

- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [Git Filter Repo](https://github.com/newren/git-filter-repo)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)

---

## 📝 快速參考

### 檔案分類速查表

| 檔案類型 | Private | Public | 說明 |
|---------|---------|--------|------|
| `public.yml` | ✅ | ✅ | 公開資訊 |
| `private.yml` | ✅ | ❌ | 敏感資訊 |
| `writeup/` | ✅ | ❌ | 官方解答 |
| `solution/`, `solve.py` | ✅ | ❌ | 解題腳本 |
| `src/` | ✅ | ⚠️ | 需審查 |
| `docker/` | ✅ | ✅ | 移除敏感資料後 |
| `files/` | ✅ | ✅ | 參賽者附件 |
| `.env` | ✅ | ❌ | 環境變數 |

### 掃描命令速查

```bash
# 掃描整個專案
uv run python scripts/scan-secrets.py --path .

# 只掃描 challenges
uv run python scripts/scan-secrets.py --path challenges/

# 掃描 public-release
uv run python scripts/scan-secrets.py --path public-release/ --fail-on-critical

# 搜尋特定 pattern
grep -r "is1abCTF{" challenges/ --exclude-dir=".git"

# 檢查 private.yml 是否在 public-release
find public-release/ -name "private.yml"

# 檢查 writeup 是否在 public-release
find public-release/ -type d -name "writeup"
```

---

**維護者**: IS1AB Team
**最後更新**: 2025-12-12
**文檔版本**: v1.0
