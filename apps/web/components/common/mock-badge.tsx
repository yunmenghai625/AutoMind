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
      title="This value is mock/demo data and will be replaced by the real API."
    >
      <span className="h-1.5 w-1.5 rounded-full bg-warning" />
      Mock
    </span>
  );
}
