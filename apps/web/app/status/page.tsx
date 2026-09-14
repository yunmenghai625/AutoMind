import type { Metadata } from "next";
import { StatusView } from "@/features/status/status-view";

export const metadata: Metadata = {
  title: "系统状态 — AutoMind",
  description: "实时查看 AutoMind 平台服务状态。",
};

export default function StatusPage() {
  return <StatusView />;
}
