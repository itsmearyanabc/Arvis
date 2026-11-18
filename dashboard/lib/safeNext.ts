/** Only allow same-site relative paths after login ("/leads?x=1"). Blocks "//evil.com", "/\\evil.com",
 *  "https://..." and anything else that would leave the dashboard (open-redirect / phishing). */
export function safeNext(next: string | null | undefined): string {
  const n = (next ?? "").trim();
  if (!n.startsWith("/") || n.startsWith("//") || n.startsWith("/\\") || /[\u0000-\u001f]/.test(n)) return "/";
  return n;
}
