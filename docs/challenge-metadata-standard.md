# 📋 Challenge Metadata 標準格式

> 標準化的題目元數據格式規範，確保所有工具和腳本都能統一讀取

## 📋 目錄

- [概述](#概述)
- [public.yml 格式](#publicyml-格式)
- [private.yml 格式](#privateyml-格式)
- [範例](#範例)
- [驗證規則](#驗證規則)

---

## 概述

每個 CTF 題目包含兩個配置檔案：

- **`public.yml`** - 公開資訊，會同步到 Public Repository
- **`private.yml`** - 敏感資訊，僅存在於 Private Repository

---

## public.yml 格式

### 必要欄位

```yaml
# 題目基本資訊
title: "題目標題"                    # 必填：顯示給參賽者的題目名稱
category: "web"                      # 必填：web | pwn | reverse | crypto | forensic | misc
difficulty: "easy"                   # 必填：baby | easy | middle | hard | impossible
author: "AuthorName"                 # 必填：題目作者
points: 100                          # 必填：題目分數
description: |                       # 必填：題目描述（多行文字）
  這是題目的詳細描述。
  可以使用多行文字。

# 發布狀態
ready_for_release: false            # 必填：是否準備好發布到 Public Repo
```

### 可選欄位

```yaml
# 題目類型
challenge_type: "static_attachment"  # static_attachment | web_challenge | nc_challenge

# 標籤和分類
tags:                                # 可選：題目標籤
  - "sql-injection"
  - "authentication"

# 提示系統
hints:                               # 可選：提示列表
  - level: 1
    cost: 10
    content: "第一個提示"
  - level: 2
    cost: 20
    content: "第二個提示"

# 檔案配置
allowed_files:                       # 可選：允許發布的檔案模式
  - "src/**"
  - "docker/Dockerfile"
  - "files/*.zip"

files:                               # 可選：提供給選手的檔案列表
  - name: "source.zip"
    description: "題目源碼"
    size: 1024

# 部署資訊
deployment:                          # 可選：部署配置
  type: "dynamic"                   # static | dynamic
  port: 3000
  nc_port: 9999                     # NC 題目專用

# 時間戳記
created_at: "2024-01-01T00:00:00Z"  # 可選：創建時間
updated_at: "2024-01-01T00:00:00Z"  # 可選：更新時間
```

---

## private.yml 格式

### 必要欄位

```yaml
# 基本資訊（與 public.yml 相同）
title: "題目標題"
category: "web"
difficulty: "easy"
author: "AuthorName"
points: 100
description: |
  題目描述

# Flag 資訊（敏感）
flag: "is1abCTF{actual_flag_here}"  # 必填：實際的 flag
flag_type: "static"                 # 必填：static | dynamic | regex
```

### 可選欄位

```yaml
# Flag 詳細資訊（敏感）
flag_description: |                 # 可選：Flag 獲取說明
  Flag 位於資料庫的 admin 表中。
  需要通過 SQL 注入獲取。

# 解題步驟（敏感）
solution_steps:                     # 可選：詳細解題步驟
  - |
    第一步：發現 SQL Injection 漏洞
    在登入表單的 username 欄位中輸入單引號 (')
  - |
    第二步：構造 payload
    使用 ' OR '1'='1 繞過驗證

# 內部筆記（敏感）
internal_notes: |                   # 可選：開發筆記
  開發筆記：
  - 資料庫使用 SQLite
  - 需要測試多種 payload

# 測試憑證（敏感）
test_credentials:                   # 可選：測試帳號
  username: "admin"
  password: "test_password"

# 部署密鑰（敏感）
deploy_secrets:                     # 可選：部署相關密鑰
  docker_registry_token: "..."
  ssh_key: "..."

# 驗證過的解法（敏感）
verified_solutions:                  # 可選：已驗證的解法
  - author: "Tester1"
    method: "SQL Injection"
    notes: "使用聯合查詢"
```

---

## 範例

### public.yml 範例

```yaml
title: "SQL Injection Login Bypass"
category: "web"
difficulty: "middle"
author: "Alice"
points: 300
description: |
  網站的登入功能存在安全漏洞，試著繞過登入驗證取得管理員權限。
  
  提示：試試看萬能密碼吧！

challenge_type: "web_challenge"
ready_for_release: true

tags:
  - "sql-injection"
  - "authentication-bypass"
  - "web-security"

hints:
  - level: 1
    cost: 10
    content: "SQL 注入通常發生在使用字串拼接的地方"
  - level: 2
    cost: 20
    content: "試試看使用單引號和 OR 條件"

allowed_files:
  - "src/**"
  - "docker/Dockerfile"
  - "docker/docker-compose.yml"
  - "files/source.zip"

deployment:
  type: "dynamic"
  port: 3000

created_at: "2024-01-15T10:00:00Z"
```

### private.yml 範例

```yaml
title: "SQL Injection Login Bypass"
category: "web"
difficulty: "middle"
author: "Alice"
points: 300
description: |
  網站的登入功能存在安全漏洞，試著繞過登入驗證取得管理員權限。

flag: "is1abCTF{sql_injection_bypass_2024}"
flag_type: "static"

flag_description: |
  Flag 位於資料庫的 admin 表中。
  參賽者需要通過 SQL injection 漏洞繞過身份驗證，
  然後查詢資料庫獲取管理員的 flag。

solution_steps:
  - |
    第一步：發現 SQL Injection 漏洞
    在登入表單的 username 欄位中輸入單引號 (')
    觀察到錯誤訊息洩露了 SQL 查詢結構
  - |
    第二步：構造 payload
    使用 ' OR '1'='1 繞過驗證
    或使用 ' UNION SELECT flag FROM admin --
  - |
    第三步：獲取 Flag
    成功登入後，查詢 admin 表獲取 flag

internal_notes: |
  開發筆記：
  - 資料庫使用 SQLite，位於 /app/database.db
  - 需要確保漏洞可被利用但不會造成資料損壞
  - 測試多種 payload 確保穩定性

test_credentials:
  username: "admin"
  password: "admin123"
```

---

## 驗證規則

### public.yml 驗證

- ✅ 必須包含所有必要欄位
- ✅ `category` 必須是有效值
- ✅ `difficulty` 必須是有效值
- ✅ `ready_for_release` 必須是布林值
- ✅ `points` 必須是正整數
- ✅ 不能包含 `flag`、`flag_description`、`solution_steps` 等敏感欄位

### private.yml 驗證

- ✅ 必須包含所有必要欄位
- ✅ `flag` 必須符合 flag 格式（由 `config.yml` 定義）
- ✅ `flag_type` 必須是有效值
- ✅ 如果 `flag_type` 是 `dynamic`，必須包含 `dynamic_flag` 配置

### 一致性驗證

- ✅ `public.yml` 和 `private.yml` 的基本資訊（title, category, difficulty, author, points）必須一致
- ✅ `public.yml` 的 `ready_for_release` 為 `true` 時，必須通過安全掃描

---

## 工具支援

以下工具會讀取這些 metadata：

- `create-challenge.py` - 創建題目時生成模板
- `validate-challenge.py` - 驗證題目結構和配置
- `build.sh` - 建置公開版本時讀取 `public.yml`
- `scan-secrets.py` - 安全掃描時檢查敏感資料
- `generate-pages.py` - 生成 GitHub Pages 時讀取 `public.yml`
- Web GUI - 顯示題目資訊和管理

---

## 最佳實踐

1. **保持一致性**：確保 `public.yml` 和 `private.yml` 的基本資訊一致
2. **及時更新**：開發過程中及時更新 metadata
3. **詳細描述**：提供清晰的題目描述和提示
4. **安全第一**：永遠不要在 `public.yml` 中包含敏感資訊
5. **版本控制**：使用 Git 追蹤 metadata 變更

---

**最後更新**：2025-01-15  
**維護者**：IS1AB Team

