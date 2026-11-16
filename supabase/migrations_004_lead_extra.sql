-- Migration 004: richer business data from the Maps scraper (category, hours, time zone, online
-- booking, description, 2 short review excerpts without reviewer names) + render flag for audits.
alter table leads add column if not exists extra jsonb;
alter table leads add column if not exists timezone text;
alter table audits add column if not exists rendered_with_browser boolean;
