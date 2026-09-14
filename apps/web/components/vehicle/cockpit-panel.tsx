"use client";

import { Minus, Plus } from "lucide-react";
import * as React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useVehicleStore } from "@/lib/store/vehicle-store";
import { AnimatedNumber } from "@/components/vehicle/animated-number";
import type {
  AcStatus,
  HeadlightMode,
  SeatHeatLevel,
  WindowLevel,
} from "@/types/vehicle";

function CoffeeSection({ label }: { label: string }) {
  return (
    <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
      {label}
    </span>
  );
}

function Segmented<T extends string | number>({
  value,
  options,
  onChange,
  disabled,
  getOptionLabel,
}: {
  value: T;
  options: T[];
  onChange: (v: T) => void;
  disabled?: boolean;
  getOptionLabel?: (value: T) => string;
}) {
  return (
    <div
      className="grid gap-1"
      style={{ gridTemplateColumns: `repeat(${options.length}, 1fr)` }}
      role="group"
    >
      {options.map((opt) => {
        const active = opt === value;
        return (
          <button
            key={String(opt)}
            type="button"
            disabled={disabled}
            onClick={() => onChange(opt)}
            className={cn(
              "rounded-md border px-2 py-1.5 text-xs font-medium transition-colors",
              active
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-muted/40 text-muted-foreground hover:text-foreground",
              disabled && "cursor-not-allowed opacity-50",
            )}
            aria-pressed={active}
          >
            {getOptionLabel ? getOptionLabel(opt) : String(opt)}
          </button>
        );
      })}
    </div>
  );
}

export function CockpitPanel() {
  const vehicle = useVehicleStore((s) => s.vehicle);
  const apply = useVehicleStore((s) => s.apply);

  const tempButton = (
    zone: "driver" | "passenger",
    delta: number,
  ) =>
    apply({
      kind: "climate",
      zone,
      value: Math.min(
        30,
        Math.max(
          16,
          (zone === "driver"
            ? vehicle.driverTemperature
            : vehicle.passengerTemperature) + delta,
        ),
      ),
    });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">手动控制</CardTitle>
        <p className="text-xs text-muted-foreground">
          手动操作与 AI 智能体共同控制同一车辆状态。
        </p>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* AC */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <CoffeeSection label="空调温控" />
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">AC</span>
              <Segmented<AcStatus>
                value={vehicle.acStatus}
                options={["OFF", "ON"]}
                getOptionLabel={(v) => (v === "ON" ? "开启" : "关闭")}
                onChange={(v) => apply({ kind: "ac", value: v })}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {(["driver", "passenger"] as const).map((zone) => {
              const temp =
                zone === "driver"
                  ? vehicle.driverTemperature
                  : vehicle.passengerTemperature;
              return (
                <div
                  key={zone}
                  className="flex items-center justify-between rounded-lg border bg-muted/30 px-3 py-2"
                >
                  <div>
                    <p className="text-[11px] text-muted-foreground capitalize">
                      {zone === "driver" ? "主驾" : "副驾"}
                    </p>
                    <p className="text-lg font-semibold tabular-nums">
                      <AnimatedNumber value={temp} suffix="°C" />
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => tempButton(zone, -1)}
                      aria-label={`降低${zone === "driver" ? "主驾" : "副驾"}温度`}
                    >
                      <Minus className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => tempButton(zone, 1)}
                      aria-label={`升高${zone === "driver" ? "主驾" : "副驾"}温度`}
                    >
                      <Plus className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Seats */}
        <div className="space-y-2">
          <CoffeeSection label="座椅加热" />
          <div className="grid grid-cols-2 gap-3">
            {(["driver", "passenger"] as const).map((zone) => (
              <div key={zone}>
                <p className="mb-1 text-[11px] text-muted-foreground capitalize">
                  {zone === "driver" ? "主驾" : "副驾"} · 挡位{" "}
                  {zone === "driver"
                    ? vehicle.driverSeatHeat
                    : vehicle.passengerSeatHeat}
                </p>
                <Segmented<SeatHeatLevel>
                  value={
                    zone === "driver"
                      ? vehicle.driverSeatHeat
                      : vehicle.passengerSeatHeat
                  }
                  options={[0, 1, 2, 3]}
                  onChange={(v) =>
                    apply({ kind: "seat_heat", zone, value: v })
                  }
                />
              </div>
            ))}
          </div>
        </div>

        {/* Windows */}
        <div className="space-y-2">
          <CoffeeSection label="车窗" />
          <div className="grid grid-cols-2 gap-3">
            {(["FL", "FR"] as const).map((zone) => (
              <div key={zone}>
                <p className="mb-1 text-[11px] text-muted-foreground">
                  {zone === "FL" ? "左前车窗" : "右前车窗"} ·{" "}
                  {zone === "FL" ? vehicle.windowFL : vehicle.windowFR}%
                </p>
                <Segmented<WindowLevel>
                  value={zone === "FL" ? vehicle.windowFL : vehicle.windowFR}
                  options={[0, 25, 50, 75, 100]}
                  onChange={(v) => apply({ kind: "window", zone, value: v })}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Headlights */}
        <div className="space-y-2">
          <CoffeeSection label="外部灯光" />
          <Segmented<HeadlightMode>
            value={vehicle.headlight}
            options={["OFF", "AUTO", "ON"]}
            getOptionLabel={(v) => ({ OFF: "关闭", AUTO: "自动", ON: "开启" })[v]}
            onChange={(v) => apply({ kind: "headlight", value: v })}
          />
        </div>
      </CardContent>
    </Card>
  );
}
