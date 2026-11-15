"use server";
import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { ALL_NICHES, marketId } from "@/lib/niches";

export async function setMarketStatus(formData: FormData) {
  const id = String(formData.get("market_id") || "");
  const status = String(formData.get("status") || "");
  if (!id || !["active", "paused", "proposed", "done"].includes(status)) return;
  const supabase = await createClient();
  await supabase.from("markets").update({ status }).eq("market_id", id);
  revalidatePath("/markets");
}

export async function addMarket(_prev: { error?: string; ok?: string } | undefined, formData: FormData) {
  const country = String(formData.get("country") || "").trim();
  const city = String(formData.get("city") || "").trim();
  const niche = String(formData.get("niche") || "").trim().toLowerCase();
  if (!country || !city) return { error: "Country and city are required." };
  if (!ALL_NICHES.includes(niche)) return { error: "Pick a niche from the groups." };
  const supabase = await createClient();
  const id = marketId(country, city, niche);
  const { error } = await supabase.from("markets").insert({
    market_id: id, country, city, niche, status: "active",
    rationale: `added from dashboard ${new Date().toISOString().slice(0, 10)}`,
  });
  if (error) return { error: error.code === "23505" ? `${id} already exists.` : error.message };
  revalidatePath("/markets");
  return { ok: `${id} added (active). The nightly scrape picks the oldest-unscraped active markets.` };
}
