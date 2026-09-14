import type { Metadata } from "next";
import { KnowledgeView } from "@/features/knowledge/knowledge-view";

export const metadata: Metadata = {
  title: "汽车知识库",
  description:
    "提供引用来源和检索详情的汽车知识 RAG。",
};

export default function KnowledgePage() {
  return <KnowledgeView />;
}
