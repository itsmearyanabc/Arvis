-- Run once in the Supabase SQL editor (adds the email source column to leads; safe to re-run)
alter table leads add column if not exists email_source text;
alter table mailboxes drop constraint if exists no_root_domains;
alter table mailboxes add constraint no_armedias_com check (domain <> 'armedias.com');
