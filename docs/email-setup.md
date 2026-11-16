# Email setup for connect@armedias.tech — step by step, and how to stay out of spam

ARVIS sends from **connect@armedias.tech** (Zoho Mail, India datacenter). armedias.com is never used,
so its reputation can't be harmed. DNS for armedias.tech is at **Hostinger** (hPanel), not Cloudflare.

## 0. Check the Zoho plan
Zoho's *Forever Free* plan has **no SMTP/IMAP**, so ARVIS could not send or read replies. You need
**Zoho Mail Lite** (cheapest paid plan, ~₹60–90 per user/month in India) for connect@. This is the one
running cost the original plan accepted ("domains + mailboxes"). Zoho Mail → Admin Console → Subscription.

## 1. DNS records (Hostinger hPanel → Domains → armedias.tech → DNS / Nameservers → Manage DNS records)
Delete any old MX records first. Then add, TTL 3600 (or default):

| Type | Name | Value / Points to | Priority |
|---|---|---|---|
| MX  | @ | `mx.zoho.in`  | 10 |
| MX  | @ | `mx2.zoho.in` | 20 |
| MX  | @ | `mx3.zoho.in` | 50 |
| TXT | @ | `v=spf1 include:zohomail.in ~all` | – |
| TXT | `zmail._domainkey` | the long `v=DKIM1; k=rsa; p=…` value from Zoho (step 2) | – |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:connect@armedias.tech; adkim=r; aspf=r; pct=100` | – |

Keep the existing `zoho-verification=…` TXT. Only ONE TXT may start with `v=spf1`.

## 2. DKIM key (Zoho)
Zoho Mail Admin Console → Domains → armedias.tech → **Email Configuration → DKIM** → Add →
selector `zmail` → Zoho shows the TXT value → paste it into Hostinger as above → back in Zoho click
**Verify** (can take 15–60 min after adding). Then **Enable** DKIM.

## 3. Verify in Zoho
Admin Console → Domains → armedias.tech → MX, SPF, DKIM all green. Then on the VPS:
`sudo -iu arvis arvisctl email check` → it lists anything still missing.

## 4. App password (what ARVIS logs in with — never your real password)
1. Zoho Mail → Settings → **Mail Accounts → IMAP Access**: enable.
2. accounts.zoho.in → Security → **App Passwords** → Generate → name "ARVIS" → copy it once.
   (If it asks, turn on two-factor login first; app passwords require it.)
3. On your Mac copy it to the clipboard, then on the VPS:
   `cat >> /opt/arvis/.env` → type `MAILBOX_1_PASS=` → paste → Enter → Ctrl+D.

## 5. Postal address (legal requirement, printed in every email footer)
On the VPS: `echo 'POSTAL_ADDRESS="AR Medias, <street>, <city> <PIN>, India"' >> /opt/arvis/.env`

## 6. Warm-up: 14–21 days before ANY cold email
New domains that suddenly send cold email go to spam. Build history first:
- Days 1–7: 5 real emails/day from connect@ to people who will reply (friends, clients, your own
  Gmail/Outlook). Reply back and forth. Open them, mark "Not spam" if they land there.
- Days 8–14: 10/day, include different providers (Gmail, Outlook, Yahoo, company mail).
- Days 15–21: 15/day. Then ARVIS starts cold email at 10/day and ramps to the 50/day cap slowly.
- Week 2: change DMARC to `p=quarantine` once Zoho reports are clean.

## 7. Test before the first campaign
- Send one email to the address shown on **mail-tester.com** → aim for **9/10 or better**.
- Register armedias.tech at **postmaster.google.com** to watch Gmail spam rate (keep < 0.1%).

## What ARVIS already does against spam
- Sends only to addresses verified by Reacher (bounces < 2%; bounce guard pauses sending at 5%).
- Plain text, no images, no tracking pixels, no link shorteners, at most one link (booking).
- Honest subject, real from-name, postal address, one-line unsubscribe + List-Unsubscribe header.
- Max 50/day across mailboxes, random gaps, recipients' business hours, max 1 email per domain/day.
- Stops a sequence the moment anyone replies; unsubscribes are permanent.
- Templates are checked in the dashboard for spam words and your house rules before approval.

No one can promise 0% spam. With the above, a warmed-up domain lands in the inbox for most business
recipients; the daily report shows bounces and replies so problems surface within a day.
