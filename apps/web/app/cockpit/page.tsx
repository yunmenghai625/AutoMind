import type { Metadata } from "next";
import { CockpitView } from "@/features/cockpit/cockpit-view";

export const metadata: Metadata = {
  title: "智能座舱",
  description:
    "通过自然语言和手动控制操作车辆数字孪生。",
};

export default function CockpitPage() {
  return <CockpitView />;
}
