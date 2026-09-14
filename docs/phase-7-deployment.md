# AutoMind Phase 7 部署手册

## 1. 前置条件

- 一个可供 GitHub Actions 读取的 GitHub 仓库，默认分支为 `main`。
- Railway 项目：API service、PostgreSQL/pgvector service、Redis service。
- 两个 Vercel 项目（staging/production），Root Directory 都指向 `apps/web`。
- staging 与 production 两个 GitHub Environment，均启用必要的审批/保护规则。
- 可选的 OTLP、R2/S3-compatible、LLM、VLM 与 embedding provider。

当前工作目录没有 Git 元数据和远端，也没有 Railway/Vercel 凭据，因此本地工程已完成发布
准备，但尚未生成公开 URL 或正式标签。不要把示例域名当成上线结果。

## 2. 配置平台

### Railway

1. 将仓库连接到 Railway，API service 使用仓库根目录。
2. 添加 PostgreSQL 与 Redis，确认 PostgreSQL 镜像支持 `vector` extension。
3. 以 `deploy/staging.env.example` 或 `deploy/production.env.example` 为清单创建变量；把所有
   `replace-with-*` 和示例域名替换为真实值。
4. 使用 `railway.json`：Dockerfile 构建、发布前 migration、启动命令与 `/health` 检查均由
   配置文件声明。
5. 为 API 配置 HTTPS 自定义域名，将最终前端域名写入 `CORS_ORIGINS`。

### Vercel

1. 创建 `automind-staging` 与 `automind-production` 两个项目。
2. 两个项目的 Root Directory 都设为 `apps/web`，框架选择 Next.js。
3. staging 使用 `.env.staging.example`，production 使用 `.env.production.example`。
4. 把 `NEXT_PUBLIC_API_BASE_URL` 改为对应 Railway HTTPS API 地址。
5. 确认 `NEXT_PUBLIC_API_MODE=live`；`vercel.json` 已关闭原生 Git 自动发布，避免与 Actions 重复。

### GitHub Environments

为 `staging` 与 `production` 分别设置：

Secrets:

- `RAILWAY_TOKEN`
- `RAILWAY_SERVICE`
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`（staging/production 分别填写对应项目）

Variables:

- `BACKEND_BASE_URL`
- `FRONTEND_BASE_URL`

Production 建议启用 required reviewers，并限制只允许受保护的 `v*` 标签部署。

## 3. 首次发布

1. 在本地执行第 5 节全部验收命令。
2. 推送到 `main`，观察 `deploy` 工作流：quality gate -> backend/frontend -> smoke。
3. 在 staging 完成 Guest/Registered、车辆控制、Agent、RAG、AIGC、诊断与 Admin 回归。
4. 校验 OTLP 仪表盘、预算和请求定位是真实数据，确认 Mock mode 为关闭状态。
5. 创建经过评审的 `v1.0.0` 标签并推送；标签触发 production 与 GitHub Release。
6. 发布后检查 `/health`、前端首页、核心用户闭环和告警。

不要在没有真实 Git 历史的目录中临时创建标签；标签必须指向实际验收过的发布提交。

## 4. 回滚

- 应用回滚：在 Railway/Vercel 重新部署上一个健康版本；不要在数据库 migration 执行期间
  强制终止。
- 数据库 migration：默认只前向修复。只有已确认 downgrade 不会丢失生产数据时才回退 schema。
- 数据恢复：先隔离写流量，再按 Runbook 恢复到新数据库并切换连接串，保留原库用于审计。
- 回滚后再次执行 `/health`、核心接口和 Admin 请求定位检查。

## 5. 发布前本地验收

```powershell
docker compose up -d postgres redis
.\.venv\Scripts\ruff.exe format --check apps tests migrations
.\.venv\Scripts\ruff.exe check apps tests migrations
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\alembic.exe check
.\.venv\Scripts\pytest.exe
.\.venv\Scripts\python.exe -m apps.api.rag.evaluate
Set-Location apps/web
npm ci
npm run typecheck
npm run build
```

容器验收：

```powershell
docker build -t automind-api:phase7 .
docker run --rm -p 18000:8000 --env-file deploy/production.env.local automind-api:phase7
Invoke-RestMethod http://127.0.0.1:18000/health
```

`deploy/production.env.local` 是操作者自行创建且不得提交的真实配置；仓库只提供 `.example`。

## 6. 备份

在带有 PostgreSQL client 工具的受控主机或定时任务中运行：

```sh
DATABASE_URL='postgresql://...' BACKUP_DIR='./backups' sh ./scripts/backup_postgres.sh
BACKUP_FILE='./backups/automind-YYYYMMDD-HHMMSS.dump' sh ./scripts/verify_backup.sh
```

备份应加密后复制到与生产数据库不同的受控存储，设置保留策略，并至少每季度执行一次恢复
演练。平台快照不能替代可验证的逻辑备份。
