# 項目整理說明

## 📁 **app/ 目錄整理到 web-interface/ 完成**

### ✅ **完成的工作**

1. **目錄整理**：
   - ✅ 將空的 `app/` 目錄移動到 `archive/app-empty/`
   - ✅ 保持 `web-interface/` 作為主要的 Web 應用目錄
   - ✅ 清理重複和無用的文件

2. **設定頁面增強**：
   - ✅ 添加「題目配額」設定顯示
   - ✅ 按分類顯示配額（Web、PWN、Crypto 等）
   - ✅ 按難度顯示配額（Baby、Easy、Middle、Hard、Impossible）
   - ✅ 顯示總目標題目數量

3. **配置整合**：
   - ✅ 正確讀取 `config.yml` 中的 `challenge_quota` 設定
   - ✅ 在設定頁面以視覺化方式展示配額信息
   - ✅ 提供清晰的配置修改指導

### 🗂 **最終項目結構**

```
is1ab-CTF-template/
├── web-interface/              # 🎯 主要 Web 應用
│   ├── app.py                 # Flask 主應用
│   ├── templates/             # Jinja2 模板
│   │   ├── settings.html      # 設定頁面（含題目配額）
│   │   └── ...
│   ├── static/               # 靜態資源
│   ├── venv/                 # Python 虛擬環境
│   ├── .venv/                # uv 虛擬環境（備用）
│   └── legacy/               # 舊版文件
├── challenges/               # CTF 題目目錄
├── archive/                  # 歷史文件
│   ├── app-empty/           # 原 app/ 目錄（空文件）
│   └── ...
├── config.yml               # 主配置（含題目配額設定）
└── ...
```

### 🎯 **新增功能**

**設定頁面 - 題目配額顯示**：

- 📊 **按分類配額**：顯示每個分類需要的題目數量
  - General: 2 題、Web: 6 題、PWN: 6 題等
- 📈 **按難度配額**：顯示每個難度需要的題目數量  
  - Baby: 8 題、Easy: 10 題、Middle: 8 題等
- 🎯 **總目標**：顯示目標總題目數（32 題）

### 🔧 **使用方式**

1. **訪問設定頁面**：<http://localhost:8004/settings>
2. **點擊「題目配額」選項**：查看當前配額設定
3. **修改配額**：編輯 `config.yml` 中的 `challenge_quota` 部分

### 📝 **配置格式**

```yaml
challenge_quota:
  by_category:
    web: 6
    pwn: 6
    crypto: 4
    # ...
  by_difficulty:
    baby: 8
    easy: 10
    # ...
  total_target: 32
```

**項目結構已整理完畢，Web 應用功能更加完善！** ✨

---
*更新時間：2025年8月4日*
