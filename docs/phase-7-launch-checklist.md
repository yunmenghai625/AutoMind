# AutoMind Phase 7 上线检查单

## 仓库内已完成

- [x] 应用版本统一为 `1.0.0`。
- [x] Docker image 使用非 root 用户并配置 `/health`。
- [x] Railway/Vercel config-as-code 和双环境变量模板已提交。
- [x] 部署前运行 migration、测试、RAG 评估、前端构建和容器构建门禁。
- [x] Rate Limit、Safety、Quota、Budget Guard 与 timeout 保持启用。
- [x] 压测流量经 Secret 校验，与用户运营指标和成本隔离。
- [x] 轻量压测阈值通过，报告明确标记为合成流量。
- [x] PostgreSQL 备份与 checksum/catalog 校验脚本已提供。
- [x] 本地 custom-format 备份已完成独立恢复演练，并核对关键表与 migration head。
- [x] README、架构、部署、压测和 Runbook 已完成。
- [x] production Admin 不使用 Mock 指标。

## 平台上线前待完成

- [ ] 将当前代码纳入真实 GitHub 仓库，保护 `main` 与 `v*` 发布标签。
- [ ] 创建 GitHub `staging`、`production` Environments，配置审批、Secrets 与 URL variables。
- [ ] 创建 Railway PostgreSQL/pgvector、Redis、API services 并注入真实 Secrets。
- [ ] 创建 Vercel 项目，Root Directory 为 `apps/web`，production 强制 live mode。
- [ ] 配置真实 HTTPS 域名；API `CORS_ORIGINS` 只包含实际前端域名。
- [ ] 配置 OTLP 仪表盘、RBAC、MFA 与 5xx/延迟/预算/依赖告警。
- [ ] 配置私有 R2/S3-compatible 对象存储与诊断图片生命周期。
- [ ] 执行首次 staging 部署和 Guest/Registered 全功能安全回归。
- [ ] 在 staging 重跑 k6，并记录平台规格、公网 P50/P95/P99、错误率和成本。
- [ ] 执行一次从逻辑备份恢复到新数据库的演练。
- [ ] 从通过验收的实际提交创建 `v1.0.0`，完成 production smoke 与 GitHub Release。
- [ ] 将真实 Live Demo、API、监控和发布链接写回 README/发布记录。

只有第二部分全部关闭后，Phase 7 才能从“release-ready”转为“publicly launched”。
