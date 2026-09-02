export type ResearchDepth = "quick" | "standard" | "deep";
export type ResearchStatus = "queued" | "running" | "completed" | "failed" | "cancelled";
export interface Source { id: number; title: string; url: string; domain: string; snippet: string; credibility: number; relevance: number; citation_id: number; }
export interface Finding { title: string; detail: string; citations: number[]; }
export interface ResearchReport { executive_summary?: string; key_findings?: Finding[]; detailed_analysis?: string; limitations?: string; conclusion?: string; confidence?: number; }
export interface Research { id: string; question: string; depth: ResearchDepth; status: ResearchStatus | string; confidence: number | null; report: ResearchReport | null; created_at: string; sources: Source[]; }
export interface ResearchEvent { type: string; message: string; payload: Record<string, unknown>; receivedAt: string; }
export interface HealthStatus { status: string; service: string; }