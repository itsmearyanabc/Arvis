/** Read-only DNS checks for the cold-email domain via Google's public DoH resolver (server side). */
export type DnsCheck = { label: string; ok: boolean; detail: string };

async function resolve(name: string, type: "MX" | "TXT"): Promise<string[]> {
  const r = await fetch(`https://dns.google/resolve?name=${encodeURIComponent(name)}&type=${type}`, { next: { revalidate: 300 } });
  if (!r.ok) throw new Error(`dns.google ${r.status}`);
  const j = (await r.json()) as { Answer?: { data: string }[] };
  return (j.Answer ?? []).map((a) => a.data.replace(/^"|"$/g, "").replace(/""/g, ""));
}

export async function checkEmailDns(domain = "armedias.tech"): Promise<DnsCheck[]> {
  const out: DnsCheck[] = [];
  try {
    const mx = await resolve(domain, "MX");
    const zoho = mx.filter((m) => /zoho/i.test(m));
    out.push({ label: "MX → Zoho", ok: zoho.length > 0, detail: mx.length ? mx.join(", ") : "no MX records" });
  } catch (e) { out.push({ label: "MX → Zoho", ok: false, detail: `lookup failed: ${(e as Error).message}` }); }
  try {
    const txt = await resolve(domain, "TXT");
    const spf = txt.find((t) => t.startsWith("v=spf1"));
    out.push({ label: "SPF", ok: !!spf && /zoho/i.test(spf), detail: spf ?? "no v=spf1 record" });
  } catch (e) { out.push({ label: "SPF", ok: false, detail: `lookup failed: ${(e as Error).message}` }); }
  try {
    const dkim = await resolve(`zmail._domainkey.${domain}`, "TXT");
    const rec = dkim.find((t) => t.startsWith("v=DKIM1"));
    out.push({ label: "DKIM (zmail)", ok: !!rec, detail: rec ? "v=DKIM1 present" : "no zmail._domainkey TXT" });
  } catch (e) { out.push({ label: "DKIM (zmail)", ok: false, detail: `lookup failed: ${(e as Error).message}` }); }
  try {
    const dmarc = await resolve(`_dmarc.${domain}`, "TXT");
    const rec = dmarc.find((t) => t.startsWith("v=DMARC1"));
    out.push({ label: "DMARC", ok: !!rec, detail: rec ?? "no _dmarc TXT" });
  } catch (e) { out.push({ label: "DMARC", ok: false, detail: `lookup failed: ${(e as Error).message}` }); }
  return out;
}
