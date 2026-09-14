"use client";

import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";

import { AssistantPanel } from "@/components/agent/assistant";
import { MockBadge } from "@/components/common/mock-badge";
import { PageHeader } from "@/components/common/page-header";
import { Button } from "@/components/ui/button";
import { CockpitPanel } from "@/components/vehicle/cockpit-panel";
import { AiThemeDialog } from "@/features/cockpit/ai-theme-dialog";
import { VehicleTwinCard } from "@/features/cockpit/vehicle-twin-card";
import { getVehicleState } from "@/lib/api/vehicleApi";
import { useVehicleStore } from "@/lib/store/vehicle-store";
import type { CockpitTheme } from "@/types/aigc";

export function CockpitView() {
  const setVehicle = useVehicleStore((state) => state.setVehicle);
  const [themeOpen, setThemeOpen] = useState(false);
  const [appliedTheme, setAppliedTheme] = useState<CockpitTheme | null>(null);

  useEffect(() => {
    let alive = true;
    void getVehicleState().then((state) => {
      if (alive) setVehicle(state);
    });
    return () => {
      alive = false;
    };
  }, [setVehicle]);

  const surfaceStyle = appliedTheme
    ? {
        backgroundColor: appliedTheme.theme_spec.ambient_color,
        backgroundImage: appliedTheme.wallpaper_url
          ? `linear-gradient(rgba(5,10,20,.78), rgba(5,10,20,.88)), url(${appliedTheme.wallpaper_url})`
          : `radial-gradient(circle at 85% 15%, ${appliedTheme.theme_spec.ambient_color}88, transparent 35%)`,
      }
    : undefined;

  return (
    <div
      className="min-h-[calc(100vh-4rem)] bg-cover bg-fixed bg-center transition-all duration-700"
      style={surfaceStyle}
    >
      <div className="container mx-auto max-w-7xl px-4 py-6">
        <PageHeader
          title="Cockpit"
          badge={<MockBadge />}
          description="Live Vehicle Digital Twin and natural-language AI controls. AI Tool calls and manual controls mutate the same Vehicle State."
          actions={
            <Button onClick={() => setThemeOpen(true)}>
              <Sparkles /> AI Theme
            </Button>
          }
        />
        {appliedTheme && (
          <div className="mt-4 flex items-center gap-3 rounded-lg border border-white/15 bg-black/35 px-4 py-3 text-sm text-white backdrop-blur-md">
            <span
              className="h-3 w-3 rounded-full ring-2 ring-white/30"
              style={{
                backgroundColor: appliedTheme.theme_spec.ambient_color,
                opacity: Math.max(
                  0.25,
                  appliedTheme.theme_spec.ambient_brightness / 100,
                ),
              }}
            />
            已应用“{appliedTheme.theme_spec.name}” · 环境光{" "}
            {appliedTheme.theme_spec.ambient_brightness}% ·{" "}
            {appliedTheme.theme_spec.temperature}°C
          </div>
        )}
        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,11fr)_minmax(0,9fr)]">
          <div className="space-y-6">
            <VehicleTwinCard />
            <CockpitPanel />
          </div>
          <div className="lg:sticky lg:top-20 lg:self-start">
            <div className="lg:max-h-[calc(100vh-110px)]">
              <AssistantPanel />
            </div>
          </div>
        </div>
        <AiThemeDialog
          open={themeOpen}
          onOpenChange={setThemeOpen}
          onApplied={setAppliedTheme}
        />
      </div>
    </div>
  );
}
