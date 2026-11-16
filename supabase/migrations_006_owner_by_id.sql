-- Migration 006: owner-only access keyed to the dashboard account's permanent id (not its email),
-- so changing the login email (now info@armedias.com) never locks Aryan out. Replaces 005's policies.
-- The brain and workers use the secret key and bypass RLS, so they are unaffected.
do $$ declare t text; begin
  for t in select unnest(array['markets','leads','audits','contacts','templates','sequences','replies',
                               'unsubscribes','bookings','mailboxes','monitors','reports','worker_runs','brain_events']) loop
    execute format('drop policy if exists "auth full" on %I', t);
    execute format('drop policy if exists "owner only" on %I', t);
    execute format($p$create policy "owner only" on %I for all to authenticated
                    using (auth.uid() = '08206007-f4eb-44c6-8795-cbfa71a1da98'::uuid)
                    with check (auth.uid() = '08206007-f4eb-44c6-8795-cbfa71a1da98'::uuid)$p$, t);
  end loop;
end $$;
