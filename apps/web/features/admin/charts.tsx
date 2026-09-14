"use client";

import * as React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function toPoints(values: number[], w: number, h: number, pad = 2) {
  if (values.length <= 1) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return values
    .map((v, i) => {
      const x = pad + (i / (values.length - 1)) * (w - pad * 2);
      const y = h - pad - ((v - min) / span) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

/** Inline SVG sparkline with gradient area fill (used inside KPI cards). */
export function Sparkline({
  values,
  className,
  width = 120,
  height = 36,
}: {
  values: number[];
  className?: string;
  width?: number;
  height?: number;
}) {
  const id = React.useId();
  const points = toPoints(values, width, height);
  if (!points) return null;
  const area = `0,${height} ${points} ${width},${height}`;
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      style={{ width, height }}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.35" />
          <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={area} fill={`url(#${id})`} />
      <polyline
        points={points}
        fill="none"
        stroke="hsl(var(--primary))"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

const AXIS_STYLE = { fontSize: 11, fill: "hsl(var(--muted-foreground))" };
const GRID_STROKE = "hsl(var(--border))";

function ChartTooltip() {
  return (
    <Tooltip
      cursor={{ fill: "hsl(var(--muted) / 0.4)" }}
      contentStyle={{
        background: "hsl(var(--popover))",
        border: "1px solid hsl(var(--border))",
        borderRadius: 10,
        fontSize: 12,
        color: "hsl(var(--popover-foreground))",
      }}
      labelStyle={{ color: "hsl(var(--muted-foreground))" }}
      formatter={(value) => [String(value), undefined]}
    />
  );
}

/** Recharts bar chart. Used for Request Traffic / Agent Success. */
export function VerticalBars({
  labels,
  values,
  height = 110,
}: {
  labels: string[];
  values: number[];
  height?: number;
}) {
  const data = labels.map((label, i) => ({ label, value: values[i] }));
  const skip = Math.max(1, Math.floor(labels.length / 7));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: -22 }}>
        <CartesianGrid stroke={GRID_STROKE} strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="label"
          tick={AXIS_STYLE}
          tickLine={false}
          axisLine={{ stroke: GRID_STROKE }}
          interval={skip}
        />
        <YAxis tick={AXIS_STYLE} tickLine={false} axisLine={false} width={34} />
        <ChartTooltip />
        <Bar dataKey="value" fill="hsl(var(--primary))" radius={[3, 3, 0, 0]} maxBarSize={26} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Recharts multi-series line chart. Used for latency / success rate. */
export function MultiLines({
  labels,
  series,
  height = 150,
}: {
  labels: string[];
  series: { name: string; color: string; values: number[] }[];
  height?: number;
}) {
  const data = labels.map((label, i) => {
    const row: Record<string, string | number> = { label };
    for (const s of series) row[s.name] = s.values[i];
    return row;
  });
  const skip = Math.max(1, Math.floor(labels.length / 6));
  return (
    <div>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 4, right: 6, bottom: 0, left: -24 }}>
          <CartesianGrid stroke={GRID_STROKE} strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="label"
            tick={AXIS_STYLE}
            tickLine={false}
            axisLine={{ stroke: GRID_STROKE }}
            interval={skip}
          />
          <YAxis tick={AXIS_STYLE} tickLine={false} axisLine={false} width={40} />
          <ChartTooltip />
          {series.map((s) => (
            <Line
              key={s.name}
              type="monotone"
              dataKey={s.name}
              stroke={s.color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 3 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      <div className="mt-1 flex flex-wrap gap-2">
        {series.map((s) => (
          <span key={s.name} className="flex items-center gap-1 text-xs text-muted-foreground">
            <span className="h-2 w-2 rounded-full" style={{ background: s.color }} />
            {s.name}
          </span>
        ))}
      </div>
    </div>
  );
}

/** Recharts horizontal bar chart for agent usage. */
export function UsageBars({
  data,
  height = 150,
}: {
  data: { label: string; value: number }[];
  height?: number;
}) {
  const rows = data.map((d) => ({ name: d.label, calls: d.value }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={rows} layout="vertical" margin={{ top: 0, right: 18, bottom: 0, left: 8 }}>
        <CartesianGrid stroke={GRID_STROKE} strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" tick={AXIS_STYLE} tickLine={false} axisLine={false} />
        <YAxis
          type="category"
          dataKey="name"
          tick={AXIS_STYLE}
          tickLine={false}
          axisLine={false}
          width={86}
        />
        <ChartTooltip />
        <Bar dataKey="calls" fill="hsl(var(--primary))" radius={[0, 3, 3, 0]} maxBarSize={16} />
      </BarChart>
    </ResponsiveContainer>
  );
}
