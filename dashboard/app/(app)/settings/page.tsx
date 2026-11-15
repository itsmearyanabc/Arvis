import { createClient } from "@/lib/supabase/server";
import { n } from "@/lib/format";

export const dynamic = "force-dynamic";

function Flag({ name, on, note }: { name: string; on: boolean; note: string }) {
  return (
    <div className="flex items-start gap-3 border-t border-line/60 py-2 text-sm">
      <span className={`mt-1 inline-block h-2.5 w-2.5 shrink-0 rounded-full ${on ? "bg-good" : "bg-line"}`} />
      <div><div className="mono text-xs">{name}</div><div className="text-xs text-muted">{on ? "configured" : "not set"} · {note}</div></div>
    </div>
  );
}

export default async function SettingsPage() {
  const supabase = await createClient();
  const [{ data: { user } }, mailboxes, monitors, templates, events] = await Promise.all([
    supabase.auth.getUser(),
    supabase.from("mailboxes").select("mailbox", { count: "exact", head: true }),
    supabase.from("monitors").select("monitor_id", { count: "exact", head: true }),
    supabase.from("templates").select("template_id", { count: "exact", head: true }),
    supabase.from("brain_events").select("id", { count: "exact", head: true }),
  ]);
  let projectRef = "";
  try { projectRef = new URL(process.env.NEXT_PUBLIC_SUPABASE_URL!).hostname.split(".")[0]; } catch {}

  return (
    <main className="grid gap-4 lg:grid-cols-2">
      <section className="card p-4">
        <div className="tile-label mb-1">Dashboard environment (read-only flags, no values)</div>
        <Flag name="NEXT_PUBLIC_SUPABASE_URL" on={!!process.env.NEXT_PUBLIC_SUPABASE_URL} note={projectRef ? `project ${projectRef}` : "Supabase project URL"} />
        <Flag name="NEXT_PUBLIC_SUPABASE_ANON_KEY" on={!!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY} note="publishable key, browser + RLS" />
        <Flag name="SUPABASE_SERVICE_KEY" on={!!process.env.SUPABASE_SERVICE_KEY} note="server only: /api/unsubscribe, /api/webhooks/calcom" />
        <Flag name="UNSUBSCRIBE_SECRET" on={!!process.env.UNSUBSCRIBE_SECRET} note="signs unsubscribe tokens" />
        <Flag name="CALCOM_WEBHOOK_SECRET" on={!!process.env.CALCOM_WEBHOOK_SECRET} note="verifies Cal.com webhook signatures (optional until Phase 4)" />
        <Flag name="NEXT_PUBLIC_SITE_URL" on={!!process.env.NEXT_PUBLIC_SITE_URL} note="public URL used in unsubscribe links" />
      </section>
      <section className="card p-4">
        <div className="tile-label mb-1">Integrations (from the database)</div>
        <Flag name="brain_events" on={!events.error} note={events.error ? "run supabase/migrations_002_brain_events.sql" : `${n(events.count)} events logged`} />
        <Flag name="mailboxes" on={(mailboxes.count ?? 0) > 0} note={`${n(mailboxes.count)} mailboxes (Zoho on armedias.tech, Phase 3)`} />
        <Flag name="templates" on={(templates.count ?? 0) > 0} note={`${n(templates.count)} templates (Phase 3)`} />
        <Flag name="monitors" on={(monitors.count ?? 0) > 0} note={`${n(monitors.count)} uptime monitors (Phase 5)`} />
        <div className="mt-4 tile-label mb-1">Session</div>
        <div className="text-sm">{user?.email}</div>
        <div className="text-xs text-muted">Supabase Auth · RLS: authenticated full access, anon none.</div>
      </section>
      <section className="card p-4 lg:col-span-2 text-sm text-muted">
        <div className="tile-label mb-1">Guardrails</div>
        <ul className="list-disc space-y-1 pl-5">
          <li>This panel only reads and edits ARVIS&apos;s own Supabase data. It never scrapes, sends email, or calls third parties.</li>
          <li>Workers run on GitHub Actions; the brain runs on the VPS. Dispatch from Telegram or <span className="mono">arvisctl</span>, not from here.</li>
          <li>Social links are stored for manual review only. No LinkedIn or Instagram automation anywhere.</li>
        </ul>
      </section>
    </main>
  );
}
