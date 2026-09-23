"use client";

import * as React from "react";
import { useReportWebVitals } from "next/web-vitals";
import { API_BASE_URL, API_MODE } from "@/lib/config";

function report(path: string, payload: Record<string, unknown>) {
  if (API_MODE !== "live") return;
  void fetch(`${API_BASE_URL}/api/v1/telemetry/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    keepalive: true,
  }).catch(() => undefined);
}

function currentRoute() {
  return window.location.pathname.slice(0, 200) || "/";
}

export function ClientObservability() {
  useReportWebVitals((metric) => {
    report("web-vitals", {
      name: metric.name,
      value: metric.value,
      rating: metric.rating,
      route: currentRoute(),
    });
  });

  React.useEffect(() => {
    const onError = (event: ErrorEvent) => {
      report("frontend-errors", {
        source: "window.error",
        name: event.error instanceof Error ? event.error.name : "Error",
        route: currentRoute(),
      });
    };
    const onUnhandledRejection = (event: PromiseRejectionEvent) => {
      report("frontend-errors", {
        source: "unhandledrejection",
        name: event.reason instanceof Error ? event.reason.name : "UnhandledRejection",
        route: currentRoute(),
      });
    };
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onUnhandledRejection);
    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onUnhandledRejection);
    };
  }, []);

  return null;
}
