import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ember — Personal Finance",
  description:
    "A private, local analytics dashboard powered by your budgeting spreadsheet.",
  icons: { icon: "/favicon.svg", shortcut: "/favicon.svg" },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
