# Phase 1 交付报告

## 实际修改文件

新增车辆实体、HAL 协议、VehicleService、属性规则、领域异常、PostgreSQL HAL、Phase 1 migration、人工控制 Schema、领域/API/数据库集成测试和 Phase 1 架构文档；更新车辆路由、ORM、配置、CI、README、环境变量示例和前端接口对照。

## 实现内容

- 表：`vehicles`、`vehicle_states`、`vehicle_state_audits`。
- 接口：持久化 `GET /api/v1/vehicle/state`；新增 `POST /api/v1/vehicle/control`。
- VehicleHAL：`get_state`、`get_property`、`set_property`。
- VehicleService：属性、区域和值域验证；只读属性保护。
- 并发：`expected_version` 乐观锁，冲突返回 409 和当前版本。
- 审计：状态和审计事件在同一 PostgreSQL 事务提交，记录 request_id。
- Agent 节点与 Tool：未实现，遵守 Phase 1 边界。

## 本地启动与验证

执行 `docker compose up -d postgres`、`alembic upgrade head` 后启动 Uvicorn。数据库 migration 已真实升级到 `20260912_0002`。

验证结果：

- Ruff：通过。
- 自动化测试：28 项全部通过，其中包含 PostgreSQL 集成测试。
- PostgreSQL 集成覆盖写入、重复读取持久化、实际版本冲突和审计。
- HTTP smoke test：健康检查显示数据库 `ok`；车窗状态从 0 更新到 25 后再次读取仍为 25，随后已恢复为 0。

## 前端改动

未改动。当前工作区没有马维斯的前端源码，因此无法完成 Cockpit Live Provider 切换和浏览器端验收。接口、Schema、错误结构和联调差异已形成文档。

## 新增依赖

本阶段没有新增运行时或开发依赖，复用 Phase 0 已引入的 FastAPI、SQLAlchemy、asyncpg、Alembic、Pytest 和 Ruff。

## 已知问题与技术债

- 前端联调待前端源码或 API Contract 提供后完成。
- 当前只提供演示车辆；用户车辆归属和数据隔离属于 Phase 5。
- SafetyPolicyEngine 尚未实现，因此 Phase 1 人工控制只保证类型、区域和值域正确；上下文安全策略属于 Phase 2。
- 测试依赖中有 2 条来自 FastAPI/Starlette TestClient 的弃用警告，不影响当前测试结果。

## 下一阶段稳定接口

Phase 2 可直接依赖 VehicleService、VehicleHAL、VehicleProperty、VehicleZone、状态版本与审计事务。Agent 必须通过 typed tools 调用 VehicleService，并在所有可写调用前经过独立 Safety Gate；不得直接执行 SQL。
