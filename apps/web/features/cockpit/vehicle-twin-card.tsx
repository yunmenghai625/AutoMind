"use client";

import { Battery, Gauge, Route, Settings2 } from "lucide-react";
import * as React from "react";
import { AnimatedNumber, ReadoutItem } from "@/components/vehicle/animated-number";
import { VehicleSvg } from "@/components/vehicle/vehicle-svg";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useVehicleStore } from "@/lib/store/vehicle-store";
import { MockBadge } from "@/components/common/mock-badge";

export function VehicleTwinCard() {
  const vehicle = useVehicleStore((s) => s.vehicle);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0 py-3">
        <CardTitle className="text-base">Vehicle Digital Twin</CardTitle>
        <MockBadge />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_170px]">
          {/* Car + live badges */}
          <div className="relative">
            <VehicleSvg vehicle={vehicle} />
            <div className="absolute left-1/2 top-1/2 z-10 -translate-x-1/2 -translate-y-1/2 sm:hidden" />
            <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
              <Badge
                variant="outline"
                className={
                  vehicle.acStatus === "ON"
                    ? "text-primary"
                    : "text-muted-foreground"
                }
              >
                AC {vehicle.acStatus}
              </Badge>
              <Badge variant="outline" className="text-muted-foreground">
                {vehicle.chargeStatus === "IDLE"
                  ? `Charging ${vehicle.chargeStatus.toLowerCase()}`
                  : vehicle.chargeStatus}
              </Badge>
              <Badge variant="outline" className="text-muted-foreground">
                Headlight {vehicle.headlight}
              </Badge>
            </div>
          </div>

          {/* Key readouts */}
          <div className="grid grid-cols-2 gap-2 lg:grid-cols-1">
            <ReadoutItem
              label="Speed"
              icon={<Gauge className="h-3 w-3" />}
              value={
                <span className="text-lg font-bold tabular-nums">
                  <AnimatedNumber value={vehicle.speed} suffix=" km/h" />
                </span>
              }
              hint={vehicle.gear === "P" ? "Parked" : `Gear ${vehicle.gear}`}
            />
            <ReadoutItem
              label="Battery"
              icon={<Battery className="h-3 w-3" />}
              value={
                <span className="text-lg font-bold tabular-nums">
                  <AnimatedNumber value={vehicle.batterySoc} suffix="%" />
                </span>
              }
              hint={vehicle.chargeStatus.toLowerCase()}
            />
            <ReadoutItem
              label="Range"
              icon={<Route className="h-3 w-3" />}
              value={
                <span className="text-lg font-bold tabular-nums">
                  <AnimatedNumber value={vehicle.rangeKm} suffix=" km" />
                </span>
              }
              hint="Estimated"
            />
            <ReadoutItem
              label="Gear"
              icon={<Settings2 className="h-3 w-3" />}
              value={<span className="text-lg font-bold">{vehicle.gear}</span>}
              hint={vehicle.speed > 0 ? "In motion" : "Stationary"}
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Battery Level</span>
            <span className="font-medium tabular-nums">{vehicle.batterySoc}%</span>
          </div>
          <Progress value={vehicle.batterySoc} className="h-2" />
        </div>
      </CardContent>
    </Card>
  );
}
