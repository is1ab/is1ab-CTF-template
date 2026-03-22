# 🐳 部署指南

本指南將協助您將 CTF 題目部署到生產環境，包含 Docker 容器化、平台整合和監控設置。

## 📋 部署概覽

### 支援的部署方式
- **🐳 Docker 容器** - 推薦方式，支援隔離和擴展
- **☁️ 雲端平台** - AWS、GCP、Azure 等
- **🖥️ 本地伺服器** - 自建機房或 VPS
- **🔗 平台整合** - GZCTF、CTFd 等 CTF 平台

### 部署架構
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   CTF Platform  │    │   Monitoring    │
│    (Nginx)      │◄──►│    (GZCTF)      │◄──►│  (Prometheus)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                       ▲                       ▲
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Challenge     │    │   Database      │    │     Logs        │
│   Containers    │    │   (PostgreSQL)  │    │   (ELK Stack)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 🐳 Docker 部署

### 1. 基本 Docker 部署

#### 單個題目部署
```bash
# 進入題目目錄
cd challenges/web/example/docker/

# 建置映像
docker build -t ctf-web-example .

# 執行容器
docker run -d \
  --name ctf-web-example \
  -p 8080:80 \
  --restart unless-stopped \
  ctf-web-example

# 檢查狀態
docker ps
docker logs ctf-web-example
```

#### 使用 Docker Compose
```yaml
# challenges/web/example/docker/docker-compose.yml
version: '3.8'

services:
  web-challenge:
    build: .
    ports:
      - "8080:80"
    environment:
      - FLAG_PREFIX=is1abCTF
      - CHALLENGE_NAME=example
    volumes:
      - ./uploads:/var/www/html/uploads
    restart: unless-stopped
    
  database:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: secure_password
      MYSQL_DATABASE: challenge_db
    volumes:
      - db_data:/var/lib/mysql
    restart: unless-stopped

volumes:
  db_data:
```

#### 執行 Docker Compose
```bash
# 啟動服務
docker-compose up -d

# 檢查狀態
docker-compose ps
docker-compose logs

# 停止服務
docker-compose down
```

### 2. 多題目批量部署

#### 使用批量部署腳本
```bash
# 建置所有題目映像
uv run scripts/build-all-challenges.py

# 或指定分類
uv run scripts/build-all-challenges.py --category web

# 部署所有題目
uv run scripts/deploy-challenges.py --environment production
```

