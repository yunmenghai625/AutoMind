"use client";

import { motion } from "framer-motion";
import type { VehicleState } from "@/types/vehicle";

/**
 * Top-view abstract vehicle SVG (No real OEM brand).
 * Every interactive part is driven by the shared VehicleState:
 * windows open/close, headlights, seat heating, lights.
 */

const BODY = "M210,30 C150,30 128,60 128,118 L128,222 C128,280 150,300 210,300 L390,300 C450,300 472,280 472,222 L472,118 C472,60 450,30 390,30 Z";
const WINDSCREEN = "M232,80 L368,80 L348,116 L252,116 Z";

function Wheel({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <rect x={x} y={y} width={20} height={84} rx={10} fill="hsl(220 14% 12%)" stroke="hsl(218 14% 22%)" />
      <rect x={x + 7} y={y + 14} width={6} height={56} rx={3} fill="hsl(220 14% 22%)" />
    </g>
  );
}

interface SeatProps {
  x: number;
  y: number;
  heatLevel: number;
  label: string;
}

function HeatSeat({ x, y, heatLevel, label }: SeatProps) {
  const colors = [
    "hsl(218 10% 22%)",
    "hsl(38 90% 45%)",
    "hsl(24 90% 48%)",
    "hsl(0 74% 48%)",
  ];
  const fill = colors[Math.min(heatLevel, 3)];
  return (
    <g>
      <motion.rect
        x={x}
        y={y}
        width={64}
        height={46}
        rx={10}
        animate={{ fill }}
        transition={{ duration: 0.6 }}
        stroke={heatLevel > 0 ? "hsl(35 92% 50% / 0.5)" : "hsl(218 14% 25%)"}
        strokeWidth={1}
      />
      <rect x={x + 14} y={y - 16} width={36} height={20} rx={8} fill={fill} opacity={0.8} />
      <text x={x + 32} y={y + 27} textAnchor="middle" fontSize="9" fill="hsl(210 20% 92%)" fontWeight={500}>
        {label} · {heatLevel}
      </text>
    </g>
  );
}

interface VehicleSvgProps {
  vehicle: VehicleState;
}

export function VehicleSvg({ vehicle }: VehicleSvgProps) {
  // Window glass heights (percent of full glass that remains shown)
  const glassRatio = (level: number) => 1 - level / 100;
  const flH = 74 * glassRatio(vehicle.windowFL);
  const frH = 74 * glassRatio(vehicle.windowFR);
  const glassY = 128;
  const headlightsOn =
    vehicle.headlight === "ON" ||
    (vehicle.headlight === "AUTO" &&
      (vehicle.speed > 0 || true));

  return (
    <svg
      viewBox="0 0 600 335"
      className="h-auto w-full max-w-[560px]"
      role="img"
      aria-label="AutoMind 演示车辆实时俯视图"
    >
      {/* Ground shadow */}
      <ellipse cx="300" cy="312" rx="210" ry="16" fill="hsl(220 17% 4%)" opacity="0.6" />

      {/* Headlights */}
      {headlightsOn && (
        <g fill="hsl(48 100% 70%)" opacity="0.9">
          <circle cx="216" cy="40" r="5" />
          <circle cx="384" cy="40" r="5" />
          <circle cx="216" cy="40" r="10" fill="none" stroke="hsl(48 100% 70%)" strokeWidth="1.5" opacity="0.5">
            <animate attributeName="r" values="10;14;10" dur="2s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.5;0.15;0.5" dur="2s" repeatCount="indefinite" />
          </circle>
          <circle cx="384" cy="40" r="10" fill="none" stroke="hsl(48 100% 70%)" strokeWidth="1.5" opacity="0.5">
            <animate attributeName="r" values="10;14;10" dur="2s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.5;0.15;0.5" dur="2s" repeatCount="indefinite" />
          </circle>
        </g>
      )}

      {/* Body */}
      <path d={BODY} fill="hsl(220 16% 14%)" stroke="hsl(218 14% 26%)" strokeWidth="2" />

      {/* Hood line */}
      <line x1="150" y1="96" x2="450" y2="96" stroke="hsl(218 14% 22%)" strokeWidth="1.5" />

      {/* Windshield */}
      <path d={WINDSCREEN} fill="hsl(200 30% 35% / 0.35)" stroke="hsl(199 95% 58% / 0.3)" strokeWidth="1" />

      {/* Roof */}
      <rect x="252" y="140" width="96" height="92" rx="12" fill="hsl(220 16% 17%)" stroke="hsl(218 14% 25%)" strokeWidth="1" />
      <rect x="272" y="152" width="56" height="56" rx="8" fill="hsl(220 16% 12%)" stroke="hsl(218 14% 24%)" strokeWidth="1" />

      {/* Seats */}
      <HeatSeat x={158} y={158} heatLevel={vehicle.driverSeatHeat} label="主驾" />
      <HeatSeat x={378} y={158} heatLevel={vehicle.passengerSeatHeat} label="副驾" />

      {/* Side windows (animated height = open level) */}
      <g>
        <motion.rect
          x={138}
          y={glassY}
          width={52}
          height={flH}
          rx={6}
          initial={false}
          animate={{ y: glassY + (74 - flH), height: flH }}
          transition={{ type: "spring", stiffness: 120, damping: 18 }}
          fill="hsl(199 95% 58% / 0.4)"
          stroke="hsl(199 95% 58% / 0.25)"
        />
        <motion.rect
          x={410}
          y={glassY}
          width={52}
          height={frH}
          rx={6}
          initial={false}
          animate={{ y: glassY + (74 - frH), height: frH }}
          transition={{ type: "spring", stiffness: 120, damping: 18 }}
          fill="hsl(199 95% 58% / 0.4)"
          stroke="hsl(199 95% 58% / 0.25)"
        />
      </g>

      {/* Rear light bar */}
      <rect x="210" y="306" width="180" height="6" rx="3" fill={vehicle.speed > 0 ? "hsl(0 74% 52% / 0.85)" : "hsl(0 74% 52% / 0.3)"} />

      {/* Brand mark (abstract) */}
      <circle cx="300" cy="314" r="5" fill="hsl(199 95% 58%)" />

      {/* Wheels */}
      <Wheel x={104} y={74} />
      <Wheel x={476} y={74} />
      <Wheel x={104} y={205} />
      <Wheel x={476} y={205} />
    </svg>
  );
}
