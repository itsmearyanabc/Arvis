"use server";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { ALL_NICHES } from "@/lib/niches";
import { checkTemplate, slugId } from "@/lib/templates";

const VARIANTS = ["issue", "no_issue"];
type Result = { error?: string; ok?: string } | undefined;

function parse(formData: FormData) {
  const step = Math.min(3, Math.max(1, parseInt(String(formData.get("step") || "1"), 10) || 1));
  const niche = String(formData.get("niche") || "default").trim().toLowerCase();
  const variant = String(formData.get("variant") || "issue");
  const subject = step === 1 ? String(formData.get("subject") || "").trim() : null;
  const body = String(formData.get("body") || "").replace(/\r\n/g, "\n");
  return { step, niche, variant, subject, body };
}

/** Create or update. Any edit un-approves (approved=false) so Aryan re-reads it. */
export async function saveTemplate(_prev: Result, formData: FormData): Promise<Result> {
  const id = String(formData.get("template_id") || "");
  const t = parse(formData);
  if (!VARIANTS.includes(t.variant)) return { error: "variant must be issue or no_issue" };
  if (t.niche !== "default" && !ALL_NICHES.includes(t.niche)) return { error: "niche must be “default” or one from the niche groups" };
  if (!t.body.trim()) return { error: "body is empty" };
  const supabase = await createClient();
  const row = { niche: t.niche, step: t.step, variant: t.variant, subject: t.subject, body: t.body, approved: false, approved_at: null };
  if (id) {
    const { error } = await supabase.from("templates").update(row).eq("template_id", id);
    if (error) return { error: error.message };
    revalidatePath("/templates");
    return { ok: "saved (approval reset)" };
  }
  const newId = slugId(t.niche, t.step, t.variant);
  const { error } = await supabase.from("templates").insert({ template_id: newId, author: "aryan", ...row });
  if (error) return { error: error.message };
  revalidatePath("/templates");
  redirect(`/templates?id=${newId}`);
}

export async function duplicateTemplate(formData: FormData) {
  const id = String(formData.get("template_id") || "");
  const supabase = await createClient();
  const { data: src } = await supabase.from("templates").select("*").eq("template_id", id).maybeSingle();
  if (!src) return;
  const newId = slugId(src.niche, src.step, src.variant);
  await supabase.from("templates").insert({ template_id: newId, niche: src.niche, step: src.step, variant: src.variant, subject: src.subject, body: src.body, approved: false, approved_at: null, author: "aryan" });
  revalidatePath("/templates");
  redirect(`/templates?id=${newId}`);
}

export async function deleteTemplate(formData: FormData) {
  const id = String(formData.get("template_id") || "");
  if (!id) return;
  const supabase = await createClient();
  await supabase.from("templates").delete().eq("template_id", id);
  revalidatePath("/templates");
  redirect("/templates");
}

/** Approve is refused while any HARD rule fails (checked here, not only in the browser). */
export async function setTemplateApproved(_prev: Result, formData: FormData): Promise<Result> {
  const id = String(formData.get("template_id") || "");
  const approve = String(formData.get("approve") || "") === "1";
  const supabase = await createClient();
  if (approve) {
    const { data: t } = await supabase.from("templates").select("subject,body,step").eq("template_id", id).maybeSingle();
    if (!t) return { error: "template not found" };
    const { hard } = checkTemplate(t);
    if (hard.length) return { error: `cannot approve: ${hard.join("; ")}` };
  }
  const { error } = await supabase.from("templates").update({
    approved: approve, approved_at: approve ? new Date().toISOString() : null, author: "aryan",
  }).eq("template_id", id);
  if (error) return { error: error.message };
  revalidatePath("/templates");
  return { ok: approve ? "approved" : "approval removed" };
}
