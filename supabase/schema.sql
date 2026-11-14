-- ARVIS schema. Run ONCE in the Supabase SQL editor of ARVIS's own project (Mumbai).
-- Brain and workers use the service_role key (bypasses RLS). The dashboard uses the anon key
-- with Aryan's login; RLS below allows authenticated users full access and anon nothing.

create extension if not exists pgcrypto;

create table if not exists markets (
  market_id text primary key,
  country text not null, city text not null, niche text not null,
  businesses_found int, pct_no_website numeric, pct_high_ticket numeric, agency_count int,
  opportunity_score int, rationale text,
  status text not null default 'proposed' check (status in ('proposed','active','paused','done')),
  last_scraped_at timestamptz, created_at timestamptz default now()
);

create table if not exists leads (
  lead_id text primary key,
  place_id text unique,
  market_id text references markets(market_id),
  business_name text not null, niche text, city text, country text, address text,
  phone text, website text, rating numeric, review_count int,
  maps_url text, instagram_url text, linkedin_url text, facebook_url text,  -- stored for Aryan only
  source text not null default 'google_maps',
  fit_score int default 0, ticket_score int default 0,
  contact_quality text default 'none' check (contact_quality in ('named','generic','none')),
  primary_email text, runs_meta_ads boolean,
  top_issue text, audit_summary text,
  status text not null default 'new' check (status in
    ('new','audited','verified','parked','drafted','in_sequence','replied','booked','won','lost','unsubscribed')),
  parked_reason text, approved_by_aryan boolean default true, notes text,
  scraped_at timestamptz default now(), updated_at timestamptz default now()
);
create index if not exists leads_status_idx on leads(status, ticket_score desc);

create table if not exists audits (
  audit_id uuid primary key default gen_random_uuid(),
  lead_id text references leads(lead_id) on delete cascade,
  website text, checked_at timestamptz default now(),
  site_status text check (site_status in ('ok','down','no_site')),
  ssl_ok boolean, https_redirect boolean, mobile_score int, perf_score int, lcp_s numeric,
  cms text, copyright_year int, looks_outdated boolean,
  has_title boolean, has_meta_desc boolean, h1_count int, img_alt_missing_pct numeric,
  broken_links_sampled int, contact_email_on_site boolean, contact_form boolean, booking_widget boolean,
  meta_pixel boolean, google_tag boolean,
  top_issue text, audit_summary text
);

create table if not exists contacts (
  contact_id uuid primary key default gen_random_uuid(),
  lead_id text references leads(lead_id) on delete cascade,
  contact_name text, role text, email text,
  email_status text check (email_status in ('safe','risky','invalid','unknown')),
  email_source text check (email_source in ('website','maps','web_search','hunter','pattern','manual')),
  contact_quality text check (contact_quality in ('named','generic','none')),
  phone text, verified_at timestamptz, verifier text
);
create index if not exists contacts_email_idx on contacts(email);

create table if not exists templates (
  template_id text primary key,            -- e.g. default_v1, dentist_v1
  niche text default 'default', step int not null check (step between 1 and 3),
  subject text, body text not null,
  variant text default 'issue' check (variant in ('issue','no_issue')),
  approved boolean default false, author text, approved_at timestamptz,
  sends_7d int default 0, replies_7d int default 0
);

create table if not exists sequences (
  sequence_id uuid primary key default gen_random_uuid(),
  lead_id text references leads(lead_id) on delete cascade,
  contact_id uuid references contacts(contact_id),
  contact_email text not null, template_id text references templates(template_id),
  mailbox text,
  step1_subject text, step1_body text, step2_body text, step3_body text,
  status text not null default 'draft' check (status in
    ('draft','approved','step1_sent','step2_sent','step3_sent','done_no_reply',
     'stopped_reply','stopped_unsub','bounced','snoozed','expired','skipped')),
  approved_by_aryan boolean default false, approved_at timestamptz, drafted_at timestamptz default now(),
  step1_sent_at timestamptz, step2_sent_at timestamptz, step3_sent_at timestamptz,
  message_id text, resume_at timestamptz, edit_note text
);
create index if not exists sequences_status_idx on sequences(status);

create table if not exists replies (
  reply_id uuid primary key default gen_random_uuid(),
  sequence_id uuid references sequences(sequence_id),
  lead_id text references leads(lead_id),
  mailbox text, from_email text, received_at timestamptz default now(),
  category text check (category in ('interested','question','not_now','not_interested','unsubscribe',
    'auto_reply','bounce','wrong_person','spam_complaint','other')),
  reply_summary text, suggested_action text,
  telegram_alerted boolean default false, handled_by_aryan boolean default false, handled_at timestamptz
);

create table if not exists unsubscribes (
  email text primary key, domain text,
  reason text check (reason in ('request','bounce','complaint','manual')),
  added_at timestamptz default now(), source_reply_id uuid
);
create index if not exists unsubscribes_domain_idx on unsubscribes(domain);

create table if not exists bookings (
  booking_id uuid primary key default gen_random_uuid(),
  lead_id text references leads(lead_id), calcom_uid text unique,
  attendee_name text, attendee_email text, start_at timestamptz, tz text,
  source text check (source in ('cold_email','referral','inbound')),
  status text default 'booked' check (status in ('booked','rescheduled','cancelled','held')),
  brief_sent_at timestamptz,
  outcome text check (outcome in ('won','proposal','lost','no_show','reschedule')),
  notes text
);

create table if not exists mailboxes (
  mailbox text primary key, address text not null, from_name text, domain text not null,
  daily_cap int default 20, warmup_until date, paused boolean default false,
  sent_today int default 0, bounces_7d int default 0,
  constraint no_armedias_com check (domain <> 'armedias.com')
);

create table if not exists monitors (
  monitor_id uuid primary key default gen_random_uuid(), monitor_ext_id text,
  name text, url text not null, type text default 'http' check (type in ('http','keyword','ping')),
  interval_s int default 300, owner text default 'us', status text,
  last_down_at timestamptz, ssl_expires_at timestamptz, uptime_7d_pct numeric, avg_response_ms int
);

create table if not exists reports (
  date date primary key, scraped int, audited int, verified int, drafts_pending int,
  sent int, bounced int, unsub int, replied int, interested int, booked int,
  reply_rate_7d numeric, booking_rate_7d numeric, issues text
);

create table if not exists worker_runs (          -- every GitHub Actions run logs here
  run_id uuid primary key default gen_random_uuid(),
  worker text not null, started_at timestamptz default now(), finished_at timestamptz,
  status text default 'running', input jsonb, counts jsonb, error text
);

-- RLS: authenticated (Aryan in the dashboard) = full access; anon = nothing.
do $$ declare t text; begin
  for t in select unnest(array['markets','leads','audits','contacts','templates','sequences','replies',
                               'unsubscribes','bookings','mailboxes','monitors','reports','worker_runs']) loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists "auth full" on %I', t);
    execute format('create policy "auth full" on %I for all to authenticated using (true) with check (true)', t);
  end loop;
end $$;
