# AutoMind Phase 5 完成报告

## 结论

任务书 v1.1 的 Phase 5 Product System 已完成。系统现已具备 JWT/Guest 双身份、注册用户数据隔离、
显式可编辑偏好记忆、个人 Garage、VIN/Recall Provider 与缓存降级、回答反馈和分层日配额。

## 交付物

- Auth dependency：验证 Bearer JWT 的 `sub`、`exp`、`aud`、可选 `iss`，并校验账户状态。
- Memory service：偏好查看、显式写入和删除；没有聊天内容自动抽取。
- Garage API：车辆档案 CRUD、主车辆读取、跨用户 404 隔离、可选 VIN 最小化存储。
- External data adapter：Provider 协议、NHTSA VIN/Recall 实现、归一化缓存和失败降级。
- Feedback API：Agent 回答点赞/点踩写入与按身份查询；现有 Assistant UI 提供反馈按钮。
- Quota：文本请求纳入 `usage_daily`，Guest 与 Registered 分别配置。
- 前端最小接入：Garage、Recall、Preferences、Chat、Diagnosis、AIGC 使用统一身份头。
- Alembic `20260913_0008`：新增产品表和使用量字段，并保持历史数据兼容。

## 验收结果

- Ruff：通过。
- Python 单元测试：71 passed。
- PostgreSQL 集成测试：6 passed。
- 前端 TypeScript typecheck：通过。
- Next.js production build：通过，11 个静态页面生成成功。
- Alembic upgrade/check：数据库位于 `20260913_0008 (head)`，无待生成差异。
- 56 条 RAG gold QA：继续作为 Phase 3 回归门禁，不因 Phase 5 改动降低指标。

完整 Pytest 回归合计 77 passed。

Phase 5 PostgreSQL 测试直接验证：用户 A 的偏好与车辆对用户 B 不可见；VIN 原文不在响应或数据库
中出现；外部 Provider 不可用时返回结构化降级状态；Guest 1 次与 Registered 2 次测试额度分别
独立生效；反馈列表按主体隔离。

## 配置说明

- `JWT_SECRET`：兼容现有 HS256 JWT 登录；生产必须使用足够长度的随机 Secret。
- `JWT_AUDIENCE` / `JWT_ISSUER`：按身份提供方设置。
- `GUEST_TEXT_DAILY_LIMIT` / `REGISTERED_TEXT_DAILY_LIMIT`：文本请求分层额度。
- `VEHICLE_DATA_PROVIDER=nhtsa`：启用 NHTSA 适配器；默认 disabled，适合离线开发。
- `VEHICLE_DATA_TIMEOUT_SECONDS` / `VEHICLE_DATA_CACHE_TTL_HOURS`：外部超时与缓存周期。
- `VIN_HASH_SECRET`：VIN HMAC 专用密钥；生产环境应与 JWT Secret 分离。

前端登录完成后把访问令牌写入 `localStorage["automind-access-token"]`；未登录时统一生成
`automind-guest-id`。这与既有前端登录模块解耦，后续替换令牌获取方式不影响业务 API。

## 阶段边界

本阶段没有引入自动敏感信息记忆、未向前端暴露第三方原始响应、未让 Agent 直接调用外部 HTTP，
也没有提前实现 Phase 6 的完整运营后台、RBAC 管理面或生产级 JWKS 密钥轮换。
