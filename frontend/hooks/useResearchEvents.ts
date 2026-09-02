"use client";
import { useEffect, useState } from "react";
import { eventUrl } from "../lib/api";
import type { ResearchEvent } from "../types/research";

export function useResearchEvents(id: string, active: boolean) {
  const [events, setEvents] = useState<ResearchEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!active) return;
    let stream: EventSource | undefined;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;
    const connect = () => {
      if (stopped) return;
      stream = new EventSource(eventUrl(id));
      stream.onopen = () => { setConnected(true); setError(""); };
      stream.onmessage = (message) => {
        try {
          const parsed = JSON.parse(message.data) as { type: string; message: string; payload?: Record<string, unknown> };
          setEvents(current => current.some(event => event.type === parsed.type && event.message === parsed.message) ? current : [...current, { type: parsed.type, message: parsed.message, payload: parsed.payload ?? {}, receivedAt: new Date().toISOString() }]);
          if (["research_completed", "research_failed", "research_cancelled"].includes(parsed.type)) { stopped = true; stream?.close(); }
        } catch { setError("Received an invalid research event."); }
      };
      stream.onerror = () => { setConnected(false); setError("Live connection interrupted. Reconnecting…"); stream?.close(); if (!stopped) retry = setTimeout(connect, 2500); };
    };
    connect();
    return () => { stopped = true; stream?.close(); if (retry) clearTimeout(retry); };
  }, [id, active]);
  return { events, connected, error };
}