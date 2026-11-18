import { NextResponse, type NextRequest } from "next/server";
import { createHmac, timingSafeEqual } from "crypto";
import { createAdminClient } from "@/lib/supabase/admin";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * POST /api/webhooks/calcom  (stub for Phase 4)
 * Cal.com -> Settings -> Developer -> Webhooks -> subscriber URL https://arvis.armedias.tech/api/webhooks/calcom
 * Events: BOOKING_CREATED, BOOKING_RESCHEDULED, BOOKING_CANCELLED. If CALCOM_WEBHOOK_SECRET is set the
 * x-cal-signature-256 header (HMAC-SHA256 of the raw body) must match. Upserts `bookings` on calcom_uid and
 * links the lead by attendee email when one matches.
 */
export async function POST(request: NextRequest) {
  const raw = await request.text();
  // Fail closed: this route writes with the secret key, so it must never accept unsigned requests.
  const secret = process.env.CALCOM_WEBHOOK_SECRET;
  if (!secret) return NextResponse.json({ error: "webhook not configured" }, { status: 503 });
  const sig = request.headers.get("x-cal-signature-256") ?? "";
  const expect = createHmac("sha256", secret).update(raw).digest("hex");
  if (sig.length !== expect.length || !timingSafeEqual(Buffer.from(sig), Buffer.from(expect)))
    return NextResponse.json({ error: "bad signature" }, { status: 401 });
  let body: { triggerEvent?: string; payload?: Record<string, unknown> };
  try { body = JSON.parse(raw); } catch { return NextResponse.json({ error: "invalid json" }, { status: 400 }); }

  const p = (body.payload ?? {}) as Record<string, unknown>;
  const uid = String(p.uid ?? p.bookingId ?? "");
  if (!uid) return NextResponse.json({ error: "no uid" }, { status: 400 });
  const attendee = (Array.isArray(p.attendees) ? p.attendees[0] : undefined) as Record<string, unknown> | undefined;
  const email = String(attendee?.email ?? "").toLowerCase() || null;
  const statusMap: Record<string, string> = { BOOKING_CREATED: "booked", BOOKING_RESCHEDULED: "rescheduled", BOOKING_CANCELLED: "cancelled" };
  const status = statusMap[body.triggerEvent ?? ""] ?? "booked";

  const db = createAdminClient();
  let leadId: string | null = null;
  if (email) {
    const { data: lead } = await db.from("leads").select("lead_id").eq("primary_email", email).limit(1).maybeSingle();
    leadId = lead?.lead_id ?? null;
    if (!leadId) {
      const { data: c } = await db.from("contacts").select("lead_id").eq("email", email).limit(1).maybeSingle();
      leadId = c?.lead_id ?? null;
    }
  }
  const { error } = await db.from("bookings").upsert({
    calcom_uid: uid, lead_id: leadId, attendee_name: attendee?.name ? String(attendee.name) : null, attendee_email: email,
    start_at: p.startTime ? new Date(String(p.startTime)).toISOString() : null,
    tz: attendee?.timeZone ? String(attendee.timeZone) : null,
    source: leadId ? "cold_email" : "inbound", status,
  }, { onConflict: "calcom_uid" });
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  if (leadId && status === "booked") await db.from("leads").update({ status: "booked", updated_at: new Date().toISOString() }).eq("lead_id", leadId);
  return NextResponse.json({ ok: true, calcom_uid: uid, lead_id: leadId, status });
}
