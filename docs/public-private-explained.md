# 為什麼有兩個設定檔？public.yml vs private.yml

> 這是本專案最核心的安全設計。讀完這頁你就懂了。

---

## 一句話解釋

**`public.yml` 是參與者看到的題目資訊，`private.yml` 是只有出題者知道的答案。**

---

## 對照表

| | public.yml | private.yml |
|---|---|---|
| **用途** | 題目的公開描述 | 包含 Flag 和解法 |
| **誰看得到** | 所有參與者、公開 repo | 僅出題團隊（私有 repo） |
| **會公開嗎** | 會同步到 public repo | 永遠不會 |
| **包含什麼** | 標題、描述、提示、難度 | Flag、解題步驟、密碼 |
| **Git 保護** | 無特殊保護 | hooks 會掃描並阻擋 |
| **能放 flag 嗎** | 絕對不行 | 專門放 flag 的地方 |

---

## 內容範例

### public.yml（安全，可公開）

```yaml
title: "RSA for Beginners"
category: "crypto"
difficulty: "easy"
description: "你截獲了一段 RSA 加密的訊息，試著破解它..."
points: 120
tags: ["crypto", "rsa", "beginner"]
hints:
  - content: "想想 RSA 的弱點在哪裡"
    cost: 0
  - content: "n 很小的時候..."
    cost: 10
```

### private.yml（機密，不公開）

```yaml
flag: "is1abCTF{rsa_t00_sm4ll_n}"
solution_steps:
  - "分解 n 得到 p 和 q"
  - "計算 phi(n) = (p-1)(q-1)"
  - "計算 d = e^(-1) mod phi(n)"
  - "解密得到 flag"
internal_notes: "n 只有 64 bits，可用 factordb.com 直接查"
```

---

## 資料流：從開發到公開

```
私有 repo（開發環境）
┌─────────────────────────┐
│  public.yml   ← 會公開  │
│  private.yml  ← 不公開  │──→ build.sh ──→ 過濾敏感資料
│  src/                    │         │
│  docker/                 │         ↓
│  solution/    ← 不公開  │    public-release/
│  writeup/     ← 可選    │    ┌──────────────┐
└─────────────────────────┘    │  public.yml   │ ← 安全的
                               │  README.md    │
                               │  docker/      │ ← flag 已移除
                               │  （無 private）│
                               └──────────────┘
                                     │
                                     ↓
                               公開 repo（參與者看到的）
```

---

## 安全防護機制

本專案有多層防護確保 private.yml 不會洩漏：

1. **`.gitignore`** — private.yml 被列在 gitignore 的排除清單
2. **Pre-commit Hook** — 每次 commit 前自動掃描 flag 格式字串
3. **Pre-push Hook** — 推送前再次檢查
4. **GitHub Actions** — PR 提交後 CI 自動掃描
5. **build.sh** — 建置公開版本時自動移除所有敏感檔案

即使你不小心把 flag 寫在 public.yml 中，Git hooks 會阻擋你的 commit：

```
🚫 BLOCKED: Flag pattern detected in public.yml
   Line 5: is1abCTF{...}

   Flag 應該只放在 private.yml 中！
```

---

## 常見問題

### Q: 我可以不用 private.yml 嗎？
不建議。private.yml 是驗證系統的一部分，validate-challenge 會檢查它的存在。

### Q: 我的 flag 需要動態產生怎麼辦？
在 private.yml 中設定 `flag_type: "dynamic"`，並在 `dynamic_flag` 欄位提供產生邏輯。

### Q: 團隊其他人能看到我的 private.yml 嗎？
在私有 repo 中可以（有 repo 存取權的人都能看到）。在公開 release 中不會出現。

---

## 下一步

理解了為什麼分兩個檔案後，回到 [QUICKSTART.md](../QUICKSTART.md) 繼續操作。
