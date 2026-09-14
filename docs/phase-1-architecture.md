# Phase 1 车辆数字孪生架构

## 范围

Phase 1 将车辆状态从 Phase 0 Mock Provider 替换为 PostgreSQL 持久化实现。公开 API 只依赖 VehicleService，VehicleService 只依赖 VehicleHAL 协议；SQLAlchemy 和数据库事务被限制在 infrastructure 层。该边界允许 Phase 2 把同一 VehicleService 注册为 typed tools，而不让 Agent 直接访问数据库。

## 调用链

```text
GET /api/v1/vehicle/state
  -> VehicleService.get_state
  -> PostgresVehicleHAL.get_state
  -> vehicle_states

POST /api/v1/vehicle/control
  -> VehicleService.set_property
  -> property and zone validation
  -> PostgresVehicleHAL.set_property
  -> optimistic UPDATE WHERE version = expected_version
  -> vehicle_state_audits
  -> commit state and audit in one transaction
```

## 数据模型

- `vehicles`：车辆档案基础字段，`user_id` 在 Phase 5 接入 Auth 后绑定。
- `vehicle_states`：数字孪生当前快照，`vehicle_id` 唯一，`version` 用于并发控制。
- `vehicle_state_audits`：不可变状态变更事件，记录 request_id、属性、区域、新旧值和提交后的版本。

演示车辆使用固定 UUID `00000000-0000-0000-0000-000000000001`，由 migration 写入，不依赖运行时隐式创建。

## 属性规则

- 温度：16 至 30 摄氏度，驾驶位和副驾驶分别存储。
- 座椅加热：驾驶位或副驾驶，整数 0 至 3。
- 车窗：驾驶位或副驾驶，0 至 100。
- 车门：驾驶位或副驾驶，`OPEN` 或 `CLOSED`。
- 灯光：`OFF`、`PARKING`、`LOW_BEAM`、`HIGH_BEAM`。
- 挡位：`P`、`R`、`N`、`D`。
- 充电：`IDLE` 或 `CHARGING`。
- 速度、电量和续航：只读。

这些规则只负责类型和值域完整性。高速开门、非 P 挡充电等上下文安全决策不会伪装在 Phase 1 中实现，它们属于 Phase 2 的独立 SafetyPolicyEngine。

## 并发与失败

客户端读取状态后必须把 `version` 作为 `expected_version` 提交。更新只在数据库版本仍一致时成功；过期请求返回 409 和当前版本。数据库不可用时返回统一 503，既不返回 Mock 数据，也不把故障伪装成成功。

