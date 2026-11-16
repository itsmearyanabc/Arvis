import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { checkEmailDns } from "@/lib/dns";
import { fmtDate, n } from "@/lib/format";
import StatusPill from "@/components/StatusPill";
import SequencesTable, { type SequenceRow } from "@/components/SequencesTable";

export const dynamic = "force-dynamic";

const TABS: Record<string, string[]> = {
  drafts: ["draft", "approved"],
  sent: ["step1_sent", "step2_sent", "step3_sent", "done_no_reply"],
  stopped: ["stopped_reply", "stopped_unsub", "bounced", "snoozed", "expired", "skipped"],
};

type Reply = { reply_id: string; received_at: string; from_email: string | null; category: string | null; reply_summary: string | null;
  suggested_action: string | null; handled_by_aryan: boolean | null; sequences: { contact_email: string; step1_subject: string | null } | null; leads: { business_name: string } | null };

export default async function EmailPage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const sp = await searchParams;
  const tab = TABS[sp.tab ?? ""] ? (sp.tab as string) : "drafts";
  const supabase = await createClient();
  const [seqs, counts, replies, mailboxes, dns] = await Promise.all([
    supabase.from("sequences").select("*, leads(business_name, city, niche)").in("status", TABS[tab]).order("drafted_at", { ascending: false }).limit(200),
    Promise.all(Object.entries(TABS).map(async ([k, st]) => [k, (await supabase.from("sequences").select("sequence_id", { count: "exact", head: true }).in("status", st)).count ?? 0] as const)),
    supabase.from("replies").select("*, sequences(contact_email, step1_subject), leads(business_name)").order("received_at", { ascending: false }).limit(50),
    supabase.from("mailboxes").select("mailbox,address,daily_cap,sent_today,paused,warmup_until"),
    checkEmailDns(),
  ]);
  const countMap = Object.fromEntries(counts);

  return (
    <main className="space-y-4">
      <section className="grid gap-4 lg:grid-cols-3">
        <div className="card p-4 lg:col-span-2">
          <div className="tile-label mb-2">Cold-email readiness · armedias.tech</div>
          <div className="grid gap-x-6 sm:grid-cols-2">
            {dns.map((c) => (
              <div key={c.label} className="flex items-start gap-2 border-t border-line/60 py-1.5 text-sm">
                <span className={`mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full ${c.ok ? "bg-good" : "bg-bad"}`} />
                <div className="min-w-0"><div>{c.label}</div><div className="mono truncate text-xs text-muted" title={c.detail}>{c.detail}</div></div>
              </div>
            ))}
            <div className="flex items-start gap-2 border-t border-line/60 py-1.5 text-sm"><span className="mt-1.5 inline-block h-2 w-2 rounded-full bg-good" /><div>Zoho app password<div className="text-xs text-muted">configured on VPS</div></div></div>
            <div className="flex items-start gap-2 border-t border-line/60 py-1.5 text-sm"><span className="mt-1.5 inline-block h-2 w-2 rounded-full bg-good" /><div>Postal address in footer<div className="text-xs text-muted">configured on VPS</div></div></div>
          </div>
          <p className="mt-3 text-xs text-muted">DNS read live from dns.google. Sending happens only from the brain after you say “send” in Telegram; this page has no send button.</p>
        </div>
        <div className="card p-4">
          <div className="tile-label mb-2">Mailboxes</div>
          {!mailboxes.data?.length && <div className="text-sm text-muted">None registered yet (Phase 3).</div>}
          {mailboxes.data?.map((m) => (
            <div key={m.mailbox} className="border-t border-line/60 py-1.5 text-sm">
              <div className="flex justify-between"><span>{m.address}</span><StatusPill value={m.paused ? "paused" : "active"} /></div>
              <div className="text-xs text-muted">{m.sent_today ?? 0} / {m.daily_cap ?? 0} today{m.warmup_until ? ` · warm-up until ${m.warmup_until}` : ""}</div>
            </div>
          ))}
        </div>
      </section>

      <div className="flex flex-wrap items-center gap-1 text-sm">
        {Object.keys(TABS).map((t) => (
          <Link key={t} href={`/email?tab=${t}`} className={`rounded-md px-3 py-1.5 capitalize ${t === tab ? "bg-panel2 text-accent" : "text-muted hover:text-text"}`}>
            {t} <span className="text-xs text-muted">{n(countMap[t])}</span>
          </Link>
        ))}
      </div>
      <SequencesTable rows={(seqs.data ?? []) as SequenceRow[]} tab={tab} />

      <section className="card overflow-x-auto">
        <div className="px-4 pt-3 tile-label">Replies · latest 50</div>
        <table className="table mt-2 min-w-[760px]">
          <thead><tr><th>Received</th><th>From</th><th>Business</th><th>Category</th><th>Summary</th><th>Suggested</th><th>Handled</th></tr></thead>
          <tbody>
            {((replies.data ?? []) as unknown as Reply[]).map((r) => (
              <tr key={r.reply_id}>
                <td className="whitespace-nowrap text-muted">{fmtDate(r.received_at)}</td>
                <td className="text-xs">{r.from_email ?? r.sequences?.contact_email}</td>
                <td>{r.leads?.business_name ?? "–"}</td>
                <td><StatusPill value={r.category} /></td>
                <td className="max-w-[320px] text-xs">{r.reply_summary}</td>
                <td className="text-xs text-muted">{r.suggested_action}</td>
                <td>{r.handled_by_aryan ? "✓" : "–"}</td>
              </tr>
            ))}
            {!replies.data?.length && <tr><td colSpan={7} className="text-muted">No replies yet.</td></tr>}
          </tbody>
        </table>
      </section>
    </main>
  );
}
