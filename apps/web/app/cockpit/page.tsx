import type { Metadata } from "next";
import { CockpitView } from "@/features/cockpit/cockpit-view";

export const metadata: Metadata = {
  title: "Cockpit",
  description:
    "Natural-language vehicle control, Vehicle Digital Twin and cockpit manual controls.",
};

export default function CockpitPage() {
  return <CockpitView />;
}
