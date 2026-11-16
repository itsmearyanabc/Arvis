/** Template placeholders, rendering and the approval checker. Shared by the editor (live) and the
 *  approve server action (authoritative). Keep the rules in sync with the brain's drafting prompt. */

export const PLACEHOLDERS = [
  { key: "first_name|there", hint: "contact's first name, or “there”" },
  { key: "business", hint: "business name" },
  { key: "city", hint: "city" },
  { key: "top_issue", hint: "audit top issue" },
  { key: "audit_summary", hint: "one-line audit summary" },
  { key: "review_excerpt", hint: "a short review quote (no reviewer names)" },
  { key: "sender_name", hint: "mailbox from-name" },
  { key: "booking_link", hint: "Cal.com link" },
] as const;
const KNOWN = new Set(PLACEHOLDERS.map((p) => p.key.split("|")[0]));

export const FOOTER = "--\nAR Medias · <postal address from the VPS env>\nIf you'd rather not hear from us, reply \"unsubscribe\" and we'll remove you.";

export type Vars = Partial<Record<"first_name" | "business" | "city" | "top_issue" | "audit_summary" | "review_excerpt" | "sender_name" | "booking_link", string | null | undefined>>;

/** {name} or {name|fallback}. Unknown keys are left as-is so the checker can flag them. */
export function renderTemplate(text: string, vars: Vars): string {
  return (text || "").replace(/\{([a-z_]+)(?:\|([^}]*))?\}/g, (m, key: string, fb?: string) => {
    if (!KNOWN.has(key)) return m;
    const v = vars[key as keyof Vars];
    return (v && String(v).trim()) || fb || "";
  });
}

export type CheckResult = { hard: string[]; soft: string[] };

const PRICE_RE = /(^|[^\w])(?:\$|₹|£|€|usd|inr|gbp|eur)\s?\d|(\d[\d,]*(?:\.\d+)?)\s?(?:\$|₹|£|€|usd|inr|gbp|eur|k\b|lakh|per\s?(?:hour|hr|day|month|project))/i;
const TEAM_RE = /\b(team of|our team of|\d+\s*(?:people|persons|employees|staff|designers|developers)|headcount|\d+[- ]person\b)/i;
const RATE_RE = /\b(hourly rate|day rate|daily rate|per hour|per day|\/hr|\/hour|\/day)\b/i;
const SPAM = ["free", "guarantee", "act now", "limited time", "winner", "100%", "$$$", "urgent", "click here", "buy now", "risk-free"];

export function checkTemplate(input: { subject?: string | null; body: string; step: number }): CheckResult {
  const hard: string[] = [], soft: string[] = [];
  const subject = (input.subject ?? "").trim();
  const body = input.body ?? "";
  const all = `${subject}\n${body}`;

  if (TEAM_RE.test(all)) hard.push("mentions team size or headcount");
  if (RATE_RE.test(all)) hard.push("mentions an hourly or day rate");
  if (/\bstarting at\b|\bfrom\s?(?:\$|₹|£|€)|\bminimum project\b/i.test(all)) hard.push("pricing language (“starting at”, “from $”, “minimum project”)");
  if (PRICE_RE.test(all)) hard.push("contains a price or money amount");
  const links = (all.match(/https?:\/\/\S+|www\.\S+|\{booking_link\}/gi) ?? []).length;
  if (links > 1) hard.push(`more than one link (${links})`);
  if (/<\s*\/?\s*[a-z][^>]*>|!\[[^\]]*\]\(/i.test(all)) hard.push("contains an HTML tag or image");
  if (input.step === 1) {
    if (!subject) hard.push("step 1 needs a subject");
    if (subject.length > 60) hard.push(`subject is ${subject.length} chars (max 60)`);
    const letters = subject.replace(/[^a-z]/gi, "");
    if (letters.length >= 4 && letters === letters.toUpperCase()) hard.push("subject is ALL CAPS");
  }
  for (const m of all.matchAll(/\{([^}]*)\}/g)) {
    const key = m[1].split("|")[0];
    if (!/^[a-z_]+$/.test(key) || !KNOWN.has(key)) hard.push(`unknown placeholder {${m[1]}}`);
  }
  if (!body.trim()) hard.push("body is empty");

  const lower = all.toLowerCase();
  const spam = SPAM.filter((w) => lower.includes(w));
  if (spam.length) soft.push(`spam-trigger words: ${spam.join(", ")}`);
  const bangs = (all.match(/!/g) ?? []).length;
  if (bangs > 1) soft.push(`${bangs} exclamation marks`);
  const words = body.trim() ? body.trim().split(/\s+/).length : 0;
  const limit = input.step === 1 ? 120 : 70;
  if (words > limit) soft.push(`${words} words (aim for ≤ ${limit} for step ${input.step})`);
  if (!/\?/.test(body) && !/\b(reply|let me know|worth a|open to|would you|could you|happy to|want me to)\b/i.test(body)) soft.push("no question or clear ask");
  return { hard, soft };
}

export function replyRate(t: { sends_7d: number | null; replies_7d: number | null }): string {
  const s = t.sends_7d ?? 0;
  return s ? `${Math.round(((t.replies_7d ?? 0) / s) * 100)}%` : "–";
}

export function slugId(niche: string, step: number, variant: string): string {
  const n = (niche || "default").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  return `${n}_s${step}_${variant}_${Date.now().toString(36)}`;
}
