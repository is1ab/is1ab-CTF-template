# 💡 題目提示系統指南

本指南將詳細介紹 is1ab-CTF-template 的多階段題目提示系統，包括設計原理、使用方法和最佳實踐。

## 📋 系統概覽

### 設計原理

題目提示系統旨在：
- **漸進式引導** - 提供分層次的解題幫助
- **平衡挑戰性** - 保持題目難度的同時給予適當幫助
- **鼓勵思考** - 引導參賽者思考而非直接給出答案
- **成本控制** - 透過分數消耗平衡提示使用

### 提示等級結構

```
💡 提示 1 (免費) - 方向性引導
    ↓
💡 提示 2 (低成本) - 技術線索
    ↓  
💡 提示 3 (高成本) - 具體步驟
```

---

## 🚀 快速開始

### 1. 創建帶提示的題目

```bash
# 創建新題目（自動包含預設提示）
uv run scripts/create-challenge.py web sql_injection medium --author YourName

# 查看生成的提示配置
cat challenges/web/sql_injection/public.yml
```

生成的 `public.yml` 會包含預設提示結構：

```yaml
hints:
  - level: 1
    cost: 0
    content: 'TODO: 第一個免費提示 - 引導參賽者思考方向'
  - level: 2
    cost: 10
    content: 'TODO: 第二個提示 - 提供具體的技術線索'
  - level: 3
    cost: 25
    content: 'TODO: 第三個提示 - 給出關鍵步驟或工具'
```

### 2. 使用提示管理工具

```bash
# 查看題目現有提示
uv run scripts/manage-hints.py list web sql_injection

# 新增提示
uv run scripts/manage-hints.py add web sql_injection \
  --level 1 --cost 0 \
  --content "檢查 SQL 查詢的參數處理方式"

# 更新提示
uv run scripts/manage-hints.py update web sql_injection \
  --level 2 --cost 15 \
  --content "嘗試在登入表單中輸入特殊字符"

# 刪除提示
uv run scripts/manage-hints.py remove web sql_injection --level 3

# 驗證提示配置
uv run scripts/manage-hints.py validate web sql_injection
```

### 3. 使用 Web 介面管理

1. 啟動 Web 介面：`cd web-interface && python server.py`
2. 開啟 http://localhost:8000
3. 在題目矩陣中點擊 💡 按鈕
4. 在彈出的視窗中管理提示

---

## 📝 提示編寫指南

### 提示等級設計

#### 🌟 等級 1 - 方向性引導 (免費)
- **目的**：幫助參賽者理解題目類型和攻擊方向
- **內容**：概念性提示，不提供具體技術細節
- **範例**：
  ```
  ✅ "這個登入系統可能存在輸入驗證問題"
  ✅ "試著分析網站如何處理用戶輸入"
  ❌ "使用 ' OR '1'='1' -- 作為密碼"
  ```

#### ⭐ 等級 2 - 技術線索 (低成本 5-20分)
- **目的**：提供技術方向和工具建議
- **內容**：指向具體技術或工具，但不給出完整解法
- **範例**：
  ```
  ✅ "考慮 SQL 注入攻擊，特別注意 WHERE 子句"
  ✅ "使用 Burp Suite 攔截請求並修改參數"
  ❌ "直接執行 sqlmap -u http://target --dump"
  ```

#### ⭐⭐ 等級 3 - 具體步驟 (高成本 20-50分)
- **目的**：提供詳細的操作步驟或關鍵 payload
- **內容**：具體的技術步驟，但仍需要參賽者理解和執行
- **範例**：
  ```
  ✅ "在 username 欄位輸入：admin' OR '1'='1' --"
  ✅ "使用 UNION SELECT 查詢來獲取資料庫結構"
  ```

### 不同難度的提示策略

#### 🍼 Baby 難度
```yaml
hints:
  - level: 1
    cost: 0
    content: "這是一個適合新手的題目，從檢查網頁原始碼開始吧！"
  - level: 2
    cost: 5
    content: "試著查看網頁的原始碼或檢查開發者工具"
  - level: 3
    cost: 10
    content: "Flag 可能隱藏在 HTML 註解或 JavaScript 中"
```

#### ⭐ Easy 難度
```yaml
hints:
  - level: 1
    cost: 0
    content: "仔細觀察題目的功能和輸入點"
  - level: 2
    cost: 10
    content: "試著測試不同的輸入，看看有什麼異常回應"
  - level: 3
    cost: 20
    content: "考慮常見的 Web 安全漏洞，如 SQL 注入或 XSS"
```

#### ⭐⭐ Medium 難度
```yaml
hints:
  - level: 1
    cost: 0
    content: "這題需要對安全概念有基本理解"
  - level: 2
    cost: 15
    content: "分析應用程式的邏輯，找出可能的攻擊點"
  - level: 3
    cost: 30
    content: "可能需要組合多種技術或繞過某些防護機制"
```

---

## 🔧 進階功能

### 初始化預設提示

根據題目難度自動初始化合適的提示：

```bash
# 為 baby 難度題目初始化預設提示
uv run scripts/manage-hints.py init web welcome --difficulty baby

# 為 hard 難度題目初始化預設提示  
uv run scripts/manage-hints.py init crypto rsa_attack --difficulty hard
```

### 批量管理提示

```bash
# 為所有 web 分類題目驗證提示
find challenges/web -name "public.yml" -execdir uv run ../../../scripts/manage-hints.py validate web $(basename $(pwd)) \;

# 匯出所有提示到 JSON
uv run scripts/export-hints.py --format json --output hints-backup.json
```

### Web API 集成

