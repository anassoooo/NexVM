import type { Metadata } from "next";
import { Space_Grotesk } from "next/font/google";
import { ToastProvider } from "@/components/toast";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "myVMS — Virtual Machine Management Platform",
  description: "Create, manage, and monitor VirtualBox VMs through a modern web interface with AI assistance.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${spaceGrotesk.variable} antialiased`} style={{ background: "var(--bg)", color: "var(--text)" }}>
        <ToastProvider>
          {children}
        </ToastProvider>
      </body>
    </html>
  );
}
