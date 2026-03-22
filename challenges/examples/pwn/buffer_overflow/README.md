# Buffer Overflow 101

> 經典的 stack buffer overflow 入門題

## 📝 題目描述

這是一個經典的 buffer overflow 題目，適合 pwn 入門者。程式沒有開啟任何保護機制，只需要覆蓋 return address 即可控制程式流程。

## 🎯 學習目標

- 理解 buffer overflow 的原理
- 學習如何利用 stack 溢出控制程式流程
- 掌握基本的 pwn 工具使用

## 🔧 環境需求

- **難度**: Easy
- **分類**: PWN
- **分數**: 150
- **預估解題時間**: 30 分鐘

## 🚀 連線方式

```bash
nc <host> <port>
```

## 📦 附件

- `chall` - 題目執行檔
- `libc.so.6` - 題目使用的 libc

## 💡 提示

### 提示 1 (免費)
檢查一下程式有沒有開啟保護機制。
提示：使用 checksec 工具。

### 提示 2 (10分)
找找看程式中是否有危險函數，例如 gets()。
嘗試輸入很長的字串看看會發生什麼。

### 提示 3 (25分)
計算從輸入點到 return address 的偏移量。
可以使用 cyclic pattern 來幫助定位。

## 🛠️ 推薦工具

- pwntools
- gdb / pwndbg / gef
- checksec
- ROPgadget

## 📚 參考資料

- [Buffer Overflow 教學](https://ctf101.org/binary-exploitation/buffer-overflow/)

---

**作者**: admin
**創建時間**: 2026-01-18
**最後更新**: 2026-01-18
