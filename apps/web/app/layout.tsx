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
    default: "AutoMind — Production Automotive AI Cockpit Platform",
    template: "%s · AutoMind",
  },
  description:
    "AutoMind is a production-grade automotive AI cockpit platform powered by Agent, RAG, Multimodal AI and Vehicle Digital Twin.",
  keywords: [
    "AutoMind",
    "Automotive AI",
    "AI Cockpit",
    "Vehicle Digital Twin",
    "RAG",
    "LLMOps",
  ],
  authors: [{ name: "AutoMind" }],
  openGraph: {
    type: "website",
    title: "AutoMind — Production Automotive AI Cockpit Platform",
    description:
      "Your AI. Your Car. Your Journey. An intelligent automotive AI platform.",
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
    <html lang="en" suppressHydrationWarning>
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
