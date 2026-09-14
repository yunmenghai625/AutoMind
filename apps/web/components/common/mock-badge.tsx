import { cn } from "@/lib/utils";

interface MockBadgeProps {
  className?: string;
}

/** Marks DEMO/MOCK data so it is never mistaken for production facts. */
export function MockBadge({ className }: MockBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border border-warning/30 bg-warning/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-warning",
        className,
      )}
      title="当前为模拟演示数据，接入真实 API 后将自动替换。"
    >
      <span className="h-1.5 w-1.5 rounded-full bg-warning" />
      模拟数据
    </span>
  );
}
