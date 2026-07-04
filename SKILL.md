---
name: job-apply
description: >-
  Job search, JD matching, and automated application filling assistant.
  Use when: finding jobs, job hunting, looking for positions, applying to jobs,
  submitting applications, matching JDs, recommending roles, auto-filling
  application forms, batch applying, helping someone else find jobs,
  evaluating job fit, or when a job posting URL or JD text is provided.
---

# Job Apply

End-to-end job search and application assistant: search JDs, score fit, extract application forms, auto-fill, and submit with user confirmation.

## Trigger Conditions

Activate on ANY of these intents:

- Job hunting / looking for a job / job search
- Help me find XX positions / find jobs in XX field
- Help [someone] find a job / help a friend submit resume
- Providing a target company link or careers page URL
- Providing a specific JD link or job description text
- I want to apply to XX company / I want to apply for this position
- Batch apply / mass apply / apply jobs
- Job matching / position recommendations / help me see if this role is a good fit
- Resume submission / submit application / auto apply

## Hard Prohibitions

1. **NEVER submit an application without explicit user confirmation** — "confirm submit" / "submit" / "go ahead" or user clicks submit in browser
2. Never fabricate user qualifications or work history
3. Never fill sensitive fields (SSN, bank info) without asking user first
4. Never skip the pre-submission review screenshot

## Workflow Overview

```
Trigger
  ↓
Pre-step: Obtain User Profile
  ↓
Module 1: JD Search + 6-Dimension Scoring
  ↓
User selects JD(s) to apply
  ↓
══ Per JD ══
Module 2: Form Extraction + Info Matching
  ↓
Module 3: Auto-Fill
  ↓
Module 4: Pre-Submit Confirmation (hard gate)
  ↓
Next JD (repeat 2→3→4)
```

## Pre-step: Obtain User Profile

Before entering any module, confirm user background:

1. Check memory for resume / profile / LinkedIn info
2. Check if user uploaded a resume PDF / portfolio
3. If neither found → ask user to provide resume or background summary
4. If user declines → continue with limitations:
   - Six-dimension scoring: Role Fit, Seniority Fit, Interview Likelihood → **N/A**
   - Only score: Salary Competitiveness, Location Feasibility, Company Stage Fit
   - More form fields will need manual input later

For "help someone else find a job" scenarios: confirm whose profile to use → request that person's resume/info.

## Module 1: JD Search + 6-Dimension Scoring

Load `references/jd-scoring.md` for the full scoring rubric and output format.

### Entry Routing

| User Input | Action |
|---|---|
| Vague intent ("help me find a job") | Ask for direction/industry/location preferences, then search |
| With conditions ("find AI PM, US remote") | Search directly |
| Company/careers page URL | Open page with browser, extract JD list |
| Specific JD URL | Skip search → score directly |
| JD text pasted | Skip search → score directly |
| Finding for someone else | Confirm target person's profile source, then same flow |

### Search Strategy: LinkedIn Script (Primary) + Web Search (Fallback)

**Primary: LinkedIn public endpoint via bundled script (no login, no browser)**

Use the bundled `scripts/linkedin_jobs.py` to search LinkedIn's public `jobs-guest` endpoints. This returns structured JSON data (job ID, title, company, location, posting date, URL) — much faster and more reliable than parsing web search results.

```bash
# Search for jobs
python3 scripts/linkedin_jobs.py search -q "<role keywords>" -l "<location>" \
  --jobage 7 --limit 20

# Get full JD detail for a specific job
python3 scripts/linkedin_jobs.py detail <jobId>
```

**Key parameters:**
- `--jobage 1|7|14|30` — filter by posting recency (days). Use 7 as default.
- `--remote remote|hybrid|onsite` — filter by workplace type
- `--explevel 1|2|3|4` — 1=Internship, 2=Entry, 3=Associate, 4=Mid-Senior
- `--title-include "keyword1,keyword2"` — keep only matching titles
- `--title-exclude "senior,director,marketing"` — drop irrelevant titles
- `--page N` — paginate results (10 per page)

**LinkedIn search tips:**
- One well-filtered query beats ten unfiltered ones. Use `--title-include` and `--title-exclude` to denoise.
- Results are sorted newest-first by posting date (freshness).
- `detail <id>` returns full JD description + criteria + apply type (Easy Apply vs offsite/external ATS).

**Company-specific search via ATS boards:**

For a known target company, also try `scripts/resolve_ats.py "<company>"` to directly probe its public ATS board (Greenhouse/Ashby/Lever). This returns all live postings with real apply URLs — no browser needed.

```bash
python3 scripts/resolve_ats.py "Stripe"
# Returns: {company, hits:[{ats, slug, board_url, jobs:[{title,location,applyUrl}]}]}
```

**Fallback: Web Search**

Use web search as fallback when:
- LinkedIn script returns no results or errors (endpoint may rate-limit or change)
- User is looking for roles on platforms not covered by LinkedIn (government jobs, niche boards)
- User provides a company name and `resolve_ats.py` finds no ATS board — use web search to find the company's careers page URL, then open it with Playwright to extract listings

