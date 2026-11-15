import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { groupOf, GROUP_NAMES } from "@/lib/niches";
import { timeAgo, n } from "@/lib/format";
import StatusPill from "@/components/StatusPill";
import { setMarketStatus } from "./actions";
import AddMarketForm from "@/components/AddMarketForm";
import type { Market } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function MarketsPage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const sp = await searchParams;
  const supabase = await createClient();
  const [{ data: markets }, { data: leadRows }] = await Promise.all([
    supabase.from("markets").select("*").order("last_scraped_at", { ascending: false, nullsFirst: false }).order("market_id"),
    supabase.from("leads").select("market_id").limit(50000),
  ]);
  const counts = new Map<string, number>();
  for (const r of leadRows ?? []) counts.set(r.market_id as string, (counts.get(r.market_id as string) ?? 0) + 1);
  let rows = (markets ?? []) as Market[];
  const g = sp.group ?? "", st = sp.status ?? "";
  if (g) rows = rows.filter((m) => groupOf(m.niche) === g);
  if (st) rows = rows.filter((m) => m.status === st);
  const active = (markets ?? []).filter((m) => m.status === "active").length;

  return (
    <main className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="card p-4 lg:col-span-1">
          <div className="tile-label mb-2">Add a market</div>
          <AddMarketForm />
        </div>
        <div className="card p-4 lg:col-span-2 text-sm text-muted">
          <div className="tile-label mb-2">How markets flow</div>
          <p>{n(markets?.length)} markets, {n(active)} active. Each night the scrape workflow picks the 3 active markets scraped longest ago (or never), runs one GitHub Actions job per market with website-email extraction, then mirrors new leads to Sheets. Pausing a market removes it from that pick. Everything else (audits, outreach) is gated by later phases.</p>
          <form className="mt-3 flex flex-wrap gap-2" method="get">
            <select name="group" defaultValue={g} className="input"><option value="">All groups</option>{GROUP_NAMES.map((x) => <option key={x}>{x}</option>)}</select>
            <select name="status" defaultValue={st} className="input"><option value="">All statuses</option>{["active", "paused", "proposed", "done"].map((x) => <option key={x}>{x}</option>)}</select>
            <button className="btn">Filter</button>
          </form>
        </div>
      </div>

      <div className="card overflow-x-auto">
        <table className="table min-w-[820px]">
          <thead><tr><th>Market</th><th>Group</th><th>Status</th><th className="text-right">Leads</th><th>Last scraped</th><th className="text-right">Action</th></tr></thead>
          <tbody>
            {rows.map((m) => (
              <tr key={m.market_id}>
                <td><div className="font-medium">{m.city}, {m.country}</div><div className="text-xs text-muted">{m.niche} · <span className="mono">{m.market_id}</span></div></td>
                <td className="text-xs text-muted">{groupOf(m.niche)}</td>
                <td><StatusPill value={m.status} /></td>
                <td className="text-right tabular-nums"><Link className="link" href={`/leads?market=${m.market_id}`}>{n(counts.get(m.market_id))}</Link></td>
                <td className="whitespace-nowrap text-muted">{timeAgo(m.last_scraped_at)}</td>
                <td className="text-right">
                  <form action={setMarketStatus} className="inline">
                    <input type="hidden" name="market_id" value={m.market_id} />
                    <input type="hidden" name="status" value={m.status === "active" ? "paused" : "active"} />
                    <button className="btn !py-1 text-xs">{m.status === "active" ? "Pause" : "Activate"}</button>
                  </form>
                </td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={6} className="text-muted">No markets.</td></tr>}
          </tbody>
        </table>
      </div>
    </main>
  );
}
