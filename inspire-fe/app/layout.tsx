import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import GroupOrderBubble from "@/components/dashboardUser/GroupOrderBubble";
import { Toaster } from "@/components/ui/sonner";
import GuestSessionBootstrap from "@/components/app/GuestSessionBootstrap";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Suggest Mon An",
  description: "Group meal decision platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <GuestSessionBootstrap />
        {children}
        <GroupOrderBubble />
        <Toaster />
      </body>
    </html>
  );
}
