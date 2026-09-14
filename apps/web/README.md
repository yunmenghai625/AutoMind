# AutoMind Web 1.0.0

Next.js 15 + React 19 驾驶舱，覆盖首页、Cockpit、Garage、Knowledge、Diagnosis、Admin、
Architecture 与 Status。开发时可显式使用 Mock；staging/production 必须使用 live FastAPI。

## 本地运行

```powershell
Set-Location C:\Users\35008\Desktop\AutoMind\apps\web
Copy-Item .env.example .env.local
npm ci
npm run dev
```

把 `.env.local` 设为：

```ini
NEXT_PUBLIC_API_MODE=live
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

后端从仓库根目录运行：

```powershell
docker compose up -d postgres redis
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\uvicorn.exe apps.api.main:app --reload
```

## 验证与发布

```powershell
npm run typecheck
npm run build
```

Vercel 项目 Root Directory 指向 `apps/web`，环境变量参考 `.env.staging.example` 和
`.env.production.example`。公开环境不得设置 Mock mode；API 地址必须是对应环境的 HTTPS
Railway 地址。完整流程见仓库根目录 `docs/phase-7-deployment.md`。
