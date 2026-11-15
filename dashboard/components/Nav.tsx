"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/", label: "Today" },
  { href: "/leads", label: "Leads" },
  { href: "/markets", label: "Markets" },
  { href: "/runs", label: "Runs & Logs" },
  { href: "/settings", label: "Settings" },
];

export default function Nav({ email }: { email: string }) {
  const path = usePathname();
  return (
    <nav className="flex flex-wrap items-center gap-1 text-sm">
      {ITEMS.map((it) => {
        const active = it.href === "/" ? path === "/" : path.startsWith(it.href);
        return (
          <Link key={it.href} href={it.href}
            className={`rounded-md px-3 py-1.5 transition-colors ${active ? "bg-panel2 text-accent" : "text-muted hover:text-text"}`}>
            {it.label}
          </Link>
        );
      })}
      <form action="/auth/signout" method="post" className="ml-auto flex items-center gap-2">
        <span className="hidden sm:inline text-xs text-muted">{email}</span>
        <button className="btn !py-1 text-xs">Sign out</button>
      </form>
    </nav>
  );
}
