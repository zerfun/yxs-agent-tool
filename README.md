# 研享数Agent工具 (YXS Agent Tool)

一个跨端 Agent 工具，通过移动端（微信、飞书、QQ 等）远程控制电脑端的 AI Agent，支持 GitHub Codex、Claude、Qwen 等多种模型接入形态。

## 🎯 核心功能

- 📱 **多平台支持** - 微信、飞书、QQ等通讯应用
- 🤖 **多AI集成** - Codex、Claude、Qwen等模型
- 💻 **跨端控制** - 移动端远程控制电脑端Agent
- 🔄 **消息队列** - 可靠的任务分发和结果回传
- 💾 **持久化** - 任务历史和上下文管理
- 🔐 **安全认证** - 完整的身份验证机制

## 📋 项目结构

```
yxs-agent-tool/
├── backend/                    # 云端 API 与任务调度服务
│   ├── src/
│   │   ├── api/               # HTTP / WebSocket 路由
│   │   ├── config/            # 配置管理
│   │   ├── daemon/            # 本地 Agent 守护进程与连接管理
│   │   ├── models/            # 数据模型
│   │   ├── services/          # 业务逻辑服务
│   │   └── utils/             # 日志等工具
│   ├── requirements.txt       # Python 依赖
│   ├── main.py                # 服务入口
│   └── tests/                 # 基础测试
│
├── client.py                  # 本地 Agent 启动脚本
├── docker-compose.yml         # 容器编排
├── .env.example              # 环境变量示例
└── docs/                     # 文档
    ├── ARCHITECTURE.md       # 架构设计
    ├── API.md               # API文档
    └── DEPLOYMENT.md        # 部署指南
```

## 🚀 快速开始

### 前置要求
- Python 3.8+
- Docker & Docker Compose
- GitHub Token（可选，用于接入 GitHub 侧能力）
- 微信公众号/企业号（如需微信回调）

### 安装

1. **克隆项目**
```bash
git clone https://github.com/zerfun/yxs-agent-tool.git
cd yxs-agent-tool
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥 / Agent 配置
```

3. **启动服务**
```bash
# 方式1: Docker Compose
docker-compose up -d

# 方式2: 本地Python
pip install -r backend/requirements.txt
cd backend
python main.py
```

## 🔧 配置指南

### GitHub Codex 配置
```bash
# .env
GITHUB_TOKEN=your_github_token_here
CODEX_MODEL=code-davinci-002
```

### 本地 Agent 配置
```bash
# .env
AGENT_API_KEYS=test-key,dev-key
LOCAL_LLM_URL=http://localhost:11434/api/generate
LOCAL_LLM_MODEL=llama2
```

### 任务存储配置
```bash
# .env
TASK_STORE_BACKEND=memory   # 可选: memory / redis
TASK_STORE_PREFIX=yxs_agent
TASK_STORE_MAX_ITEMS=1000
REDIS_URL=redis://localhost:6379/0
```

### 微信公众号配置
```bash
# .env
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret
WECHAT_TOKEN=your_token
```

## 🧪 当前可用能力

- FastAPI 服务可正常启动
- `POST /api/v1/agent/task` 支持创建任务
- `GET /api/v1/agent/tasks` 支持查看最近任务
- 有在线本地 Agent 时，任务优先远程派发
- 没有在线 Agent 时，Codex 请求会本地兜底到演示模式
- 支持 `memory` / `redis` 两种任务存储后端，Redis 不可用时自动回退到内存
- 微信支持“帮助 / 最近任务 / 状态 <任务ID>”命令
- 远程任务完成后，可通过公众号客服消息主动推送结果
- 基础测试已覆盖本地执行和远程排队两条主路径

## 🔌 启动本地 Agent

```bash
python client.py --server ws://localhost:8000/api/v1/agent/ws --key test-key --name my-agent
```

本地 Agent 连上后，`/api/v1/agent/task` 创建的任务会优先返回 `queued`，等待远程执行。

## 📚 使用示例

### 通过微信控制Agent
```
用户: @Agent 帮我写一个Python的快速排序函数
回复: [Agent执行中...]
回复: def quicksort(arr):
     if len(arr) <= 1:
         return arr
     ...
```

### 微信命令
```
帮助
最近任务
状态 <任务ID>
```

当任务被分发到在线本地 Agent 时，微信会先同步回复任务已接收，后续再通过公众号客服消息主动推送最终结果。

## 🏗️ 架构设计

详见 [ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 📖 API文档

详见 [API.md](docs/API.md)

## 🐳 部署指南

详见 [DEPLOYMENT.md](docs/DEPLOYMENT.md)

## 📝 开发计划

### Phase 1: MVP
- [x] 项目框架
- [x] 微信基础回调接入
- [x] 本地 / 远程任务分发骨架
- [x] 本地 Agent WebSocket 通道
- [x] 可切换的任务存储层
- [ ] 真实模型 API 适配
- [ ] 生产级持久化任务队列

### Phase 2: 增强功能
- [ ] 多AI模型支持
- [ ] 会话管理
- [ ] 持久化存储
- [ ] Web控制面板
- [ ] 飞书/QQ集成

### Phase 3: 生产就绪
- [ ] 集群部署
- [ ] 监控系统
- [ ] 日志系统
- [ ] 安全加固
- [ ] 性能优化

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 👨‍💻 作者

@zerfun

## 💬 联系方式

有问题或建议？欢迎通过微信机器人与我联系！
