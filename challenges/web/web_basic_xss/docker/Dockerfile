FROM ubuntu:20.04

# 設定工作目錄
WORKDIR /app

# 安裝基本套件
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 複製應用程式檔案
COPY src/ /app/

# 設定執行權限
RUN chmod +x /app/*

# 暴露端口
EXPOSE 8080

# 啟動應用程式
CMD ["./start.sh"]
