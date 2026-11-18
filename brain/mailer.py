"""ARVIS mailer: one-off emails Aryan explicitly asks for from Telegram (not the cold sequence).
Flow, enforced here and in the arvis-ops skill:
  1. `arvisctl email draft --to X --subject S --body B [--name N]` → stores a draft, prints the EXACT email.
  2. ARVIS shows that text to Aryan and waits for him to reply "send" (or edit).
  3. `arvisctl email send --id ID --confirm` → only then it goes out.
Guards: sender is SEND_DOMAIN only (never armedias.com); MX/SPF must exist for the sending domain;
postal address + unsubscribe line appended; unsubscribed addresses refused; daily cap DAILY_SEND_CAP.
SMTP: Zoho (India DC default smtp.zoho.in:465) with an APP password in MAILBOX_1_PASS."""
import os, re, ssl, json, smtplib, uuid, datetime as dt, urllib.request
from email.message import EmailMessage
from email.utils import make_msgid, formataddr

def _env(k, d=None): return os.environ.get(k, d)

def dns(name, rtype):
    try:
        with urllib.request.urlopen(f"https://dns.google/resolve?name={name}&type={rtype}", timeout=10) as r:
            return [a.get("data", "") for a in json.load(r).get("Answer", [])]
    except Exception:
        return []

def deliverability_check(domain):
    mx = dns(domain, "MX"); txt = dns(domain, "TXT"); dmarc = dns("_dmarc." + domain, "TXT")
    spf = [t for t in txt if "v=spf1" in t]
    problems = []
    if not mx: problems.append(f"no MX records on {domain} (replies would bounce)")
    if not spf: problems.append(f"no SPF record on {domain} (mail goes to spam)")
    if not dmarc: problems.append(f"no DMARC record on _dmarc.{domain}")
    dkim = dns(_env("DKIM_SELECTOR", "zmail") + "._domainkey." + domain, "TXT")
    if not any("p=" in t for t in dkim): problems.append(f"no DKIM key at {_env('DKIM_SELECTOR', 'zmail')}._domainkey.{domain}")
    return problems

def footer():
    addr = _env("POSTAL_ADDRESS", "").strip()
    if not addr: raise SystemExit("POSTAL_ADDRESS is not set in /opt/arvis/.env — required in every email (CAN-SPAM/CASL).")
    return f"\n\n--\nAR Medias · {addr}\nIf you'd rather not hear from us, reply \"unsubscribe\" and we'll remove you."

def sent_today(db):
    start = dt.datetime.now(dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    return len(db().table("sequences").select("sequence_id").gte("step1_sent_at", start).execute().data)

def draft(db, to, subject, body, name=None):
    to = to.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", to): raise SystemExit(f"not an email address: {to}")
    subject = " ".join((subject or "").split())[:150]            # headers must be one line
    body = (body or "").replace("\\n", "\n").strip()               # literal \n typed in chat -> line break
    if not subject or not body: raise SystemExit("subject and body must not be empty")
    row = {"contact_email": to, "step1_subject": subject, "step1_body": body, "status": "draft",
           "approved_by_aryan": False, "edit_note": f"one-off from Telegram{(' to ' + name) if name else ''}"}
    rec = db().table("sequences").insert(row).execute().data[0]
    return rec["sequence_id"], render(subject, body)

def render(subject, body):
    sender = f'{_env("MAILBOX_1_FROM_NAME", "AR Medias")} <{_env("MAILBOX_1_USER", "connect@armedias.tech")}>'
    return f"From: {sender}\nSubject: {subject.strip()}\n\n{body.strip()}{footer()}"

def send(db, seq_id):
    rec = db().table("sequences").select("*").eq("sequence_id", seq_id).single().execute().data
    if rec["status"] != "draft": raise SystemExit(f"draft {seq_id} is already {rec['status']}")
    user = _env("MAILBOX_1_USER", ""); pw = _env("MAILBOX_1_PASS", "")
    domain = user.split("@")[-1].lower()
    if not user or not pw: raise SystemExit("MAILBOX_1_USER / MAILBOX_1_PASS (Zoho app password) missing in /opt/arvis/.env")
    if domain == "armedias.com": raise SystemExit("refusing to send from armedias.com")
    problems = deliverability_check(domain)
    if problems: raise SystemExit("not sending, DNS not ready: " + "; ".join(problems) + ". See docs/dns.md.")
    to = rec["contact_email"].lower()
    if db().table("unsubscribes").select("email").eq("email", to).execute().data or \
       db().table("unsubscribes").select("domain").eq("domain", to.split("@")[-1]).execute().data:
        raise SystemExit(f"{to} has unsubscribed; not sending")
    cap = int(_env("DAILY_SEND_CAP", "50"))
    if sent_today(db) >= cap: raise SystemExit(f"daily cap {cap} reached; try tomorrow")
    # claim the draft first so a retry after a failure can never send it twice
    claimed = db().table("sequences").update({"status": "approved"}).eq("sequence_id", seq_id).eq("status", "draft").execute().data
    if not claimed: raise SystemExit(f"draft {seq_id} was already claimed by another send")
    msg = EmailMessage()
    msg["From"] = formataddr((_env("MAILBOX_1_FROM_NAME", "AR Medias"), user))
    msg["To"] = to; msg["Subject"] = rec["step1_subject"]
    mid = make_msgid(domain=domain); msg["Message-ID"] = mid
    msg["List-Unsubscribe"] = f"<mailto:{user}?subject=unsubscribe>"
    msg.set_content(rec["step1_body"] + footer())
    host = _env("ZOHO_SMTP_HOST", "smtp.zoho.in"); port = int(_env("ZOHO_SMTP_PORT", "465"))
    try:
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=30) as s:
            s.login(user, pw); s.send_message(msg)
    except Exception as e:
        db().table("sequences").update({"status": "draft"}).eq("sequence_id", seq_id).execute()   # nothing went out
        raise SystemExit(f"send failed, draft kept: {type(e).__name__}: {str(e)[:200]}")
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    db().table("sequences").update({"status": "step1_sent", "approved_by_aryan": True, "approved_at": now,
                                    "step1_sent_at": now, "message_id": mid, "mailbox": user}).eq("sequence_id", seq_id).execute()
    return to, mid
