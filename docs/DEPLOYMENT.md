# 部署指南

## 前置要求

- Python 3.8+
- Docker & Docker Compose
- MongoDB 5.0+
- Redis 7.0+

## 本地开发部署

### 1. 环境配置

```bash
# 克隆项目
git clone https://github.com/zerfun/yxs-agent-tool.git
cd yxs-agent-tool

# 复制环境变量配置
cp .env.example .env

# 编辑.env文件，配置你的API密钥
vim .env
```

### 2. Docker Compose启动（推荐）

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f backend

# 停止服务
docker-compose down
```

### 3. 本地Python环境启动

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r backend/requirements.txt

# 启动MongoDB
mongod --dbpath ./data/db

# 启动Redis（另一个终端）
redis-server

# 启动应用（第三个终端）
cd backend
python main.py
```

## 测试服务

### 健康检查

```bash
curl http://localhost:8000/health
```

### 创建测试任务

```bash
curl -X POST http://localhost:8000/api/v1/agent/task \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "写一个快速排序函数",
    "model": "codex"
  }'
```

### 启动本地 Agent

在另一个终端中启动本地 Agent，用于验证远程派发链路：

```bash
python client.py --server ws://localhost:8000/api/v1/agent/ws --key test-key --name local-dev-agent
```

本地 Agent 在线时，创建任务接口会优先返回 `queued`，后续由守护进程通过 WebSocket 回传状态与结果。

## 生产部署

### 1. 云服务器配置

使用AWS EC2或阿里云ECS等云服务器

#### 推荐配置
- CPU: 4核+
- 内存: 8GB+
- 存储: 50GB+
- 系统: Ubuntu 20.04 LTS

### 2. 安装依赖

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y curl wget git

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 3. 使用Docker Swarm或Kubernetes

#### Docker Swarm

```bash
# 初始化Swarm
sudo docker swarm init

# 部署服务
sudo docker stack deploy -c docker-compose.yml yxs-agent

# 查看服务
sudo docker stack services yxs-agent
```

#### Kubernetes

```bash
# 安装kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# 创建deployment
kubectl apply -f k8s/deployment.yaml

# 查看Pod
kubectl get pods
```

### 4. 反向代理配置（Nginx）

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # 重定向到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL证书配置
    ssl_certificate /etc/ssl/certs/yourdomain.com.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 反向代理
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 日志
    access_log /var/log/nginx/yxs-agent-access.log;
    error_log /var/log/nginx/yxs-agent-error.log;
}
```

### 5. SSL证书配置

使用Let's Encrypt免费证书：

```bash
# 安装Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot certonly --nginx -d yourdomain.com

# 自动续期（Certbot会自动设置）
sudo systemctl enable certbot.timer
```

### 6. 监控和日志

#### Prometheus监控

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'yxs-agent'
    static_configs:
      - targets: ['localhost:8000']
```

#### ELK日志收集

```bash
# 启动ELK Stack
docker run -d --name elasticsearch docker.elastic.co/elasticsearch/elasticsearch:8.0.0
docker run -d --name kibana docker.elastic.co/kibana/kibana:8.0.0
```

### 7. 自动备份

```bash
# MongoDB备份
mongodump --uri "mongodb://admin:password@localhost:27017" --out /backup/mongo

# 定时备份脚本
crontab -e
0 2 * * * /usr/local/bin/backup.sh
```

## 常见问题

### Q: 如何修改API密钥？
A: 编辑`.env`文件，重启应用即可

### Q: 如何查看应用日志？
A: 使用 `docker-compose logs backend` 或直接查看日志文件

### Q: 如何扩展服务？
A: 修改docker-compose.yml中的副本数

### Q: 如何连接远程数据库？
A: 在.env中修改DB_URL和REDIS_URL指向远程地址
