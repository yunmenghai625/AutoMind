/** Automotive Knowledge RAG domain types.
 * Mirror of future POST /api/v1/knowledge/query contract.
 */

export interface KnowledgeSource {
  id: string;
  title: string;
  description: string;
  documents: number;
  status: "indexed" | "syncing";
  updatedAt: string;
}

export interface Citation {
  source: string;
  chapter?: string;
  page?: number;
  snippet: string;
}

export interface RetrievalDetails {
  originalQuery: string;
  rewrittenQuery: string;
  retrievedDocuments: number;
  rerankerEnabled: boolean;
  vectorSearchMs: number;
  rerankMs: number;
}

export interface KnowledgeAnswer {
  answer: string;
  citations: Citation[];
  retrieval: RetrievalDetails;
}

export interface KnowledgeMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  at: string;
  meta?: {
    citations?: Citation[];
    retrieval?: RetrievalDetails;
  };
}
