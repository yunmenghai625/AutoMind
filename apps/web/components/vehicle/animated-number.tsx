"use client";

import { animate, motion } from "framer-motion";
import * as React from "react";

interface AnimatedNumberProps {
  value: number;
  decimals?: number;
  suffix?: string;
  className?: string;
}

/** Smoothly animates to the latest numeric value (e.g. 22 -> 24 °C). */
export function AnimatedNumber({
  value,
  decimals = 0,
  suffix = "",
  className,
}: AnimatedNumberProps) {
  const ref = React.useRef<HTMLSpanElement>(null);
  const prev = React.useRef(value);

  React.useEffect(() => {
    const controls = animate(prev.current, value, {
      duration: 0.6,
      ease: "easeOut",
      onUpdate: (v) => {
        if (ref.current) {
          ref.current.textContent = `${v.toFixed(decimals)}${suffix}`;
        }
      },
    });
    prev.current = value;
    return () => controls.stop();
  }, [value, decimals, suffix]);

  React.useEffect(() => {
    if (ref.current) {
      ref.current.textContent = `${value.toFixed(decimals)}${suffix}`;
    }
  }, [decimals, suffix]);

  return <span ref={ref} className={className} />;
}

interface ReadoutItemProps {
  label: string;
  icon?: React.ReactNode;
  value: React.ReactNode;
  hint?: string;
}

export function ReadoutItem({ label, icon, value, hint }: ReadoutItemProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col gap-1 rounded-lg border bg-muted/40 px-3 py-2"
    >
      <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
        {icon}
        {label}
      </span>
      <span className="text-sm font-semibold tabular-nums text-foreground">
        {value}
      </span>
      {hint && <span className="text-[10px] text-muted-foreground">{hint}</span>}
    </motion.div>
  );
}
