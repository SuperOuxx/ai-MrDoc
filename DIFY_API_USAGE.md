# Dify API 使用文档

本文档说明如何使用新增的 Dify 会话管理 API。

## API 端点

### 1. 会话管理

#### 1.1 获取会话列表
```http
GET /ai/dify/conversations/
```

**响应示例：**
```json
{
  "status": true,
  "data": [
    {
      "id": 1,
      "conversation_id": "conv-xxx",
      "app_name": "文档助手",
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

#### 1.2 创建或获取会话
```http
POST /ai/dify/conversations/create/
Content-Type: application/json

{
  "conversation_id": "conv-xxx",  // 可选，如果为空则创建新会话
  "app_name": "我的应用",          // 可选，默认"默认应用"
  "app_api_key": "app-xxx",       // 可选，不提供则使用系统配置
  "dify_api_address": "https://api.dify.ai/v1"  // 可选，不提供则使用系统配置
}
```

**响应示例：**
```json
{
  "status": true,
  "data": {
    "id": 1,
    "conversation_id": null,  // 首次创建时为空，发送第一条消息后会自动设置
    "app_name": "我的应用",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
  }
}
```

#### 1.3 重命名会话
```http
POST /ai/dify/conversations/rename/
Content-Type: application/json

{
  "conversation_id": "conv-xxx",
  "name": "新会话名称"
}
```

**响应示例：**
```json
{
  "status": true,
  "data": {
    // Dify API 返回的数据
  }
}
```

### 2. 消息管理

#### 2.1 获取消息列表
```http
GET /ai/dify/messages/?conversation_id=conv-xxx
```

**响应示例：**
```json
{
  "status": true,
  "data": {
    "data": [
      {
        "id": "msg-xxx",
        "query": "用户提问",
        "answer": "助手回答",
        "created_at": 1234567890
      }
    ]
  }
}
```

#### 2.2 发送消息（阻塞模式）
```http
POST /ai/dify/messages/send/
Content-Type: application/json

{
  "conversation_id": 1,  // 数据库中的会话 ID（不是 Dify 的 conversation_id）
  "query": "你好，请帮我写一段代码",
  "inputs": {},  // 可选，应用的输入参数
  "response_mode": "blocking"  // 阻塞模式
}
```

**响应示例：**
```json
{
  "status": true,
  "data": {
    "conversation_id": "conv-xxx",
    "id": "msg-xxx",
    "answer": "这是助手的回复",
    "created_at": 1234567890
  }
}
```

#### 2.3 发送消息（流式模式）
```http
POST /ai/dify/messages/send/
Content-Type: application/json

{
  "conversation_id": 1,
  "query": "你好，请帮我写一段代码",
  "inputs": {},
  "response_mode": "streaming"  // 流式模式
}
```

**响应格式（Server-Sent Events）：**
```
data: {"event": "message", "conversation_id": "conv-xxx", "answer": "这"}
data: {"event": "message", "answer": "是"}
data: {"event": "message", "answer": "回复"}
data: {"event": "message_end"}
```

### 3. 应用信息

#### 3.1 获取应用信息
```http
GET /ai/dify/app/info/
# 或
GET /ai/dify/app/info/?conversation_id=1
```

**响应示例：**
```json
{
  "status": true,
  "data": {
    "opening_statement": "欢迎使用...",
    "suggested_questions": ["问题1", "问题2"],
    "user_input_form": []
  }
}
```

## 使用流程示例

### 完整的对话流程

```javascript
// 1. 创建新会话
const createResponse = await fetch('/ai/dify/conversations/create/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    app_name: '文档助手'
  })
});
const { data: conversation } = await createResponse.json();
console.log('会话 ID:', conversation.id);

// 2. 获取应用信息（可选）
const appInfoResponse = await fetch(`/ai/dify/app/info/?conversation_id=${conversation.id}`);
const { data: appInfo } = await appInfoResponse.json();
console.log('应用信息:', appInfo);

// 3. 发送消息（流式）
const eventSource = new EventSource('/ai/dify/messages/send/');
const response = await fetch('/ai/dify/messages/send/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    conversation_id: conversation.id,
    query: '请帮我总结这篇文档',
    response_mode: 'streaming'
  })
});

// 处理流式响应
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      if (data.answer) {
        console.log(data.answer); // 逐字输出
      }
    }
  }
}

// 4. 获取历史消息
const messagesResponse = await fetch(`/ai/dify/messages/?conversation_id=${conversation.conversation_id}`);
const { data: messages } = await messagesResponse.json();
console.log('历史消息:', messages);

// 5. 重命名会话（可选）
await fetch('/ai/dify/conversations/rename/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    conversation_id: conversation.conversation_id,
    name: '文档总结会话'
  })
});
```

## 特性说明

### 1. 会话层面的应用选择
- 每个会话可以绑定不同的 Dify 应用（通过 app_api_key 和 dify_api_address）
- 如果不指定应用配置，则使用系统默认配置
- 这样可以在同一个系统中使用多个不同的 Dify 应用

### 2. 自动管理 conversation_id
- 创建会话时 conversation_id 可以为空
- 第一次发送消息时，系统会自动从 Dify 获取 conversation_id 并保存
- 后续消息会自动使用该 conversation_id 保持会话连续性

### 3. 消息持久化
- 所有消息（用户和助手）都会自动保存到本地数据库
- 流式模式下会累积完整的回复内容后保存
- 支持从 Dify API 同步历史消息到本地数据库

### 4. 安全性
- API 密钥使用加密存储
- 所有接口都需要登录认证
- 支持速率限制（通过 dynamic_rate_limit 装饰器）

## 注意事项

1. 确保已安装 `dify-client`：
   ```bash
   pip install dify-client
   ```

2. 系统配置中需要设置以下参数：
   - `ai_dify_api_address`: Dify API 地址
   - `ai_dify_chat_api_key`: Dify 聊天应用 API 密钥

3. conversation_id 参数说明：
   - 在创建/获取会话和重命名接口中，`conversation_id` 是 Dify 的会话 ID（格式：conv-xxx）
   - 在发送消息接口中，`conversation_id` 是数据库中的会话 ID（数字）

4. 流式响应注意事项：
   - 使用 Server-Sent Events 格式
   - 需要在前端使用 EventSource 或 fetch + stream 处理
   - 每个 data 行都是独立的 JSON 对象
