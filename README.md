# IS1AB CTF Template

> CTF 題目開發與管理模板 — 從 Private 開發到 Public 發布的完整自動化流程

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## 第一次使用？

**30 分鐘建立你的第一個題目** → **[QUICKSTART.md](QUICKSTART.md)**

| 我想... | 去哪裡 |
|---------|--------|
| 從零開始建立題目 | [QUICKSTART.md](QUICKSTART.md) |
| 選擇題目類型 | [題目類型指南](docs/challenge-types-guide.md) |
| 理解 public/private YAML | [為什麼分兩個設定檔](docs/public-private-explained.md) |
| 解決遇到的問題 | [常見問題](docs/troubleshooting.md) |
| Git 操作速查 | [Git 速查表](docs/git-workflow-cheatsheet.md) |
| 查看常用指令 | `make help` 或 [命令速查表](docs/quick-reference.md) |
| 完整文件索引 | [docs/README.md](docs/README.md) |

---

## 專案概述

專為**團隊協作開發 CTF 比賽題目**設計的三階段系統：

```
Template Repository（本專案）
        ↓ Use Template
Private Dev Repo（團隊開發倉庫）
        ↓ Feature Branches + PR + Code Review
合併到 main branch → CI 自動驗證
        ↓ 比賽結束後觸發發布
Public Release（自動移除 flag）→ GitHub Pages
```

> 詳細流程：[CTF 題目開發完整流程指南](docs/ctf-challenge-workflow.md)

---

## 快速開始

```bash
# 1. 取得專案
git clone <your-private-repo-url>
cd <repo-name>

# 2. 安裝依賴 + 設定環境
uv sync && make setup

# 3. 建立題目
make new-challenge ARGS="web my_challenge easy"

# 4. 驗證 + 掃描
make validate ARGS="challenges/web/my_challenge"
make scan

# 5. 提交 PR
git add challenges/web/my_challenge/
git commit -m "feat(web): add my_challenge"
git push -u origin challenge/web/my_challenge
```

---

## 題目範例

| 類型 | 範例 | 難度 | 路徑 |
|------|------|------|------|
| PWN | Buffer Overflow 101 | Easy | `challenges/examples/pwn/buffer_overflow/` |
| WEB | SQL Injection 101 | Easy | `challenges/examples/web/sql_injection/` |
| CRYPTO | RSA for Beginners | Easy | `challenges/examples/crypto/rsa_beginner/` |
| REVERSE | Simple Crackme | Easy | `challenges/examples/reverse/simple_crackme/` |
| MISC | Hidden Message | Baby | `challenges/examples/misc/forensics_basic/` |

每個範例都含：`public.yml` + `private.yml` + 原始碼 + Docker 設定 + 解答。

---

## 專案結構

```
is1ab-CTF-template/
├── challenges/              # CTF 題目目錄
│   └── examples/            # 5 種完整範例題目
├── scripts/                 # 自動化腳本
│   ├── create-challenge.py  # 題目建立精靈
│   ├── validate-challenge.py # 題目驗證
│   ├── scan-secrets.py      # 安全掃描
│   └── build.sh             # 公開版本建置
├── docs/                    # 完整文件（25+ 份）
├── viewer/site/             # 內部進度 Viewer
├── web-interface/           # Web 管理介面
├── .github/workflows/       # 10 個 CI/CD 工作流程
├── config.yml               # 全域設定
├── Makefile                 # 統一指令入口
└── QUICKSTART.md            # 新手入門教學
```

---

## 常用指令

```bash
make help            # 查看所有指令
make setup           # 初始設置（hooks + 驗證）
make new-challenge   # 建立新題目
make validate        # 驗證題目
make validate-all    # 驗證所有題目
make scan            # 安全掃描
make test            # 執行測試
make build           # 建置公開版本
make viewer          # 生成 Viewer 資料
```

---

## 安全機制

| 防護層 | 機制 | 說明 |
|--------|------|------|
| 本地 | Git Hooks | commit/push 前自動掃描 flag 和敏感檔案 |
| 本地 | pre-commit | YAML 驗證、大檔案檢查、安全掃描 |
| CI | validate-challenge | 驗證目錄結構、YAML 格式、Docker 建置 |
| CI | pr-policy-check | 分支命名、ownership 驗證 |
| CI | security-scan | Flag 洩漏、敏感資料、第三方掃描 |
| 建置 | build.sh | 移除所有 private.yml、flag、解答 |

> 詳細說明：[安全流程指南](wiki/Security-Workflow-Guide.md) | [安全檢查清單](docs/security-checklist.md)

---

## 初始化檢查清單

使用 Template 建立私有 repo 後，完成以下設定：

- [ ] `make setup` — 安裝 Git Hooks + 驗證環境
- [ ] 編輯 `config.yml` — 設定 flag_prefix、平台 URL
- [ ] 編輯 `.github/CODEOWNERS` — 替換 `@admin`/`@senior-dev` 為實際用戶名
- [ ] 設定 GitHub Secrets — 參閱 [GitHub Secrets 指南](wiki/GitHub-Secrets-Setup.md)
- [ ] 設定分支保護 — 參閱 [分支保護指南](wiki/Branch-Protection-Setup.md)
- [ ] （推薦）設定 GPG 簽名 — 參閱 [Commit 簽名指南](wiki/Commit-Signing-Guide.md)

---

## 貢獻

請參閱 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [行為準則](CODE_OF_CONDUCT.md)。

## 授權

MIT License — 詳見 [LICENSE](LICENSE)。

## 支援

- [Troubleshooting](docs/troubleshooting.md) | [完整 FAQ](wiki/FAQ-and-Troubleshooting.md)
- [提交 Issue](https://github.com/is1ab/is1ab-CTF-template/issues) | [討論區](https://github.com/is1ab/is1ab-CTF-template/discussions)
