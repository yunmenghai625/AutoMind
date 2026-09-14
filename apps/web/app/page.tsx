import type { Metadata } from "next";
import { HomeView } from "@/features/home/home-view";

export const metadata: Metadata = {
  title: "AutoMind — 汽车智能平台",
  description:
    "集智能座舱、车辆数字孪生、汽车知识 RAG 与多模态诊断于一体。",
};

export default function HomePage() {
  return <HomeView />;
}
