# API文档

## 基础信息

**Base URL**: `http://localhost:8000/api/v1`

**Content-Type**: `application/json`

## 通用响应格式

所有API返回统一的JSON响应格式：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

- `code`: 0表示成功，其他值表示错误
- `message`: 响应信息
- `data`: 响应数据

## 健康检查

### 检查服务状态

```http
GET /health
```

**响应:**
```json
{
  "code": 0,
  "message": "Health check passed",
  "data": {
    "status": "healthy",
    "task_store": "memory",
    "online_agents": 0
  }
}
```

## Agent API

### 创建任务

创建一个新的AI任务

```http
POST /agent/task
Content-Type: application/json

{
  "prompt": "写一个Python的快速排序函数",
  "model": "codex",
  "temperature": 0.5,
  "max_tokens": 2048
}
```

**请求参数:**

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| prompt | string | 任务提示 | 必填 |
| model | string | AI模型 (codex/claude/qwen) | codex |
| temperature | float | 温度参数 (0-1) | 0.5 |
| max_tokens | integer | 最大生成令牌数 | 2048 |
| context | object | 上下文信息 | 可选 |

**响应:**
```json
{
  "code": 0,
  "message": "Task created successfully",
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "result": "def quicksort(arr):\n    ...",
    "created_at": "2024-01-01T00:00:00",
    "completed_at": "2024-01-01T00:00:10"
  }
}
```

当存在在线本地 Agent 且支持对应模型时，接口会优先将任务派发到远程执行节点，此时响应状态可能为：

```json
{
  "code": 0,
  "message": "Task created successfully",
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "queued",
    "result": null,
    "created_at": "2024-01-01T00:00:00",
    "completed_at": null
  }
}
```

**状态值:**
- `idle`: 待处理
- `queued`: 已入队，等待本地 Agent 执行
- `running`: 处理中
- `completed`: 已完成
- `failed`: 处理失败

### 查询任务

查询任务执行状态和结果

```http
GET /agent/task/{task_id}
```

**路径参数:**
- `task_id`: 任务ID

**响应:**
```json
{
  "code": 0,
  "message": "Task retrieved successfully",
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "result": "...",
    "error": null,
    "created_at": "2024-01-01T00:00:00",
    "completed_at": "2024-01-01T00:00:10"
  }
}
```

### 列出最近任务

按创建时间倒序返回最近任务。

```http
GET /agent/tasks?limit=20&user_id=default_user&status=completed
```

**查询参数:**

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| limit | integer | 返回数量，1-100 | 20 |
| user_id | string | 按用户过滤 | 可选 |
| status | string | 按状态过滤 | 可选 |

**响应:**
```json
{
  "code": 0,
  "message": "Tasks retrieved successfully",
  "data": {
    "total": 2,
    "tasks": [
      {
        "task_id": "task-2",
        "status": "completed",
        "user_id": "default_user",
        "model": "qwen",
        "source": "api",
        "result": "...",
        "error": null,
        "created_at": "2024-01-01T00:00:20",
        "completed_at": "2024-01-01T00:00:21",
        "metadata": {}
      }
    ]
  }
}
```

## Agent WebSocket API

### 本地 Agent 连接

本地守护进程通过 WebSocket 接入云端服务：

```http
GET /agent/ws?agent_id=my-agent&api_key=test-key
```

### 查看在线 Agent

```http
GET /agent/agents
```

### 查询远程结果缓存

```http
GET /agent/task/{task_id}/result
```

## 微信API

### 服务验证

微信服务器验证（GET请求）

```http
GET /wechat/callback?signature=xxx&timestamp=xxx&nonce=xxx&echostr=xxx
```

### 接收消息

接收并处理微信消息（POST请求）

```http
POST /wechat/callback
Content-Type: application/xml

<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[FromUser]]></FromUserName>
  <CreateTime>123456789</CreateTime>
  <MsgType><![CDATA[text]]></MsgType>
  <Content><![CDATA[this is a test]]></Content>
  <MsgId>1234567890123456</MsgId>
</xml>
```

## 错误处理

### 常见错误码

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 禁止访问 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

### 错误响应示例

```json
{
  "code": 400,
  "message": "Bad Request",
  "detail": "Invalid model parameter"
}
```

## 示例代码

### Python

```python
import requests

url = "http://localhost:8000/api/v1/agent/task"
payload = {
    "prompt": "写一个Python的快速排序函数",
    "model": "codex",
    "temperature": 0.5,
    "max_tokens": 2048
}

response = requests.post(url, json=payload)
data = response.json()
print(data)
```

### JavaScript

```javascript
const response = await fetch('http://localhost:8000/api/v1/agent/task', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    prompt: '写一个Python的快速排序函数',
    model: 'codex',
    temperature: 0.5,
    max_tokens: 2048
  })
});

const data = await response.json();
console.log(data);
```

### cURL

```bash
curl -X POST http://localhost:8000/api/v1/agent/task \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "写一个Python的快速排序函数",
    "model": "codex",
    "temperature": 0.5,
    "max_tokens": 2048
  }'
```
