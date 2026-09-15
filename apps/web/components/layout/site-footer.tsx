import Link from "next/link";
import { APP_NAME } from "@/lib/config";

export function SiteFooter() {
  return (
    <footer className="border-t">
      <div className="container mx-auto flex max-w-7xl flex-col gap-4 px-4 py-6 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <span className="flex h-5 w-5 items-center justify-center rounded bg-primary text-[9px] font-bold text-primary-foreground">
            AM
          </span>
          <span>
            {APP_NAME} · 个人作品集演示
          </span>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/status" className="hover:text-foreground">
            系统状态
          </Link>
          <Link href="/legal" className="hover:text-foreground">
            项目声明
          </Link>
          <Link
            href="https://github.com/yunmenghai625/AutoMind"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground"
          >
            GitHub
          </Link>
          <span>© 2026 yunmenghai625</span>
        </div>
      </div>
    </footer>
  );
}
