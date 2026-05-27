# 研享数Agent工具 (YXS Agent Tool)

一个跨端Agent工具，通过移动端（微信、飞书、QQ等）远程控制电脑端的AI Agent，支持GitHub Codex、Claude Code、Qwen Code等多个AI模型。

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
├── backend/                    # 电脑端代理服务
│   ├── src/
│   │   ├── agent/             # Agent核心逻辑
│   │   ├── models/            # 数据模型
│   │   ├── services/          # 业务逻辑服务
│   │   ├── api/               # API接口
│   │   └── config/            # 配置管理
│   ├── requirements.txt        # Python依赖
│   └── main.py               # 主入口
│
├── frontend/                  # 移动端集成
│   ├── wechat/               # 微信机器人
│   ├── feishu/               # 飞书机器人
│   └── qq/                   # QQ机器人
│
├── shared/                    # 共享模块
│   ├── schemas/              # 数据架构
│   ├── utils/                # 工具函数
│   └── constants/            # 常量定义
│
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
- GitHub Personal Access Token (for Codex)
- 微信公众号/企业号

### 安装

1. **克隆项目**
```bash
git clone https://github.com/zerfun/yxs-agent-tool.git
cd yxs-agent-tool
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的API密钥
```

3. **启动服务**
```bash
# 方式1: Docker Compose
docker-compose up -d

# 方式2: 本地Python
pip install -r backend/requirements.txt
python backend/main.py
```

## 🔧 配置指南

### GitHub Codex配置
```bash
# .env
GITHUB_TOKEN=your_github_token_here
CODEX_MODEL=code-davinci-002
```

### 微信公众号配置
```bash
# .env
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret
WECHAT_TOKEN=your_token
```

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

## 🏗️ 架构设计

详见 [ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 📖 API文档

详见 [API.md](docs/API.md)

## 🐳 部署指南

详见 [DEPLOYMENT.md](docs/DEPLOYMENT.md)

## 📝 开发计划

### Phase 1: MVP
- [x] 项目框架
- [ ] 微信基础集成
- [ ] Codex API适配
- [ ] 基础命令执行
- [ ] 任务队列

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
