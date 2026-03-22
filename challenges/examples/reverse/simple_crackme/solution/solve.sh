#!/bin/bash
# Simple Crackme - Solution Script

echo "=== Simple Crackme Solution ==="
echo ""

BINARY="../files/crackme"

if [[ ! -f "$BINARY" ]]; then
    echo "[!] Binary not found at $BINARY"
    echo "[*] Trying to find in current directory..."
    BINARY="./crackme"
fi

echo "[*] Method 1: Using strings"
echo "    Command: strings crackme | grep -E '(FLAG|password|secret)'"
echo ""
strings "$BINARY" 2>/dev/null | grep -iE '(FLAG|password|secret)' || echo "    (Binary not found, showing expected output)"
echo ""

echo "[*] Method 2: Using ltrace (if available)"
echo "    Command: echo 'test' | ltrace ./crackme 2>&1 | grep strcmp"
echo ""

echo "[*] Method 3: Direct execution with found password"
echo "    Password: sup3r_s3cr3t_p4ssw0rd"
echo ""

echo "[+] Expected Flag: FLAG{r3v3rs3_3ng1n33r1ng_101}"
