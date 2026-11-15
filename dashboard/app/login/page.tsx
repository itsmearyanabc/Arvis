"use client";
import { useActionState } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { login } from "./actions";
import BrainCanvas from "@/components/BrainCanvas";

function LoginForm() {
  const params = useSearchParams();
  const [state, action, pending] = useActionState(login, undefined);
  return (
    <form action={action} className="card w-full max-w-sm p-6 space-y-4">
      <input type="hidden" name="next" value={params.get("next") || "/"} />
      <div>
        <div className="text-lg font-semibold">ARVIS</div>
        <div className="text-sm text-muted">Sign in to the operating panel.</div>
      </div>
      <label className="block space-y-1">
        <span className="tile-label">Email</span>
        <input name="email" type="email" required autoComplete="username" className="input w-full" />
      </label>
      <label className="block space-y-1">
        <span className="tile-label">Password</span>
        <input name="password" type="password" required autoComplete="current-password" className="input w-full" />
      </label>
      {state?.error && <div className="text-sm text-bad">{state.error}</div>}
      <button className="btn-primary w-full justify-center" disabled={pending}>{pending ? "Signing in…" : "Sign in"}</button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <main className="min-h-dvh flex flex-col items-center justify-center gap-6 p-4">
      <div className="w-full max-w-sm h-40 card overflow-hidden">
        <BrainCanvas idle compact />
      </div>
      <Suspense><LoginForm /></Suspense>
    </main>
  );
}
