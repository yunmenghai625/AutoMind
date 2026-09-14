# 前端 API 契约对照

## Phase 2 对照结论

工作区现有前端定义了 `SendChatRequest`、`SendChatResponse`、`ChatMessage`、`ToolCall`、
`VehicleState` 和 Agent Run 类型。Phase 2 后端按这些类型提供真实接口，但为避免覆盖正在并行写入的前端，
本阶段未修改 `apps/web`。

| 前端能力 | 后端接口 | 状态 |
| --- | --- | --- |
| 非流式座舱对话 | `POST /api/v1/chat` | 已实现，返回 `messages[]` 与可选 `vehicle` |
| 流式座舱对话 | `GET /api/v1/chat/stream` | 已实现 SSE：`started/message/vehicle/done` |
| Agent Run 列表 | `GET /api/v1/admin/agent-runs` | 已实现，返回真实 PostgreSQL 数据 |
| Agent Run 详情 | `GET /api/v1/admin/agent-runs/{id}` | 已实现，返回节点与工具 trace |
| VehicleState | Chat 响应 `vehicle` | 已按前端 camelCase 字段输出 |

## 联调注意事项

- `apps/web/lib/api/adminApi.ts` 在 live 模式调用真实 Admin API，并统一携带登录身份；Mock 模式仍可独立演示。
- Chat 的工具状态为 `SUCCESS`、`FAILED` 或 `BLOCKED`；Agent Run 状态为小写 `success`、`failed`、`blocked`、`rejected` 或 `running`。
- SSE 查询参数为 `message` 与可选 `session_id`；事件数据均为 JSON。
- 统一错误仍为 `{"error":{"code":"...","message":"...","details":...},"request_id":"..."}`。
- 每条 Chat 消息的 `meta.runId` 可直接用于读取 Agent Run 详情。
- Admin API 强制 `role=admin`；未登录返回 401，普通注册用户返回 403。
