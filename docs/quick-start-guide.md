# ⚡ 快速開始指南

想要立即開始使用 is1ab-CTF-template？這份指南將帶您在 15 分鐘內完成第一個 CTF 題目的創建！

## 🎯 預期結果

完成本指南後，您將：
- ✅ 擁有一個可運行的 CTF 開發環境
- ✅ 創建第一個 Web 題目
- ✅ 了解基本的工作流程
- ✅ 能夠啟動 Web 管理介面

---

## 🚀 第一步：環境準備（5 分鐘）

### 安裝必要工具

```bash
# 安裝 UV（現代 Python 包管理器）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip
pip install uv

# 安裝 GitHub CLI（可選）
# macOS
brew install gh

# Ubuntu/Debian
sudo apt install gh

# Windows
winget install GitHub.cli
```

### 克隆模板

```bash
# 方法一：直接克隆
git clone https://github.com/is1ab/is1ab-CTF-template.git my-ctf-2024
cd my-ctf-2024

# 方法二：使用 GitHub template（推薦）
# 1. 前往 GitHub 點擊 "Use this template"
# 2. 創建新倉庫
# 3. 克隆您的新倉庫
```

### 初始化環境

```bash
# 創建虛擬環境並安裝依賴
uv venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

uv pip install -r requirements.txt

# 初始化專案
uv run scripts/init-project.py --year 2024 --org your-org
```


---

## 🎨 第二步：創建第一個題目（5 分鐘）

### 創建 Web 題目

```bash
# 使用腳本快速創建
uv run scripts/create-challenge.py web welcome baby --author "$(git config user.name)"

# 進入題目目錄
cd challenges/web/welcome/
ls -la
```

您應該看到這樣的目錄結構：
```
welcome/
├── README.md          # 題目說明
├── public.yml         # 公開發布配置  
├── private.yml        # 私有配置
├── attachments/       # 附件目錄
├── src/              # 源碼目錄
│   └── app.py        # Flask 應用
├── solution/         # 解題腳本
│   ├── solve.py
│   └── writeup.md
└── docker/           # Docker 配置
    ├── Dockerfile
    └── docker-compose.yml
```

### 編輯題目內容

```bash
# 編輯題目描述
cat > README.md << 'EOF'
# Welcome Challenge

歡迎來到我們的 CTF 比賽！這是一個簡單的歡迎題目。

## 題目描述

訪問網站，找到隱藏的 Flag。

## 題目網址

http://localhost:3000

## 提示

有時候最簡單的地方往往隱藏著答案...
EOF

# 編輯 public.yml
cat > public.yml << 'EOF'
title: "歡迎來到 CTF"
category: "web"
difficulty: "baby"
author: "CTF Team"
points: 100
description: |
  歡迎來到我們的 CTF 比賽！
  
  這是一個簡單的入門題目，訪問網站並找到隱藏的 Flag。
  
  網站地址：http://challenge-host:3000

ready_for_release: true

allowed_files:
  - "src/**"
  - "docker/**"
  - "attachments/*"

deployment:
  type: "static"
  port: 3000

tags:
  - "beginner"
  - "web"
  - "welcome"
EOF
```

### 建立簡單的 Web 應用

```bash
# 編輯 Flask 應用
cat > src/app.py << 'EOF'
from flask import Flask, render_template_string

app = Flask(__name__)

FLAG = "your-orgCTF{welcome_to_our_amazing_ctf_2024!}"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>歡迎來到 CTF 2024</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .flag { display: none; color: green; font-family: monospace; }
        h1 { color: #2c3e50; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎉 歡迎來到 CTF 2024！</h1>
        <p>恭喜您成功訪問了我們的比賽網站！</p>
        <p>現在開始您的 CTF 之旅吧！</p>
        
        <h2>🔍 任務</h2>
        <p>您的第一個任務是找到隱藏在這個網頁中的 Flag。</p>
        <p>提示：檢查網頁的源碼...</p>
        
        <!-- Flag: {{ flag }} -->
        <div class="flag">{{ flag }}</div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, flag=FLAG)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
EOF

# 建立 requirements.txt
echo "flask==2.3.3" > src/requirements.txt
```

### 設定 Docker

