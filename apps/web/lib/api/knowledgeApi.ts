import { http, simulate } from "@/lib/api/apiClient";
import { API_MODE } from "@/lib/config";
import type { KnowledgeAnswer, KnowledgeSource } from "@/types/knowledge";

/**
 * Knowledge RAG services.
 * POST /api/v1/knowledge/query (future backend).
 */

export async function getKnowledgeSources(): Promise<KnowledgeSource[]> {
  if (API_MODE === "live") {
    return http<KnowledgeSource[]>("/api/v1/knowledge/sources");
  }
  const { MOCK_KNOWLEDGE_SOURCES } = await import("@/lib/mock/knowledge");
  return simulate(() => MOCK_KNOWLEDGE_SOURCES);
}

export async function queryKnowledge(query: string): Promise<KnowledgeAnswer> {
  if (API_MODE === "live") {
    return http<KnowledgeAnswer>("/api/v1/knowledge/query", {
      method: "POST",
      body: { query },
    });
  }
  const { mockKnowledgeQuery } = await import("@/lib/mock/knowledge");
  return simulate(() => mockKnowledgeQuery(query), 700);
}
