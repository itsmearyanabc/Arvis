import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { groupOf } from "@/lib/niches";
import { replyRate } from "@/lib/templates";
import { fmtDate } from "@/lib/format";
import TemplateEditor, { type Template } from "@/components/TemplateEditor";

export const dynamic = "force-dynamic";

export default async function TemplatesPage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const sp = await searchParams;
  const supabase = await createClient();
  const { data, error } = await supabase.from("templates").select("*").order("niche").order("step").order("variant");
  const templates = (data ?? []) as Template[];
  const selected = sp.id ? templates.find((t) => t.template_id === sp.id) ?? null : null;
  const creating = sp.new === "1";

  const byNiche = new Map<string, Template[]>();
  for (const t of templates) { const k = t.niche || "default"; byNiche.set(k, [...(byNiche.get(k) ?? []), t]); }

  return (
    <main className="grid gap-4 xl:grid-cols-5">
      <section className="space-y-3 xl:col-span-2">
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted">{templates.length} templates · {templates.filter((t) => t.approved).length} approved{error ? ` · ${error.message}` : ""}</div>
          <Link href="/templates?new=1" className="btn-primary">New template</Link>
        </div>
        {!templates.length && <div className="card p-4 text-sm text-muted">No templates yet. Write the first one; the brain only drafts from approved templates and sends only after you say “send” in Telegram.</div>}
        {[...byNiche.entries()].map(([niche, list]) => (
          <div key={niche} className="card overflow-hidden">
            <div className="flex items-baseline justify-between px-4 pt-3 pb-1"><div className="tile-label">{niche}</div><div className="text-xs text-muted">{niche === "default" ? "fallback for every niche" : groupOf(niche)}</div></div>
            <table className="table">
              <thead><tr><th>Step</th><th>Variant</th><th>Subject / first line</th><th className="text-right">7d</th><th></th></tr></thead>
              <tbody>
                {list.map((t) => (
                  <tr key={t.template_id} className={t.template_id === sp.id ? "bg-panel2/60" : ""}>
                    <td className="whitespace-nowrap">{t.step}</td>
                    <td className="text-xs text-muted">{t.variant}</td>
                    <td className="max-w-[260px]"><Link href={`/templates?id=${t.template_id}`} className="link block truncate">{t.subject || t.body.split("\n")[0] || t.template_id}</Link>
                      <div className="text-[11px] text-muted">{t.approved ? `approved ${fmtDate(t.approved_at)}` : "draft"} · <span className="mono">{t.template_id}</span></div></td>
                    <td className="whitespace-nowrap text-right text-xs tabular-nums" title="replies / sends, last 7 days">{t.replies_7d ?? 0}/{t.sends_7d ?? 0} · {replyRate(t)}</td>
                    <td className="text-right">{t.approved ? <span className="pill border-good/40 text-good">approved</span> : <span className="pill border-line text-muted">draft</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </section>
      <section className="xl:col-span-3">
        {selected || creating
          ? <TemplateEditor key={selected?.template_id ?? "new"} template={selected} />
          : <div className="card p-6 text-sm text-muted">Pick a template on the left or create a new one. Approve is blocked while a hard rule fails (pricing, team size, more than one link, HTML, long or shouting subject, unknown placeholder). Sending never happens from here.</div>}
      </section>
    </main>
  );
}
