# HA-AI-API

这是一个高可用的 AI API 转发服务，支持多上游服务配置，可以根据上游服务的响应状态和超时自动切换上游模型。目前支持统一对外提供 `deepseek-chat` 模型服务。

> 鉴于近期DeepSeek因网络攻击频繁宕机导致我部署的dify、n8n无法正常使用，但我也不想因为这种问题就彻底放弃deepseek，所以就写了这个项目。

## 功能特点

- 支持多上游服务配置
- 基于优先级的服务自动切换
- 统一的对外模型名称
- API Key 认证
- Docker 支持

## 快速开始

### 配置

1. 复制配置文件模板：

```bash
cp config.yaml.example config.yaml
```

2. 编辑 `config.yaml` 文件，配置你的服务：

```yaml
settings:
  api_key: "your-api-key-here"  # 设置你的 API Key

upstream_services:
  - name: upstream1
    priority: 1
    base_url: "https://api.openai.com/v1"
    api_key: "your-api-key-1"
    model_mapping:
      "deepseek-chat": "gpt-3.5-turbo"
    timeout: 30

  - name: upstream2
    priority: 2
    base_url: "https://api.another-provider.com/v1"
    api_key: "your-api-key-2"
    model_mapping:
      "deepseek-chat": "claude-v1"
    timeout: 30
```

### 使用 Docker 运行

1. 使用 docker-compose 启动服务：

```bash
docker-compose up -d
```

2. 服务将在 `http://localhost:8000` 启动

### 本地运行

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 启动服务：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API 使用

### 认证

所有请求需要在 Header 中携带 API Key：

```
Authorization: Bearer your-api-key-here
```

### Chat Completion 接口

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key-here" \
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {
        "role": "user",
        "content": "Hello!"
      }
    ]
  }'
```

## 配置说明

### 全局设置

- `api_key`: 用于验证客户端请求的 Key

### 上游服务配置

- `name`: 服务名称
- `priority`: 优先级（数字越小优先级越高）
- `base_url`: 上游服务的基础 URL
- `api_key`: 上游服务的 API Key
- `model_mapping`: 模型名称映射
- `timeout`: 请求超时时间（秒）

## 开发

项目使用 Python FastAPI 框架开发，主要文件结构：

```
.
├── app
│   ├── __init__.py
│   ├── config.py        # 配置加载
│   ├── main.py         # 应用入口
│   ├── models.py       # 数据模型
│   ├── router.py       # 路由处理
│   └── services        # 服务实现
├── config.yaml         # 配置文件
├── Dockerfile
├── docker-compose.yaml
├── README.md
└── requirements.txt
```

## License

MIT
