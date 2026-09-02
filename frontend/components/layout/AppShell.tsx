"use client";
import Link from "next/link";
import { BookOpen, Clock3, FileSearch, Settings, Sparkles } from "lucide-react";
import { usePathname } from "next/navigation";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const links = [["/", "New research", Sparkles], ["/history", "History", Clock3], ["/sources", "Sources", FileSearch], ["/settings", "Settings", Settings]] as const;
  return <div className="app-shell"><aside className="sidebar"><Link href="/" className="brand"><span className="brand-mark"><BookOpen size={16}/></span><span>ATLAS<span className="brand-dot">.</span></span></Link><div className="nav-label">Workspace</div><nav>{links.map(([href, label, Icon]) => <Link key={href} href={href} className={path === href || (href !== "/" && path.startsWith(href)) ? "nav-item active" : "nav-item"}><Icon size={17}/>{label}</Link>)}</nav><div className="sidebar-foot"><span className="live-dot"/> Engine online</div></aside><main className="main-content"><header className="mobile-header"><Link href="/" className="brand"><span className="brand-mark"><BookOpen size={15}/></span>ATLAS<span className="brand-dot">.</span></Link><Link href="/settings" aria-label="Settings"><Settings size={18}/></Link></header>{children}</main></div>;
}
