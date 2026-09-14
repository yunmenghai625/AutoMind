# AutoMind Phase 6 安全检查清单

## 上线前必须完成

- [ ] `APP_ENV=production`，关闭不需要的 `/docs`。
- [ ] `JWT_SECRET` 使用至少 32 字节的随机值，并与 `VIN_HASH_SECRET` 分离。
- [ ] `DATABASE_URL`、`REDIS_URL`、Provider API Key 和 OTLP Header 只由部署平台 Secret 注入。
- [ ] `CORS_ORIGINS` 仅列出明确的 HTTPS 前端域名；禁止 `*` 与 HTTP。
- [ ] Admin 令牌只授予受控人员，确认匿名访问返回 401、普通用户返回 403。
- [ ] Grafana/OTLP 管理入口不公开，使用供应商 RBAC、MFA 与最小权限 Token。
- [ ] 设置 `REQUEST_TIMEOUT_SECONDS`、`RATE_LIMIT_PER_MINUTE`、`DAILY_AI_BUDGET_CNY` 与
  `BUDGET_ECONOMY_THRESHOLD_RATIO`，并根据实际流量压测结果调整。
- [ ] OTLP 标签和日志不得加入 Prompt、Authorization、VIN、电子邮件或图片内容。
- [ ] 确认反向代理只接受 HTTPS，并保留 HSTS、nosniff、DENY、no-referrer、no-store 响应头。
- [ ] 数据库账号限制到应用 schema；Redis 不暴露公网端口并要求私网/TLS/认证。
- [ ] 验证诊断衍生图片生命周期清理与对象存储私有访问策略。
- [ ] 为预算进入 economy/exhausted、熔断打开、Redis/数据库降级和 5xx 配置告警。

## 已由代码和测试保证

- 日志 Formatter 对 Authorization、Password、Secret、API Key、Token 与 VIN 递归脱敏。
- 限流身份只使用不可逆摘要，响应只暴露限额和剩余额度。
- 错误结构不返回异常堆栈或 Provider 原始响应。
- Admin API 统一执行注册用户与管理员角色检查。
- VIN 继续只保存 HMAC 摘要与后四位；Agent 工具仍必须通过 SafetyPolicyEngine。
- 失败请求保存 request_id、trace_id、错误码、状态码和耗时，便于审计而不保存请求正文。

## 运行中复核

- [ ] 每周检查 Token/成本、P95/P99、Tool 失败、RAG 延迟和 Safety 拒绝趋势。
- [ ] 每月轮换 Provider/OTLP 凭据，并演练撤销。
- [ ] 每次发布执行 Ruff、Pytest、Alembic check、前端 typecheck/build 与 RAG gold QA。
- [ ] 若出现敏感信息误写日志，立即撤销相关凭据、限制日志访问并按保留策略清理。
