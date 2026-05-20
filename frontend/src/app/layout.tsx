import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Entrevistador Técnico por IA",
  description:
    "Plataforma de entrevistas técnicas simuladas por voz con Inteligencia Artificial. Carga tu CV y la vacante para comenzar una entrevista realista.",
  keywords: ["entrevista técnica", "inteligencia artificial", "voz", "simulación", "empleo"],
  openGraph: {
    title: "Entrevistador Técnico por IA",
    description:
      "Simula entrevistas técnicas reales con un entrevistador de IA por voz.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
