import { createClient } from "@/lib/supabase/server";
import { providerStats } from "@/lib/llm";
import { timeAgo, n } from "@/lib/format";
import Tile from "@/components/Tile";
import BrainLog from "@/components/BrainLog";
import type { BrainEvent } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function AiPage() {
  const supabase = await createClient();
  const since7 = new Date(Date.now() - 7 * 86400_000).toISOString();
  const { data, error } = await supabase.from("brain_events").select("*").eq("data->>kind", "llm").gte("ts", since7).order("ts", { ascending: false }).limit(5000);
  const events = (data ?? []) as BrainEvent[];
  const stats = providerStats(events);
  const total7 = events.length, total24 = stats.reduce((a, s) => a + s.calls24h, 0);
  const served7 = stats.reduce((a, s) => a + s.ok7d, 0), failovers7 = stats.reduce((a, s) => a + s.failovers7d, 0);
  const trimmed7 = stats.reduce((a, s) => a + s.trimmed7d, 0);
  const allSecs = events.filter((e) => e.data?.ok !== false && typeof e.data?.secs === "number").map((e) => e.data!.secs as number);
  const med = allSecs.length ? [...allSecs].sort((a, b) => a - b)[Math.floor(allSecs.length / 2)] : null;

  return (
    <main className="space-y-4">
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Tile label="Model calls · 24h" value={n(total24)} sub={`${n(total7)} in 7 days`} />
        <Tile label="Success rate · 7d" value={total7 ? `${Math.round((served7 / total7) * 100)}%` : "–"} sub={`${n(served7)} served`} tone="good" />
        <Tile label="Failovers · 7d" value={n(failovers7)} sub="provider errors, routed on" tone={failovers7 ? "warn" : undefined} />
        <Tile label="Median latency" value={med === null ? "–" : `${med.toFixed(1)}s`} sub="served calls, 7d" />
        <Tile label="Trimmed requests" value={n(trimmed7)} sub="history cut to fit" tone={trimmed7 ? "warn" : undefined} />
        <Tile label="Providers active" value={n(stats.filter((s) => s.calls7d > 0).length)} sub={`of ${stats.length} known`} />
      </section>

      <section className="card overflow-x-auto">
        <div className="px-4 pt-3 tile-label">Providers · free tiers behind arvis-router {error && <span className="text-bad">· {error.message}</span>}</div>
        <table className="table mt-2 min-w-[820px]">
          <thead><tr><th>Provider</th><th>Model</th><th className="text-right">24h</th><th className="text-right">7d</th><th className="text-right">Success</th><th className="text-right">Failovers</th><th className="text-right">Trimmed</th><th className="text-right">Median</th><th>Last call</th></tr></thead>
          <tbody>
            {stats.map((s) => (
              <tr key={s.provider} className={s.calls7d ? "" : "text-muted"}>
                <td className="mono text-xs">{s.provider}</td>
                <td className="text-xs text-muted">{s.model ?? "–"}</td>
                <td className="text-right tabular-nums">{n(s.calls24h)}</td>
                <td className="text-right tabular-nums">{n(s.calls7d)}</td>
                <td className="text-right tabular-nums">{s.calls7d ? `${Math.round((s.ok7d / s.calls7d) * 100)}%` : "–"}</td>
                <td className={`text-right tabular-nums ${s.failovers7d ? "text-warn" : ""}`}>{n(s.failovers7d)}</td>
                <td className="text-right tabular-nums">{n(s.trimmed7d)}</td>
                <td className="text-right tabular-nums">{s.medianSecs === null ? "–" : `${s.medianSecs.toFixed(1)}s`}</td>
                <td className="whitespace-nowrap text-muted">{timeAgo(s.lastAt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card overflow-hidden">
        <div className="flex items-center justify-between px-4 pt-3"><div className="tile-label">Model calls · live</div>
          <span className="text-xs text-muted">brain_events where kind = llm</span></div>
        <BrainLog initial={events.slice(0, 200).reverse()} available={!error} kind="llm" height={380} />
      </section>
    </main>
  );
}
