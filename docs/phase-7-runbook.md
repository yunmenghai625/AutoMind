# AutoMind Phase 7 运维 Runbook

## 值班入口

先记录事件时间、环境、发布版本、`request_id`、`trace_id` 和影响范围。检查顺序：公开
`/health` -> Railway/Vercel 部署状态 -> Admin components/budget/requests -> OTLP 仪表盘 ->
依赖平台。禁止把 Authorization、VIN、图片或 Prompt 复制到工单。

## 告警建议

- 5 分钟窗口 HTTP 5xx >= 2% 或 P95 超过 1 秒。
- `/health` 连续 3 次失败，或数据库状态不是 `ok`。
- Agent/Tool 成功率低于 95%。
- Budget 进入 `economy` 或 `exhausted`。
- Provider 熔断打开、Redis 持续降级、RAG 无答案率突增。
- 备份或校验任务失败。

压测请求已由 `traffic_class=load_test` 隔离，不参与用户 SLO、Agent/Tool 用户成功率和成本预算；
排障时仍可按测试请求数和 run ID 单独查询。

## LLM / VLM / embedding 故障

症状：Provider 超时、5xx、熔断打开、延迟或成本突增。

1. 用 `request_id` 定位请求与对应 run，确认是单 Provider 还是全链路问题。
2. 检查 Budget 状态；若为 economy/exhausted，确认这是策略降级而非服务故障。
3. 检查 Provider 状态页、凭据有效期、配额和模型名，不要在日志打印密钥。
4. 保持 Safety Gate 与限流启用；必要时切换到已配置的本地/Mock 降级能力并向用户明确标识。
5. 恢复后使用非破坏性请求验证，再观察 15 分钟错误率和 P95。

## PostgreSQL 故障

症状：`/health` degraded、核心接口返回存储不可用、连接耗尽或 migration 失败。

1. 暂停新部署与高写入操作，检查 Railway PostgreSQL 状态、连接上限和磁盘。
2. 核对 `DATABASE_URL` Secret 与网络，不修改业务数据绕过 migration。
3. migration 失败时保留完整日志；确认 schema 当前版本后决定前向修复或回滚应用。
4. 需要恢复时，在新数据库执行恢复并验证：

```sh
sha256sum -c automind.dump.sha256
createdb automind_restore
pg_restore --exit-on-error --no-owner --no-privileges --dbname "$RESTORE_DATABASE_URL" automind.dump
alembic current
```

5. 对恢复库执行只读核对、`/health` 和核心回归后再切换流量。原库保持只读以便审计。

## Redis 故障

普通 HTTP 限流会降级为进程内计数，但多实例间无法共享；AI 运行时开关与跨实例并发闸门在
staging/production 会失败关闭，拒绝新的 AI 请求，避免 Redis 故障时失控放量。

1. 检查 Redis service、私网连接、认证和延迟。
2. 不得因 Redis 故障关闭 Rate Limit；必要时临时降低入口流量。
3. Redis 恢复后确认组件状态与限流响应头正常。

## 外部车辆数据 Provider 故障

VIN/recall Provider 受 timeout、circuit breaker 和 cache fallback 保护。

1. 确认 fresh/stale/unavailable 状态与熔断事件。
2. 若 stale 数据仍在有效策略范围内，保持显式 stale 标记；不要伪装成实时数据。
3. Provider 恢复后等待熔断半开探测，避免手工清空所有缓存造成流量尖峰。

## Budget 触发

- `economy`：确认高成本生成已切换到低成本/本地策略，并在 Admin 中观察调用和成本。
- `exhausted`：保留确定性、低成本与安全能力，拒绝超预算生成；不要提高预算来掩盖异常调用。
- 若成本异常，按 request/run/provider/model 聚合，吊销泄漏凭据并冻结高成本入口。
- 预算调整需记录负责人、原因、时限与回滚值。

## Safety 或隐私事件

1. 保持 SafetyPolicyEngine 在线并保全审计链；禁止关闭规则复现问题。
2. 隔离受影响的入口/令牌，必要时回滚应用。
3. 若日志或对象存储疑似含敏感信息，立即限制访问并轮换相关凭据。
4. 记录安全拒绝、工具参数摘要和版本，不保存原始敏感内容。
5. 修复后运行全部安全回归再恢复流量。

## 发布后核对

- API 与前端 HTTPS 正常，CORS 只允许预期域名。
- Guest 与 Registered 核心闭环可用，Admin 权限边界正确。
- DB migration 位于 head，OTLP 有真实 trace/metric，Admin 无生产 Mock 数据。
- Rate Limit、Safety、Quota、Budget 和全局 timeout 均启用。
- 备份最新任务成功且校验和可验证。
