import type { Metadata } from "next";
import { AdminView } from "@/features/admin/admin-view";

export const metadata: Metadata = {
  title: "Admin",
  description:
    "Platform observability dashboard — agent success rate, latency, tool usage and cost.",
};

export default function AdminPage() {
  return <AdminView />;
}
