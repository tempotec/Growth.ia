import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Growth.ia | Glacier AI",
  description: "Copiloto analitico para validar a experiencia do chat com o backend Glacier AI.",
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
