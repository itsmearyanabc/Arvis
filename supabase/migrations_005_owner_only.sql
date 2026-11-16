-- Migration 005: lock every table to Aryan's login only. Before this, ANY signed-in user had full
-- access, and public sign-ups are enabled on the project, so a stranger could register and read
-- everything. After this, only the JWT email below can read/write via the dashboard. The brain and
-- workers use the secret key and bypass RLS, so they are unaffected.
-- ALSO: Supabase -> Authentication -> Sign In / Providers -> turn OFF "Allow new users to sign up".
do $$ declare t text; begin
  for t in select unnest(array['markets','leads','audits','contacts','templates','sequences','replies',
                               'unsubscribes','bookings','mailboxes','monitors','reports','worker_runs','brain_events']) loop
    execute format('drop policy if exists "auth full" on %I', t);
    execute format('drop policy if exists "owner only" on %I', t);
    execute format($p$create policy "owner only" on %I for all to authenticated
                    using ((auth.jwt() ->> 'email') = 'armedias005@gmail.com')
                    with check ((auth.jwt() ->> 'email') = 'armedias005@gmail.com')$p$, t);
  end loop;
end $$;
