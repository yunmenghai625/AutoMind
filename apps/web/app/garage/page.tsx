import type { Metadata } from "next";
import { GarageView } from "@/features/garage/garage-view";

export const metadata: Metadata = {
  title: "Garage",
  description: "Your connected vehicle — health, battery and service notifications.",
};

export default function GaragePage() {
  return <GarageView />;
}
