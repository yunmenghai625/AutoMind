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
import { IS_MOCK } from "@/lib/config";
import { useVehicleStore } from "@/lib/store/vehicle-store";
import type { CockpitTheme } from "@/types/aigc";

export function CockpitView() {
  const setVehicle = useVehicleStore((state) => state.setVehicle);
  const [themeOpen, setThemeOpen] = useState(false);
  const [appliedTheme, setAppliedTheme] = useState<CockpitTheme | null>(null);
  const [vehicleStatus, setVehicleStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );

  useEffect(() => {
    let alive = true;
    void getVehicleState()
      .then((state) => {
        if (alive) {
          setVehicle(state);
          setVehicleStatus("ready");
        }
      })
      .catch(() => {
        if (alive) setVehicleStatus("error");
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
          title="智能座舱"
          badge={IS_MOCK ? <MockBadge /> : undefined}
          description="实时车辆数字孪生与自然语言 AI 控制。智能体工具调用和手动操作共同作用于同一车辆状态。"
          actions={
            <Button
              onClick={() => setThemeOpen(true)}
              disabled={vehicleStatus !== "ready"}
            >
              <Sparkles /> AI 座舱主题
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
        {vehicleStatus === "loading" && (
          <div className="mt-6 h-80 animate-pulse rounded-xl bg-muted/50" />
        )}
        {vehicleStatus === "error" && (
          <div className="mt-6 rounded-xl border border-destructive/40 bg-destructive/5 p-6 text-sm text-destructive">
            无法读取实时车辆状态。为避免展示过期或模拟数据，车辆面板与控制功能已暂停。
          </div>
        )}
        {vehicleStatus === "ready" && (
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
        )}
        <AiThemeDialog
          open={themeOpen}
          onOpenChange={setThemeOpen}
          onApplied={setAppliedTheme}
        />
      </div>
    </div>
  );
}
