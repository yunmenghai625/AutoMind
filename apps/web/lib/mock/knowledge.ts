import type {
  Citation,
  KnowledgeAnswer,
  KnowledgeSource,
} from "@/types/knowledge";

export const MOCK_KNOWLEDGE_SOURCES: KnowledgeSource[] = [
  {
    id: "vehicle-manual",
    title: "Vehicle Manual",
    description: "Owner's manual & operation guide",
    documents: 214,
    status: "indexed",
    updatedAt: "2026-09-10",
  },
  {
    id: "ev-charging",
    title: "EV Charging Guide",
    description: "Charging, range and battery care",
    documents: 58,
    status: "indexed",
    updatedAt: "2026-09-08",
  },
  {
    id: "adas-manual",
    title: "ADAS Manual",
    description: "Advanced driver assistance systems",
    documents: 96,
    status: "indexed",
    updatedAt: "2026-08-30",
  },
  {
    id: "maintenance",
    title: "Maintenance Guide",
    description: "Service intervals & DIY checks",
    documents: 132,
    status: "syncing",
    updatedAt: "2026-09-11",
  },
  {
    id: "warning-lights",
    title: "Warning Light Guide",
    description: "Dashboard warning indicators",
    documents: 74,
    status: "indexed",
    updatedAt: "2026-09-05",
  },
];

const citations: Citation[] = [
  {
    source: "Vehicle Manual",
    chapter: "Warning Indicators",
    page: 217,
    snippet:
      "The Tire Pressure Monitoring System indicator illuminates when one or more tires are significantly under-inflated…",
  },
  {
    source: "Warning Light Guide",
    chapter: "TPMS",
    page: 12,
    snippet:
      "If TPMS lamp stays on, check tire pressures with a gauge; if it flashes for 60s, a TPMS fault is present…",
  },
];

export function mockKnowledgeQuery(query: string): KnowledgeAnswer {
  return {
    answer:
      "Yes, you can continue driving short distances, but carefully. The TPMS warning light means at least one tire is running below the recommended pressure.\n\nCheck all four pressures at the next safe stop — recommended cold inflation is 250 kPa (36 psi). If the tire visually looks flat, do not keep driving; stop and inspect. If the light flashes for about 60 seconds then stays on, there may be a system fault rather than a low tire — have the TPMS checked at a service center.\n\nReduce your speed and avoid hard braking. Keep the drive short and head to the nearest safe location to add air.",
    citations,
    retrieval: {
      originalQuery: query,
      rewrittenQuery:
        query + " TPMS tire pressure warning recommended action safe driving",
      retrievedDocuments: 5,
      rerankerEnabled: true,
      vectorSearchMs: 64,
      rerankMs: 18,
    },
  };
}