提示系統提供完整的 RESTful API：

```javascript
// 獲取題目提示
GET /api/challenges/{category}/{name}/hints

// 新增提示
POST /api/challenges/{category}/{name}/hints
{
  "level": 1,
  "cost": 0,
  "content": "提示內容"
}

// 更新提示
PUT /api/challenges/{category}/{name}/hints/{level}
{
  "cost": 15,
  "content": "更新的提示內容"
}

// 刪除提示
DELETE /api/challenges/{category}/{name}/hints/{level}
```

---

## 🎯 最佳實踐

### 1. 提示設計原則

#### ✅ 好的提示
- **漸進式揭示**：從概念到具體逐步深入
- **教育導向**：幫助理解而非直接給答案
- **技術準確**：確保技術資訊正確無誤
- **適當難度**：符合目標受眾的技能水平

#### ❌ 避免的做法
- **直接洩露**：不要直接給出 Flag 或完整解法
- **誤導資訊**：避免提供錯誤或過時的技術資訊
- **跳躍太大**：提示之間的難度差距不要太大
- **過於籠統**：避免沒有實際幫助的空泛提示

### 2. 成本設定建議

| 提示等級 | 建議成本 | 適用情況 |
|----------|----------|----------|
| 等級 1 | 0 分 | 方向性引導，所有題目 |
| 等級 2 | 5-20 分 | 技術線索，根據難度調整 |
| 等級 3 | 20-50 分 | 具體步驟，高難度題目 |
| 等級 4+ | 50+ 分 | 關鍵 payload，極限挑戰 |

### 3. 內容撰寫技巧

#### 🎨 使用表情符號增強可讀性
```yaml
content: "🔍 檢查網頁原始碼，特別注意 JavaScript 部分"
content: "🛠️ 試試使用 Burp Suite 攔截和修改請求"
content: "💡 考慮使用 sqlmap 進行自動化注入測試"
```

#### 📚 提供學習資源
```yaml
content: "這題涉及 SQL 注入，建議先了解 OWASP Top 10 中的相關內容"
content: "需要用到 Union-based SQL 注入技術，可參考 PortSwigger 的教學"
```

#### 🔗 分步驟指導
```yaml
content: |
  按照以下步驟進行：
  1. 攔截登入請求
  2. 修改 username 參數
  3. 觀察回應的變化
  4. 構造適當的 payload
```

---

## 📊 監控和分析

### 提示使用統計

```bash
# 分析提示使用情況（需要在比賽平台實現）
uv run scripts/analyze-hints.py --competition 2024-is1ab-CTF

# 生成提示效果報告
uv run scripts/hint-report.py --output hints-analysis.html
```

### 品質評估指標

- **解題成功率**：使用提示後的解題成功率變化
- **提示順序**：參賽者使用提示的順序模式
- **成本效益**：不同成本提示的使用頻率
- **滿意度調查**：收集參賽者對提示品質的回饋

---

## 🚨 常見問題

### Q: 如何為已存在的題目添加提示？

```bash
# 方法一：使用管理腳本
uv run scripts/manage-hints.py add web existing_challenge \
  --level 1 --cost 0 --content "新的提示內容"

# 方法二：直接編輯 public.yml
# 手動在 hints 陣列中添加新的提示項目
```

### Q: 提示內容可以包含程式碼嗎？

可以，但建議遵循以下格式：

```yaml
content: |
  使用以下 payload 進行測試：
  ```
  ' OR '1'='1' --
  ```
  記得觀察伺服器的回應變化
```

### Q: 如何處理提示中的特殊字符？

在 YAML 中使用適當的引號和轉義：

```yaml
content: "使用 payload：' OR \"1\"=\"1\" --"
content: |
  多行提示可以包含：
  - 特殊字符 ' " \ 
  - 程式碼片段
  - 格式化內容
```

### Q: 可以為不同分類設定不同的預設提示嗎？

可以修改 `scripts/manage-hints.py` 中的 `init_default_hints` 函數：

```python
def init_default_hints(self, category, name, difficulty):
    if category == 'crypto':
        # 密碼學題目的特殊提示模板
        default_hints = [...]
    elif category == 'pwn':
        # PWN 題目的特殊提示模板  
        default_hints = [...]
    # ...
```

---

## 🔗 整合與擴展

### CTF 平台整合

提示系統可以與主流 CTF 平台整合：

#### GZCTF 整合
```python
# 在 sync-to-gzctf.py 中添加提示同步
def sync_hints_to_gzctf(challenge_data):
    hints = challenge_data.get('hints', [])
    for hint in hints:
        gzctf_api.create_hint(
            challenge_id=challenge_id,
            content=hint['content'],
            cost=hint['cost']
        )
```

#### CTFd 整合
```python
# 在 sync-to-ctfd.py 中添加提示同步
def sync_hints_to_ctfd(challenge_data):
    hints = challenge_data.get('hints', [])
    for hint in hints:
        ctfd_api.create_hint(
            challenge_id=challenge_id,
            content=hint['content'],
            cost=hint['cost']
        )
```

### 自定義提示類型

擴展提示系統支援更多類型：

```yaml
hints:
  - level: 1
    cost: 0
    type: "text"
    content: "文字提示"
  - level: 2
    cost: 10
    type: "code"
    language: "python"
    content: |
      # 範例程式碼
      import requests
      response = requests.get(url)
  - level: 3
    cost: 20
    type: "file"
    filename: "hint.py"
    content: "..."
```

---

**🎯 透過這個完善的提示系統，您可以為參賽者提供更好的學習體驗，同時保持適當的挑戰性！**

---

*最後更新：2025-08-03*