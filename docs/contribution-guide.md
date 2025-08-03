# 🤝 貢獻指南

歡迎參與 is1ab-CTF-template 的開發！本指南將幫助您了解如何為這個專案做出貢獻。

## 📋 貢獻方式

### 🐛 報告錯誤
- 使用 [GitHub Issues](../../issues) 報告錯誤
- 提供詳細的錯誤描述和重現步驟
- 附上相關的日誌或截圖

### 💡 建議功能
- 在 [GitHub Discussions](../../discussions) 中討論新功能想法
- 提交詳細的功能需求說明
- 考慮功能的實用性和通用性

### 📝 改進文檔
- 修正文檔中的錯誤或不清楚的地方
- 添加使用範例和最佳實踐
- 翻譯文檔到其他語言

### 💻 貢獻程式碼
- 修復錯誤
- 實現新功能
- 改進效能和程式碼品質

---

## 🚀 開始貢獻

### 1. 設置開發環境

```bash
# Fork 並克隆倉庫
git clone https://github.com/your-username/is1ab-CTF-template.git
cd is1ab-CTF-template

# 設置上游倉庫
git remote add upstream https://github.com/is1ab/is1ab-CTF-template.git

# 安裝依賴
uv venv
source .venv/bin/activate  # Linux/Mac
uv sync

# 安裝開發依賴
uv add --dev pytest black flake8 mypy
```

### 2. 創建開發分支

```bash
# 同步最新變更
git fetch upstream
git checkout main
git merge upstream/main

# 創建功能分支
git checkout -b feature/your-feature-name
# 或修復分支
git checkout -b fix/bug-description
```

### 3. 進行開發

- 遵循現有的程式碼風格
- 添加適當的註釋和文檔
- 編寫測試（如適用）
- 確保不會破壞現有功能

### 4. 測試變更

```bash
# 執行程式碼格式檢查
black scripts/ web-interface/
flake8 scripts/ web-interface/

# 執行類型檢查
mypy scripts/

# 執行測試
pytest tests/

# 測試敏感資料檢查
uv run scripts/check-sensitive.py

# 測試 Web 介面
cd web-interface
python server.py --port 8001 &
curl http://localhost:8001/api/challenges
```

### 5. 提交變更

```bash
# 提交變更
git add .
git commit -m "feat: add new feature description"

# 推送到您的 Fork
git push origin feature/your-feature-name
```

### 6. 創建 Pull Request

- 在 GitHub 上創建 Pull Request
- 填寫 PR 模板中的所有必要資訊
- 確保 CI 檢查通過
- 回應審查者的意見

---

## 📏 開發規範

### 程式碼風格

**Python 程式碼**
```python
# 使用 Black 進行格式化
# 使用 type hints
def create_challenge(name: str, category: str, difficulty: str) -> bool:
    """創建新的 CTF 題目
    
    Args:
        name: 題目名稱
        category: 題目分類
        difficulty: 難度級別
        
    Returns:
        bool: 創建是否成功
    """
    pass
```

**JavaScript 程式碼**
```javascript
// 使用現代 ES6+ 語法
// 添加適當的錯誤處理
async function fetchChallenges() {
    try {
        const response = await fetch('/api/challenges');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Failed to fetch challenges:', error);
        throw error;
    }
}
```

### 提交訊息格式

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**類型（type）：**
- `feat`: 新功能
- `fix`: 錯誤修復
- `docs`: 文檔變更
- `style`: 程式碼格式（不影響程式碼運行）
- `refactor`: 程式碼重構
- `test`: 添加測試
- `chore`: 建置過程或輔助工具的變動

**範例：**
```bash
feat(scripts): add challenge validation with detailed error messages

- Add comprehensive validation for challenge structure
- Include helpful error messages for common issues
- Support for multiple challenge types

Closes #123
```

### 分支命名規範

- `feature/功能名稱` - 新功能開發
- `fix/錯誤描述` - 錯誤修復
- `docs/文檔主題` - 文檔更新
- `refactor/重構範圍` - 程式碼重構

---

## 🧪 測試指南

### 單元測試

```python
# tests/test_challenge_creation.py
import pytest
from scripts.create_challenge import create_challenge_structure

def test_create_challenge_structure():
    """測試題目結構創建"""
    result = create_challenge_structure("web", "test_challenge", "easy")
    assert result.exists()
    assert (result / "public.yml").exists()
    assert (result / "README.md").exists()

def test_invalid_category():
    """測試無效分類處理"""
    with pytest.raises(ValueError):
        create_challenge_structure("invalid", "test", "easy")
```

### 整合測試

```python
# tests/test_web_interface.py
import requests
import pytest

@pytest.fixture
def server_url():
    """測試服務器 URL"""
    return "http://localhost:8001"

def test_challenges_api(server_url):
    """測試題目 API"""
    response = requests.get(f"{server_url}/api/challenges")
    assert response.status_code == 200
    
    data = response.json()
    assert "challenges" in data
    assert isinstance(data["challenges"], list)
```

