# Phase 2 LangGraph Cockpit Agent 架构

## 结论

Phase 2 已建立第一条完整智能座舱链路。确定性请求由 Cheap Router 直接规划，含糊请求最多调用一次
OpenAI-compatible 模型；所有候选工具在执行前必须依次通过白名单参数校验和代码化 Safety Gate。
模型只做意图规划，不能批准安全操作。

## 请求链路

    自然语言
      -> load_context 读取 PostgreSQL VehicleState
      -> route_intent Cheap Router
           -> 高置信命令或查询：规则规划
           -> 含糊请求：Model Gateway 单次规划
      -> validate_tools Pydantic 白名单参数校验
      -> safety_gate SafetyPolicyEngine 硬规则
      -> execute_tools Safety Permit + VehicleService + HAL
      -> compose_response
      -> JSON 响应或 SSE 事件

LangGraph 使用单一 AgentState，节点为 load_context、route_intent、model_plan、
validate_tools、safety_gate、execute_tools 和 compose_response。图的递归上限为 16，
没有引入额外 Agent。

## 安全边界

SafetyPolicyEngine 是确定性代码，不读取模型的安全结论。当前硬规则包括：

- 实际速度或用户陈述速度大于 0 km/h 时，打开车门一律拒绝。
- 非 P 挡时，打开车门一律拒绝。
- 非 P 挡时，开始充电一律拒绝。
- 车辆移动时，智能助手切换挡位一律拒绝。

执行器只接收带内部 Safety Permit 的 AuthorizedToolCall。未授权或伪造授权会在执行器入口被拒绝。
Phase 1 人工控制 API 仍保留，其用途与 Agent 工具入口分离。

## Typed Vehicle Tools

| 工具 | 参数 | VehicleProperty |
| --- | --- | --- |
| set_temperature | zone, temp_c | DRIVER_TEMP / PASSENGER_TEMP |
| set_seat_heating | zone, level | SEAT_HEAT |
| set_window | zone, position | WINDOW_POSITION |
| set_door_state | zone, state | DOOR_STATE |
| set_light | state | LIGHT_STATE |
| set_charge | status | CHARGE_STATUS |

工具注册器会拒绝未登记工具、越界参数和额外字段。工具最终复用 Phase 1 VehicleService 的值域规则、
乐观锁、数据库事务和状态审计。

## Model Gateway

Qwen 通过可配置的 OpenAI-compatible chat completions 接口接入。只有同时配置
LLM_API_KEY、LLM_BASE_URL 和 LLM_MODEL 才启用模型；否则确定性命令仍可工作，含糊请求安全降级。
模型温度为 0，输出必须符合 JSON ModelPlan，并记录 provider、model、token、时延和估算成本。

## 运行审计

- agent_runs：请求、Agent、模型、状态、总时延、token、成本和 LLM 调用次数。
- agent_steps：图节点顺序、时延、状态和有限摘要，不存储思维链。
- tool_calls：工具名、参数、结果、状态以及安全决定和规则代码。
- vehicle_state_audits：沿用 Phase 1，记录真实状态变更和版本。

数据库版本为 20260912_0003。管理接口可读取真实 Run 列表及详情。

## API 契约

- POST /api/v1/chat：非流式对话，匹配现有前端 SendChatResponse。
- GET /api/v1/chat/stream：SSE 流，事件为 started、message、vehicle、done。
- GET /api/v1/admin/agent-runs：真实 Agent Run 列表。
- GET /api/v1/admin/agent-runs/{id}：节点和工具 trace。
