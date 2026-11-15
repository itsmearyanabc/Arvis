export type Market = {
  market_id: string; country: string; city: string; niche: string;
  businesses_found: number | null; opportunity_score: number | null; rationale: string | null;
  status: "proposed" | "active" | "paused" | "done";
  last_scraped_at: string | null; created_at: string | null;
};

export type Lead = {
  lead_id: string; place_id: string | null; market_id: string | null;
  business_name: string; niche: string | null; city: string | null; country: string | null; address: string | null;
  phone: string | null; website: string | null; rating: number | null; review_count: number | null;
  maps_url: string | null; instagram_url: string | null; linkedin_url: string | null; facebook_url: string | null;
  source: string; fit_score: number | null; ticket_score: number | null;
  contact_quality: "named" | "generic" | "none" | null;
  primary_email: string | null; email_source: string | null; runs_meta_ads: boolean | null;
  top_issue: string | null; audit_summary: string | null; status: string;
  parked_reason: string | null; approved_by_aryan: boolean | null; notes: string | null;
  scraped_at: string | null; updated_at: string | null;
};

export type Audit = {
  audit_id: string; lead_id: string; website: string | null; checked_at: string | null;
  site_status: string | null; ssl_ok: boolean | null; https_redirect: boolean | null;
  mobile_score: number | null; perf_score: number | null; lcp_s: number | null; cms: string | null;
  copyright_year: number | null; looks_outdated: boolean | null; has_title: boolean | null;
  has_meta_desc: boolean | null; h1_count: number | null; img_alt_missing_pct: number | null;
  broken_links_sampled: number | null; contact_email_on_site: boolean | null; contact_form: boolean | null;
  booking_widget: boolean | null; meta_pixel: boolean | null; google_tag: boolean | null;
  top_issue: string | null; audit_summary: string | null;
};

export type Contact = {
  contact_id: string; lead_id: string; contact_name: string | null; role: string | null;
  email: string | null; email_status: string | null; email_source: string | null;
  contact_quality: string | null; phone: string | null; verified_at: string | null; verifier: string | null;
};

export type WorkerRun = {
  run_id: string; worker: string; started_at: string; finished_at: string | null;
  status: string; input: Record<string, unknown> | null; counts: Record<string, unknown> | null; error: string | null;
};

export type BrainSource = "brain" | "scrape" | "audit" | "mirror" | "telegram";
export type BrainEvent = {
  id: number; ts: string; source: BrainSource; level: "debug" | "info" | "warn" | "error";
  message: string; data: Record<string, unknown> | null;
};

export const LEAD_STATUSES = ["new","audited","verified","parked","drafted","in_sequence","replied","booked","won","lost","unsubscribed"] as const;
export const BRAIN_SOURCES: BrainSource[] = ["brain", "scrape", "audit", "mirror", "telegram"];