### 安全性測試

```bash
# 測試敏感資料檢查
echo "flag{test_flag}" > test_file.txt
uv run scripts/check-sensitive.py test_file.txt
# 應該檢測到敏感資料

# 測試 XSS 防護
curl -X POST localhost:8001/api/challenges \
  -H "Content-Type: application/json" \
  -d '{"title": "<script>alert(1)</script>"}'
# 應該被正確轉義
```

---

## 📋 Pull Request 檢查清單

提交 PR 前請確認：

### 📝 基本要求
- [ ] 分支基於最新的 `main` 分支
- [ ] 程式碼通過所有 CI 檢查
- [ ] 添加了適當的測試
- [ ] 更新了相關文檔
- [ ] 沒有破壞現有功能

### 🔒 安全性檢查
- [ ] 沒有硬編碼敏感資訊
- [ ] 輸入驗證和清理
- [ ] 適當的錯誤處理
- [ ] 權限檢查（如適用）

### 📚 文檔檢查
- [ ] 程式碼有適當的註釋
- [ ] API 變更已記錄
- [ ] README 已更新（如需要）
- [ ] 範例程式碼可以運行

### 🧪 測試檢查
- [ ] 單元測試覆蓋新功能
- [ ] 整合測試通過
- [ ] 手動測試確認功能正常
- [ ] 效能測試（如適用）

---

## 👥 程式碼審查流程

### 作為作者
1. **清楚的描述**：在 PR 中清楚說明變更內容和原因
2. **自我審查**：提交前先自己檢查一遍程式碼
3. **回應意見**：及時回應審查者的問題和建議
4. **保持更新**：根據回饋及時更新程式碼

### 作為審查者
1. **建設性回饋**：提供具體、有幫助的建議
2. **及時回應**：在合理時間內完成審查
3. **測試驗證**：實際測試變更的功能
4. **知識分享**：分享相關的最佳實踐

### 審查重點
- **功能性**：功能是否按預期工作
- **安全性**：是否有安全漏洞
- **效能**：是否影響系統效能
- **可維護性**：程式碼是否易於理解和維護
- **一致性**：是否符合專案風格

---

## 🏷️ 發布流程

### 版本號規則
遵循 [Semantic Versioning](https://semver.org/)：
- `MAJOR.MINOR.PATCH`
- `1.0.0` → `1.0.1`（修復）
- `1.0.0` → `1.1.0`（新功能）
- `1.0.0` → `2.0.0`（破壞性變更）

### 發布步驟
1. 更新 `CHANGELOG.md`
2. 更新版本號
3. 創建 Git 標籤
4. 發布 GitHub Release
5. 更新文檔網站

---

## 🎯 貢獻者等級

### 🌱 新手貢獻者
- 修復文檔錯誤
- 改進錯誤訊息
- 添加測試案例
- 回報詳細的錯誤

### 🔧 經驗貢獻者
- 實現新功能
- 重構程式碼
- 改進效能
- 設計新的 API

### 🏆 核心貢獻者
- 架構設計
- 安全性審查
- 發布管理
- 社群維護

---

## 🤝 社群守則

### 我們的承諾
- 創造開放、友善、多元的環境
- 尊重不同觀點和經驗
- 優雅地接受建設性回饋
- 專注於對社群最有利的事情

### 期望行為
- 使用友善和包容的語言
- 尊重不同的觀點和經驗
- 優雅地接受建設性批評
- 專注於對社群最有利的事情
- 對其他社群成員表現同理心

### 不當行為
- 使用具有性暗示的語言或圖像
- 釣魚、侮辱或貶損的評論
- 公開或私下騷擾
- 未經許可發布他人的私人資訊
- 其他在專業環境中可能被認為不當的行為

---

## 📞 取得幫助

遇到問題？有以下管道可以取得幫助：

### 💬 社群支援
- [GitHub Discussions](../../discussions) - 一般討論和問題
- [Discord Server](https://discord.gg/your-server) - 即時聊天
- [Stack Overflow](https://stackoverflow.com/questions/tagged/is1ab-ctf) - 技術問題

### 📚 文檔資源
- [快速開始指南](quick-start-guide.md)
- [工作流程教學](workflow-tutorial.md)
- [API 文檔](../web-interface/README.md)

### 🐛 問題回報
- [Bug 回報模板](../.github/ISSUE_TEMPLATE/bug-report.md)
- [功能請求模板](../.github/ISSUE_TEMPLATE/feature-request.md)

---

**🎉 感謝您對 is1ab-CTF-template 的貢獻！每一個貢獻都讓這個專案變得更好。**

---

*最後更新：2025-08-03*