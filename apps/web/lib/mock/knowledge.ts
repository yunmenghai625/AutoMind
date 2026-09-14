import type {
  Citation,
  KnowledgeAnswer,
  KnowledgeSource,
} from "@/types/knowledge";

export const MOCK_KNOWLEDGE_SOURCES: KnowledgeSource[] = [
  {
    id: "vehicle-manual",
    title: "车辆用户手册",
    description: "车主手册与操作指南",
    documents: 214,
    status: "indexed",
    updatedAt: "2026-09-10",
  },
  {
    id: "ev-charging",
    title: "电动汽车充电指南",
    description: "充电、续航与电池养护",
    documents: 58,
    status: "indexed",
    updatedAt: "2026-09-08",
  },
  {
    id: "adas-manual",
    title: "ADAS 使用手册",
    description: "高级驾驶辅助系统说明",
    documents: 96,
    status: "indexed",
    updatedAt: "2026-08-30",
  },
  {
    id: "maintenance",
    title: "车辆保养指南",
    description: "保养周期与日常自检",
    documents: 132,
    status: "syncing",
    updatedAt: "2026-09-11",
  },
  {
    id: "warning-lights",
    title: "仪表警告灯指南",
    description: "仪表盘警告指示说明",
    documents: 74,
    status: "indexed",
    updatedAt: "2026-09-05",
  },
];

const citations: Citation[] = [
  {
    source: "车辆用户手册",
    chapter: "警告指示灯",
    page: 217,
    snippet:
      "当一个或多个轮胎的气压明显低于标准值时，胎压监测系统指示灯会亮起……",
  },
  {
    source: "仪表警告灯指南",
    chapter: "TPMS",
    page: 12,
    snippet:
      "若 TPMS 指示灯持续点亮，请使用胎压计检查轮胎；若闪烁约 60 秒，则可能存在系统故障……",
  },
];

export function mockKnowledgeQuery(query: string): KnowledgeAnswer {
  return {
    answer:
      "可以谨慎地短距离行驶，但应尽快处理。TPMS 胎压警告灯表示至少有一个轮胎低于建议胎压。\n\n请在下一个安全停车点检查四个轮胎，建议冷态胎压为 250 kPa（36 psi）。如果轮胎肉眼可见明显瘪塌，请不要继续行驶，应立即停车检查。如果指示灯先闪烁约 60 秒后常亮，可能是胎压监测系统故障，建议前往服务中心检查。\n\n请降低车速、避免急刹，并尽快前往最近的安全地点补充胎压。",
    citations,
    retrieval: {
      originalQuery: query,
      rewrittenQuery:
        query + " TPMS 胎压警告 建议措施 安全驾驶",
      retrievedDocuments: 5,
      rerankerEnabled: true,
      vectorSearchMs: 64,
      rerankMs: 18,
    },
  };
}
