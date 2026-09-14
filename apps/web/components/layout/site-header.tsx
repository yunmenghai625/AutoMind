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
  { href: "/cockpit", label: "智能座舱" },
  { href: "/knowledge", label: "知识库" },
  { href: "/diagnosis", label: "智能诊断" },
  { href: "/garage", label: "我的车库" },
  { href: "/architecture", label: "技术架构" },
  { href: "/status", label: "系统状态" },
] as const;

const ADMIN_ITEMS = [{ href: "/admin", label: "运营管理" }] as const;

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
            aria-label="返回 AutoMind 首页"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-[11px] font-bold text-primary-foreground">
              AM
            </span>
            <span className="text-sm">AutoMind</span>
          </Link>

          <nav className="hidden items-center gap-0.5 lg:flex" aria-label="主导航">
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
            href="https://github.com/yunmenghai625/AutoMind"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden h-9 items-center rounded-md px-2.5 text-sm text-muted-foreground transition-colors hover:text-foreground sm:inline-flex"
            aria-label="AutoMind GitHub 代码仓库"
          >
            GitHub
          </Link>
          <div
            className="hidden h-7 w-7 items-center justify-center rounded-full bg-muted text-xs font-semibold md:flex"
            aria-label="当前为演示用户"
            title="演示用户"
          >
            AV
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setOpen((v) => !v)}
            aria-label={open ? "关闭导航菜单" : "打开导航菜单"}
            aria-expanded={open}
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      {/* Mobile drawer */}
      {open && (
        <div className="border-t lg:hidden">
          <nav className="container mx-auto flex max-w-7xl flex-col gap-1 px-4 py-3" aria-label="移动端导航">
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
