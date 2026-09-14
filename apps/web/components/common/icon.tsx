import * as LucideIcons from "lucide-react";
import type { LucideProps } from "lucide-react";
import { cn } from "@/lib/utils";

type IconName = keyof typeof LucideIcons;

interface IconProps extends Omit<LucideProps, "ref"> {
  name: string;
}

/**
 * Lucide icon dynamic renderer.
 * Keeping a single dynamic renderer instead of importing dozens of icons
 * across the app makes swapping icon names trivial.
 */
export function Icon({ name, className, ...props }: IconProps) {
  const Comp =
    (LucideIcons[name as IconName] ??
      LucideIcons.HelpCircle) as React.ComponentType<LucideProps>;
  return (
    <Comp className={cn("h-4 w-4", className)} aria-hidden="true" {...props} />
  );
}
