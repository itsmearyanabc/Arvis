"use client";
import { createClient, withRealtimeAuth } from "@/lib/supabase/client";
import type { BrainEvent, BrainSource } from "@/lib/types";

export type FeedState = { recent10m: number; lastBySource: Partial<Record<BrainSource, number>>; available: boolean };

/**
 * Loads recent brain_events and streams new rows via Supabase Realtime.
 * onEvent fires for each live insert; onState after initial load and each event.
 */
export function subscribeBrainFeed(
  onState: (s: FeedState) => void,
  onEvent?: (e: BrainEvent) => void,
) {
  const supabase = createClient();
  const state: FeedState = { recent10m: 0, lastBySource: {}, available: false };
  let stopped = false;

  (async () => {
    const since = new Date(Date.now() - 10 * 60_000).toISOString();
    const { data, error } = await supabase
      .from("brain_events").select("ts,source").gte("ts", since).order("ts", { ascending: false }).limit(500);
    if (stopped) return;
    if (error) { onState({ ...state, available: false }); return; }
    state.available = true;
    state.recent10m = data?.length ?? 0;
    for (const r of data ?? []) {
      const t = new Date(r.ts).getTime();
      const src = r.source as BrainSource;
      if (!state.lastBySource[src] || state.lastBySource[src]! < t) state.lastBySource[src] = t;
    }
    onState({ ...state });
  })();

  let channel: ReturnType<typeof supabase.channel> | null = null;
  withRealtimeAuth(supabase).then(() => {
    if (stopped) return;
    channel = supabase
      .channel(`brain_events_feed_${Math.random().toString(36).slice(2)}`)
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "brain_events" }, (payload) => {
        const e = payload.new as BrainEvent;
        state.available = true;
        state.recent10m += 1;
        state.lastBySource[e.source] = Date.now();
        onState({ ...state });
        onEvent?.(e);
      })
      .subscribe();
  });

  // decay the 10-minute window roughly once a minute
  const timer = setInterval(async () => {
    if (!state.available) return;
    const since = new Date(Date.now() - 10 * 60_000).toISOString();
    const { count } = await supabase.from("brain_events").select("id", { count: "exact", head: true }).gte("ts", since);
    if (typeof count === "number") { state.recent10m = count; onState({ ...state }); }
  }, 60_000);

  return () => { stopped = true; clearInterval(timer); if (channel) supabase.removeChannel(channel); };
}
