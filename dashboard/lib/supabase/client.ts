"use client";
import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}

/** Realtime applies RLS with whatever JWT the socket carries. Make sure it is the user's
 *  before subscribing, otherwise postgres_changes silently delivers nothing. */
export async function withRealtimeAuth(sb: ReturnType<typeof createClient>) {
  const { data: { session } } = await sb.auth.getSession();
  if (session?.access_token) await sb.realtime.setAuth(session.access_token);
  return sb;
}
