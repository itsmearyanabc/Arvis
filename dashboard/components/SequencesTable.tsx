"use client";
import { useState } from "react";
import StatusPill from "@/components/StatusPill";
import { fmtDate } from "@/lib/format";
import { setApproved } from "@/app/(app)/email/actions";

export type SequenceRow = {
  sequence_id: string; lead_id: string | null; contact_email: string; template_id: string | null; mailbox: string | null;
  step1_subject: string | null; step1_body: string | null; step2_body: string | null; step3_body: string | null;
  status: string; approved_by_aryan: boolean | null; approved_at: string | null; drafted_at: string | null;
  step1_sent_at: string | null; step2_sent_at: string | null; step3_sent_at: string | null; edit_note: string | null;
  leads: { business_name: string; city: string | null; niche: string | null } | null;
};

export default function SequencesTable({ rows, tab }: { rows: SequenceRow[]; tab: string }) {
  const [open, setOpen] = useState<SequenceRow | null>(null);
  return (
    <>
      <div className="card overflow-x-auto">
        <table className="table min-w-[900px]">
          <thead><tr><th>Status</th><th>To</th><th>Business</th><th>Subject</th><th>Step 1 sent</th><th>Mailbox</th><th>Note</th>{tab === "drafts" && <th className="text-right">Approve</th>}</tr></thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.sequence_id} className="cursor-pointer" onClick={() => setOpen(s)}>
                <td><StatusPill value={s.status} /></td>
                <td className="text-xs">{s.contact_email}</td>
                <td>{s.leads?.business_name ?? s.lead_id}<div className="text-xs text-muted">{s.leads?.city} · {s.leads?.niche}</div></td>
                <td className="max-w-[280px] truncate">{s.step1_subject ?? "–"}</td>
                <td className="whitespace-nowrap text-muted">{fmtDate(s.step1_sent_at)}</td>
                <td className="text-xs">{s.mailbox ?? "–"}</td>
                <td className="max-w-[200px] truncate text-xs text-muted">{s.edit_note}</td>
                {tab === "drafts" && (
                  <td className="text-right" onClick={(e) => e.stopPropagation()}>
                    <form action={setApproved}>
                      <input type="hidden" name="sequence_id" value={s.sequence_id} />
                      <input type="hidden" name="approve" value={s.approved_by_aryan ? "0" : "1"} />
                      <button className={`btn !py-1 text-xs ${s.approved_by_aryan ? "text-good" : ""}`}>{s.approved_by_aryan ? "Approved ✓" : "Approve"}</button>
                    </form>
                  </td>
                )}
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={8} className="text-muted">Nothing in {tab}. Drafts are created by the brain (Phase 3); sending needs your “send” in Telegram.</td></tr>}
          </tbody>
        </table>
      </div>
      {open && (
        <div className="fixed inset-0 z-40 flex justify-end bg-black/50" onClick={() => setOpen(null)}>
          <aside className="h-full w-full max-w-xl overflow-y-auto border-l border-line bg-bg2 p-5" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between gap-3">
              <div><div className="text-lg font-semibold">{open.step1_subject ?? "(no subject)"}</div>
                <div className="text-sm text-muted">to {open.contact_email} · {open.leads?.business_name} · <StatusPill value={open.status} /></div></div>
              <button className="btn" onClick={() => setOpen(null)}>Close</button>
            </div>
            <div className="mt-3 text-xs text-muted">template {open.template_id ?? "–"} · mailbox {open.mailbox ?? "–"} · drafted {fmtDate(open.drafted_at)}{open.approved_at ? ` · approved ${fmtDate(open.approved_at)}` : ""}</div>
            {open.edit_note && <div className="mt-2 rounded-md border border-warn/40 p-2 text-sm text-warn">{open.edit_note}</div>}
            {[["Step 1", open.step1_body, open.step1_sent_at], ["Step 2", open.step2_body, open.step2_sent_at], ["Step 3", open.step3_body, open.step3_sent_at]].map(([k, body, sent]) => (
              <section key={k as string} className="mt-4">
                <div className="tile-label mb-1">{k} {sent ? <span className="normal-case tracking-normal text-good">· sent {fmtDate(sent as string)}</span> : null}</div>
                <pre className="whitespace-pre-wrap rounded-md border border-line bg-bg p-3 font-sans text-sm">{(body as string) || "–"}</pre>
              </section>
            ))}
          </aside>
        </div>
      )}
    </>
  );
}
