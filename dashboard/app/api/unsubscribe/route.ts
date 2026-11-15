import { NextResponse, type NextRequest } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { verifyUnsubscribeToken } from "@/lib/unsubscribe";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const page = (title: string, body: string, status = 200) =>
  new NextResponse(
    `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>${title}</title>
<style>body{font-family:system-ui,sans-serif;background:#07090f;color:#e6ebf2;display:grid;place-items:center;min-height:100dvh;margin:0;padding:24px}main{max-width:460px;text-align:center}h1{font-size:20px}p{color:#8591a3}</style></head>
<body><main><h1>${title}</h1><p>${body}</p></main></body></html>`,
    { status, headers: { "content-type": "text/html; charset=utf-8" } },
  );

/**
 * GET /api/unsubscribe?token=<sequence_id>.<hmac>
 * Verifies the token, records the contact's email (and domain) in `unsubscribes`,
 * stops the sequence and marks the lead unsubscribed. Idempotent.
 */
export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get("token") ?? "";
  const sequenceId = verifyUnsubscribeToken(token);
  if (!sequenceId) return page("Link not valid", "This unsubscribe link is missing or has expired. Reply to the email instead and we will remove you by hand.", 400);

  const db = createAdminClient();
  const { data: seq } = await db.from("sequences").select("sequence_id,lead_id,contact_email,status").eq("sequence_id", sequenceId).maybeSingle();
  if (!seq) return page("Already removed", "No active email sequence matches this link. You will not hear from us again.");

  const email = seq.contact_email.toLowerCase();
  const domain = email.split("@")[1] ?? null;
  await db.from("unsubscribes").upsert({ email, domain, reason: "request" }, { onConflict: "email", ignoreDuplicates: true });
  await db.from("sequences").update({ status: "stopped_unsub" }).eq("sequence_id", sequenceId);
  if (seq.lead_id) await db.from("leads").update({ status: "unsubscribed", updated_at: new Date().toISOString() }).eq("lead_id", seq.lead_id);
  return page("You are unsubscribed", `${email} will not receive any further email from us.`);
}
