import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { fmtDate, duration, n } from "@/lib/format";
import StatusPill from "@/components/StatusPill";
import BrainLog from "@/components/BrainLog";
import type { BrainEvent, WorkerRun } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function TasksPage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const sp = await searchParams;
  const tab = sp.tab === "workers" ? "workers" : "brain";
  const filter = sp.ok === "ok" || sp.ok === "failed" ? sp.ok : "";
  const supabase = await createClient();

  let q = supabase.from("brain_events").select("*").eq("data->>kind", "task").order("ts", { ascending: false }).limit(300);
  if (filter === "ok") q = q.eq("data->>ok", "true");
  if (filter === "failed") q = q.eq("data->>ok", "false");
  const [tasks, runs] = await Promise.all([
    q,
    tab === "workers" ? supabase.from("worker_runs").select("*").order("started_at", { ascending: false }).limit(200) : Promise.resolve({ data: [] as WorkerRun[], error: null }),
  ]);
  const events = (tasks.data ?? []) as BrainEvent[];
  const failed = events.filter((e) => e.data?.ok === false).length;

  return (
    <main className="space-y-4">
      <div className="flex flex-wrap items-center gap-1 text-sm">
        <Link href="/tasks" className={`rounded-md px-3 py-1.5 ${tab === "brain" ? "bg-panel2 text-accent" : "text-muted hover:text-text"}`}>Brain tasks</Link>
        <Link href="/tasks?tab=workers" className={`rounded-md px-3 py-1.5 ${tab === "workers" ? "bg-panel2 text-accent" : "text-muted hover:text-text"}`}>Workers</Link>
        {tab === "brain" && (
          <span className="ml-auto flex items-center gap-1 text-xs">
            {[["", "all"], ["ok", "ok"], ["failed", "failed"]].map(([v, l]) => (
              <Link key={l} href={v ? `/tasks?ok=${v}` : "/tasks"} className={`rounded-md px-2 py-1 ${filter === v ? "bg-panel2 text-accent" : "text-muted hover:text-text"}`}>{l}</Link>
            ))}
            <span className="ml-2 text-muted">{n(events.length)} shown · {n(failed)} failed</span>
          </span>
        )}
      </div>

      {tab === "brain" ? (
        <>
          <section className="card overflow-x-auto">
            <table className="table min-w-[760px]">
              <thead><tr><th>When</th><th>Result</th><th>Command</th><th className="text-right">Secs</th><th>Error</th></tr></thead>
              <tbody>
                {events.map((e) => {
                  const d = (e.data ?? {}) as Record<string, unknown>;
                  return (
                    <tr key={e.id}>
                      <td className="whitespace-nowrap text-muted">{fmtDate(e.ts)}</td>
                      <td><StatusPill value={d.ok === false ? "failed" : "ok"} /></td>
                      <td className="mono text-xs">{e.message.replace(/^task (done|failed|crashed): /, "")}</td>
                      <td className="text-right tabular-nums">{typeof d.secs === "number" ? d.secs.toFixed(1) : "–"}</td>
                      <td className="max-w-[360px] whitespace-pre-wrap text-xs text-bad">{d.error ? String(d.error) : ""}</td>
                    </tr>
                  );
                })}
                {!events.length && <tr><td colSpan={5} className="text-muted">{tasks.error ? tasks.error.message : "No tasks logged yet. Every arvisctl command the brain runs lands here."}</td></tr>}
              </tbody>
            </table>
          </section>
          <section className="card overflow-hidden">
            <div className="flex items-center justify-between px-4 pt-3"><div className="tile-label">Tasks · live</div><span className="text-xs text-muted">brain_events where kind = task</span></div>
            <BrainLog initial={events.slice(0, 100).reverse()} available={!tasks.error} kind="task" height={260} />
          </section>
        </>
      ) : (
        <section className="card overflow-x-auto">
          <table className="table min-w-[640px]">
            <thead><tr><th>Worker</th><th>Started</th><th>Status</th><th>Input</th><th>Counts</th><th className="text-right">Duration</th></tr></thead>
            <tbody>
              {((runs.data ?? []) as WorkerRun[]).map((r) => (
                <tr key={r.run_id}>
                  <td>{r.worker}</td>
                  <td className="whitespace-nowrap text-muted">{fmtDate(r.started_at)}</td>
                  <td><StatusPill value={r.status} />{r.error && <div className="mt-1 max-w-[260px] whitespace-pre-wrap text-xs text-bad">{r.error}</div>}</td>
                  <td className="mono text-xs text-muted">{r.input ? Object.entries(r.input).map(([k, v]) => `${k}=${String(v)}`).join(" ") : ""}</td>
                  <td className="mono text-xs">{r.counts ? Object.entries(r.counts).map(([k, v]) => `${k}=${String(v)}`).join(" ") : ""}</td>
                  <td className="text-right tabular-nums text-muted">{duration(r.started_at, r.finished_at)}</td>
                </tr>
              ))}
              {!runs.data?.length && <tr><td colSpan={6} className="text-muted">No worker runs.</td></tr>}
            </tbody>
          </table>
        </section>
      )}
    </main>
  );
}
