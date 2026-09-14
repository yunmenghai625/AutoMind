# AutoMind Phase 5 Product System 架构

## 目标与边界

Phase 5 把 Phase 0–4 的单车 AI Demo 升级为具备用户、显式偏好记忆、个人车库、外部车辆数据、
反馈和分级配额的产品系统。前端只复用既有 Mavis 页面和 API Service Layer，没有重写界面。

长期记忆只接收用户在设置表单中明确提交的低风险结构化偏好；聊天、诊断文本和 VIN 不会被自动
抽取为长期记忆。VIN 仅在请求生命周期内用于校验、Provider 查询和 HMAC 计算，数据库只保存
不可逆摘要与后四位。

## 请求与数据流

```text
Browser / existing login
  -> Authorization: Bearer JWT | stable X-Guest-ID
  -> FastAPI identity dependency
     -> registered: validate HS256 JWT (sub/exp/aud/iss), ensure active user
     -> guest: derive non-PII subject key
  -> quota reservation (guest and registered limits are independent)
  -> ownership-scoped service/repository
     -> PostgreSQL

Garage vehicle
  -> normalized make/model/year/powertrain/mileage
  -> optional VIN -> validate -> HMAC-SHA256 + last4 -> persist

Recall/VIN request
  -> cache lookup
  -> VehicleDataProvider (disabled or NHTSA adapter, one short retry)
  -> normalize allow-listed fields
  -> persist normalized cache/recalls
  -> success | cached | degraded | unavailable
```

## 模块职责

- `auth/`：Bearer JWT 认证与最小身份对象；无令牌请求保留 Guest 能力。
- `product/repository.py`：用户、偏好、车库、外部数据缓存、反馈和文本额度的持久化边界。
- `product/service.py`：所有权校验、VIN 最小化、缓存降级、显式 Memory 和配额语义。
- `product/vehicle_data.py`：外部 Provider 协议及 NHTSA 适配器。Agent 不直接发起 HTTP 请求。
- `api/routes/`：Auth、Preferences、Garage、Vehicle Data、Feedback API。
- `web/lib/api/identity.ts`：现有前端登录令牌与稳定 Guest ID 的统一请求头。

## 数据模型

- `users`：认证主体、角色、启停状态。
- `user_preferences`：温度、座椅加热、充电上限、驾驶模式和受限扩展 JSON。
- `vehicles`：用户归属、车辆档案、VIN HMAC 与后四位。
- `vehicle_recalls`：归一化召回数据、来源、抓取与过期时间。
- `vehicle_data_cache`：只保存归一化结果，不保存第三方原始响应。
- `feedback`：按 `subject_key` 隔离的点赞/点踩，绑定 Agent Run 或消息。
- `usage_daily`：分别统计文本、AIGC、诊断和图片调用。

## 安全不变量

1. 注册用户所有 Garage 查询和修改都同时限定 `vehicle_id` 与 `user_id`。
2. Guest 只能使用预置演示车辆，不能通过指定 UUID 访问注册用户车辆。
3. 偏好 API 必须登录，且只能查看、修改或删除自己的记录。
4. JWT 固定允许 HS256，要求 `sub` 与 `exp`，可配置 `aud` 和 `iss`；禁用账户返回 403。
5. 外部 API 的原始 JSON 不向前端透传；返回 Schema 只包含 allow-list 字段。
6. Provider 超时最多一次短重试；有旧缓存时降级返回，无缓存时明确 unavailable。
7. VIN 不明文落库或回传，只显示掩码。

## API

- `GET /api/v1/auth/me`
- `GET|PUT|DELETE /api/v1/preferences`
- `GET /api/v1/garage/vehicle`
- `GET|POST /api/v1/garage/vehicles`
- `GET|PATCH|DELETE /api/v1/garage/vehicles/{vehicle_id}`
- `POST /api/v1/vehicle/vin/decode`
- `GET /api/v1/vehicle/recalls`
- `GET|POST /api/v1/feedback`

