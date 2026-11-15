import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import Nav from "@/components/Nav";
import BrainCanvas from "@/components/BrainCanvas";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  return (
    <div className="mx-auto max-w-7xl px-4 pb-10">
      <header className="sticky top-0 z-20 -mx-4 mb-4 border-b border-line bg-bg/80 px-4 backdrop-blur">
        <div className="flex items-center gap-3 py-2">
          <div className="h-12 w-28 shrink-0 overflow-hidden rounded-lg border border-line bg-panel sm:w-40">
            <BrainCanvas compact />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline gap-2">
              <span className="font-semibold tracking-wide">ARVIS</span>
              <span className="text-xs text-muted">operating panel</span>
            </div>
            <Nav email={user.email ?? ""} />
          </div>
        </div>
      </header>
      {children}
    </div>
  );
}
