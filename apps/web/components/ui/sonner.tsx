"use client";

import * as React from "react";
import { create } from "zustand";
import { CheckCircle2, AlertTriangle, XCircle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastVariant = "default" | "success" | "warning" | "error" | "info";

interface Toast {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
}

interface ToastStore {
  toasts: Toast[];
  addToast: (t: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (t) => {
    const id = Math.random().toString(36).slice(2);
    set((s) => ({ toasts: [...s.toasts, { ...t, id }] }));
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((x) => x.id !== id) }));
    }, 4500);
  },
  removeToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((x) => x.id !== id) })),
}));

type ToastFn = (
  title: string,
  description?: string,
) => void;

export const toast: Record<ToastVariant, ToastFn> = {
  default: (t, d) => useToastStore.getState().addToast({ title: t, description: d, variant: "default" }),
  success: (t, d) => useToastStore.getState().addToast({ title: t, description: d, variant: "success" }),
  warning: (t, d) => useToastStore.getState().addToast({ title: t, description: d, variant: "warning" }),
  error: (t, d) => useToastStore.getState().addToast({ title: t, description: d, variant: "error" }),
  info: (t, d) => useToastStore.getState().addToast({ title: t, description: d, variant: "info" }),
};

const icons: Record<ToastVariant, React.ReactNode> = {
  default: <Info className="h-4 w-4" />,
  success: <CheckCircle2 className="h-4 w-4 text-success" />,
  warning: <AlertTriangle className="h-4 w-4 text-warning" />,
  error: <XCircle className="h-4 w-4 text-destructive" />,
  info: <Info className="h-4 w-4 text-accent" />,
};

export function Toaster() {
  const toasts = useToastStore((s) => s.toasts);
  const removeToast = useToastStore((s) => s.removeToast);

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-full max-w-sm flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            "pointer-events-auto flex items-start gap-3 rounded-lg border bg-popover p-3.5 shadow-lg",
            t.variant === "error" && "border-destructive/30",
            t.variant === "warning" && "border-warning/30",
            t.variant === "success" && "border-success/30",
          )}
          role="status"
        >
          {icons[t.variant]}
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium">{t.title}</p>
            {t.description && (
              <p className="mt-0.5 text-xs text-muted-foreground">
                {t.description}
              </p>
            )}
          </div>
          <button
            onClick={() => removeToast(t.id)}
            aria-label="关闭通知"
            className="text-muted-foreground transition hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
