"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface SliderProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number;
  min: number;
  max: number;
  step?: number;
  onValueChange?: (value: number) => void;
  disabled?: boolean;
}

const Slider = React.forwardRef<HTMLDivElement, SliderProps>(
  ({ className, value, min, max, step = 1, onValueChange, disabled, ...props }, ref) => {
    const ratio = ((value - min) / (max - min)) * 100;

    const handlePointer = (clientX: number) => {
      if (disabled) return;
      const el = ref && typeof ref !== "function" ? ref.current : null;
      const target = el ?? document.querySelector(`[data-slider="${props.id ?? ""}"]`);
      const rect = (target as HTMLElement)?.getBoundingClientRect();
      if (!rect) return;
      const pct = Math.min(Math.max((clientX - rect.left) / rect.width, 0), 1);
      const raw = min + pct * (max - min);
      const stepped = Math.round(raw / step) * step;
      onValueChange?.(Math.min(Math.max(stepped, min), max));
    };

    return (
      <div
        ref={ref}
        data-slider={props.id ?? ""}
        className={cn(
          "relative flex h-5 w-full touch-none select-none items-center",
          disabled && "opacity-50",
          className,
        )}
        onPointerDown={(e) => {
          (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
          handlePointer(e.clientX);
        }}
        onPointerMove={(e) => {
          if (e.buttons === 1) handlePointer(e.clientX);
        }}
        {...props}
      >
        <div className="relative h-1.5 w-full grow overflow-hidden rounded-full bg-muted">
          <div
            className="absolute inset-y-0 left-0 rounded-full bg-primary"
            style={{ width: `${ratio}%` }}
          />
        </div>
        <div
          className="absolute h-4 w-4 rounded-full border border-primary/40 bg-background shadow transition hover:bg-primary/10"
          style={{ left: `calc(${ratio}% - 8px)` }}
        />
      </div>
    );
  },
);
Slider.displayName = "Slider";

export { Slider };
