# AutoMind Phase 7 上线架构

## 目标

Phase 7 将 Phase 0–6 的功能、安全与可观测能力装配成可发布的 1.0.0 系统。PostgreSQL
仍是业务事实源，Redis 仅用于限流与短期协调；SafetyPolicyEngine、配额、预算保护和限流在
staging、production 与压测期间均保持启用。

## 运行拓扑

```text
Browser
  -> HTTPS Frontend (Vercel)
       -> HTTPS API (Railway, non-root container)
            -> Request context / CORS / timeout / rate limit
            -> FastAPI routes
            -> Agent / RAG / AIGC / diagnosis / vehicle domains
            -> SafetyPolicyEngine -> typed vehicle tools
            -> PostgreSQL + pgvector (business truth, audit, metrics)
            -> Redis (rate limit and graceful fallback)
            -> optional LLM/VLM/embedding/R2 providers
            -> OTLP gateway (traces, metrics and sanitized logs)
```

## 发布链路

```text
push main                         push v* tag
    |                                  |
    +---------- GitHub Actions --------+
                 |
           quality gate
      Ruff / Alembic / Pytest
      typecheck / Next build
                 |
       +---------+---------+
       |                   |
 Railway staging      Railway production
 Vercel staging       Vercel production
       |                   |
       +---- health smoke--+
                           |
                     GitHub Release
```

`main` 发布到 staging，符合 `v*` 的已存在标签发布到 production。两个 Vercel 项目分别提供
稳定的 staging/production 地址，原生 Git 自动发布关闭，统一由 GitHub Actions 发布。发布作业
使用 GitHub Environment 分离 Secrets 与变量，并在前、后端均成功后检查 API `/health` 和前端首页。

## 数据与迁移

- Railway 在启动新版本前执行 `alembic upgrade head`。
- 当前数据库头版本为 `20260913_0010`。
- `agent_runs`、`rag_queries`、`http_request_metrics` 记录 `traffic_class`。
- 只有同时携带 `X-AutoMind-Traffic-Class: load_test` 与正确 `X-Load-Test-Token` 的请求会被
  标记为压测；伪造或缺少令牌的请求仍按用户流量处理。
- Admin 用户指标、Agent/Tool 成功率与预算成本排除 `load_test`，另行显示测试请求数。
- 数据库备份使用 PostgreSQL custom format、SHA-256 校验和与 `pg_restore --list` 完整性检查。

## 安全边界

- production 只允许明确列出的 HTTPS CORS origin，关闭接口文档。
- 容器以 `automind` 非 root 用户运行。
- JWT、VIN HMAC、审计链、压测、Provider 和 OTLP 凭据只由部署平台 Secret 注入。
- Rate Limit、Usage Quota、Budget Guard、全局超时与 Safety Gate 不因发布或压测关闭。
- 日志与遥测不记录 Authorization、Prompt、图片内容或 VIN 明文。

## 稳定接口

- 健康检查：`GET /health`、`GET /api/v1/health`
- 核心闭环：`/api/v1/auth`、`/vehicle`、`/chat`、`/knowledge`、`/aigc`、`/diagnosis`、
  `/garage`、`/preferences`、`/feedback`
- 运维审计：`/api/v1/admin/*`
- 请求关联：响应 `X-Request-ID`，服务端关联 `request_id`、`trace_id`、可选 `run_id`

详细部署步骤见 `phase-7-deployment.md`，故障处置见 `phase-7-runbook.md`。
