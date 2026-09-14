import type { Metadata } from "next";
import { ArchitectureView } from "@/features/architecture/architecture-view";

export const metadata: Metadata = {
  title: "技术架构 — AutoMind",
  description: "AutoMind 平台的系统与智能体架构。",
};

export default function ArchitecturePage() {
  return <ArchitectureView />;
}
