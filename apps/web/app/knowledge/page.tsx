import type { Metadata } from "next";
import { KnowledgeView } from "@/features/knowledge/knowledge-view";

export const metadata: Metadata = {
  title: "Knowledge",
  description:
    "Automotive knowledge RAG with citations and retrieval details.",
};

export default function KnowledgePage() {
  return <KnowledgeView />;
}
