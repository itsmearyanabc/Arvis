import type { BrainEvent } from "@/lib/types";

export const PROVIDERS = ["gemini-lite", "gemini", "groq", "cerebras", "mistral", "nvidia", "github", "openrouter-free", "modal"] as const;

export type ProviderStats = { provider: string; calls24h: number; calls7d: number; ok7d: number; failovers7d: number; trimmed7d: number; medianSecs: number | null; lastAt: string | null; model: string | null };

export function median(xs: number[]): number | null {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b); const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/** Aggregate kind=llm events (router writes one per attempt: ok=true served, ok=false failover). */
export function providerStats(events: BrainEvent[]): ProviderStats[] {
  const dayAgo = Date.now() - 86400_000;
  const map = new Map<string, ProviderStats & { secs: number[] }>();
  const get = (p: string) => {
    let r = map.get(p);
    if (!r) { r = { provider: p, calls24h: 0, calls7d: 0, ok7d: 0, failovers7d: 0, trimmed7d: 0, medianSecs: null, lastAt: null, model: null, secs: [] }; map.set(p, r); }
    return r;
  };
  for (const p of PROVIDERS) get(p);
  for (const e of events) {
    const d = (e.data ?? {}) as Record<string, unknown>;
    const r = get(String(d.provider ?? "unknown"));
    const t = new Date(e.ts).getTime();
    r.calls7d++; if (t > dayAgo) r.calls24h++;
    if (d.ok === false) r.failovers7d++; else { r.ok7d++; if (typeof d.secs === "number") r.secs.push(d.secs); }
    if (typeof d.trimmed === "number" && d.trimmed > 0) r.trimmed7d++;
    if (!r.lastAt || r.lastAt < e.ts) { r.lastAt = e.ts; if (d.model) r.model = String(d.model); }
  }
  return [...map.values()].map(({ secs, ...r }) => ({ ...r, medianSecs: median(secs) })).sort((a, b) => b.calls7d - a.calls7d);
}
