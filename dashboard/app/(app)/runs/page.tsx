import { createClient } from "@/lib/supabase/server";
import { fmtDate, duration } from "@/lib/format";
import StatusPill from "@/components/StatusPill";
import BrainLog from "@/components/BrainLog";
import type { WorkerRun, BrainEvent } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const supabase = await createClient();
  const [{ data: runs }, events] = await Promise.all([
    supabase.from("worker_runs").select("*").order("started_at", { ascending: false }).limit(100),
    supabase.from("brain_events").select("*").order("ts", { ascending: false }).limit(200),
  ]);
  const available = !events.error;
  const initial = ((events.data ?? []) as BrainEvent[]).reverse();

  return (
    <main className="grid gap-4 xl:grid-cols-2">
      <section className="card overflow-hidden">
        <div className="flex items-center justify-between px-4 pt-3"><div className="tile-label">Brain log · live</div>
          <span className="text-xs text-muted">{available ? "streaming via Realtime" : "table missing: run supabase/migrations_002_brain_events.sql"}</span></div>
        <BrainLog initial={initial} available={available} />
      </section>

      <section className="card overflow-x-auto">
        <div className="px-4 pt-3 tile-label">Worker runs · last 100</div>
        <table className="table mt-2 min-w-[640px]">
          <thead><tr><th>Worker</th><th>Started</th><th>Status</th><th>Input</th><th>Counts</th><th className="text-right">Duration</th></tr></thead>
          <tbody>
            {((runs ?? []) as WorkerRun[]).map((r) => (
              <tr key={r.run_id}>
                <td>{r.worker}</td>
                <td className="whitespace-nowrap text-muted">{fmtDate(r.started_at)}</td>
                <td><StatusPill value={r.status} />{r.error && <div className="mt-1 max-w-[260px] whitespace-pre-wrap text-xs text-bad">{r.error}</div>}</td>
                <td className="mono text-xs text-muted">{r.input ? Object.entries(r.input).map(([k, v]) => `${k}=${String(v)}`).join(" ") : ""}</td>
                <td className="mono text-xs">{r.counts ? Object.entries(r.counts).filter(([k]) => k !== "market_id").map(([k, v]) => `${k}=${String(v)}`).join(" ") : ""}</td>
                <td className="text-right tabular-nums text-muted">{duration(r.started_at, r.finished_at)}</td>
              </tr>
            ))}
            {!runs?.length && <tr><td colSpan={6} className="text-muted">No runs yet.</td></tr>}
          </tbody>
        </table>
      </section>
    </main>
  );
}
