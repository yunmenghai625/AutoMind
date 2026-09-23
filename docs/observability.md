# AutoMind 可观测性与告警基线

## 信号与关联方式

- Railway stdout：脱敏 JSON 日志，包含 `request_id`；启用 OTLP 后同步导出脱敏后的日志。
- Grafana Cloud：OTLP traces、metrics、logs；HTTP 指标使用路由模板，避免 UUID 造成高基数。
- PostgreSQL：请求索引、Agent/Tool/RAG 审计与运营聚合，可按 `request_id`、`trace_id`、`run_id` 关联。
- 浏览器：仅上报 Web Vitals、错误类型和页面路径，不上传错误正文、用户输入或车辆数据。
- GitHub Actions：每 15 分钟检查 API、数据库、Redis、知识库和前端；失败运行即为外部可用性告警。

## Grafana 告警建议

在 Grafana Alerting 中使用实际导入后的指标标签确认查询，再创建以下规则：

1. **API 5xx**：5 分钟内 `operation.kind=http` 且 `operation.status=server_error` 的比例 >= 2%，持续 5 分钟。
2. **API 延迟**：HTTP duration 的 P95 > 1000ms，持续 10 分钟。
3. **AI 失败**：`operation.kind` 为 `llm`、`rag`、`tool` 或 `frontend` 的失败率 >= 5%，持续 10 分钟。
4. **前端体验**：LCP/INP/CLS 的 `poor` 比例 >= 10%，持续 15 分钟。
5. **数据停止**：服务 10 分钟没有任何 HTTP 指标，配合外部探测失败触发。
6. **预算和容量**：Admin Budget 进入 `economy/exhausted`，或 AI admission 持续拒绝请求。

通知联系人至少配置一个个人邮箱；如接入团队工具，再增加 Webhook。告警消息不得包含 Prompt、VIN、图片或令牌。

## 验收

1. 访问 `/health`，确认 database、redis 为 `ok`，storage/telemetry 符合当前配置。
2. 在浏览器打开多个页面，Grafana 能查询 `frontend.web_vital` 指标。
3. 人为访问一个不存在的 API，日志中能用响应的 `X-Request-ID` 找到对应记录。
4. 手动运行 `continuous-monitor` 工作流并确认成功。
5. 使用测试告警验证通知联系人，再恢复正常阈值。
