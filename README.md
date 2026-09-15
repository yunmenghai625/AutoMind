# AutoMind 1.0.1

AutoMind 是面向公网运行的汽车 AI Agent 产品：Next.js 驾驶舱连接 FastAPI、PostgreSQL/
pgvector 与 Redis，提供车辆数字孪生、自然语言座舱控制、带引用的汽车知识 RAG、AI 主题、
仪表图片诊断、用户偏好与车辆档案，以及真实运营审计。

当前状态：**个人独立开发的非商业作品集演示，已完成 production 发布与云端验收。**

## Live Demo

- Frontend: <https://auto-mind-eight.vercel.app/>
- API health: <https://automind-api-production.up.railway.app/health>

请勿在演示环境上传人脸、车牌、证件、真实 VIN 或其他个人信息。

## 项目归属与使用边界

Copyright © 2026 yunmenghai625。AutoMind 是个人独立开发的非商业作品集演示项目，用于技术
展示与面试交流，与任何同名企业、汽车制造商或第三方品牌不存在隶属、授权或合作关系。

项目中的原创源代码、文档及界面编排保留全部权利；开源组件、第三方服务、模型及数据分别受
其各自许可证和服务条款约束。部分功能由 AI 模型辅助，生成及车辆诊断结果仅供演示参考，不能
替代专业维修检查。详细边界见 [NOTICE](NOTICE)、[数据来源说明](DATA_SOURCES.md) 和
[第三方许可说明](THIRD_PARTY_NOTICES.md)。

## 核心能力

- 车辆状态持久化、属性/区域/值域校验、乐观锁和请求级审计。
- LangGraph 座舱 Agent、SSE、typed tools；任何车控都必须经过独立 SafetyPolicyEngine。
- pgvector + 全文混合检索、重排、低置信度改写、文档/章节/页码/原文引用与无证据拒答。
- ThemeSpec 主题生成和显式应用；仪表图片净化、结构化识别、置信度闸门、风险分级和引用。
- Guest/Bearer JWT 身份、偏好、车辆档案、VIN HMAC 摘要、召回查询与用户反馈。
- request/trace/run 关联、HTTP/LLM/Agent/Tool/RAG 指标、Redis 限流、配额、预算降级、
  全局 timeout、Provider 熔断和日志脱敏。
- Admin 只读取真实数据库/Redis/配置数据，不在 production 注入 Mock 指标。
- 合法压测流量使用 Secret 校验并与用户指标、成功率和成本预算隔离。

## Architecture

```text
Browser -> Vercel / Next.js -> Railway / FastAPI
                                  |-> PostgreSQL + pgvector
                                  |-> Redis
                                  |-> Safety Gate -> Vehicle Tools
                                  |-> LLM/VLM/Embedding/R2 providers
                                  `-> OTLP observability
```

- [Phase 7 上线架构](docs/phase-7-architecture.md)
- [部署手册](docs/phase-7-deployment.md)
- [运维 Runbook](docs/phase-7-runbook.md)
- [压测报告](docs/phase-7-load-test-report.md)
- [发布就绪报告](docs/phase-7-report.md)
- [上线检查单](docs/phase-7-launch-checklist.md)

## 本地启动

要求：Python 3.11+、Node.js 22、Docker。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
docker compose up -d postgres redis
alembic upgrade head
python -m apps.api.rag.ingest_cli data/knowledge
uvicorn apps.api.main:app --reload
```

另开终端启动前端：

```powershell
Set-Location apps/web
Copy-Item .env.example .env.local
# 将 NEXT_PUBLIC_API_MODE 改为 live
npm ci
npm run dev
```

访问 `http://localhost:3000`。开发环境可访问 `http://127.0.0.1:8000/docs`；production 模板
关闭接口文档。数据库暂不可用时健康检查返回 `degraded`，依赖数据库的接口返回结构化 503。

## 验证

```powershell
docker compose up -d postgres redis
.\.venv\Scripts\ruff.exe format --check apps tests migrations
.\.venv\Scripts\ruff.exe check apps tests migrations
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\alembic.exe check
.\.venv\Scripts\pytest.exe
.\.venv\Scripts\python.exe -m apps.api.rag.evaluate
Set-Location apps/web
npm run typecheck
npm run build
```

当前验收基线：88 个测试通过；Alembic head 为 `20260913_0010`；56 条 RAG gold QA 通过；
前端生成 11 个静态页面。

## Performance

2026-09-13 的本地 production-container 轻量压测：5 VU、50 秒、385 请求，P50 17.97 ms、
P95 131.75 ms、P99 143.34 ms、HTTP error 0%；Agent 78/78、Tool 80/80 成功。该结果是
Secret 标记的合成测试流量，不是实际用户量，也不是公网容量结论。复现方法见
`loadtests/README.md`，完整边界见 `docs/phase-7-load-test-report.md`。

## Deployment

- `railway.json`：Dockerfile 构建、发布前 Alembic migration、启动命令与健康检查。
- `apps/web/vercel.json`：Vercel Next.js monorepo 配置，并关闭与 Actions 重复的原生 Git 发布。
- `deploy/*.env.example` 与 `apps/web/.env.*.example`：staging/production 变量清单，不含凭据。
- `.github/workflows/ci.yml`：常规后端、数据库、RAG、前端和容器验证。
- `.github/workflows/deploy.yml`：先执行独立质量门禁，再发布前后端并 smoke test。
- `scripts/backup_postgres.sh` 与 `scripts/verify_backup.sh`：可验证逻辑备份。

`main` 面向 staging，实际 `v*` 标签面向 production。只有 staging 云端回归完成后，才从真实
发布提交创建 `v1.0.0`；不要在无 Git 历史的副本中制造标签。

## Monitoring 与安全

配置 `OTEL_ENABLED=true`、OTLP endpoint 和 Secret header 后，可导出 traces/metrics 到兼容
平台。Admin API 提供 overview、时序指标、components、budget、safety events 和 request_id
定位。production 必须使用明确 HTTPS `CORS_ORIGINS`、独立高熵 Secrets、私网数据库/Redis、
私有对象存储与最小权限管理账号。

Rate Limit、Safety、Quota、Budget Guard 与 request timeout 不得为上线或压测关闭。合法压测
必须同时提供 `X-AutoMind-Traffic-Class: load_test` 和正确 `X-Load-Test-Token`；错误令牌仍按
用户流量处理。告警、故障处置和恢复步骤见 `docs/phase-7-runbook.md`。

## 目录

```text
apps/api/       FastAPI、Agent、Safety、RAG、AIGC、diagnosis、operations
apps/web/       Next.js 驾驶舱与 Admin
migrations/     Alembic schema history
tests/          单元、API 和 PostgreSQL/Redis 集成测试
loadtests/      k6 轻量压测
deploy/         staging/production 环境清单
scripts/        备份和校验脚本
docs/           各阶段架构、验收、部署和 Runbook
```
