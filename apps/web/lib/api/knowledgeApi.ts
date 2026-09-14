import { http, simulate } from "@/lib/api/apiClient";
import { MOCK_KNOWLEDGE_SOURCES, mockKnowledgeQuery } from "@/lib/mock/knowledge";
import type { KnowledgeAnswer, KnowledgeSource } from "@/types/knowledge";

/**
 * Knowledge RAG services.
 * POST /api/v1/knowledge/query (future backend).
 */

export async function getKnowledgeSources(): Promise<KnowledgeSource[]> {
  return simulate(() => MOCK_KNOWLEDGE_SOURCES);
}

export async function queryKnowledge(query: string): Promise<KnowledgeAnswer> {
  return simulate(() => mockKnowledgeQuery(query), 700);
}
