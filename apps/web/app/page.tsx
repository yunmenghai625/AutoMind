import type { Metadata } from "next";
import { HomeView } from "@/features/home/home-view";

export const metadata: Metadata = {
  title: "AutoMind — AI Vehicle Platform",
  description:
    "AI Cockpit, Vehicle Digital Twin, automotive RAG and multimodal diagnosis for your car.",
};

export default function HomePage() {
  return <HomeView />;
}
