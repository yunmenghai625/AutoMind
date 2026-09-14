import type { Metadata } from "next";
import { AdminView } from "@/features/admin/admin-view";

export const metadata: Metadata = {
  title: "运营管理",
  description:
    "平台可观测性看板，包括智能体成功率、延迟、工具调用和成本。",
};

export default function AdminPage() {
  return <AdminView />;
}