```bash
# 編輯 Dockerfile
cat > docker/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY src/requirements.txt .
RUN pip install -r requirements.txt

COPY src/ .

EXPOSE 3000

CMD ["python", "app.py"]
EOF

# 編輯 docker-compose.yml
cat > docker/docker-compose.yml << 'EOF'
version: '3.8'

services:
  welcome-challenge:
    build: .
    ports:
      - "3000:3000"
    environment:
      - FLASK_ENV=production
EOF
```

**✅ 檢查點**：執行 `uv run scripts/validate-challenge.py challenges/web/welcome/`，應該看到驗證通過

---

## 🧪 第三步：測試題目（3 分鐘）

### 啟動 Docker 容器

```bash
cd docker/

# 建置並啟動容器
docker-compose up -d

# 檢查容器狀態
docker-compose ps

# 測試網站
curl http://localhost:3000
```

您應該看到 HTML 輸出，其中包含隱藏的 Flag。

### 編寫解題腳本

```bash
cd ../solution/

# 編輯解題腳本
cat > solve.py << 'EOF'
#!/usr/bin/env python3
import requests
import re

def solve():
    """解決 Welcome Challenge"""
    
    # 目標 URL
    url = "http://localhost:3000"
    
    print(f"🎯 正在訪問: {url}")
    
    try:
        # 發送 GET 請求
        response = requests.get(url)
        response.raise_for_status()
        
        print("✅ 成功獲取網頁內容")
        
        # 尋找 Flag（在 HTML 註釋中）
        flag_pattern = r'your-orgCTF\{[^}]+\}'
        flags = re.findall(flag_pattern, response.text)
        
        if flags:
            flag = flags[0]
            print(f"🏁 找到 Flag: {flag}")
            return flag
        else:
            print("❌ 未找到 Flag")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 網路錯誤: {e}")
        return None

if __name__ == "__main__":
    flag = solve()
    if flag:
        print(f"\n🎉 解題成功！")
        print(f"Flag: {flag}")
    else:
        print("\n😞 解題失敗，請檢查題目設定")
EOF

# 測試解題腳本
chmod +x solve.py
python solve.py
```

**✅ 檢查點**：解題腳本應該成功找到 Flag

---

## 🌐 第四步：啟動管理介面（2 分鐘）

### 啟動 Web 介面

```bash
# 返回專案根目錄
cd ../../

# 啟動 Web 管理介面
cd web-interface/
python server.py --host localhost --port 8000
```

在瀏覽器中訪問 http://localhost:8000，您應該看到：
- 📊 題目進度儀表板
- 📋 題目配額狀況
- 🎯 題目矩陣顯示
- ✅ 您剛創建的 "歡迎來到 CTF" 題目

**✅ 檢查點**：Web 介面顯示 1/32 題目完成，Web 分類有 1 個題目

---

## 🎉 完成！下一步

恭喜！您已經成功：
- ✅ 設置了 CTF 開發環境
- ✅ 創建了第一個題目
- ✅ 測試了題目功能
- ✅ 啟動了管理介面

### 接下來可以做什麼？

1. **📚 學習完整工作流程**
   ```bash
   # 閱讀詳細教學
   cat docs/workflow-tutorial.md
   ```

2. **🔧 創建更多題目**
   ```bash
   # 創建 Pwn 題目
   uv run scripts/create-challenge.py pwn buffer_overflow easy --author "YourName"
   
   # 創建 Crypto 題目
   uv run scripts/create-challenge.py crypto rsa_challenge middle --author "YourName"
   ```

3. **🚀 設置 Git 工作流程**
   ```bash
   # 建立開發分支
   git checkout -b challenge/web/welcome
   git add .
   git commit -m "feat(web): add welcome challenge"
   ```

4. **🔍 探索進階功能**
   - 批量驗證：`uv run scripts/validate-challenge.py`
   - 公開發布準備：`uv run scripts/prepare-public-release.py`

### 常用命令速查

```bash
# 創建題目
uv run scripts/create-challenge.py <category> <name> <difficulty> --author <author>

# 驗證題目
uv run scripts/validate-challenge.py challenges/<category>/<name>/

# 檢查敏感資料

# 啟動 Web 介面
cd web-interface && python server.py

# 更新進度
uv run scripts/update-readme.py
```

### 🆘 遇到問題？

- 📖 閱讀 [詳細教學](workflow-tutorial.md)
- 🐛 查看 [GitHub Issues](../../issues)
- 💬 參與 [討論區](../../discussions)
- 📧 聯絡我們：[support@is1ab.org]

---

**🎯 目標達成！您現在已經準備好開始您的 CTF 開發之旅了！**