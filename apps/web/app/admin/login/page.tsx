import type { Metadata } from "next";
import { AdminLoginView } from "@/features/admin/admin-login-view";

export const metadata: Metadata = {
  title: "管理员登录",
  description: "登录 AutoMind 运营管理看板。",
};

export default function AdminLoginPage() {
  return <AdminLoginView />;
}
