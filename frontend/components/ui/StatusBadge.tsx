import type { ResearchStatus } from "../../types/research";
export default function StatusBadge({ status }: { status: ResearchStatus | string }) { const label = status.replace("_", " "); return <span className={`status-badge status-${status}`}><span className="status-dot"/>{label}</span>; }
