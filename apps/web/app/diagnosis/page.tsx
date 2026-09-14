import type { Metadata } from "next";
import { DiagnosisView } from "@/features/diagnosis/diagnosis-view";

export const metadata: Metadata = {
  title: "智能诊断",
  description:
    "通过仪表照片进行多模态故障诊断，包括视觉识别、警告检测与知识检索。",
};

export default function DiagnosisPage() {
  return <DiagnosisView />;
}
