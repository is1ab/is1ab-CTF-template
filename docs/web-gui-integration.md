# 🌐 Web GUI 與安全流程整合說明

> Web 管理介面與新安全流程的整合狀態和使用指南

## 📋 概述

Web GUI (`web-interface/`) 是一個基於 Flask 的 Web 管理介面，提供視覺化的題目管理功能。本文檔說明它與新安全流程的整合情況。

## ✅ 兼容性分析

### 已兼容的功能

#### 1. **題目瀏覽和統計** ✅

- **功能**：儀表板顯示題目統計、分類、難度分布
- **狀態**：✅ **完全兼容**
- **說明**：只讀取 `public.yml`，不涉及敏感資料

```python
# web-interface/app.py
# 只讀取 public.yml，不讀取 private.yml
public_yml = challenge_dir / "public.yml"
if public_yml.exists():
    with open(public_yml, "r", encoding="utf-8") as yml_file:
        challenge_data = yaml.safe_load(yml_file)
```

#### 2. **題目創建** ✅

- **功能**：通過 Web 表單創建新題目
- **狀態**：✅ **已支援新結構**
- **說明**：自動創建 `private.yml` 和 `public.yml`，並正確分離敏感資料

```python
# web-interface/app.py (line 287-378)
# 創建 private.yml（含 flag）
private_config = {
    "flag": challenge_data.get("flag", f"is1abCTF{{{name}_example_flag}}"),
    "flag_description": "...",
    "solution_steps": [...],
    # ...
}

# 創建 public.yml（移除敏感資訊）
public_config = {
    k: v for k, v in private_config.items()
    if not k.startswith(("flag", "solution_", "internal_", "testing"))
}
```

#### 3. **配額追蹤** ✅

- **功能**：顯示題目配額進度和統計
- **狀態**：✅ **完全兼容**
- **說明**：基於 `config.yml` 和 `public.yml` 計算

### 需要更新的功能

#### 1. **題目編輯** ⚠️

- **當前狀態**：可能同時編輯 `private.yml` 和 `public.yml`
- **建議**：分離編輯介面
  - 公開資訊編輯（public.yml）
  - 敏感資訊編輯（private.yml，需權限控制）

#### 2. **安全掃描整合** ⚠️

- **當前狀態**：無安全掃描功能
- **建議**：整合 `scan-secrets.py`
  - 在創建/編輯題目時自動掃描
  - 顯示掃描結果和警告

#### 3. **建置功能整合** ⚠️

- **當前狀態**：無建置功能
- **建議**：整合 `build.sh`
  - 提供「建置公開版本」按鈕
  - 顯示建置進度和結果

## 🔄 整合建議

### 方案 A：保持現狀（推薦）

**適用場景**：
- 團隊習慣使用命令列工具
- Web GUI 主要用於瀏覽和統計
- 建置和安全掃描通過 CI/CD 自動化

**優點**：
- ✅ 無需修改現有代碼
- ✅ 功能分離清晰
- ✅ 安全性更高（敏感操作在本地）

**使用流程**：
```
1. Web GUI 創建題目（自動生成 private.yml + public.yml）
2. 本地編輯 private.yml（設定真實 flag）
3. 本地執行 build.sh 建置
4. CI/CD 自動掃描和部署
```

### 方案 B：增強整合（進階）

**適用場景**：
- 團隊希望完全通過 Web GUI 操作
- 需要視覺化的安全掃描結果
- 需要一鍵建置功能

**需要新增的功能**：

1. **安全掃描整合**
   ```python
   # 在 app.py 中新增
   @app.route("/api/scan/<category>/<name>")
   def scan_challenge(category, name):
       """掃描題目安全問題"""
       result = subprocess.run(
           ["python", "scripts/scan-secrets.py", 
            f"challenges/{category}/{name}"],
           capture_output=True
       )
       return jsonify({"result": result.stdout.decode()})
   ```

2. **建置功能整合**
   ```python
   @app.route("/api/build", methods=["POST"])
   def build_public():
       """建置公開版本"""
       result = subprocess.run(
           ["./scripts/build.sh", "--force"],
           capture_output=True
       )
       return jsonify({"status": "success" if result.returncode == 0 else "failed"})
   ```

