import type { Metadata } from "next";
import { StatusView } from "@/features/status/status-view";

export const metadata: Metadata = {
  title: "System Status — AutoMind",
  description: "Live status of the AutoMind platform services.",
};

export default function StatusPage() {
  return <StatusView />;
}
