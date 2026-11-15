import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { GROUP_NAMES, groupOf } from "@/lib/niches";
import { fmtDate, duration, n } from "@/lib/format";
import Tile from "@/components/Tile";
import BarChart from "@/components/BarChart";
import StatusPill from "@/components/StatusPill";
import BrainCanvas from "@/components/BrainCanvas";
import type { WorkerRun } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function Overview() {
  const supabase = await createClient();
  const dayAgo = new Date(Date.now() - 86400_000).toISOString();
  const since30 = new Date(Date.now() - 30 * 86400_000); since30.setUTCHours(0, 0, 0, 0);

  const cnt = (q: PromiseLike<{ count: number | null }>) => q.then((r) => r.count ?? 0);
  const [total, withEmail, named, new24, marketsActive, marketsScraped, runsOk, runsFailed, perDay, groupRows, runs] = await Promise.all([
    cnt(supabase.from("leads").select("lead_id", { count: "exact", head: true })),
    cnt(supabase.from("leads").select("lead_id", { count: "exact", head: true }).not("primary_email", "is", null).neq("primary_email", "")),
    cnt(supabase.from("leads").select("lead_id", { count: "exact", head: true }).eq("contact_quality", "named")),
    cnt(supabase.from("leads").select("lead_id", { count: "exact", head: true }).gte("scraped_at", dayAgo)),
    cnt(supabase.from("markets").select("market_id", { count: "exact", head: true }).eq("status", "active")),
    cnt(supabase.from("markets").select("market_id", { count: "exact", head: true }).not("last_scraped_at", "is", null)),
    cnt(supabase.from("worker_runs").select("run_id", { count: "exact", head: true }).eq("status", "ok")),
    cnt(supabase.from("worker_runs").select("run_id", { count: "exact", head: true }).eq("status", "failed")),
    supabase.from("leads").select("scraped_at").gte("scraped_at", since30.toISOString()).limit(20000),
    supabase.from("leads").select("niche,primary_email").limit(20000),
    supabase.from("worker_runs").select("*").order("started_at", { ascending: false }).limit(8),
  ]);

  // leads per day, 30 buckets (IST days)
  const days: { label: string; value: number }[] = [];
  const keyOf = (d: Date) => d.toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
  const idx = new Map<string, number>();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(Date.now() - i * 86400_000);
    const k = keyOf(d);
    idx.set(k, days.length);
    days.push({ label: d.toLocaleDateString("en-GB", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short" }), value: 0 });
  }
  for (const r of perDay.data ?? []) {
    const k = keyOf(new Date(r.scraped_at as string));
    const i = idx.get(k); if (i !== undefined) days[i].value++;
  }

  const groups = new Map<string, { leads: number; emails: number }>(GROUP_NAMES.map((g) => [g, { leads: 0, emails: 0 }]));
  for (const r of groupRows.data ?? []) {
    const g = groupOf(r.niche as string);
    const row = groups.get(g) ?? { leads: 0, emails: 0 };
    row.leads++; if (r.primary_email) row.emails++;
    groups.set(g, row);
  }

  return (
    <main className="space-y-6">
      <section className="card relative h-56 overflow-hidden sm:h-64">
        <BrainCanvas showLegend />
        <div className="pointer-events-none absolute left-4 top-3">
          <div className="text-sm font-semibold">Today</div>
          <div className="text-xs text-muted">{new Date().toLocaleDateString("en-GB", { timeZone: "Asia/Kolkata", weekday: "long", day: "2-digit", month: "long" })} · IST</div>
        </div>
      </section>

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Tile label="Leads" value={n(total)} sub={`${n(new24)} new in 24h`} />
        <Tile label="With email" value={n(withEmail)} sub={total ? `${Math.round((withEmail / total) * 100)}% of leads` : undefined} tone="good" />
        <Tile label="Named contacts" value={n(named)} sub="contact_quality = named" />
        <Tile label="Markets" value={`${n(marketsScraped)} / ${n(marketsActive)}`} sub="scraped / active" />
        <Tile label="Runs ok" value={n(runsOk)} tone="good" />
        <Tile label="Runs failed" value={n(runsFailed)} tone={runsFailed ? "bad" : undefined} />
      </section>

      <section className="grid gap-4 lg:grid-cols-5">
        <div className="card p-4 lg:col-span-3">
          <div className="mb-2 flex items-baseline justify-between"><div className="tile-label">Leads per day · 30 days</div>
            <div className="text-xs text-muted">{n(days.reduce((a, b) => a + b.value, 0))} total</div></div>
          <BarChart points={days} />
        </div>
        <div className="card overflow-hidden lg:col-span-2">
          <table className="table">
            <thead><tr><th>Group</th><th className="text-right">Leads</th><th className="text-right">Emails</th></tr></thead>
            <tbody>
              {[...groups.entries()].map(([g, v]) => (
                <tr key={g}>
                  <td><Link className="link" href={`/leads?group=${encodeURIComponent(g)}`}>{g}</Link></td>
                  <td className="text-right tabular-nums">{n(v.leads)}</td>
                  <td className="text-right tabular-nums">{n(v.emails)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card overflow-x-auto">
        <div className="flex items-center justify-between px-4 pt-3"><div className="tile-label">Latest worker runs</div>
          <Link className="link text-xs" href="/runs">all runs →</Link></div>
        <table className="table mt-2">
          <thead><tr><th>Worker</th><th>Started</th><th>Status</th><th>Market</th><th className="text-right">New leads</th><th className="text-right">Duration</th></tr></thead>
          <tbody>
            {((runs.data ?? []) as WorkerRun[]).map((r) => (
              <tr key={r.run_id}>
                <td>{r.worker}</td><td className="whitespace-nowrap text-muted">{fmtDate(r.started_at)}</td>
                <td><StatusPill value={r.status} /></td>
                <td className="mono text-xs">{String(r.input?.market_id ?? r.counts?.market_id ?? "")}</td>
                <td className="text-right tabular-nums">{String(r.counts?.new_leads ?? "")}</td>
                <td className="text-right tabular-nums text-muted">{duration(r.started_at, r.finished_at)}</td>
              </tr>
            ))}
            {!runs.data?.length && <tr><td colSpan={6} className="text-muted">No runs yet.</td></tr>}
          </tbody>
        </table>
      </section>
    </main>
  );
}
