# Phase 2 交付报告

## 交付结论

任务书定义的 LangGraph Cockpit Agent 与 Safety Gate 已完成，数据库已升级至
20260912_0003。本阶段没有实现 RAG、多模态诊断或新增大量 Agent，也没有修改正在并行开发的前端。

## 验收结果

| 验收项 | 结果 | 验证方式 |
| --- | --- | --- |
| 车控 Tool 不得绕过 Safety Gate | 通过 | 执行器拒绝无有效 Safety Permit 的调用 |
| speed 大于 0 时开门 100% 拒绝 | 通过 | 实际速度与 120km/h开门 两类自动测试 |
| Tool 真实改变数据库状态 | 通过 | PostgreSQL 集成测试验证副驾温度和座椅加热 |
| Admin 可读取真实 Run | 通过 | Run 详情返回实际节点与工具审计 |
| 普通请求 1 至 2 次 LLM 调用 | 通过 | 确定性请求为 0 次；含糊请求最多 1 次 |

## 三个基准案例

- 我有点冷：主驾温度设为 24℃，主驾座椅加热设为 1 挡，0 次模型调用。
- 我妈有点冷：按前排乘客解释，副驾温度设为 25℃，副驾座椅加热设为 1 挡，0 次模型调用。
- 120km/h开门：Safety Gate 返回 DOOR_OPEN_WHILE_MOVING，车门状态不变。

## 验证命令

    ruff check apps/api migrations tests
    设置 TEST_DATABASE_URL 后运行 pytest
    alembic current
    alembic check

自动测试覆盖 Cheap Router、Model Gateway 限次、typed tool 参数、安全策略、防伪授权、LangGraph、
非流式 Chat、SSE 流、PostgreSQL 状态变更与 Admin Trace。

## 后续联调

前端完成写入后，将座舱和 Admin 的 Mock Provider 切换至 Live API 即可。Phase 3 的 RAG、知识库表、
向量检索和引用功能不在本阶段范围内。
