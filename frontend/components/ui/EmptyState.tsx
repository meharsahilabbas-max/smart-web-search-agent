import Link from "next/link";
import { ArrowUpRight, Inbox } from "lucide-react";
export default function EmptyState({ title, description, action = "Start research" }: { title: string; description: string; action?: string }) { return <div className="empty-state"><Inbox size={24}/><h3>{title}</h3><p>{description}</p><Link href="/" className="button button-dark">{action}<ArrowUpRight size={15}/></Link></div>; }
