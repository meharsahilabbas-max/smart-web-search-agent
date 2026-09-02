import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "Atlas Research", description: "Evidence-led web research workspace" };
import AppShell from "../components/layout/AppShell";
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body><AppShell>{children}</AppShell></body></html>; }