3. **分離編輯介面**
   ```python
   @app.route("/challenges/<category>/<name>/edit/public")
   def edit_public(category, name):
       """編輯公開資訊"""
       # 只顯示和編輯 public.yml
       
   @app.route("/challenges/<category>/<name>/edit/private")
   def edit_private(category, name):
       """編輯敏感資訊（需權限）"""
       # 顯示和編輯 private.yml
       # 需要身份驗證
   ```

## 📊 功能對照表

| 功能 | Web GUI | 命令列 | CI/CD | 狀態 |
|------|---------|--------|-------|------|
| 題目瀏覽 | ✅ | ✅ | - | 兼容 |
| 題目統計 | ✅ | ✅ | - | 兼容 |
| 題目創建 | ✅ | ✅ | - | 兼容 |
| 題目編輯 | ⚠️ | ✅ | - | 需改進 |
| 安全掃描 | ❌ | ✅ | ✅ | 建議整合 |
| 建置公開版本 | ❌ | ✅ | ✅ | 建議整合 |
| 配額追蹤 | ✅ | ✅ | - | 兼容 |

## 🚀 使用建議

### 日常開發流程

#### 1. 使用 Web GUI 創建題目

```bash
# 啟動 Web GUI
cd web-interface
uv run python app.py

# 訪問 http://localhost:8004
# 使用「創建題目」功能
```

#### 2. 編輯敏感資訊（使用命令列）

```bash
# 編輯 private.yml（設定真實 flag）
vim challenges/web/my_challenge/private.yml

# 編輯 public.yml（設定公開資訊）
vim challenges/web/my_challenge/public.yml
```

#### 3. 本地測試和建置

```bash
# 安全掃描
uv run python scripts/scan-secrets.py --path challenges/web/my_challenge

# 建置測試
./scripts/build.sh --challenge challenges/web/my_challenge --dry-run

# 實際建置
./scripts/build.sh --challenge challenges/web/my_challenge --force
```

#### 4. 提交和自動化

```bash
# 提交 PR
git add challenges/web/my_challenge/
git commit -m "feat(web): add my_challenge"
git push origin feature/my_challenge

# CI/CD 自動執行：
# - security-scan.yml（安全掃描）
# - build-public.yml（建置公開版本）
# - deploy-pages.yml（部署 GitHub Pages）
```

## 🔒 安全注意事項

### Web GUI 安全設定

1. **不要暴露敏感資料**
   - ✅ Web GUI 只讀取 `public.yml`
   - ✅ 不顯示 `private.yml` 內容
   - ✅ 不允許通過 Web 介面編輯 flag

2. **權限控制**
   ```python
   # 建議新增身份驗證
   from flask_login import LoginManager, login_required
   
   @app.route("/challenges/<category>/<name>/edit/private")
   @login_required
   def edit_private(category, name):
       # 只有授權用戶可以編輯 private.yml
   ```

3. **生產環境設定**
   ```python
   # 不要在生產環境暴露 Web GUI
   # 或使用身份驗證和 HTTPS
   if not app.debug:
       app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
   ```

## 📝 更新日誌

### 當前版本（v2.1.0）

- ✅ Web GUI 已支援創建 `private.yml` + `public.yml`
- ✅ 自動分離敏感資料
- ✅ 與新安全流程兼容

### 未來改進計劃

- [ ] 整合安全掃描功能
- [ ] 整合建置功能
- [ ] 分離編輯介面（公開/私密）
- [ ] 新增身份驗證
- [ ] 顯示建置狀態和結果

## 🎯 總結

### Web GUI 的定位

**主要用途**：
- 📊 題目統計和進度追蹤
- 📋 題目瀏覽和搜尋
- ➕ 快速創建題目結構

**不建議用於**：
- ❌ 編輯敏感資料（flag、解答）
- ❌ 執行安全掃描（使用命令列或 CI/CD）
- ❌ 建置公開版本（使用命令列或 CI/CD）

### 最佳實踐

1. **開發階段**：使用 Web GUI 創建題目和瀏覽統計
2. **敏感操作**：使用命令列工具（更安全、更靈活）
3. **自動化**：依賴 CI/CD 進行安全掃描和建置

---

**結論**：Web GUI **可以使用**，且已與新安全流程兼容。建議保持現狀，將敏感操作（掃描、建置）保留在命令列和 CI/CD 中，以確保安全性。

