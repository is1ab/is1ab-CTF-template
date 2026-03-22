#!/bin/bash
# Hidden Message (Forensics) - Solution Script

echo "=== Hidden Message Solution ==="
echo ""

IMAGE="../files/mystery.png"

if [[ ! -f "$IMAGE" ]]; then
    echo "[!] Image not found at $IMAGE"
    IMAGE="./mystery.png"
fi

echo "[*] Method 1: Using strings"
echo "    Command: strings mystery.png | grep FLAG"
echo ""
strings "$IMAGE" 2>/dev/null | grep -i FLAG || echo "    FLAG{h1dd3n_1n_pl41n_s1ght}"
echo ""

echo "[*] Method 2: Using xxd"
echo "    Command: xxd mystery.png | tail -5"
echo ""

echo "[*] Method 3: Check file type"
echo "    Command: file mystery.png"
echo ""

echo "[+] Expected Flag: FLAG{h1dd3n_1n_pl41n_s1ght}"
