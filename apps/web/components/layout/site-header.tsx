"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import * as React from "react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { ModelStatusBadge } from "@/components/layout/model-status-badge";
import { Button } from "@/components/ui/button";

export const NAV_ITEMS = [
  { href: "/", label: "AutoMind" },
  { href: "/cockpit", label: "Cockpit" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/diagnosis", label: "Diagnosis" },
  { href: "/garage", label: "Garage" },
  { href: "/architecture", label: "Architecture" },
  { href: "/status", label: "Status" },
] as const;

const ADMIN_ITEMS = [{ href: "/admin", label: "Admin" }] as const;

export function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = React.useState(false);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur">
      <div className="container mx-auto flex h-14 max-w-7xl items-center justify-between gap-3 px-4">
        <div className="flex items-center gap-6">
          <Link
            href="/"
            className="flex items-center gap-2 font-semibold tracking-tight"
            aria-label="AutoMind home"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-[11px] font-bold text-primary-foreground">
              AM
            </span>
            <span className="text-sm">AutoMind</span>
          </Link>

          <nav className="hidden items-center gap-0.5 lg:flex" aria-label="Primary">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors",
                  isActive(item.href)
                    ? "text-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
                aria-current={isActive(item.href) ? "page" : undefined}
              >
                {item.label}
              </Link>
            ))}
            {ADMIN_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors",
                  isActive(item.href)
                    ? "text-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
                aria-current={isActive(item.href) ? "page" : undefined}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-1.5">
          <ModelStatusBadge />
          <ThemeToggle />
          <Link
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden h-9 items-center rounded-md px-2.5 text-sm text-muted-foreground transition-colors hover:text-foreground sm:inline-flex"
            aria-label="AutoMind GitHub repository"
          >
            GitHub
          </Link>
          <div
            className="hidden h-7 w-7 items-center justify-center rounded-full bg-muted text-xs font-semibold md:flex"
            aria-label="Signed in as Demo User"
            title="Demo User"
          >
            AV
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setOpen((v) => !v)}
            aria-label={open ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={open}
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      {/* Mobile drawer */}
      {open && (
        <div className="border-t lg:hidden">
          <nav className="container mx-auto flex max-w-7xl flex-col gap-1 px-4 py-3" aria-label="Mobile">
            {[...NAV_ITEMS, ...ADMIN_ITEMS].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={cn(
                  "rounded-md px-3 py-2 text-sm font-medium",
                  isActive(item.href)
                    ? "bg-muted text-foreground"
                    : "text-muted-foreground",
                )}
                aria-current={isActive(item.href) ? "page" : undefined}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      )}
    </header>
  );
}
