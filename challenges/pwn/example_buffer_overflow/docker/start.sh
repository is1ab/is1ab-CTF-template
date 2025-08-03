#!/bin/bash

# 設定 flag 檔案
echo "$FLAG" > /home/ctf/flag.txt
chown root:ctf /home/ctf/flag.txt
chmod 640 /home/ctf/flag.txt

# 使用 socat 啟動服務
echo "Starting challenge on port 9999..."
socat TCP-LISTEN:9999,reuseaddr,fork EXEC:"timeout 60 ./run.sh",su=ctf,pty,stderr