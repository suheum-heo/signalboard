import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SignalBoard",
  description: "KOSPI 200 daily signal scores",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className={`${geistSans.variable} ${geistMono.variable} h-full`}>
      <body className="min-h-full bg-gray-950 text-gray-100 antialiased">
        <header className="border-b border-gray-800 px-6 py-3 flex items-center gap-8">
          <span className="font-bold text-white tracking-tight">SignalBoard</span>
          <nav className="flex gap-6 text-sm">
            <Link href="/" className="text-gray-400 hover:text-white transition-colors">
              Radar
            </Link>
            <Link href="/changes" className="text-gray-400 hover:text-white transition-colors">
              Changes
            </Link>
            <Link href="/history" className="text-gray-400 hover:text-white transition-colors">
              History
            </Link>
          </nav>
        </header>
        <main className="p-6 max-w-5xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
