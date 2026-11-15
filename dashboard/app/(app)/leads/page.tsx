import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { GROUP_NAMES, ALL_NICHES, nichesOf } from "@/lib/niches";
import { LEAD_STATUSES, type Lead, type Market } from "@/lib/types";
import LeadsTable from "@/components/LeadsTable";

export const dynamic = "force-dynamic";
const PAGE = 50;

type SP = Record<string, string | string[] | undefined>;
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";

export default async function LeadsPage({ searchParams }: { searchParams: Promise<SP> }) {
  const sp = await searchParams;
  const f = {
    q: one(sp.q).trim(), group: one(sp.group), niche: one(sp.niche), market: one(sp.market),
    email: one(sp.email), quality: one(sp.quality), status: one(sp.status), score: one(sp.score),
    page: Math.max(1, parseInt(one(sp.page) || "1", 10) || 1),
  };
  const supabase = await createClient();

  let q = supabase.from("leads").select("*", { count: "exact" });
  if (f.q) q = q.ilike("business_name", `%${f.q.replace(/[%_]/g, "\\$&")}%`);
  if (f.niche) q = q.eq("niche", f.niche);
  else if (f.group) q = q.in("niche", nichesOf(f.group));
  if (f.market) q = q.eq("market_id", f.market);
  if (f.email === "yes") q = q.not("primary_email", "is", null).neq("primary_email", "");
  if (f.email === "no") q = q.or("primary_email.is.null,primary_email.eq.");
  if (f.quality) q = q.eq("contact_quality", f.quality);
  if (f.status) q = q.eq("status", f.status);
  if (f.score) q = q.gte("ticket_score", parseInt(f.score, 10) || 0);
  const from = (f.page - 1) * PAGE;
  q = q.order("ticket_score", { ascending: false, nullsFirst: false }).order("scraped_at", { ascending: false }).range(from, from + PAGE - 1);

  const [{ data, count, error }, markets] = await Promise.all([
    q,
    supabase.from("markets").select("market_id,city,country,niche,status").order("market_id"),
  ]);
  const leads = (data ?? []) as Lead[];
  const total = count ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE));
  const link = (p: number) => {
    const u = new URLSearchParams();
    Object.entries(f).forEach(([k, v]) => { if (v && k !== "page") u.set(k, String(v)); });
    u.set("page", String(p));
    return `/leads?${u}`;
  };

  return (
    <main className="space-y-4">
      <form className="card grid grid-cols-2 gap-2 p-3 sm:grid-cols-4 lg:grid-cols-9" method="get">
        <input name="q" defaultValue={f.q} placeholder="Search business…" className="input col-span-2" />
        <select name="group" defaultValue={f.group} className="input"><option value="">All groups</option>{GROUP_NAMES.map((g) => <option key={g}>{g}</option>)}</select>
        <select name="niche" defaultValue={f.niche} className="input"><option value="">All niches</option>{(f.group ? nichesOf(f.group) : ALL_NICHES).map((n) => <option key={n}>{n}</option>)}</select>
        <select name="market" defaultValue={f.market} className="input"><option value="">All markets</option>
          {((markets.data ?? []) as Market[]).map((m) => <option key={m.market_id} value={m.market_id}>{m.city} · {m.niche}</option>)}</select>
        <select name="email" defaultValue={f.email} className="input"><option value="">Email: any</option><option value="yes">Has email</option><option value="no">No email</option></select>
        <select name="quality" defaultValue={f.quality} className="input"><option value="">Quality: any</option><option>named</option><option>generic</option><option>none</option></select>
        <select name="status" defaultValue={f.status} className="input"><option value="">Status: any</option>{LEAD_STATUSES.map((s) => <option key={s}>{s}</option>)}</select>
        <div className="flex gap-2">
          <input name="score" type="number" min={0} max={100} defaultValue={f.score} placeholder="Min score" className="input w-full" />
          <button className="btn-primary">Go</button>
        </div>
      </form>

      <div className="flex items-center justify-between text-sm text-muted">
        <span>{total.toLocaleString("en-IN")} leads{error ? ` · ${error.message}` : ""}</span>
        <span className="flex items-center gap-2">
          {f.page > 1 && <Link className="btn" href={link(f.page - 1)}>← Prev</Link>}
          <span>page {f.page} / {pages}</span>
          {f.page < pages && <Link className="btn" href={link(f.page + 1)}>Next →</Link>}
        </span>
      </div>

      <LeadsTable leads={leads} />
    </main>
  );
}
