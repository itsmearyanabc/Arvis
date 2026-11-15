"use client";
import { useEffect, useState } from "react";
import type { Lead, Audit, Contact } from "@/lib/types";
import { createClient } from "@/lib/supabase/client";
import { groupOf } from "@/lib/niches";
import { host, fmtDate } from "@/lib/format";
import StatusPill from "@/components/StatusPill";

function Ext({ href, children }: { href: string | null | undefined; children: React.ReactNode }) {
  if (!href) return <span className="text-muted">–</span>;
  const h = href.startsWith("http") ? href : `https://${href}`;
  return <a className="link" href={h} target="_blank" rel="noopener noreferrer nofollow">{children}</a>;
}

export default function LeadsTable({ leads }: { leads: Lead[] }) {
  const [open, setOpen] = useState<Lead | null>(null);
  return (
    <>
      <div className="card overflow-x-auto">
        <table className="table min-w-[1100px]">
          <thead><tr>
            <th>Business</th><th>Market</th><th>Group</th><th className="text-right">Score</th><th>Quality</th>
            <th>Email</th><th>Source</th><th>Website</th><th>Phone</th><th>Instagram</th><th>Status</th><th>Maps</th>
          </tr></thead>
          <tbody>
            {leads.map((l) => (
              <tr key={l.lead_id} className="cursor-pointer" onClick={() => setOpen(l)}>
                <td className="max-w-[260px]"><div className="truncate font-medium">{l.business_name}</div>
                  <div className="truncate text-xs text-muted">{l.rating ?? "–"}★ · {l.review_count ?? 0} reviews</div></td>
                <td className="whitespace-nowrap text-xs">{l.city}<div className="text-muted">{l.niche}</div></td>
                <td className="whitespace-nowrap text-xs text-muted">{groupOf(l.niche)}</td>
                <td className="text-right tabular-nums">{l.ticket_score ?? 0}</td>
                <td><StatusPill value={l.contact_quality} /></td>
                <td className="max-w-[220px] truncate" onClick={(e) => e.stopPropagation()}>
                  {l.primary_email ? <a className="link" href={`mailto:${l.primary_email}`}>{l.primary_email}</a> : <span className="text-muted">–</span>}</td>
                <td className="text-xs text-muted">{l.email_source ?? "–"}</td>
                <td className="max-w-[160px] truncate" onClick={(e) => e.stopPropagation()}><Ext href={l.website}>{host(l.website)}</Ext></td>
                <td className="whitespace-nowrap text-xs">{l.phone ?? "–"}</td>
                <td onClick={(e) => e.stopPropagation()}>{l.instagram_url ? <Ext href={l.instagram_url}>@{l.instagram_url.replace(/\/$/, "").split("/").pop()}</Ext> : <span className="text-muted">–</span>}</td>
                <td><StatusPill value={l.status} /></td>
                <td onClick={(e) => e.stopPropagation()}><Ext href={l.maps_url}>{l.source === "google_maps" ? "Maps ↗" : l.source}</Ext></td>
              </tr>
            ))}
            {!leads.length && <tr><td colSpan={12} className="text-muted">No leads match.</td></tr>}
          </tbody>
        </table>
      </div>
      {open && <LeadDrawer lead={open} onClose={() => setOpen(null)} />}
    </>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return <div className="flex gap-3 border-t border-line/60 py-1.5 text-sm"><span className="w-36 shrink-0 text-muted">{k}</span><span className="min-w-0 break-words">{v ?? "–"}</span></div>;
}

function LeadDrawer({ lead, onClose }: { lead: Lead; onClose: () => void }) {
  const [audits, setAudits] = useState<Audit[] | null>(null);
  const [contacts, setContacts] = useState<Contact[] | null>(null);
  useEffect(() => {
    const sb = createClient();
    sb.from("audits").select("*").eq("lead_id", lead.lead_id).order("checked_at", { ascending: false }).then((r) => setAudits((r.data ?? []) as Audit[]));
    sb.from("contacts").select("*").eq("lead_id", lead.lead_id).then((r) => setContacts((r.data ?? []) as Contact[]));
  }, [lead.lead_id]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey); return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/50" onClick={onClose}>
      <aside className="h-full w-full max-w-xl overflow-y-auto border-l border-line bg-bg2 p-5" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3">
          <div><div className="text-lg font-semibold">{lead.business_name}</div>
            <div className="text-sm text-muted">{lead.niche} · {lead.city}, {lead.country} · {groupOf(lead.niche)}</div></div>
          <button className="btn" onClick={onClose}>Close</button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-sm">
          <Ext href={lead.maps_url}>Google Maps ↗</Ext><Ext href={lead.website}>Website ↗</Ext>
          <Ext href={lead.instagram_url}>Instagram ↗</Ext><Ext href={lead.facebook_url}>Facebook ↗</Ext><Ext href={lead.linkedin_url}>LinkedIn ↗</Ext>
        </div>
        <section className="mt-4">
          <div className="tile-label mb-1">Lead</div>
          <Row k="lead_id" v={<span className="mono text-xs">{lead.lead_id}</span>} />
          <Row k="Market" v={<span className="mono text-xs">{lead.market_id}</span>} />
          <Row k="Status" v={<StatusPill value={lead.status} />} />
          <Row k="Scores" v={`ticket ${lead.ticket_score ?? 0} · fit ${lead.fit_score ?? 0}`} />
          <Row k="Rating" v={`${lead.rating ?? "–"}★ · ${lead.review_count ?? 0} reviews`} />
          <Row k="Email" v={lead.primary_email ? <a className="link" href={`mailto:${lead.primary_email}`}>{lead.primary_email}</a> : null} />
          <Row k="Email source" v={lead.email_source} />
          <Row k="Contact quality" v={<StatusPill value={lead.contact_quality} />} />
          <Row k="Phone" v={lead.phone} />
          <Row k="Address" v={lead.address} />
          <Row k="Runs Meta ads" v={lead.runs_meta_ads === null ? "unknown" : lead.runs_meta_ads ? "yes" : "no"} />
          <Row k="Top issue" v={lead.top_issue} />
          <Row k="Audit summary" v={lead.audit_summary} />
          <Row k="Parked reason" v={lead.parked_reason} />
          <Row k="Notes" v={lead.notes} />
          <Row k="Scraped" v={fmtDate(lead.scraped_at)} />
          <Row k="Updated" v={fmtDate(lead.updated_at)} />
        </section>
        <section className="mt-5">
          <div className="tile-label mb-1">Audits {audits && `(${audits.length})`}</div>
          {audits === null ? <div className="text-sm text-muted">Loading…</div> : !audits.length ? <div className="text-sm text-muted">No audit yet.</div> :
            audits.map((a) => (
              <div key={a.audit_id} className="card mt-2 p-3 text-sm">
                <div className="mb-1 flex justify-between text-xs text-muted"><span>{fmtDate(a.checked_at)}</span><StatusPill value={a.site_status} /></div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:grid-cols-3">
                  <span>mobile {a.mobile_score ?? "–"}</span><span>perf {a.perf_score ?? "–"}</span><span>LCP {a.lcp_s ?? "–"}s</span>
                  <span>SSL {a.ssl_ok ? "ok" : "no"}</span><span>CMS {a.cms ?? "–"}</span><span>© {a.copyright_year ?? "–"}</span>
                  <span>title {a.has_title ? "✓" : "✗"}</span><span>meta {a.has_meta_desc ? "✓" : "✗"}</span><span>h1 ×{a.h1_count ?? "–"}</span>
                  <span>form {a.contact_form ? "✓" : "✗"}</span><span>booking {a.booking_widget ? "✓" : "✗"}</span><span>pixel {a.meta_pixel ? "✓" : "✗"}</span>
                </div>
                {a.top_issue && <div className="mt-2"><span className="text-muted">Top issue: </span>{a.top_issue}</div>}
                {a.audit_summary && <div className="mt-1 text-muted">{a.audit_summary}</div>}
              </div>
            ))}
        </section>
        <section className="mt-5">
          <div className="tile-label mb-1">Contacts {contacts && `(${contacts.length})`}</div>
          {contacts === null ? <div className="text-sm text-muted">Loading…</div> : !contacts.length ? <div className="text-sm text-muted">No contacts yet.</div> :
            contacts.map((c) => (
              <div key={c.contact_id} className="card mt-2 p-3 text-sm">
                <div className="font-medium">{c.contact_name ?? "(no name)"} <span className="text-muted">{c.role}</span></div>
                <div className="text-xs">{c.email} · {c.email_status ?? "unknown"} · {c.email_source ?? "–"} · <StatusPill value={c.contact_quality} /></div>
              </div>
            ))}
        </section>
      </aside>
    </div>
  );
}
