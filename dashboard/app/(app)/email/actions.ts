"use server";
import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";

/** Approve toggle on a draft. Sending never happens here: the brain sends only after Aryan says so in Telegram. */
export async function setApproved(formData: FormData) {
  const id = String(formData.get("sequence_id") || "");
  const approve = String(formData.get("approve") || "") === "1";
  if (!id) return;
  const supabase = await createClient();
  await supabase.from("sequences").update({
    approved_by_aryan: approve, approved_at: approve ? new Date().toISOString() : null,
    status: approve ? "approved" : "draft",
  }).eq("sequence_id", id).in("status", ["draft", "approved"]);
  revalidatePath("/email");
}
