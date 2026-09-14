"use client";

import { useState } from "react";
import { Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { applyCockpitTheme, generateCockpitTheme } from "@/lib/api/aigcApi";
import { getVehicleState } from "@/lib/api/vehicleApi";
import { useVehicleStore } from "@/lib/store/vehicle-store";
import type { CockpitTheme } from "@/types/aigc";

interface AiThemeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onApplied: (theme: CockpitTheme) => void;
}

export function AiThemeDialog({ open, onOpenChange, onApplied }: AiThemeDialogProps) {
  const [prompt, setPrompt] = useState("给我一个适合海边夜间驾驶的安静主题");
  const [preview, setPreview] = useState<CockpitTheme | null>(null);
  const [busy, setBusy] = useState<"generate" | "apply" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const setVehicle = useVehicleStore((state) => state.setVehicle);

  async function generate(regenerate = false) {
    setBusy("generate");
    setError(null);
    try {
      setPreview(await generateCockpitTheme(prompt, regenerate));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "主题生成失败");
    } finally {
      setBusy(null);
    }
  }

  async function apply() {
    if (!preview) return;
    setBusy("apply");
    setError(null);
    try {
      const applied = await applyCockpitTheme(preview.theme_id);
      onApplied({
        ...preview,
        theme_spec: applied.theme_spec,
        wallpaper_url: applied.wallpaper_url,
      });
      setVehicle(await getVehicleState());
      onOpenChange(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "主题应用失败");
    } finally {
      setBusy(null);
    }
  }

  const previewStyle = preview
    ? {
        backgroundColor: preview.theme_spec.ambient_color,
        backgroundImage: preview.wallpaper_url
          ? `linear-gradient(90deg, rgba(3,10,20,.70), rgba(3,10,20,.18)), url(${preview.wallpaper_url})`
          : "radial-gradient(circle at 75% 25%, rgba(94,219,232,.45), transparent 38%), linear-gradient(135deg, #06152f, #123b5d 60%, #087f8c)",
      }
    : undefined;

  return (
    <Dialog open={open} onOpenChange={onOpenChange} className="max-w-2xl">
      <DialogClose onClose={() => onOpenChange(false)} />
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-cyan-500" /> AI 座舱主题
        </DialogTitle>
        <DialogDescription>
          先生成预览；只有点击“确认应用”后，才会通过安全门和车辆工具修改座舱状态。
        </DialogDescription>
      </DialogHeader>

      <div className="space-y-4">
        <Textarea
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          rows={3}
          maxLength={500}
          placeholder="描述你想要的驾驶氛围…"
          disabled={busy !== null}
        />
        <Button onClick={() => generate(false)} disabled={busy !== null || prompt.trim().length < 2}>
          {busy === "generate" && <Loader2 className="animate-spin" />}
          {preview ? "重新按原提示生成" : "生成主题预览"}
        </Button>

        {preview && (
          <div className="overflow-hidden rounded-xl border">
            <div
              className="flex min-h-52 flex-col justify-end bg-cover bg-center p-5 text-white"
              style={previewStyle}
            >
              <p className="text-xs tracking-[0.25em] text-white/65">仅供预览</p>
              <h3 className="mt-1 text-2xl font-semibold">{preview.theme_spec.name}</h3>
              <p className="mt-2 text-sm text-white/80">
                {{ comfort: "舒适", night: "夜间", minimal: "极简", focus: "专注" }[
                  preview.theme_spec.display_mode
                ]} · {preview.theme_spec.music_style} · {preview.theme_spec.temperature}°C
              </p>
              <div className="mt-3 flex items-center gap-2 text-xs text-white/70">
                <span
                  className="h-3 w-3 rounded-full border border-white/40"
                  style={{ backgroundColor: preview.theme_spec.ambient_color }}
                />
                环境光 {preview.theme_spec.ambient_brightness}% · {{ success: "生成成功", cached: "缓存结果", degraded: "降级生成" }[preview.metadata.status] ?? preview.metadata.status}
                {preview.metadata.cached ? " · 缓存命中" : ""}
              </div>
            </div>
          </div>
        )}
        {error && <p className="text-sm text-destructive">{error}</p>}
      </div>

      {preview && (
        <DialogFooter>
          <Button variant="outline" onClick={() => generate(true)} disabled={busy !== null}>
            再生成一个
          </Button>
          <Button onClick={apply} disabled={busy !== null}>
            {busy === "apply" && <Loader2 className="animate-spin" />}
            确认应用
          </Button>
        </DialogFooter>
      )}
    </Dialog>
  );
}
