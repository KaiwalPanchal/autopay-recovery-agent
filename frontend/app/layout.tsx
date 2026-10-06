import "./globals.css";
import type { Metadata } from "next";

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
    <html lang="en" className="dark">
      <body className="antialiased selection:bg-indigo-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
