import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ember — Personal Finance",
  description: "A calm, local-first personal finance dashboard for spending, budgets, and FIRE progress.",
  icons: { icon: "/favicon.svg", shortcut: "/favicon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
