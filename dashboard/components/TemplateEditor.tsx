"use client";
import { useActionState, useEffect, useMemo, useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { ALL_NICHES, GROUPS, GROUP_NAMES } from "@/lib/niches";
import { PLACEHOLDERS, FOOTER, checkTemplate, renderTemplate, type Vars } from "@/lib/templates";
import { saveTemplate, duplicateTemplate, deleteTemplate, setTemplateApproved } from "@/app/(app)/templates/actions";

export type Template = {
  template_id: string; niche: string | null; step: number; subject: string | null; body: string; variant: "issue" | "no_issue";
  approved: boolean | null; author: string | null; approved_at: string | null; sends_7d: number | null; replies_7d: number | null;
};
type LeadLite = { lead_id: string; business_name: string; city: string | null; niche: string | null; top_issue: string | null; audit_summary: string | null; extra: { review_excerpts?: { text?: string }[] } | null };

export default function TemplateEditor({ template }: { template: Template | null }) {
  const [step, setStep] = useState(template?.step ?? 1);
  const [subject, setSubject] = useState(template?.subject ?? "");
  const [body, setBody] = useState(template?.body ?? "");
  const [variant, setVariant] = useState(template?.variant ?? "issue");
  const [niche, setNiche] = useState(template?.niche ?? "default");
  const bodyRef = useRef<HTMLTextAreaElement>(null);
  const subjRef = useRef<HTMLInputElement>(null);
  const [lastFocus, setLastFocus] = useState<"body" | "subject">("body");
  const [saveState, saveAction, saving] = useActionState(saveTemplate, undefined);
  const [apprState, apprAction, approving] = useActionState(setTemplateApproved, undefined);

  const check = useMemo(() => checkTemplate({ subject: step === 1 ? subject : null, body, step }), [subject, body, step]);
  const dirty = !!template && (subject !== (template.subject ?? "") || body !== template.body || variant !== template.variant || niche !== (template.niche ?? "default") || step !== template.step);

  // preview lead
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<LeadLite[]>([]);
  const [lead, setLead] = useState<LeadLite | null>(null);
  const [firstName, setFirstName] = useState<string | null>(null);
  useEffect(() => {
    if (!q.trim()) { setHits([]); return; }
    const sb = createClient(); let on = true;
    const t = setTimeout(async () => {
      const { data } = await sb.from("leads").select("lead_id,business_name,city,niche,top_issue,audit_summary,extra").ilike("business_name", `%${q.replace(/[%_]/g, "\\$&")}%`).limit(8);
      if (on) setHits((data ?? []) as LeadLite[]);
    }, 250);
    return () => { on = false; clearTimeout(t); };
  }, [q]);
  useEffect(() => {
    if (!lead) { setFirstName(null); return; }
    const sb = createClient();
    sb.from("contacts").select("contact_name").eq("lead_id", lead.lead_id).not("contact_name", "is", null).limit(1).maybeSingle()
      .then((r) => setFirstName(r.data?.contact_name ? String(r.data.contact_name).trim().split(/\s+/)[0] : null));
  }, [lead]);

  const vars: Vars = {
    first_name: firstName, business: lead?.business_name ?? "{business}", city: lead?.city ?? "{city}",
    top_issue: lead?.top_issue ?? (lead ? "" : "{top_issue}"), audit_summary: lead?.audit_summary ?? (lead ? "" : "{audit_summary}"),
    review_excerpt: lead?.extra?.review_excerpts?.[0]?.text ?? (lead ? "" : "{review_excerpt}"),
    sender_name: "Aryan", booking_link: "https://book.armedias.tech/aryan/intro",
  };

  const insert = (token: string) => {
    const el = lastFocus === "subject" && step === 1 ? subjRef.current : bodyRef.current;
    const set = lastFocus === "subject" && step === 1 ? setSubject : setBody;
    const val = lastFocus === "subject" && step === 1 ? subject : body;
    const s = el?.selectionStart ?? val.length, e = el?.selectionEnd ?? val.length;
    const next = val.slice(0, s) + `{${token}}` + val.slice(e);
    set(next);
    requestAnimationFrame(() => { el?.focus(); el?.setSelectionRange(s + token.length + 2, s + token.length + 2); });
  };

  return (
    <div className="space-y-4">
      <form action={saveAction} className="card space-y-3 p-4">
        {template && <input type="hidden" name="template_id" value={template.template_id} />}
        <div className="flex flex-wrap items-center gap-2">
          <div className="text-sm font-semibold">{template ? "Edit template" : "New template"}</div>
          {template && <span className="mono text-xs text-muted">{template.template_id}</span>}
          {template?.approved && !dirty && <span className="pill border-good/40 text-good">approved</span>}
          {dirty && <span className="pill border-warn/40 text-warn">unsaved · saving resets approval</span>}
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          <label className="space-y-1"><span className="tile-label">Niche</span>
            <select name="niche" value={niche} onChange={(e) => setNiche(e.target.value)} className="input w-full">
              <option value="default">default (any niche)</option>
              {GROUP_NAMES.map((g) => <optgroup key={g} label={g}>{Object.keys(GROUPS[g]).map((n) => <option key={n} value={n}>{n}</option>)}</optgroup>)}
              {!ALL_NICHES.includes(niche) && niche !== "default" && <option value={niche}>{niche}</option>}
            </select></label>
          <label className="space-y-1"><span className="tile-label">Step</span>
            <select name="step" value={step} onChange={(e) => setStep(parseInt(e.target.value, 10))} className="input w-full">
              <option value={1}>1 · first email</option><option value={2}>2 · follow-up</option><option value={3}>3 · last nudge</option></select></label>
          <label className="space-y-1"><span className="tile-label">Variant</span>
            <select name="variant" value={variant} onChange={(e) => setVariant(e.target.value as Template["variant"])} className="input w-full">
              <option value="issue">issue (audit found something)</option><option value="no_issue">no_issue (site looks fine)</option></select></label>
        </div>
        {step === 1 && (
          <label className="block space-y-1"><span className="tile-label">Subject <span className={subject.length > 60 ? "text-bad" : "text-muted"}>({subject.length}/60)</span></span>
            <input ref={subjRef} name="subject" value={subject} onChange={(e) => setSubject(e.target.value)} onFocus={() => setLastFocus("subject")} className="input w-full" placeholder="quick note about {business}'s website" /></label>
        )}
        <div className="flex flex-wrap gap-1.5">
          {PLACEHOLDERS.map((p) => (
            <button type="button" key={p.key} onClick={() => insert(p.key)} title={p.hint} className="rounded-full border border-line bg-bg2 px-2 py-0.5 text-[11px] text-accent2 hover:border-accent/60">{`{${p.key}}`}</button>
          ))}
        </div>
        <label className="block space-y-1"><span className="tile-label">Body <span className="text-muted">({body.trim() ? body.trim().split(/\s+/).length : 0} words)</span></span>
          <textarea ref={bodyRef} name="body" value={body} onChange={(e) => setBody(e.target.value)} onFocus={() => setLastFocus("body")} rows={10} className="input w-full font-sans leading-6" placeholder={"Hi {first_name|there},\n\n..."} /></label>
        <div className="flex flex-wrap items-center gap-2">
          <button className="btn-primary" disabled={saving}>{saving ? "Saving…" : template ? "Save" : "Create"}</button>
          {saveState?.error && <span className="text-sm text-bad">{saveState.error}</span>}
          {saveState?.ok && <span className="text-sm text-good">{saveState.ok}</span>}
        </div>
      </form>

      {template && (
        <div className="card flex flex-wrap items-center gap-2 p-3">
          <form action={apprAction} className="contents">
            <input type="hidden" name="template_id" value={template.template_id} />
            <input type="hidden" name="approve" value={template.approved ? "0" : "1"} />
            <button className={template.approved ? "btn" : "btn-primary"} disabled={approving || dirty || (!template.approved && check.hard.length > 0)}
              title={dirty ? "save first" : check.hard.length ? "fix hard issues first" : ""}>
              {approving ? "…" : template.approved ? "Remove approval" : "Approve"}
            </button>
          </form>
          <form action={duplicateTemplate} className="contents"><input type="hidden" name="template_id" value={template.template_id} /><button className="btn">Duplicate</button></form>
          <form action={deleteTemplate} className="contents" onSubmit={(e) => { if (!confirm(`Delete ${template.template_id}?`)) e.preventDefault(); }}>
            <input type="hidden" name="template_id" value={template.template_id} /><button className="btn text-bad">Delete</button></form>
          {apprState?.error && <span className="text-sm text-bad">{apprState.error}</span>}
          {apprState?.ok && <span className="text-sm text-good">{apprState.ok}</span>}
          <span className="ml-auto text-xs text-muted">sending stays in Telegram</span>
        </div>
      )}

      <div className="card p-4">
        <div className="mb-2 flex items-center gap-2"><div className="tile-label">Checker</div>
          <span className={`pill ${check.hard.length ? "border-bad/40 text-bad" : "border-good/40 text-good"}`}>{check.hard.length ? `${check.hard.length} hard` : "hard rules pass"}</span>
          <span className={`pill ${check.soft.length ? "border-warn/40 text-warn" : "border-line text-muted"}`}>{check.soft.length} soft</span></div>
        {check.hard.map((h) => <div key={h} className="text-sm text-bad">✕ {h}</div>)}
        {check.soft.map((s) => <div key={s} className="text-sm text-warn">△ {s}</div>)}
        {!check.hard.length && !check.soft.length && <div className="text-sm text-muted">Clean.</div>}
      </div>

      <div className="card p-4">
        <div className="mb-2 flex flex-wrap items-center gap-2"><div className="tile-label">Preview</div>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="search a business to preview with real data…" className="input min-w-[240px] flex-1" />
          {lead && <button type="button" className="btn !py-1 text-xs" onClick={() => { setLead(null); setQ(""); }}>clear</button>}</div>
        {hits.length > 0 && !lead && (
          <div className="mb-2 max-h-48 overflow-y-auto rounded-md border border-line">
            {hits.map((h) => <button type="button" key={h.lead_id} onClick={() => { setLead(h); setHits([]); setQ(h.business_name); }} className="block w-full px-3 py-1.5 text-left text-sm hover:bg-panel2">{h.business_name} <span className="text-xs text-muted">{h.city} · {h.niche}{h.top_issue ? " · audited" : ""}</span></button>)}
          </div>
        )}
        {lead && <div className="mb-2 text-xs text-muted">{lead.business_name} · first name {firstName ?? "unknown → “there”"} · top issue {lead.top_issue ? "✓" : "none"} · review excerpt {lead.extra?.review_excerpts?.[0]?.text ? "✓" : "none"}</div>}
        <div className="rounded-md border border-line bg-bg p-3 text-sm">
          {step === 1 && <div className="mb-2 border-b border-line pb-2"><span className="text-muted">Subject: </span>{renderTemplate(subject, vars) || <span className="text-muted">(empty)</span>}</div>}
          <pre className="whitespace-pre-wrap font-sans leading-6">{renderTemplate(body, vars) || <span className="text-muted">(empty body)</span>}</pre>
          <pre className="mt-3 whitespace-pre-wrap border-t border-line/60 pt-2 font-sans text-xs text-muted">{FOOTER}</pre>
        </div>
        <div className="mt-1 text-[11px] text-muted">Footer is appended by the sender on the VPS (postal address + unsubscribe line); it is not part of the template.</div>
      </div>
    </div>
  );
}