**Important constraints:**
- The LinkedIn script is **search-only** — it cannot log in, apply, or interact with LinkedIn in any way.
- Keep volume low (personal use). The script backs off automatically on 429/5xx errors.
- Do NOT open a browser or try to log in to LinkedIn for search — the guest endpoints need neither.

### Scoring

1. For each discovered JD, get the full detail (via `linkedin_jobs.py detail` or by reading the JD page)
2. Score each JD on 6 dimensions (1.0–5.0) per `references/jd-scoring.md`
3. Output ranked JD list with scores + brief assessment
4. Wait for user to select which JD(s) to apply to

## Module 2: Form Extraction + Info Matching

For each selected JD, use a **dual-channel approach**: ATS API first (fast, no browser), Playwright as fallback.

### Step 1: Identify ATS Platform

Determine the ATS from the application URL:

| ATS | URL Pattern | Has Public API? |
|---|---|---|
| Greenhouse | `boards.greenhouse.io`, `job-boards.greenhouse.io` | ✅ Yes — full form fields via API |
| Lever | `jobs.lever.co` | ✅ Partial — standard fields only, custom questions need browser |
| Ashby | `jobs.ashbyhq.com` | ✅ Yes — job listings via API |
| Workday | `*.myworkdayjobs.com` | ❌ No — browser only |
| Rippling | `*.rippling.com/careers` | ❌ No — browser only |
| Other | varies | ❌ No — browser only |

### Step 2A: API Fast Path (Greenhouse / Lever / Ashby)

If the application URL is on Greenhouse, Lever, or Ashby, use `scripts/ats_form.py` to extract form fields **without launching a browser**:

```bash
# Pass the application URL directly
python3 scripts/ats_form.py <greenhouse-or-lever-url>

# Or specify ATS + identifiers explicitly
python3 scripts/ats_form.py greenhouse <board_token> <job_id>
python3 scripts/ats_form.py lever <company> <posting_id>
```

**Output:** JSON with `{ats, title, company, location, applyUrl, jd, fields:[{label, required, type, options}], note}`

**Platform-specific notes:**
- **Greenhouse**: Returns the FULL form — every field, required flag, type, and dropdown options. This is the source of truth; no need for browser.
- **Lever**: Public API returns only standard fields (name, email, resume, phone, links). Custom application questions are NOT exposed via API. If the `note` field indicates custom questions exist, you will need Playwright in Module 3 to see and fill those fields.
- **Ashby**: Job listing data available via API; for the actual application form, open in browser.

After API extraction, proceed to **Step 3: Match fields**.

### Step 2B: Browser Path (Workday / Rippling / Other / API failure)

If the ATS has no public API, or if the API call fails, fall back to Playwright:

1. **Open application page** with Playwright browser
2. Load `references/form-extraction.md` for platform-specific DOM extraction guidance
3. **Scan DOM** to extract all form fields
4. **Login/auth gate**: if the page requires login or other user action before form is accessible:
   - Tell user exactly what action is needed (e.g. "Please log in to your account")
   - Call `request_human_help` to hand over browser control
   - Wait for user to complete, then resume extraction

### Step 3: Match fields against user profile

Regardless of which path was used (API or browser):

1. **Match fields** against user profile:
   - Matched → mark as ready to fill
   - Missing → list all missing fields for user
2. User chooses:
   - Provide missing info → continue
   - Skip → fill what's available, leave gaps for manual input

## Module 3: Auto-Fill

Using extracted fields from Module 2 + matched user info:

1. **Open the application page in Playwright** (even if form fields were extracted via API, filling must happen in the browser)
2. **Semantic mapping**: understand each field's intent → match to user data → fill
3. **Uncertainty protocol** — when unsure:
   - Multiple-choice with unclear answer → screenshot options + ask user
   - Open-ended questions (e.g. "Why do you want to work here?") → draft answer, show to user, fill only after confirmation
   - Ambiguous fields (e.g. "Expected start date") → ask directly
4. **Resume upload**: if form has file upload and user provided resume PDF → upload it
5. Fill fields using browser tools (type, select, click)

## Module 4: Pre-Submit Confirmation (HARD GATE)

After filling is complete:

1. **Take full-page screenshot** of the completed form → send to user for review
2. **Hand over browser** via `request_human_help` so user can:
   - Inspect the form in the browser
   - Manually edit or fill empty fields
   - Submit themselves if preferred
3. **Wait for explicit confirmation** — one of:
   - User says: "confirm submit" / "submit" / "go ahead" / "looks good"
   - User submits via browser themselves
4. ❌ **NO confirmation signal → DO NOT submit. Ever.**
5. On confirmation → click submit button
6. Confirm submission success → screenshot confirmation page → inform user

Then proceed to next JD if batch applying.

## Validation Checklist

Before completing any application cycle, verify:

- [ ] User profile was checked/obtained before scoring
- [ ] All 6 dimensions scored (or marked N/A with reason)
- [ ] Form fields fully extracted before filling began
- [ ] User was notified of all missing/unmatched fields
- [ ] Uncertain fields were confirmed with user before filling
- [ ] Pre-submission screenshot was sent to user
- [ ] Browser handover was offered
- [ ] Explicit confirmation received before any submission
- [ ] Post-submission confirmation screenshot sent
