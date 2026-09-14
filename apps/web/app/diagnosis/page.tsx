import type { Metadata } from "next";
import { DiagnosisView } from "@/features/diagnosis/diagnosis-view";

export const metadata: Metadata = {
  title: "Diagnosis",
  description:
    "Multimodal fault diagnosis from dashboard photos — Vision Model, warning detection and knowledge retrieval.",
};

export default function DiagnosisPage() {
  return <DiagnosisView />;
}
