# Example Buffer Overflow

**Author:** GZTime  
**Difficulty:** baby  
**Category:** pwn

---

一個簡單的緩衝區溢位題目，適合初學者練習基本的漏洞利用技巧

## Flag 格式
```
flag: is1abCTF{...}
```

## 題目類型
- [ ] **靜態附件**: 共用附件，任意 flag
- [ ] **靜態容器**: 共用容器，任意 flag  
- [ ] **動態附件**: 依照隊伍分配附件
- [ ] **動態容器**: 自動生成 flag，每隊唯一
- [x] **NC 題目**: 透過 netcat 連線的題目

## 提供的檔案
- 無

## 原始碼提供
- **是否提供原始碼**: ❌ 否

## 連線資訊
- **本地測試**: `nc localhost 9999`
- **遠端連線**: `nc TBD 9999`
- **連線逾時**: 60 秒

---

## 🏃‍♂️ 快速開始

### 本地測試
```bash
cd docker/
docker-compose up -d
nc localhost 9999
```

### 編譯題目
```bash
cd src/
make
cp challenge ../docker/bin/
```

## 🔧 開發資訊

- **狀態**: planning
- **分數**: 50
- **標籤**: pwn, buffer_overflow, beginner
- **建立時間**: 2024-08-02

## 🔍 解題思路 (僅內部可見)

<details>
<summary>點擊展開解題提示</summary>

1. TODO: 第一步提示
2. TODO: 第二步提示  
3. TODO: 第三步提示

**實際 Flag**: `is1abCTF{TODO_actual_flag_here}`

</details>

## 📁 檔案說明

- `src/`: 完整源碼
- `docker/`: Docker 部署檔案
- `bin/`: 編譯後的可執行檔案 (nc 題目)
- `files/`: 提供給參賽者的檔案
- `writeup/`: 官方詳細解答

## ⚠️ 注意事項

- TODO: 添加特殊注意事項
- TODO: 安全考量
- TODO: 效能考量

---
**最後更新**: 2024-08-02  
**測試狀態**: ❌ 待測試