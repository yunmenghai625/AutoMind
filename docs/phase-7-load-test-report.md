# AutoMind Phase 7 轻量压测报告

## 结论

2026-09-13 的本地 production-container 验收通过全部 k6 阈值。该数据是合成压测流量，绝不
代表真实用户或公网生产容量；运行环境也不是 Railway/Vercel，因此上线后必须在 staging 用同一
脚本复测并建立公网基线。

## 环境与方法

- API image：`automind-api:phase7`，版本 `1.0.0`，非 root 用户运行，Docker health 为 healthy。
- 依赖：本地 Docker PostgreSQL/pgvector 与 Redis。
- Run ID：`phase7-final-20260913`。
- 模型：确定性本地 Agent 路径，记录成本为 CNY 0；未消耗外部 LLM/VLM 额度。
- 负载：10 秒升至 5 VU，保持 30 秒，10 秒降至 0，共 50 秒。
- 请求组合：健康检查、车辆状态和确定性只读 Agent 场景。
- 每个 VU 使用独立 Guest ID；Safety、Rate Limit、Quota、Budget 和 timeout 均保持启用。
- 合法测试头由服务端 Secret 校验，所有 385 个 HTTP 请求均记录为 `load_test`。

## 结果

| 指标 | 结果 | 阈值 | 判定 |
| --- | ---: | ---: | --- |
| HTTP 请求 / iteration | 385 | 记录项 | - |
| 并发 VU | 5 | 5 | 符合 |
| P50 | 17.97 ms | 记录项 | - |
| P95 | 131.75 ms | < 500 ms | 通过 |
| P99 | 143.34 ms | < 1000 ms | 通过 |
| HTTP error rate | 0% | < 1% | 通过 |
| Check success | 100% | > 99% | 通过 |
| Agent runs | 78/78 成功 | 记录项 | 100% |
| Tool calls | 80/80 成功 | 记录项 | 100% |
| Agent 平均耗时 | 64.14 ms | 记录项 | - |
| Tool 平均耗时 | 10.29 ms | 记录项 | - |
| Agent 记录成本 | CNY 0 | 记录项 | - |

本次请求中的车辆状态变更来自确定性座舱控制用例。验收完成后已把副驾驶温度恢复到运行前的
22°C；版本号因审计型写入由 204 增至 285，未回写伪造历史。

## 流量隔离验证

- 正确测试令牌：请求、Agent 与 RAG 记录使用 `traffic_class=load_test`。
- 错误或缺失令牌：即使伪造流量头也按 `user` 记录。
- Admin overview 单独返回 `testRequests`，用户请求指标不含压测流量。
- Agent/Tool 用户成功率、RAG 用户统计与 daily cost 均排除压测流量。

## 限制与上线复测

- 5 VU 只验证轻负载稳定性，不构成容量上限或扩缩容结论。
- 本地网络、缓存、数据库和确定性模型路径低估公网与第三方 Provider 延迟。
- staging 复测须保留同一阈值，记录部署区域、实例规格、Provider 模式、P50/P95/P99、错误率、
  Agent/Tool 成功率与成本，并确认告警收到但用户仪表盘未混入测试流量。
