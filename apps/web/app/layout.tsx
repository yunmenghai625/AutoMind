import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme/theme-provider";
import { SiteHeader } from "@/components/layout/site-header";
import { SiteFooter } from "@/components/layout/site-footer";
import { Toaster } from "@/components/ui/sonner";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "AutoMind — 生产级汽车智能座舱平台",
    template: "%s · AutoMind",
  },
  description:
    "AutoMind 是融合智能体、RAG、多模态 AI 与车辆数字孪生的生产级汽车智能座舱平台。",
  keywords: [
    "AutoMind",
    "汽车人工智能",
    "智能座舱",
    "车辆数字孪生",
    "RAG",
    "LLMOps",
  ],
  authors: [{ name: "yunmenghai625" }],
  creator: "yunmenghai625",
  openGraph: {
    type: "website",
    title: "AutoMind — 生产级汽车智能座舱平台",
    description:
      "你的智能，你的爱车，你的旅程。面向汽车场景的智能 AI 平台。",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f8fb" },
    { media: "(prefers-color-scheme: dark)", color: "#08090c" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem={false}
          disableTransitionOnChange
        >
          <div className="flex min-h-screen flex-col">
            <SiteHeader />
            <main className="flex-1">{children}</main>
            <SiteFooter />
          </div>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
