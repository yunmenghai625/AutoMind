"use client";

import { Flame, Gauge, Sparkles, Thermometer, Zap } from "lucide-react";
import * as React from "react";
import { MockBadge } from "@/components/common/mock-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import { getPreferences, savePreferences, deletePreferences } from "@/lib/api/preferenceApi";
import { hasAccessToken } from "@/lib/api/identity";
import { IS_MOCK } from "@/lib/config";
import { usePreferencesStore } from "@/lib/store/preferences-store";
import { cn } from "@/lib/utils";
import type { PreferencesState } from "@/types/preferences";

const DRIVING_MODES: PreferencesState["preferredDrivingMode"][] = ["Comfort", "Sport", "Eco"];
const OPTION_LABELS: Record<string, string> = {
  Comfort: "舒适",
  Sport: "运动",
  Eco: "节能",
};

function SegmentGroup<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: readonly T[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {options.map((opt) => (
          <button
            key={opt}
            type="button"
            aria-pressed={value === opt}
            onClick={() => onChange(opt)}
            className={cn(
              "rounded-md border px-3 py-1.5 text-xs font-medium transition-colors",
              value === opt
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-muted-foreground hover:border-primary/40 hover:text-foreground",
            )}
          >
            {OPTION_LABELS[opt] ?? opt}
          </button>
        ))}
      </div>
    </div>
  );
}

export function AiPreferences() {
  const preferences = usePreferencesStore((s) => s.preferences);
  const update = usePreferencesStore((s) => s.update);
  const [registered, setRegistered] = React.useState(false);
  const [syncState, setSyncState] = React.useState<"local" | "saved" | "error">("local");
  const timerRef = React.useRef<number | null>(null);

  React.useEffect(() => {
    usePreferencesStore.getState().hydrate();
    const canSync = !IS_MOCK && hasAccessToken();
    setRegistered(canSync);
    if (canSync) {
      void getPreferences()
        .then((remote) => {
          update(remote);
          setSyncState("saved");
        })
        .catch(() => setSyncState("error"));
    }
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, []);

  const change = (patch: Partial<PreferencesState>) => {
    const next = { ...usePreferencesStore.getState().preferences, ...patch };
    update(patch);
    if (!registered) return;
    if (timerRef.current) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => {
      void savePreferences(next)
        .then(() => setSyncState("saved"))
        .catch(() => setSyncState("error"));
    }, 350);
  };

  const removeMemory = async () => {
    if (!registered) return;
    try {
      await deletePreferences();
      update({
        preferredTemperature: 23,
        seatHeatingLevel: 1,
        preferredChargingLimit: 80,
        preferredDrivingMode: "Comfort",
      });
      setSyncState("saved");
    } catch {
      setSyncState("error");
    }
  };

  return (
    <Card>
      <CardHeader className="border-b py-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Sparkles className="h-4 w-4 text-primary" />
          AI 偏好设置
          <span className="ml-auto">
            {IS_MOCK && <MockBadge />}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5 pt-4">
        <p className="text-xs text-muted-foreground">
          助手只会记住你在此处明确设置的偏好。
          {registered ? "你可以随时修改或删除。" : "登录后可在不同设备间同步。"}
        </p>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Thermometer className="h-3.5 w-3.5" />
              偏好温度
            </p>
            <Badge variant="outline" className="tabular-nums text-[11px]">
              {preferences.preferredTemperature}°C
            </Badge>
          </div>
          <Slider
            value={preferences.preferredTemperature}
            min={16}
            max={30}
            step={1}
            onValueChange={(v) => change({ preferredTemperature: v })}
            aria-label="偏好温度"
          />
          <p className="text-[11px] text-muted-foreground/70">
            AI 调节空调时默认采用的目标温度。
          </p>
        </div>

        <SegmentGroup
          label="座椅加热挡位"
          value={String(preferences.seatHeatingLevel)}
          options={["0", "1", "2", "3"] as const}
          onChange={(v) => change({ seatHeatingLevel: Number(v) as PreferencesState["seatHeatingLevel"] })}
        />

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Zap className="h-3.5 w-3.5" />
              偏好充电上限
            </p>
            <Badge variant="outline" className="tabular-nums text-[11px]">
              {preferences.preferredChargingLimit}%
            </Badge>
          </div>
          <Slider
            value={preferences.preferredChargingLimit}
            min={50}
            max={100}
            step={5}
            onValueChange={(v) => change({ preferredChargingLimit: v })}
            aria-label="偏好充电上限"
          />
        </div>

        <div className="flex items-start gap-2">
          <Gauge className="mt-0.5 h-3.5 w-3.5 text-muted-foreground" />
          <SegmentGroup
            label="偏好驾驶模式"
            value={preferences.preferredDrivingMode}
            options={DRIVING_MODES}
            onChange={(v) => change({ preferredDrivingMode: v })}
          />
        </div>

        <div className="flex items-center gap-1.5 rounded-lg bg-success/10 px-3 py-2 text-[11px] text-success">
          <Flame className="h-3.5 w-3.5" />
          {registered
            ? syncState === "error" ? "同步失败 · 已保留本地副本" : "偏好已同步到你的账户"
            : "偏好已保存在本地 · 下次会话自动应用"}
        </div>
        {registered && (
          <Button type="button" variant="outline" size="sm" onClick={() => void removeMemory()}>
            删除偏好记忆
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
