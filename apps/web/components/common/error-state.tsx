import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/common/icon";

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  compact?: boolean;
}

export function ErrorState({
  title = "出现异常",
  description = "AutoMind API 暂时不可用，请稍后重试。",
  onRetry,
  compact = false,
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-xl border border-destructive/20 bg-destructive/5 py-10 text-center",
        compact && "py-6",
      )}
      role="alert"
    >
      <Icon name="TriangleAlert" className="h-8 w-8 text-destructive" />
      <div className="space-y-1">
        <p className="text-sm font-semibold">{title}</p>
        <p className="max-w-sm text-xs text-muted-foreground">{description}</p>
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <Icon name="RotateCcw" />
          重试
        </Button>
      )}
    </div>
  );
}
