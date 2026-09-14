# Phase 3 Automotive RAG 架构

## 目标与边界

Phase 3 在既有 FastAPI、PostgreSQL 和可观测基础上构建汽车知识检索。实现严格限制为
PostgreSQL FTS + pgvector，不引入 Qdrant、消息队列或额外检索中间件。答案必须来自命中片段；
达不到置信度阈值时返回固定的“无可靠资料”回答。

## 入库链路

```text
Markdown / PDF
  -> 解析正文、章节、页码
  -> 700 字符分块（100 字符重叠）
  -> 生成 simple FTS 可检索文本
  -> 384 维 embedding 批处理
  -> documents + chunks 原子替换
```

- Markdown 使用 `<!-- page: N -->` 标记页码，最近的标题作为章节。
- PDF 通过 pypdf 按物理页提取文本，页码从 1 开始。
- `source_key` 唯一；相同校验和重复入库直接复用，内容变化时删除旧 chunk 并提升版本。
- embedding provider 是独立接口。默认 hashing provider 可离线、确定性运行；生产可切换
  OpenAI-compatible `/embeddings` 服务。数据库列固定为 `vector(384)`，配置不允许维度漂移。

## 检索与回答链路

```text
用户问题
  -> 保存 rag_queries(status=running)
  -> query embedding
  -> pgvector cosine 70% + PostgreSQL FTS 30%
  -> Reranker Adapter（本地 token overlap）
  -> 置信度门槛
       ├─ 通过：抽取式回答 + 前 3 条 citation
       └─ 未通过：规则 Query Rewrite，最多 2 次；仍失败则不回答
  -> 保存每次 rag_hits 与最终状态/耗时
```

当前重排分数由 65% hybrid score 与 35% query/content token overlap 组成。该实现位于独立
`Reranker` 接口后，可在不修改检索服务的前提下替换 provider。`MAX_RETRY` 在配置、服务与
数据库约束三层均限定不超过 2。

## 数据模型

| 表 | 用途 | 关键追溯字段 |
| --- | --- | --- |
| `documents` | 知识源版本与状态 | `source_key`、checksum、URI、version |
| `chunks` | 可检索证据单元 | document、section、page、content、embedding |
| `rag_queries` | 每次问答审计 | request、原始/改写问题、状态、重试、耗时、错误 |
| `rag_hits` | 每轮候选排序 | attempt、rank、三种检索分数、重排分数、selected |

`chunks.search_vector` 是持久化计算列并建立 GIN 索引；`chunks.embedding` 建立 cosine HNSW
索引。外键删除采用级联，避免文档更新后保留失效引用。

## API 契约

- `POST /api/v1/knowledge/documents/ingest`：接收 Markdown 内容与知识源 metadata。
- `GET /api/v1/knowledge/sources`：列出索引完成的知识源。
- `POST /api/v1/knowledge/query`：返回 `answer`、`citations[]` 和 `retrieval`。

每个 citation 包含 `source`、`chapter`、`page`、`snippet`；retrieval 公开原始/改写问题、
文档数量、重排开关、检索耗时、重排耗时、重试次数和 query ID。该结构允许前端展示引用，
也允许运维从 query ID 追查每轮命中。

## 评估与失败策略

`data/evaluation/gold_qa.jsonl` 包含 56 条问题，覆盖用户手册、充电、ADAS、维护和无证据
问题。`python -m apps.api.rag.evaluate` 重复运行 source recall@3、回答门禁准确率与关键词覆盖率。

embedding、数据库或检索异常会把 `rag_queries.status` 标记为 `failed` 并保存异常类型；API
返回统一错误码 `RAG_QUERY_FAILED`。低置信度不是系统错误，记录为 `no_evidence`，不生成
脱离资料的建议。
