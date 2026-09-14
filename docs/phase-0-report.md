# Phase 0 交付报告

## 实际修改文件

新增 FastAPI 应用、配置与中间件、统一错误处理、数据库基础设施、Phase 0 Mock Vehicle Repository、Pydantic Schema、Alembic migration、测试、CI、容器配置和项目文档。完整文件清单以 Git 工作区为准。

## 实现内容

- 接口：`GET /health`、`GET /api/v1/health`、`GET /api/v1/vehicle/state`。
- 数据库：async PostgreSQL engine/session factory；首个 `service_metadata` migration。
- 工程能力：app factory、环境配置、JSON 日志、request_id、统一错误、CORS、CI。
- Agent 节点与 Tool：未实现，严格遵守 Phase 0 禁止项。

## 本地启动与验证

按照 README 创建虚拟环境、安装依赖、启动 PostgreSQL、执行 `alembic upgrade head`，再启动 Uvicorn。Ruff 与 Pytest 命令也在 README 中给出。

本次交付已执行以下验证：

- Ruff：通过，无静态检查错误。
- Pytest：9 项测试全部通过；依赖包自身产生 2 条弃用警告，不影响结果。
- Alembic：`upgrade head --sql` 成功生成 PostgreSQL migration SQL。
- Docker Compose：配置解析通过；当前 Docker daemon 未运行，因此未执行容器内 PostgreSQL migration。
- HTTP smoke test：真实启动 Uvicorn 后，健康检查返回 `status=ok`、`version=0.1.0`，车辆状态返回 `source=mock`、`gear=P`。

## 前端改动

未改动。工作区没有前端源码，无法完成既有前端的 Live Provider 切换；已提供接口对照和待核对项。

## 新增依赖

- FastAPI/Uvicorn：HTTP 服务。
- Pydantic Settings：环境配置与校验。
- SQLAlchemy/asyncpg/Alembic：PostgreSQL 异步访问与迁移。
- Pytest/httpx/pytest-asyncio/Ruff：测试和质量门禁。

没有引入 LangGraph、向量数据库、Redis、VLM 或其他后续阶段依赖。

## 已知问题与技术债

- 车辆状态仍为显式 Mock，Phase 1 才持久化。
- 缺少前端仓库，尚未完成真实浏览器端 Live API 验收。
- 当前环境未提供可运行的 PostgreSQL 服务时，migration 与真实数据库健康检查需在本地 Docker 或 Supabase 环境验证。
- JWT、Rate Limit、Trace、Metrics 和 Budget Guard 属于后续阶段。

## 下一阶段稳定接口

Phase 1 可直接依赖 app factory、Settings、request_id、统一错误结构、数据库 engine/session、Alembic 和公开 `VehicleStateResponse`。实现时应以真实 Vehicle Repository 替换 Mock Repository，并保持 `GET /api/v1/vehicle/state` 响应兼容。
