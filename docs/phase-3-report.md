# Phase 3 验收报告

验收日期：2026-09-12

## 结论

Phase 3 Automotive RAG 已完成。数据库迁移已应用到 `20260912_0004 (head)`，四份汽车知识
样例已实际写入 PostgreSQL，共 17 个带章节和页码的 chunk。真实 PostgreSQL 端到端测试与
56 条 gold QA 均通过。

## 交付物

- RAG pipeline：Markdown/PDF 解析、分块、embedding 批处理、hybrid retrieval、reranker、
  Query Rewrite、置信度门禁和引用生成。
- 入库能力：`python -m apps.api.rag.ingest_cli data/knowledge` 与 Markdown 入库 API。
- 检索 API：`POST /api/v1/knowledge/query`；知识源 API：`GET /api/v1/knowledge/sources`。
- 引用结构：文档标题、章节、页码、原文片段，以及可关联审计的 query ID。
- 数据与迁移：`documents`、`chunks`、`rag_queries`、`rag_hits` 及 pgvector/GIN/HNSW 索引。
- 评估资产：56 条 `data/evaluation/gold_qa.jsonl` 与可重复评估脚本。

## 自动化验证

| 验证项 | 结果 |
| --- | --- |
| Ruff format/check | 通过 |
| 非集成测试 | 49 passed |
| PostgreSQL 集成测试 | 3 passed |
| Alembic 当前版本 | `20260912_0004 (head)` |
| Alembic schema drift | No new upgrade operations detected |
| 知识入库 | 4 documents / 17 chunks |

PostgreSQL 集成测试覆盖：文档真实入库、pgvector + FTS hybrid retrieval、重排、答案引用、
无证据拒答，以及 `rag_queries` 最终状态审计。原有车辆控制与 Agent 审计集成测试同时通过。

## Gold QA 评估

运行命令：

```powershell
.\.venv\Scripts\python.exe -m apps.api.rag.evaluate
```

| 指标 | 结果 |
| --- | ---: |
| Cases | 56 |
| Source recall@3 | 1.0000 |
| Answer guard accuracy | 1.0000 |
| Keyword coverage | 1.0000 |

数据集包含 52 条有证据问题和 4 条无证据问题，覆盖 TPMS、制动、车门、仪表警告、充电、
低温续航、长期停放、ACC、LKA、AEB、保养、轮胎、雨刮、制动液和冷却液。四条无证据问题
全部返回固定拒答且无 citation；低置信度 Query Rewrite 在真实评估中被触发，重试次数未超过 2。

## 任务书验收逐项核对

- 回答可定位 document/section/page：通过，citation 同时带 snippet。
- 无证据时不编造：通过，固定拒答且 `citations=[]`。
- 检索失败可观测：通过，query/hit、各阶段分数、重试、耗时、错误码均持久化。
- gold set 可重复跑：通过，56 条 JSONL 由独立 CLI 运行。
- 不使用独立 Qdrant：通过，只使用现有 PostgreSQL 与 pgvector 扩展。

## 风险说明

当前 1.0000 是针对仓库内受控的最小验收集，不等同于开放域生产准确率。默认 hashing
embedding 的目的，是让本地和 CI 在无外部模型密钥时仍能重复验收；生产部署应接入经过汽车
语料评估的 OpenAI-compatible embedding provider，并扩大真实车型、语言变体与对抗性无证据集。
