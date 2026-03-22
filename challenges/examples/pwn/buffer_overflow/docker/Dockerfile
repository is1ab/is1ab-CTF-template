FROM ubuntu:22.04

# 安裝必要套件
RUN apt-get update && \
    apt-get install -y socat && \
    rm -rf /var/lib/apt/lists/*

# 創建題目目錄
WORKDIR /home/ctf

# 複製編譯好的執行檔
COPY chall /home/ctf/chall

# 創建預設 flag（會被 docker-compose 的 volume 覆蓋）
RUN echo "FLAG{placeholder_replace_me}" > /home/ctf/flag.txt

# 如果有提供 flag.txt 則複製（build 時可選）
COPY flag.tx[t] /home/ctf/

# 設定權限
RUN chmod 755 /home/ctf/chall && \
    chmod 444 /home/ctf/flag.txt

# 創建 ctf 用戶（安全考量）
RUN useradd -m ctf && \
    chown -R root:ctf /home/ctf && \
    chmod 750 /home/ctf

# 切換到 ctf 用戶
USER ctf

# 暴露端口
EXPOSE 9999

# 使用 socat 啟動 NC 服務
CMD ["socat", "TCP-LISTEN:9999,reuseaddr,fork", "EXEC:./chall,stderr"]
