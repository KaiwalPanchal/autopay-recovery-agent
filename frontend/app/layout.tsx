import "./globals.css";
import type { Metadata } from "next";
import { Newsreader, Inter, JetBrains_Mono } from "next/font/google";

const serif = Newsreader({
  adjustFontFallback: false,
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
});
const sans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});
const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Autopay Recovery Voice Agent | Operator Dashboard",
  description: "Autonomous Conversational Payment Recovery System with LiveKit, FastAPI, and Deterministic Financial Guardrails.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${serif.variable} ${sans.variable} ${mono.variable}`}>
      <body className="antialiased bg-paper text-ink font-sans">
        {children}
      </body>
    </html>
  );
}
