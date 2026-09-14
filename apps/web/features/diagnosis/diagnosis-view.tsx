"use client";

import { AlertTriangle, ArrowRight, ImagePlus, Loader2, RefreshCw, ScanSearch, Trash2 } from "lucide-react";
import * as React from "react";
import { PageHeader } from "@/components/common/page-header";
import { MockBadge } from "@/components/common/mock-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import { runDiagnosis } from "@/lib/api/diagnosisApi";
import { IS_MOCK } from "@/lib/config";
import type { DiagnosisResult } from "@/types/diagnosis";

const PIPELINE = [
  "Image Guard",
  "Compress & Store",
  "Vision Model",
  "Confidence Gate",
  "Knowledge Retrieval",
  "Risk Classification",
];

export function DiagnosisView() {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [preview, setPreview] = React.useState<string | null>(null);
  const [file, setFile] = React.useState<File | null>(null);
  const [fileName, setFileName] = React.useState<string | null>(null);
  const [phase, setPhase] = React.useState<
    "idle" | "loading" | "success" | "error"
  >("idle");
  const [result, setResult] = React.useState<DiagnosisResult | null>(null);
  const [dragOver, setDragOver] = React.useState(false);

  const onFile = (file: File | undefined) => {
    if (!file) return;
    if (!file.type.startsWith("image/")) return;
    if (preview) URL.revokeObjectURL(preview);
    setFile(file);
    setFileName(file.name);
    setPreview(URL.createObjectURL(file));
    setResult(null);
    setPhase("idle");
  };

  const analyze = async () => {
    if (!file || phase === "loading") return;
    setPhase("loading");
    try {
      const res = await runDiagnosis(file);
      setResult(res);
      setPhase("success");
    } catch {
      setPhase("error");
    }
  };

  const reset = () => {
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null);
    setFile(null);
    setFileName(null);
    setResult(null);
    setPhase("idle");
  };

  return (
    <div className="container mx-auto max-w-7xl px-4 py-6">
      <PageHeader
        title="Diagnosis"
        badge={IS_MOCK ? <MockBadge /> : undefined}
        description="Upload a photo of your dashboard or a warning light, and the multimodal pipeline returns a structured diagnosis."
      />

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        {/* Upload / Analyze */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="border-b py-3">
              <CardTitle className="text-base">Upload Vehicle Dashboard Image</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              {!preview ? (
                <button
                  type="button"
                  onClick={() => inputRef.current?.click()}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(true);
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragOver(false);
                    onFile(e.dataTransfer.files?.[0]);
                  }}
                  className={cn(
                    "flex aspect-video w-full flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed text-muted-foreground transition-colors",
                    dragOver
                      ? "border-primary bg-primary/5 text-primary"
                      : "border-border hover:border-primary/50 hover:text-foreground",
                  )}
                  aria-label="Upload a dashboard image by clicking or dragging"
                >
                  <ImagePlus className="h-8 w-8" />
                  <span className="text-sm">Click to upload or drag & drop</span>
                  <span className="text-xs">PNG / JPG · dashboard photo or warning light</span>
                </button>
              ) : (
                <div className="relative overflow-hidden rounded-xl border">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={preview}
                    alt="Dashboard preview"
                    className="aspect-video w-full object-cover"
                  />
                  <div className="absolute inset-x-0 bottom-0 flex items-center justify-between bg-gradient-to-t from-black/70 to-transparent p-2">
                    <span className="truncate text-xs text-white">{fileName}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={reset}
                      className="h-8 text-white hover:bg-white/20"
                      aria-label="Remove uploaded image"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              )}
              <input
                ref={inputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => onFile(e.target.files?.[0])}
                aria-label="Dashboard image file input"
              />

              {preview && (
                <Button
                  onClick={() => void analyze()}
                  disabled={phase === "loading"}
                  className="w-full"
                >
                  {phase === "loading" ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Analyzing…
                    </>
                  ) : (
                    <>
                      <ScanSearch className="mr-2 h-4 w-4" />
                      Analyze
                    </>
                  )}
                </Button>
              )}

              {phase === "loading" && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Running multimodal diagnosis pipeline</span>
                  </div>
                  <Progress value={66} className="h-1.5" />
                </div>
              )}

              {phase === "error" && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>Analysis failed</AlertTitle>
                  <AlertDescription>
                    AutoMind API is temporarily unavailable.
                    <Button
                      variant="link"
                      size="sm"
                      className="h-auto p-0 px-1"
                      onClick={() => void analyze()}
                    >
                      <RefreshCw className="mr-1 h-3 w-3" /> Retry
                    </Button>
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Pipeline */}
          <Card>
            <CardContent className="p-4">
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Analysis Pipeline
              </p>
              <ol className="flex flex-wrap items-center gap-1.5 text-xs">
                {PIPELINE.map((step, i) => (
                  <li key={step} className="flex items-center gap-1.5">
                    <span className="rounded-md border bg-muted/40 px-2 py-1 text-muted-foreground">
                      {step}
                    </span>
                    {i < PIPELINE.length - 1 && (
                      <ArrowRight className="h-3 w-3 text-muted-foreground/50" />
                    )}
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        </div>

        {/* Result */}
        <div className="space-y-4">
          {phase === "idle" && (
            <Card className="flex min-h-[360px] items-center justify-center">
              <div className="text-center text-muted-foreground">
                <ScanSearch className="mx-auto mb-2 h-10 w-10 text-primary/40" />
                <p className="text-sm">Upload an image, then press Analyze.</p>
              </div>
            </Card>
          )}

          {phase === "success" && result && (
            <DiagnosisResultCard result={result} />
          )}

          {phase === "error" && (
            <Card className="flex min-h-[360px] items-center justify-center">
              <div className="text-center text-destructive">
                <AlertTriangle className="mx-auto mb-2 h-10 w-10" />
                <p className="text-sm">Analysis could not be completed.</p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function DiagnosisResultCard({ result }: { result: DiagnosisResult }) {
  return (
    <div className="space-y-4">
      {result.message && (
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>识别说明</AlertTitle>
          <AlertDescription>{result.message}</AlertDescription>
        </Alert>
      )}
      {result.detected.map((d) => (
        <Card key={d.code} className="border-primary/30 bg-primary/5">
          <CardContent className="space-y-3 pt-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-mono text-xs text-primary">{d.code}</p>
                <h3 className="text-base font-semibold">{d.label}</h3>
              </div>
              <Badge className="bg-destructive/10 text-destructive" variant="outline">
                {d.risk}
              </Badge>
            </div>
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Confidence</span>
                <span className="tabular-nums">{d.confidence}%</span>
              </div>
              <Progress value={d.confidence} className="h-1.5" />
            </div>
          </CardContent>
        </Card>
      ))}

      <Section title="Possible Causes">
        <ul className="space-y-2">
          {result.causes.map((c) => (
            <li key={c.title} className="rounded-lg border bg-card p-3">
              <p className="text-sm font-medium">{c.title}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">{c.detail}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Recommended Action">
        <ul className="space-y-2">
          {result.recommendations.map((r) => (
            <li key={r.title} className="rounded-lg border bg-card p-3">
              <p className="text-sm font-medium">{r.title}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">{r.detail}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Knowledge References">
        <ul className="space-y-2">
          {result.references.map((ref, i) => (
            <li key={i} className="rounded-lg border bg-muted/30 p-3 text-xs">
              <p className="font-medium text-foreground">
                {ref.source}
                {ref.chapter ? ` · ${ref.chapter}` : ""}
                {ref.page ? ` · p.${ref.page}` : ""}
              </p>
              <p className="mt-1 text-muted-foreground">{ref.snippet}</p>
            </li>
          ))}
        </ul>
      </Section>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="border-b py-3">
        <CardTitle className="text-sm">{title}</CardTitle>
      </CardHeader>
      <CardContent className="pt-4">{children}</CardContent>
    </Card>
  );
}
