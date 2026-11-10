import type { Metadata, Viewport } from "next";
import { Archivo } from "next/font/google";
import "./globals.css";

const archivo = Archivo({
  subsets: ["latin"],
  axes: ["wdth"],
  variable: "--font-archivo",
});

export const metadata: Metadata = {
  title: "psst",
  description:
    "El amigo invisible por enlace: cada uno ve solo su nombre y puede preguntar a su persona sin que sepa quién es.",
};

export const viewport: Viewport = {
  themeColor: "#2a0a10",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className={archivo.variable}>
      <body>{children}</body>
    </html>
  );
}
