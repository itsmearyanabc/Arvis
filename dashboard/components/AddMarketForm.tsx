"use client";
import { useActionState } from "react";
import { addMarket } from "@/app/(app)/markets/actions";
import { GROUPS, GROUP_NAMES } from "@/lib/niches";

export default function AddMarketForm() {
  const [state, action, pending] = useActionState(addMarket, undefined);
  return (
    <form action={action} className="space-y-2">
      <input name="country" required placeholder="Country (e.g. Canada)" className="input w-full" />
      <input name="city" required placeholder="City (e.g. Calgary)" className="input w-full" />
      <select name="niche" required className="input w-full" defaultValue="">
        <option value="" disabled>Niche…</option>
        {GROUP_NAMES.map((g) => (
          <optgroup key={g} label={g}>{Object.keys(GROUPS[g]).map((n) => <option key={n} value={n}>{n}</option>)}</optgroup>
        ))}
      </select>
      <button className="btn-primary w-full justify-center" disabled={pending}>{pending ? "Adding…" : "Add market (active)"}</button>
      {state?.error && <div className="text-xs text-bad">{state.error}</div>}
      {state?.ok && <div className="text-xs text-good">{state.ok}</div>}
    </form>
  );
}
