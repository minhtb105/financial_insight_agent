import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/layout/header";
import { Providers } from "./providers";
import { getServerSession } from "next-auth";
import { authOptions } from "@/auth";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Financial Insight Agent — Trợ lý chứng khoán Việt Nam",
  description: "LLM Agent phân tích chứng khoán Việt Nam với ReAct, 12 tools, streaming và trích dẫn.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const session = await getServerSession(authOptions);
  return (
    <html lang="vi" suppressHydrationWarning className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body suppressHydrationWarning className="min-h-full flex flex-col bg-background">
        <Providers session={session}>
          <Header />
          <main className="flex-1 flex flex-col">{children}</main>
          <footer className="border-t py-4 text-center text-xs text-muted-foreground">
            Financial Insight Agent — Chỉ phục vụ giáo dục & thông tin, không phải lời khuyên đầu tư.
          </footer>
        </Providers>
      </body>
    </html>
  );
}
