import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Growth.ia | Glacier AI",
  description: "Base limpa do frontend para reconstruir o dashboard e o copilot do Glacier AI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
