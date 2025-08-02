FROM ubuntu:22.04

# 安裝基本工具
RUN apt-get update && apt-get install -y \
    xinetd \
    socat \
    && rm -rf /var/lib/apt/lists/*

# 建立 ctf 用戶
RUN useradd -m -s /bin/bash ctf

# 設定工作目錄
WORKDIR /home/ctf

# 複製題目檔案
COPY bin/ ./
COPY start.sh ./
COPY run.sh ./

# 設定權限
RUN chmod +x start.sh run.sh
RUN chmod +x ./* 2>/dev/null || true
RUN chown -R root:ctf /home/ctf
RUN chmod -R 750 /home/ctf

# 暴露端口
EXPOSE 9999

# 設定啟動命令
CMD ["./start.sh"]