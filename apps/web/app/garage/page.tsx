import type { Metadata } from "next";
import { GarageView } from "@/features/garage/garage-view";

export const metadata: Metadata = {
  title: "我的车库",
  description: "查看车辆健康、电池状态、召回与保养提醒。",
};

export default function GaragePage() {
  return <GarageView />;
}
