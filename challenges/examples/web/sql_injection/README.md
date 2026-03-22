# SQL Injection 101

> 經典的 SQL Injection 入門題

## 📝 題目描述

一個簡單的登入頁面，但似乎有些安全問題...試著繞過登入機制找到 flag 吧！

## 🎯 學習目標

- 理解 SQL Injection 的原理
- 學習如何利用輸入驗證不足的漏洞
- 掌握基本的 SQL 語法

## 🔧 環境需求

- **難度**: Easy
- **分類**: WEB
- **分數**: 100
- **預估解題時間**: 20 分鐘

## 🚀 連線方式

訪問: `http://localhost:8080`

## 💡 提示

### 提示 1 (免費)
SQL Injection 的經典入門。
試試看在登入表單中輸入特殊字元，例如單引號 '

### 提示 2 (10分)
想想看 SQL 查詢的結構可能是什麼樣子。
`username=' OR 1=1 --` 這樣的輸入會發生什麼？

### 提示 3 (25分)
繞過登入後，flag 可能存在於：
- 登入成功頁面
- 資料庫的其他表格
- Cookie 或 Session

## 🛠️ 推薦工具

- Burp Suite
- curl
- Browser DevTools
- sqlmap (進階)

## 📚 參考資料

- [SQL Injection 教學](https://portswigger.net/web-security/sql-injection)
- [OWASP SQL Injection](https://owasp.org/www-community/attacks/SQL_Injection)

---

**作者**: admin
**創建時間**: 2026-01-18
**最後更新**: 2026-01-18
