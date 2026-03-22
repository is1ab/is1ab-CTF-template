#!/bin/bash
# PWN 題目建構腳本

set -e

echo "🔨 Building PWN challenge: Buffer Overflow"

# 進入 src 目錄編譯
cd ../src
make clean
make

# 複製執行檔到 docker 目錄
cp chall ../docker/
cp chall ../files/  # 也複製到 files 給選手下載

# 複製 libc
cp /lib/x86_64-linux-gnu/libc.so.6 ../files/ 2>/dev/null || \
    echo "⚠️  Warning: Could not copy libc.so.6"

# 創建 flag 文件
echo "FLAG{buff3r_0v3rfl0w_1s_34sy}" > ../docker/flag.txt

# 回到 docker 目錄
cd ../docker

# 建構 Docker image
echo "🐳 Building Docker image..."
docker compose build

echo "✅ Build complete!"
echo ""
echo "To start the challenge:"
echo "  docker compose up -d"
echo ""
echo "To test locally:"
echo "  nc localhost 9999"
