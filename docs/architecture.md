# AutoMind 架构索引

当前发布架构以 `phase-7-architecture.md` 为准。本文件保留为稳定入口，历史阶段文档用于说明
演进过程，不覆盖后续阶段的实现与安全边界。

## 当前组件

```text
apps/web (Next.js)
  -> apps/api (FastAPI)
       -> Agent / RAG / AIGC / Diagnosis / Identity
       -> SafetyPolicyEngine -> typed Vehicle Tools
       -> PostgreSQL + pgvector
       -> Redis
       -> optional external providers and object storage
       -> OpenTelemetry exporter
```

- 上线拓扑、CI/CD、数据与安全边界：`phase-7-architecture.md`
- 平台配置、迁移、回滚与备份：`phase-7-deployment.md`
- 告警和故障处置：`phase-7-runbook.md`
- 真实本地压测记录：`phase-7-load-test-report.md`

## 不变原则

- PostgreSQL 是业务事实源；Migration 是 schema 变更的唯一入口。
- SafetyPolicyEngine 独立于模型，模型不能批准安全操作。
- API 层不直接编写 SQL，领域层不依赖 FastAPI。
- Mock、压测和用户流量必须显式区分；production 不展示伪指标。
- 每个请求关联 request_id/trace_id，可选关联 Agent run_id。
