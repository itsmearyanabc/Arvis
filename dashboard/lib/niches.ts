/** Mirror of workers/common/niches.py. Keep both in sync. */
export const GROUPS: Record<string, Record<string, string[]>> = {
  Healthcare: {
    dentist: ["dentist", "dental clinic", "orthodontist"],
    physiotherapy: ["physiotherapy clinic", "physiotherapist", "chiropractor"],
    "cosmetic clinic": ["cosmetic clinic", "medical spa", "dermatology clinic"],
  },
  "Legal & Finance": {
    "law firm": ["law firm", "lawyer", "solicitor"],
    "accounting firm": ["accounting firm", "chartered accountant", "tax advisor"],
  },
  Property: {
    "real estate": ["real estate agency", "realtor", "estate agent"],
    "interior design": ["interior designer", "interior design studio", "architect"],
  },
  "Home Services": {
    roofing: ["roofing contractor", "roofer"],
    hvac: ["hvac contractor", "air conditioning repair", "heating company"],
    renovation: ["renovation contractor", "kitchen remodeling", "general contractor"],
  },
  "Hospitality & Wellness": {
    "boutique hotel": ["boutique hotel", "bed and breakfast"],
    gym: ["gym", "fitness studio", "yoga studio"],
  },
  Education: {
    "private school": ["private school", "international school", "tutoring center"],
  },
};

export const GROUP_NAMES = Object.keys(GROUPS);
export const ALL_NICHES = GROUP_NAMES.flatMap((g) => Object.keys(GROUPS[g]));

export const NICHE_TO_GROUP: Record<string, string> = Object.fromEntries(
  GROUP_NAMES.flatMap((g) => Object.keys(GROUPS[g]).map((n) => [n, g])),
);

export function groupOf(niche: string | null | undefined): string {
  return NICHE_TO_GROUP[(niche || "").toLowerCase()] ?? "Other";
}

export function nichesOf(group: string): string[] {
  return Object.keys(GROUPS[group] ?? {});
}

/** Same as seed_markets.py: mk_<country[:2]>_<city>_<niche>. */
export function slug(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}
export function marketId(country: string, city: string, niche: string): string {
  return `mk_${slug(country).slice(0, 2)}_${slug(city)}_${slug(niche)}`;
}
