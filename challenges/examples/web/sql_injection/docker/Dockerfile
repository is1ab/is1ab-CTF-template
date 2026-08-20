FROM python:3.14-slim

WORKDIR /app

# 複製應用程式
COPY src/ /app/

# 安裝依賴
RUN pip install --no-cache-dir -r requirements.txt

# 創建資料庫目錄
RUN mkdir -p /app/data

# 設定環境變數
ENV FLASK_APP=app.py
# 注意：FLAG 應該透過 docker-compose.yml 或 --env-file 傳入
# 不要在 Dockerfile 中硬編碼 flag，因為會被記錄在 image layers

# 建立非 root 用戶（釘數字 UID 1000；k3s PSA restricted + runAsNonRoot 需數字 USER）
RUN useradd -m -u 1000 -s /bin/bash appuser && chown -R appuser:appuser /app
USER 1000

# 暴露端口
EXPOSE 8080

# 啟動應用
CMD ["python", "app.py"]
