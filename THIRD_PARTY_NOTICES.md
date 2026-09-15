# AutoMind 第三方许可说明

AutoMind 使用第三方开源软件和托管服务。下列材料不属于 AutoMind 的独占版权范围，使用时应
以对应项目发布版本附带的许可证和服务条款为准。

## 前端主要依赖

| 组件 | 许可证 |
| --- | --- |
| Next.js、React、React DOM | MIT |
| Framer Motion、Recharts、Zustand、clsx、tailwind-merge | MIT |
| class-variance-authority | Apache-2.0 |
| Lucide React | ISC |
| Tailwind CSS | MIT |
| TypeScript | Apache-2.0 |

构建依赖还包含 `sharp`/`libvips` 相关组件（Apache-2.0、LGPL-3.0-or-later、MIT）及
`caniuse-lite` 数据（CC-BY-4.0）。完整、精确的版本清单以 `apps/web/package-lock.json`
为准。

## 后端主要依赖

FastAPI、SQLAlchemy、Alembic、LangGraph、Redis client、boto3、asyncpg、HTTPX、Pillow、
pgvector、pypdf、PyJWT、OpenTelemetry、Uvicorn 及其依赖分别采用 MIT、Apache-2.0、BSD、
ISC 或其他兼容许可证。完整、精确的版本清单以 `pyproject.toml` 和实际安装包元数据为准。

## 外部服务与标识

GitHub、Vercel、Railway、Grafana、Alibaba Cloud/通义千问、NHTSA 及其他服务名称和商标归其
各自权利人所有。它们在本项目中仅用于描述技术集成，不表示授权、赞助或合作关系。

在重新分发构建产物或将项目转为商业用途前，应生成完整的软件物料清单，并随分发物保留各组件
要求的版权、许可证和归属通知。
