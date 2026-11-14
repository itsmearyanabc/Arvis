# DNS records for ARVIS (all on armedias.tech; armedias.com is not touched)

Add these in the DNS panel where armedias.tech is managed. Values marked `<...>` come from the
service's own setup screen; copy exactly what it shows.

## 1. Cold-email subdomain: mail.armedias.tech (Zoho Mail)
Zoho Mail → Add domain → `mail.armedias.tech` → follow its verification screen.

| Type | Host | Value | Note |
|---|---|---|---|
| TXT | mail | `zoho-verification=<code>` | domain verification |
| MX | mail | `mx.zoho.com` prio 10, `mx2.zoho.com` 20, `mx3.zoho.com` 50 | replies land in Zoho |
| TXT | mail | `v=spf1 include:zohomail.com ~all` | SPF (Zoho's exact include may differ by region: use theirs) |
| TXT | zmail._domainkey.mail | `v=DKIM1; k=rsa; p=<key from Zoho>` | DKIM, selector shown by Zoho |
| TXT | _dmarc.mail | `v=DMARC1; p=quarantine; rua=mailto:dmarc@mail.armedias.tech; adkim=s; aspf=s` | start `p=none` for the first week, then quarantine |

Then: create the mailbox (your first name @ mail.armedias.tech), enable IMAP in Zoho Mail
settings, generate an **app password** for SMTP/IMAP (never your real password), and start a
warm-up: send 5–10 real emails a day to people you know for 2–3 weeks, replying to replies.

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
