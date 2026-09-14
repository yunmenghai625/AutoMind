# AutoMind Phase 6 Production Observability / Security / Budget 架构

## 目标与边界

Phase 6 把现有产品后端提升为可运营、可诊断、可控成本的服务。系统保留轻量部署：应用直接通过
OTLP/HTTP 把遥测发送到 Grafana Cloud 或任意兼容 Collector，不在项目内自建 Prometheus、Tempo、
Loki 或 Grafana 管理栈。Admin 接口只对 JWT `role=admin` 开放。

## 请求关联与可观测性

```text
HTTP request
  -> RequestContextMiddleware
     -> validate/create request_id
     -> create OTel server span and trace_id
     -> Redis rate limit
     -> global timeout
     -> route / Agent workflow
        -> AgentRun creates run_id and stores trace_id
        -> LLM / Agent / Tool / RAG record duration, status, tokens, cost
     -> structured redacted log
     -> http_request_metrics persistence
  -> X-Request-ID + X-Trace-ID response headers

Administrator
  -> GET /admin/requests/{request_id}
  -> request_id -> trace_id -> Agent run / Tool / RAG records -> OTLP trace
```

指标名称为 `automind.operation.count`、`automind.operation.duration`、
`automind.llm.tokens` 和 `automind.ai.cost`，维度限制为 operation kind/status/name 与 token type，
避免把用户输入、VIN 或凭据写成高基数标签。PostgreSQL 同时保留轻量运营聚合所需的数据，确保
OTLP 暂时不可用时 Admin 仍能诊断。

## 可靠性与成本控制

- Redis 限流按认证头、Guest ID 或来源地址的 SHA-256 摘要计数，绝不保存原值；Redis 故障时使用
  进程内 fallback，生产配置则强制要求 `REDIS_URL`。
- 全局 `REQUEST_TIMEOUT_SECONDS` 用统一 `504 REQUEST_TIMEOUT` 终止超时请求。
- NHTSA Provider 使用三次失败打开、30 秒恢复探测的 circuit breaker；上层继续复用 Phase 5 的
  fresh/stale cache 与 unavailable 语义。
- `BudgetGuard` 汇总当日 Agent、AIGC 和 Diagnosis 成本。达到配置比例进入 `economy`，达到日上限
  进入 `exhausted`；两种状态都会阻止 AIGC/VLM 外部调用并切换本地或 Mock Provider。
- AIGC 仍保留独立月度图片预算，Diagnosis 仍保留独立月度 VLM 预算，形成全局日预算与业务预算
  两级保护。

## Admin 真实数据 API

- `GET /api/v1/admin/overview`：用户数、24 小时请求数、Agent/Tool 成功率、P95 与当日 AI 成本。
- `GET /api/v1/admin/metrics?days=14`：流量、成功率、P50/P95/P99、Agent 用量和每日成本。
- `GET /api/v1/admin/operational-metrics`：Agent Token/成本/延迟、Tool 与 RAG 聚合。
- `GET /api/v1/admin/budget`：实时预算状态与 Economy 阈值。
- `GET /api/v1/admin/components`：API、PostgreSQL、Redis 与 OTLP 配置状态。
- `GET /api/v1/admin/safety-events`：真实 SafetyPolicyEngine 拒绝记录。
- `GET /api/v1/admin/requests/{request_id}`：失败请求定位入口。
- `GET /api/v1/admin/agent-runs` 及详情：包含 requestId、traceId、runId、步骤和工具审计。

## 数据变更

Alembic `20260913_0009` 为 `agent_runs`、`rag_queries` 增加 `trace_id`，并新增
`http_request_metrics`。请求 ID 唯一写入，重试写入不会产生重复运营记录。
