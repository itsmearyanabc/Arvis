-- Migration 002: brain_events — the live "brain log" the dashboard streams via Realtime.
-- Run once in the Supabase SQL editor (after schema.sql). Writers: workers/common/events.py
-- (service key). Readers: the dashboard as the authenticated user.

create table if not exists brain_events (
  id bigint generated always as identity primary key,
  ts timestamptz not null default now(),
  source text not null check (source in ('brain','scrape','audit','mirror','telegram')),
  level text not null default 'info' check (level in ('debug','info','warn','error')),
  message text not null,
  data jsonb
);
create index if not exists brain_events_ts_idx on brain_events(ts desc);
create index if not exists brain_events_source_ts_idx on brain_events(source, ts desc);

alter table brain_events enable row level security;
drop policy if exists "auth full" on brain_events;
create policy "auth full" on brain_events for all to authenticated using (true) with check (true);

-- Realtime: stream inserts to the dashboard (publication exists on every Supabase project).
do $$ begin
  if not exists (select 1 from pg_publication_tables where pubname = 'supabase_realtime' and tablename = 'brain_events') then
    alter publication supabase_realtime add table brain_events;
  end if;
end $$;

-- Housekeeping (optional, keeps the free tier small): delete events older than 30 days.
-- Call from a cron or the brain: select prune_brain_events();
create or replace function prune_brain_events() returns int language sql as $$
  with d as (delete from brain_events where ts < now() - interval '30 days' returning 1) select count(*)::int from d;
$$;
