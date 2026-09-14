import type { Metadata } from "next";
import { ArchitectureView } from "@/features/architecture/architecture-view";

export const metadata: Metadata = {
  title: "Architecture — AutoMind",
  description: "System and agent architecture of the AutoMind platform.",
};

export default function ArchitecturePage() {
  return <ArchitectureView />;
}
