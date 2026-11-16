"use client";
import { useEffect, useRef, useState } from "react";
import { createClient, withRealtimeAuth } from "@/lib/supabase/client";
import type { BrainEvent } from "@/lib/types";
import { SOURCE_COLORS } from "@/components/BrainCanvas";

const LEVEL: Record<string, string> = { debug: "text-muted", info: "text-text", warn: "text-warn", error: "text-bad" };

export default function BrainLog({ initial, available, kind, height = 460 }: { initial: BrainEvent[]; available: boolean; kind?: string; height?: number }) {
  const [events, setEvents] = useState<BrainEvent[]>(initial);
  const [live, setLive] = useState<"connecting" | "live" | "off">(available ? "connecting" : "off");
  const [filter, setFilter] = useState("");
  const [follow, setFollow] = useState(true);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!available) return;
    const sb = createClient();
    let ch: ReturnType<typeof sb.channel> | null = null;
    let cancelled = false;
    withRealtimeAuth(sb).then(() => {
      if (cancelled) return;
      ch = sb.channel(`brain_log_${Math.random().toString(36).slice(2)}`)
        .on("postgres_changes", { event: "INSERT", schema: "public", table: "brain_events" }, (p) => {
          const e = p.new as BrainEvent;
          if (kind && String(e.data?.kind ?? "") !== kind) return;
          setEvents((ev) => [...ev.slice(-999), e]);
        })
        .subscribe((status) => setLive(status === "SUBSCRIBED" ? "live" : status === "CHANNEL_ERROR" || status === "TIMED_OUT" ? "off" : "connecting"));
    });
    return () => { cancelled = true; if (ch) sb.removeChannel(ch); };
  }, [available, kind]);

  useEffect(() => {
    if (follow && box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [events, follow]);

  const shown = filter ? events.filter((e) => e.source === filter) : events;
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 px-4 py-2 text-xs">
        <span className={`inline-flex items-center gap-1 ${live === "live" ? "text-good" : live === "off" ? "text-bad" : "text-warn"}`}>
          <span className={`inline-block h-2 w-2 rounded-full ${live === "live" ? "bg-good animate-pulse" : live === "off" ? "bg-bad" : "bg-warn"}`} />{live}
        </span>
        <select value={filter} onChange={(e) => setFilter(e.target.value)} className="input !py-0.5 text-xs">
          <option value="">all sources</option>{Object.keys(SOURCE_COLORS).map((s) => <option key={s}>{s}</option>)}
        </select>
        <label className="ml-auto inline-flex items-center gap-1 text-muted"><input type="checkbox" checked={follow} onChange={(e) => setFollow(e.target.checked)} /> follow</label>
        <span className="text-muted">{shown.length} lines</span>
      </div>
      <div ref={box} style={{ height }} className="mono overflow-y-auto border-t border-line bg-bg px-3 py-2 text-[12px] leading-5">
        {!shown.length && <div className="text-muted">{available ? "No events yet. The scrape upload step and arvisctl commands write here." : "brain_events table not found."}</div>}
        {shown.map((e) => (
          <div key={e.id} className="flex gap-2 whitespace-pre-wrap break-words">
            <span className="shrink-0 text-muted">{new Date(e.ts).toLocaleTimeString("en-GB", { timeZone: "Asia/Kolkata", hour12: false })}</span>
            <span className="shrink-0 w-16" style={{ color: SOURCE_COLORS[e.source] ?? "#8591a3" }}>{e.source}</span>
            <span className={`shrink-0 w-10 ${LEVEL[e.level] ?? ""}`}>{e.level}</span>
            <span className={LEVEL[e.level] ?? ""}>{e.message}{e.data && Object.keys(e.data).length ? <span className="text-muted"> {JSON.stringify(e.data)}</span> : null}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