#### 創建主要 docker-compose.yml
```yaml
# docker/docker-compose.production.yml
version: '3.8'

services:
  # Web 題目
  web-challenge-1:
    image: ctf-registry/web/challenge-1:latest
    ports:
      - "8001:80"
    environment:
      - NODE_ENV=production
    restart: unless-stopped

  web-challenge-2:
    image: ctf-registry/web/challenge-2:latest
    ports:
      - "8002:80"
    restart: unless-stopped

  # PWN 題目
  pwn-challenge-1:
    image: ctf-registry/pwn/challenge-1:latest
    ports:
      - "9001:9999"
    security_opt:
      - seccomp:unconfined
    restart: unless-stopped

  # 反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - web-challenge-1
      - web-challenge-2
    restart: unless-stopped

  # 監控
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    restart: unless-stopped

networks:
  default:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

---

## ☁️ 雲端部署

### 1. AWS 部署

#### 使用 ECS (Elastic Container Service)
```yaml
# aws/ecs-task-definition.json
{
  "family": "ctf-challenges",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "web-challenge",
      "image": "your-account.dkr.ecr.region.amazonaws.com/ctf-web:latest",
      "portMappings": [
        {
          "containerPort": 80,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "FLAG_PREFIX",
          "value": "is1abCTF"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ctf-challenges",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### 部署腳本
```bash
#!/bin/bash
# scripts/deploy-aws.sh

# 建置並推送到 ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-west-2.amazonaws.com

# 標記並推送映像
docker tag ctf-web-challenge:latest your-account.dkr.ecr.us-west-2.amazonaws.com/ctf-web:latest
docker push your-account.dkr.ecr.us-west-2.amazonaws.com/ctf-web:latest

# 更新 ECS 服務
aws ecs update-service \
  --cluster ctf-cluster \
  --service ctf-web-service \
  --force-new-deployment
```

### 2. Google Cloud Platform

#### 使用 Cloud Run
```yaml
# gcp/cloudrun-service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: ctf-web-challenge
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
    spec:
      containers:
      - image: gcr.io/project-id/ctf-web-challenge:latest
        ports:
        - containerPort: 8080
        env:
        - name: FLAG_PREFIX
          value: "is1abCTF"
        resources:
          limits:
            cpu: 1000m
            memory: 512Mi
```

#### 部署腳本
```bash
#!/bin/bash
# scripts/deploy-gcp.sh

# 建置並推送到 Container Registry
gcloud builds submit --tag gcr.io/project-id/ctf-web-challenge:latest .

# 部署到 Cloud Run
gcloud run deploy ctf-web-challenge \
  --image gcr.io/project-id/ctf-web-challenge:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### 3. Azure 部署

#### 使用 Container Instances
```bash
# 創建資源群組
az group create --name ctf-resources --location eastus

# 部署容器
az container create \
  --resource-group ctf-resources \
  --name ctf-web-challenge \
  --image yourregistry.azurecr.io/ctf-web:latest \
  --cpu 1 \
  --memory 1 \
  --ports 80 \
  --environment-variables FLAG_PREFIX=is1abCTF \
  --restart-policy Always
```

---

## 🎯 CTF 平台整合

### 1. GZCTF 整合

#### 動態容器配置
```yaml
# gzctf-config.yml
challenges:
  - name: "Web Challenge 1"
    category: "Web"
    type: "DynamicContainer"
    image: "ctf-registry/web/challenge-1:latest"
    memoryLimit: 64
    cpuCount: 1
    storageLimit: 256
    enableTrafficCapture: true
    ports:
      - type: "HTTP"
        port: 80
    flags:
      - flag: "is1abCTF{dynamic_flag_here}"
        env: "FLAG"
```

#### API 整合腳本
```python
# scripts/sync-to-gzctf.py
import requests
import yaml
from pathlib import Path

class GZCTFIntegration:
    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def create_challenge(self, challenge_data):
        """創建題目到 GZCTF"""
        response = requests.post(
            f"{self.api_url}/api/admin/challenges",
            json=challenge_data,
            headers=self.headers
        )
        return response.json()
    
    def sync_all_challenges(self):
        """同步所有準備好的題目"""
        challenges_dir = Path('challenges')
        
        for category_dir in challenges_dir.iterdir():
            if not category_dir.is_dir():
                continue
                
            for challenge_dir in category_dir.iterdir():
                if not challenge_dir.is_dir():
                    continue
                
                public_yml = challenge_dir / 'public.yml'
                if not public_yml.exists():
                    continue
                
                with open(public_yml) as f:
                    config = yaml.safe_load(f)
                
                if config.get('ready_for_deployment'):
                    challenge_data = self.convert_to_gzctf_format(config)
                    result = self.create_challenge(challenge_data)
                    print(f"Created challenge: {result}")
    
    def convert_to_gzctf_format(self, config):
        """轉換為 GZCTF 格式"""
        return {
            'title': config['title'],
            'content': config['description'],
            'category': config['category'],
            'type': 'DynamicContainer' if config.get('deployment', {}).get('type') == 'dynamic' else 'StaticAttachment',
            'isEnabled': True,
            'containerImage': f"ctf-registry/{config['category']}/{config['title'].lower()}:latest",
            'memoryLimit': config.get('resources', {}).get('memory', 64),
            'cpuCount': config.get('resources', {}).get('cpu', 1),
            'originalScore': config.get('points', 100)
        }
```

### 2. CTFd 整合

#### 挑戰導入腳本
```python
# scripts/sync-to-ctfd.py
import requests
import yaml
from pathlib import Path

class CTFdIntegration:
    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.headers = {
            'Authorization': f'Token {api_key}',
            'Content-Type': 'application/json'
        }
    
    def create_challenge(self, challenge_data):
        """創建題目到 CTFd"""
        response = requests.post(
            f"{self.api_url}/api/v1/challenges",
            json=challenge_data,
            headers=self.headers
        )
        return response.json()
    
    def upload_file(self, file_path, challenge_id):
        """上傳附件檔案"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'challenge_id': challenge_id, 'type': 'challenge'}
            
            response = requests.post(
                f"{self.api_url}/api/v1/files",
                files=files,
                data=data,
                headers={'Authorization': f'Token {self.api_key}'}
            )
        return response.json()
```

---

## 🔧 自動化部署

### 1. GitHub Actions CI/CD

```yaml
# .github/workflows/deploy-production.yml
name: 🚀 Deploy to Production

on:
  push:
    branches: [main]
    paths: ['challenges/**/docker/**']
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment environment'
        required: true
        default: 'production'
        type: choice
        options:
          - staging
          - production

env:
  REGISTRY: ghcr.io
  DOCKER_USERNAME: ${{ github.actor }}
  DOCKER_PASSWORD: ${{ secrets.GITHUB_TOKEN }}

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.changes.outputs.matrix }}
    steps:
      - uses: actions/checkout@v4
      - id: changes
        run: |
          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
            CHALLENGES=$(find challenges -name "Dockerfile" -exec dirname {} \; | sort)
          else
            CHALLENGES=$(git diff --name-only HEAD^ | grep "challenges/.*/docker/" | xargs dirname | sort -u)
          fi
          
          MATRIX=$(echo "$CHALLENGES" | jq -R -s -c 'split("\n")[:-1]')
          echo "matrix=$MATRIX" >> $GITHUB_OUTPUT

  build-and-deploy:
    needs: detect-changes
    if: needs.detect-changes.outputs.matrix != '[]'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        challenge: ${{ fromJson(needs.detect-changes.outputs.matrix) }}
      
    steps:
      - uses: actions/checkout@v4
      
      - name: 🐳 Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: 🔐 Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ env.DOCKER_USERNAME }}
          password: ${{ env.DOCKER_PASSWORD }}
      
      - name: 📝 Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ github.repository }}/${{ matrix.challenge }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}
      
      - name: 🏗️ Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: ${{ matrix.challenge }}
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: 🚀 Deploy to server
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_KEY }}
          script: |
            cd /opt/ctf-deployment
            
            # 更新 docker-compose.yml 中的映像標籤
            CHALLENGE_NAME=$(basename ${{ matrix.challenge }})
            CATEGORY=$(basename $(dirname ${{ matrix.challenge }}))
            
            # 拉取最新映像
            docker pull ${{ env.REGISTRY }}/${{ github.repository }}/${{ matrix.challenge }}:latest
            
            # 重新啟動服務
            docker-compose up -d ${CATEGORY}_${CHALLENGE_NAME}
            
            # 健康檢查
            sleep 10
            docker-compose ps ${CATEGORY}_${CHALLENGE_NAME}
```

### 2. 監控和健康檢查

```python
# scripts/health-check.py
import requests
import time
import yaml
from pathlib import Path

class HealthChecker:
    def __init__(self, config_file='deployment.yml'):
        with open(config_file) as f:
            self.config = yaml.safe_load(f)
    
    def check_challenge_health(self, challenge_url, expected_status=200):
        """檢查單個題目的健康狀態"""
        try:
            response = requests.get(challenge_url, timeout=10)
            return {
                'status': 'healthy' if response.status_code == expected_status else 'unhealthy',
                'response_time': response.elapsed.total_seconds(),
                'status_code': response.status_code
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def check_all_challenges(self):
        """檢查所有部署的題目"""
        results = {}
        
        for challenge in self.config.get('challenges', []):
            url = challenge['url']
            result = self.check_challenge_health(url)
            results[challenge['name']] = result
            
            print(f"Challenge: {challenge['name']}")
            print(f"Status: {result['status']}")
            if 'response_time' in result:
                print(f"Response time: {result['response_time']:.3f}s")
            if 'error' in result:
                print(f"Error: {result['error']}")
            print("-" * 40)
        
        return results
    
    def send_alert(self, unhealthy_challenges):
        """發送告警通知"""
        if not unhealthy_challenges:
            return
        
        webhook_url = self.config.get('alerts', {}).get('webhook_url')
        if not webhook_url:
            return
        
        message = f"🚨 Unhealthy challenges detected:\n"
        for name, status in unhealthy_challenges.items():
            message += f"- {name}: {status.get('error', 'Unknown error')}\n"
        
        requests.post(webhook_url, json={'text': message})

if __name__ == "__main__":
    checker = HealthChecker()
    results = checker.check_all_challenges()
    
    unhealthy = {name: result for name, result in results.items() 
                if result['status'] == 'unhealthy'}
    
    if unhealthy:
        checker.send_alert(unhealthy)
        exit(1)
    else:
        print("✅ All challenges are healthy!")
```

---

## 📊 監控和日誌

### 1. Prometheus 監控配置

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ctf-challenges'
    static_configs:
      - targets:
        - 'localhost:8001'  # web-challenge-1
        - 'localhost:8002'  # web-challenge-2
        - 'localhost:9001'  # pwn-challenge-1
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'docker'
    static_configs:
      - targets: ['localhost:9323']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### 2. 告警規則

```yaml
# monitoring/alert_rules.yml
groups:
  - name: ctf_challenges
    rules:
      - alert: ChallengeDown
        expr: up{job="ctf-challenges"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "CTF Challenge {{ $labels.instance }} is down"
          description: "Challenge {{ $labels.instance }} has been down for more than 1 minute"

      - alert: HighResponseTime
        expr: http_request_duration_seconds > 5
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High response time on {{ $labels.instance }}"
          description: "Response time is {{ $value }} seconds"

      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage in {{ $labels.name }}"
          description: "Memory usage is above 90%"
```

### 3. 日誌收集

```yaml
# logging/docker-compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.17.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:7.17.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf:ro
    ports:
      - "5044:5044"
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:7.17.0
    ports:
      - "5601:5601"
    environment:
      ELASTICSEARCH_HOSTS: http://elasticsearch:9200
    depends_on:
      - elasticsearch

  filebeat:
    image: docker.elastic.co/beats/filebeat:7.17.0
    volumes:
      - ./filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - logstash

volumes:
  es_data:
```

---

## 🔒 安全最佳實踐

### 1. 容器安全

```dockerfile
# Dockerfile 安全範例
FROM node:16-alpine

# 創建非 root 用戶
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# 設置工作目錄
WORKDIR /app

# 複製並安裝依賴
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# 複製應用程式碼
COPY --chown=nextjs:nodejs . .

# 移除不必要的套件
RUN apk del .build-deps

# 使用非 root 用戶執行
USER nextjs

# 僅暴露必要的埠
EXPOSE 3000

# 使用 exec 形式的 CMD
CMD ["node", "server.js"]
```

### 2. 網路安全

```yaml
# docker-compose.security.yml
version: '3.8'

services:
  web-challenge:
    image: ctf-web:latest
    networks:
      - challenge_network
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID

networks:
  challenge_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
```

### 3. 資源限制

```yaml
# 資源限制配置
services:
  web-challenge:
    image: ctf-web:latest
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
        reservations:
          cpus: '0.1'
          memory: 64M
    ulimits:
      nproc: 65535
      nofile:
        soft: 20000
        hard: 40000
```

---

## 📞 故障排除

### 常見問題

#### 1. 容器啟動失敗
```bash
# 檢查容器日誌
docker logs container_name

# 檢查容器配置
docker inspect container_name

# 進入容器除錯
docker exec -it container_name /bin/sh
```

#### 2. 網路連接問題
```bash
# 檢查網路設定
docker network ls
docker network inspect network_name

# 測試連接
docker run --rm --network container:container_name nicolaka/netshoot ping target_host
```

#### 3. 效能問題
```bash
# 檢查資源使用
docker stats

# 檢查系統負載
htop
iostat -x 1
```

#### 4. 存儲問題
```bash
# 檢查磁碟空間
df -h
docker system df

# 清理未使用的資源
docker system prune -a
```

---

**🎯 透過這份部署指南，您可以安全、穩定地部署 CTF 題目到生產環境！**

---

*最後更新：2025-08-03*