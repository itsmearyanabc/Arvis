# DNS records for ARVIS (all on armedias.tech; armedias.com is not touched)

DNS for armedias.tech is at Hostinger (nameservers hyperion/atlas.dns-parking.com): hPanel →
Domains → armedias.tech → DNS / Name Servers. Values marked `<...>` come from the service's own
setup screen; copy exactly what it shows.

## 1. Cold-email domain: armedias.tech root (Zoho Mail, India datacenter)
Aryan connected the ROOT domain in Zoho on 2026-11-15 (mailbox connect@armedias.tech), not the
`mail.` subdomain originally planned. Verification TXT is already in place. Consequence: cold
email reputation now sits on armedias.tech itself, so DMARC starts at `p=none`, warm-up is
mandatory, and caps stay low. armedias.com is still never used.

| Type | Host | Value | TTL | Note |
|---|---|---|---|---|
| MX | @ | `mx.zoho.in` priority 10 | 3600 | Zoho India (your verification code ends in zoho.in) |
| MX | @ | `mx2.zoho.in` priority 20 | 3600 | |
| MX | @ | `mx3.zoho.in` priority 50 | 3600 | |
| TXT | @ | `v=spf1 include:zohomail.in ~all` | 3600 | SPF. If an SPF TXT already exists, merge: one SPF record only |
| TXT | zmail._domainkey | `v=DKIM1; k=rsa; p=<key>` | 3600 | DKIM: Zoho Mail Admin → Email Configuration → DKIM → add selector `zmail` → copy the TXT |
| TXT | _dmarc | `v=DMARC1; p=none; rua=mailto:connect@armedias.tech; adkim=s; aspf=s` | 3600 | week 1–2 `p=none`, then `p=quarantine` |

Zoho steps after DNS: Admin console → Email Configuration → verify MX / SPF / DKIM (green
ticks). Mail Settings → Mail Accounts → enable **IMAP access** for connect@. Zoho Accounts →
Security → **App passwords** → create one named "ARVIS" (SMTP/IMAP use this, never the real
password). Warm-up: from day 1 send 5–10 real, human emails a day from connect@ to people
who will reply, for 2–3 weeks, before any cold email.

## 2. Dashboard: arvis.armedias.tech (Vercel)
| Type | Host | Value |
|---|---|---|
| CNAME | arvis | `cname.vercel-dns.com` |

Vercel → project → Settings → Domains → add `arvis.armedias.tech`.

## 3. Booking: book.armedias.tech (Cal.com hosted)
| Type | Host | Value |
|---|---|---|
| CNAME | book | value shown in Cal.com → Settings → Domains (custom domain) |

If the free plan does not include a custom domain at the time of setup, use the
`cal.com/<username>` link in emails; the subdomain can be added later.

## 4. Nothing for the VPS
The brain serves no website. No A record points at the VPS for ARVIS, no nginx change on the
armedias.com server, no open ports.

## Check after adding
```
dig +short TXT mail.armedias.tech
dig +short MX mail.armedias.tech
dig +short TXT zmail._domainkey.mail.armedias.tech
dig +short TXT _dmarc.mail.armedias.tech
dig +short CNAME arvis.armedias.tech
```
Paste the outputs to Claude.
