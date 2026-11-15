// Create (or reset the password of) the single dashboard login. Run locally, never on a server:
//   node scripts/create-user.mjs you@example.com      (reads .env.local, prompts for the password)
import { createClient } from "@supabase/supabase-js";
import { readFileSync } from "node:fs";
import { createInterface } from "node:readline/promises";

for (const line of readFileSync(new URL("../.env.local", import.meta.url), "utf8").split("\n")) {
  const m = line.match(/^([A-Z_]+)=(.*)$/); if (m && !process.env[m[1]]) process.env[m[1]] = m[2].trim();
}
const email = process.argv[2];
if (!email) { console.error("usage: node scripts/create-user.mjs you@example.com"); process.exit(1); }
const rl = createInterface({ input: process.stdin, output: process.stdout });
const password = await rl.question("password (min 8 chars): "); rl.close();
if (password.length < 8) { console.error("too short"); process.exit(1); }

const admin = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY, { auth: { persistSession: false } });
const { data: list } = await admin.auth.admin.listUsers({ perPage: 200 });
const existing = list?.users.find((u) => u.email?.toLowerCase() === email.toLowerCase());
const r = existing
  ? await admin.auth.admin.updateUserById(existing.id, { password })
  : await admin.auth.admin.createUser({ email, password, email_confirm: true });
if (r.error) { console.error(r.error.message); process.exit(1); }
console.log(existing ? `password updated for ${email}` : `created ${email}`);
