# ARVIS Google Sheet — tabs and columns

One spreadsheet (`GOOGLE_SHEET_ID`), shared with the service-account email as Editor. Row 1 =
headers exactly as below. ARVIS appends/updates by `*_id`; Aryan edits freely (`approved_by_aryan`,
`status`, notes). Later a one-way push copies tabs into ARVIS's own Supabase project.

Common conventions: timestamps ISO-8601 with tz; booleans `TRUE`/`FALSE`; scores 0–100 integers;
`source` ∈ `google_maps | website | web_search | hunter | manual | referral | inbound`;
`contact_quality` ∈ `named | generic | none`.

## Markets
| column | type | notes |
|---|---|---|
| market_id | text | `mk_<slug>` |
| country, city, niche | text | |
| businesses_found | int | from probe / last scrape |
| pct_no_website, pct_high_ticket | number | 0–100 |
| agency_count | int | saturation proxy |
| opportunity_score | int | 0–100 |
| rationale | text | one line |
| status | enum | proposed · active · paused · done |
| last_scraped_at, created_at | datetime | |

## Leads
| column | type | notes |
|---|---|---|
| lead_id | text | `ld_<yyyymmdd>_<n>` |
| place_id | text | Google Maps id, dedup key |
| business_name, niche, city, country, address | text | |
| phone | text | owner/business phone from Maps |
| website | url | |
| rating | number | |
| review_count | int | |
| maps_url, instagram_url, linkedin_url, facebook_url | url | social URLs stored for Aryan only, never automated |
| source | enum | |
| fit_score | int | 0–100 |
| ticket_score | int | 0–100 (reviews, rating, ads, site issues) |
| contact_quality | enum | named · generic · none |
| primary_email | text | best verified email (from Contacts) |
| runs_meta_ads | bool | Meta Ad Library public check |
| top_issue, audit_summary | text | from Audits |
| status | enum | new · audited · verified · parked · drafted · in_sequence · replied · booked · won · lost · unsubscribed |
| parked_reason | text | no_email · invalid_only · consumer · chain · duplicate |
| approved_by_aryan | bool | optional per-lead veto; FALSE blocks drafting |
| notes | text | Aryan's |
| scraped_at, updated_at | datetime | |

## Audits
| column | type |
|---|---|
| audit_id, lead_id | text |
| website | url |
| checked_at | datetime |
| site_status | enum: ok · down · no_site |
| ssl_ok, https_redirect | bool |
| mobile_score, perf_score | int |
| lcp_s | number |
| cms | text |
| copyright_year | int |
| looks_outdated | bool |
| has_title, has_meta_desc | bool |
| h1_count | int |
| img_alt_missing_pct | number |
| broken_links_sampled | int |
| contact_email_on_site, contact_form, booking_widget | bool |
| meta_pixel, google_tag | bool |
| top_issue | text |
| audit_summary | text (≤ 2 sentences, factual) |

## Contacts
| column | type |
|---|---|
| contact_id, lead_id | text |
| contact_name, role | text |
| email | text |
| email_status | enum: safe · risky · invalid · unknown |
| email_source | enum: website · maps · web_search · hunter · pattern · manual |
| contact_quality | enum: named · generic · none |
| phone | text |
| verified_at | datetime |
| verifier | enum: reacher · hunter |

## Templates
| column | type |
|---|---|
| template_id | text, e.g. `default_v1`, `dentist_v1` |
| niche | text or `default` |
| step | int 1–3 |
| subject | text (step 1 only) |
| body | text with placeholders |
| variant | enum: issue · no_issue |
| approved | bool (Aryan) |
| author, approved_at | text, datetime |
| replies_7d, sends_7d | int (filled by daily-report) |

## Sequences
| column | type |
|---|---|
| sequence_id, lead_id, contact_id | text |
| contact_email | text |
| template_id | text |
| mailbox | text (`MAILBOX_n` user) |
| step1_subject, step1_body, step2_body, step3_body | text |
| status | enum: draft · approved · step1_sent · step2_sent · step3_sent · done_no_reply · stopped_reply · stopped_unsub · bounced · snoozed · expired · skipped |
| approved_by_aryan | bool |
| approved_at, drafted_at | datetime |
| step1_sent_at, step2_sent_at, step3_sent_at | datetime |
| message_id | text (step 1 Message-ID for threading) |
| resume_at | datetime (snoozed) |
| edit_note | text (Aryan's "edit <id>: …") |

## Replies
| column | type |
|---|---|
| reply_id, sequence_id, lead_id | text |
| mailbox, from_email | text |
| received_at | datetime |
| category | enum: interested · question · not_now · not_interested · unsubscribe · auto_reply · bounce · wrong_person · spam_complaint · other |
| reply_summary | text ≤ 25 words |
| suggested_action | text |
| telegram_alerted | bool |
| handled_by_aryan | bool |
| handled_at | datetime |

## Unsubscribes
| column | type |
|---|---|
| email, domain | text |
| reason | enum: request · bounce · complaint · manual |
| added_at | datetime |
| source_reply_id | text |

## Bookings
| column | type |
|---|---|
| booking_id, lead_id, calcom_uid | text |
| attendee_name, attendee_email | text |
| start_at, tz | datetime, text |
| source | enum: cold_email · referral · inbound |
| status | enum: booked · rescheduled · cancelled · held |
| brief_sent_at | datetime |
| outcome | enum: won · proposal · lost · no_show · reschedule · (blank) |
| notes | text |

## Mailboxes
| column | type |
|---|---|
| mailbox | text (`MAILBOX_n`) |
| address, from_name | text |
| domain | text (never armedias.com / .tech) |
| daily_cap | int |
| warmup_until | date |
| paused | bool |
| sent_today, bounces_7d | int |

## Monitors
| column | type |
|---|---|
| monitor_id, kuma_id | text |
| name, url | text |
| type | enum: http · keyword · ping |
| interval_s | int |
| owner | text: `us` or `client:<name>` |
| status | enum: up · down · pending |
| last_down_at, ssl_expires_at | datetime |
| uptime_7d_pct | number |
| avg_response_ms | int |

## Reports
`date, scraped, audited, verified, drafts_pending, sent, bounced, unsub, replied, interested,
booked, reply_rate_7d, booking_rate_7d, issues`
