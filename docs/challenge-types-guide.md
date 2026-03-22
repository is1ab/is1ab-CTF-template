# 題目類型選擇指南

> 不知道該選什麼類型？這份指南幫你做決定。

---

## 決策樹

```
你的題目需要參與者連線到網路服務嗎？
│
├── 是 → 參與者透過什麼方式連線？
│   │
│   ├── nc / TCP 直連（例：buffer overflow）
│   │   → 選擇 nc_challenge
│   │
│   └── HTTP / 網頁瀏覽器（例：SQL injection, XSS）
│       → 選擇 static_container
│
└── 否 → 參與者需要下載檔案嗎？
    │
    ├── 是 → 下載什麼？
    │   │
    │   ├── 加密文件、密鑰（密碼學）
    │   │   → crypto + static_attachment
    │   │
    │   ├── 執行檔、binary（逆向工程）
    │   │   → reverse + static_attachment
    │   │
    │   ├── 圖片、封包、記憶體 dump（鑑識）
    │   │   → misc + static_attachment
    │   │
    │   └── 其他檔案
    │       → misc + static_attachment
    │
    └── 否 → 純文字題或 OSINT
        → misc + static_attachment（無附件）
```

---

## 五種題目類型對照表

| 類型 | 說明 | 需要 Docker | 範例 |
|---|---|---|---|
| `static_attachment` | 給參與者下載檔案，離線解題 | 不需要 | 密碼學、逆向工程、鑑識 |
| `nc_challenge` | 參與者用 nc/netcat 連線互動 | 需要 | Buffer overflow、format string |
| `static_container` | 部署 Web 服務讓參與者存取 | 需要 | SQL injection、XSS、SSRF |
| `dynamic_attachment` | 每位參與者取得不同檔案 | 需要 | 動態 flag 的 crypto 題 |
| `dynamic_container` | 每位參與者取得獨立容器 | 需要 | 需要隔離環境的題目 |

> 新手建議從 `static_attachment` 開始，不需要 Docker，最簡單。

---

## 各類型最小檔案結構

### static_attachment（最簡單）

```
my_challenge/
├── public.yml          # 題目資訊
├── private.yml         # Flag
├── README.md           # 題目敘述
├── src/                # 原始碼（產生附件用）
│   └── generate.py
└── files/              # 給參與者下載的檔案
    └── challenge.txt
```

不需要 `docker/` 目錄。參考範例：`challenges/examples/crypto/rsa_beginner/`

### nc_challenge

```
my_challenge/
├── public.yml
├── private.yml
├── README.md
├── src/                # 服務原始碼
│   ├── chall.c
│   └── Makefile
├── docker/
│   ├── Dockerfile      # 用 socat 暴露服務
│   ├── docker-compose.yml
│   └── bin/            # 編譯後的執行檔
└── solution/
    └── exploit.py
```

參考範例：`challenges/examples/pwn/buffer_overflow/`

### static_container

```
my_challenge/
├── public.yml
├── private.yml
├── README.md
├── src/                # Web 應用原始碼
│   ├── app.py
│   ├── requirements.txt
│   └── templates/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
└── solution/
    └── exploit.py
```

參考範例：`challenges/examples/web/sql_injection/`

---

## 建立指令

```bash
# static_attachment（Crypto 題目）
make new-challenge ARGS="crypto my_crypto easy"

# nc_challenge（PWN 題目）
make new-challenge ARGS="pwn my_pwn easy --type nc_challenge"

# static_container（Web 題目）
make new-challenge ARGS="web my_web easy --type static_container"

# 鑑識題目
make new-challenge ARGS="forensic my_forensic easy"

# 腳本會自動偵測類型，但你也可以用 --type 手動指定
```

> 可用 category：`web`、`pwn`、`reverse`、`crypto`、`forensic`、`misc`、`general`
> 可用 difficulty：`baby`、`easy`、`middle`、`hard`、`impossible`
```

---

## 下一步

選好類型後，回到 [QUICKSTART.md](../QUICKSTART.md) 繼續 Phase B。
