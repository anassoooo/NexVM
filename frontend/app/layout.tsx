import type { Metadata } from "next";
import { Space_Grotesk } from "next/font/google";
import Link from "next/link";
import LogoutButton from "./dashboard/logout-button";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "myVMS",
  description: "Virtual Machine Management System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${spaceGrotesk.variable} antialiased`} style={{ background: "var(--bg)", color: "var(--text)" }}>
        <nav
          className="flex items-center justify-between px-6"
          style={{
            height: 56,
            background: "rgba(10,15,13,0.85)",
            backdropFilter: "blur(12px)",
            WebkitBackdropFilter: "blur(12px)",
            borderBottom: "1px solid var(--border)",
            position: "sticky",
            top: 0,
            zIndex: 50,
          }}
        >
          <div className="flex items-center gap-6">
            <Link href="/ai" className="font-bold text-lg nav-logo">
              myVMS
            </Link>
            <Link href="/ai" className="text-sm font-medium nav-link">
              AI
            </Link>
          </div>
          <LogoutButton />
        </nav>
        {children}
      </body>
    </html>
  );
}
