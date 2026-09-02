import type { HealthStatus, Research, ResearchEvent, ResearchReport, Source } from "../types/research";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	const response = await fetch(`${API}${path}`, { ...init, cache: "no-store", headers: { "Content-Type": "application/json", ...init?.headers } });
	if (!response.ok) {
		let message = `Request failed (${response.status})`;
		try { const body = await response.json(); message = body.detail ?? body.error?.message ?? message; } catch { /* non-JSON error */ }
		throw new Error(message);
	}
	if (response.status === 204) return undefined as T;
	return response.json() as Promise<T>;
}

export function createResearch(question: string, depth: Research["depth"], maxSources: number) {
	return request<Research>("/research", { method: "POST", body: JSON.stringify({ question, depth, max_sources: maxSources }) });
}
export function getResearch(id: string) { return request<Research>(`/research/${id}`); }
export function getSources(id: string) { return request<Source[]>(`/research/${id}/sources`); }
export function getReport(id: string) { return request<ResearchReport>(`/research/${id}/report`); }
export function getHistory() { return request<Research[]>("/research"); }
export function deleteResearch(id: string) { return request<void>(`/research/${id}`, { method: "DELETE" }); }
export function cancelResearch(id: string) { return request<{ status: string }>(`/research/${id}/cancel`, { method: "POST" }); }
export function getHealth() { return request<HealthStatus>("/health"); }
export function getConfigStatus() { return request<{ llm_configured: boolean; search_provider: string; search_ready: boolean }>("/config/status"); }
export function eventUrl(id: string) { return `${API}/research/${id}/events`; }
export type { ResearchEvent };
