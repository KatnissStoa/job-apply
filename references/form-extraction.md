# Form Extraction Guide

This reference covers **browser-based form extraction** (Step 2B in Module 2). Use this when the ATS has no public API, or when the API path fails/returns incomplete data.

For Greenhouse/Lever with public API, prefer `scripts/ats_form.py` first (see Module 2, Step 2A in SKILL.md).

## ATS Platform Detection

Identify the ATS by checking page URL patterns and DOM structure:

| ATS | URL Pattern | DOM Signals |
|---|---|---|
| Greenhouse | `boards.greenhouse.io`, `job-boards.greenhouse.io` | `#grnhse_app`, `.grnhse-iframe` |
| Ashby | `jobs.ashbyhq.com`, `*.ashbyhq.com` | `ashby-job-posting-widget` |
| Lever | `jobs.lever.co` | `.lever-application-form` |
| Workday | `*.myworkdayjobs.com`, `*.wd5.myworkdayjobs.com` | `[data-automation-id]` elements |
| Rippling | `*.rippling.com/careers` | Rippling-specific form containers |
| Custom / Other | varies | Standard HTML forms |

## Extraction Strategy

### Step 1: Wait for page load

- Wait for DOM content loaded
- If Greenhouse: check for iframe — may need to access iframe content
- If SPA: wait for form elements to render (up to 10s)

### Step 2: Extract form fields

For each form field, capture:

1. **Field name/label** — the visible label text
2. **Field type** — text, email, phone, textarea, select, radio, checkbox, file upload
3. **Required status** — check for `required` attribute, `*` in label, or aria-required
4. **Options** — for select/radio/checkbox, list all available options
5. **Placeholder text** — may contain format hints
6. **Current value** — if pre-filled

### Step 3: Categorize fields

Group extracted fields into:

- **Personal info**: name, email, phone, address, LinkedIn URL
- **Professional info**: current company, title, years of experience
- **Education**: degree, school, graduation year
- **Documents**: resume/CV upload, cover letter, portfolio
- **Job-specific**: salary expectation, start date, visa/work authorization, relocation
- **Open questions**: "Why this role?", "Tell us about yourself", custom questions
- **Demographics**: gender, race, veteran status, disability (mark as optional/voluntary)
- **Legal**: work authorization, NDA acknowledgment

### Common Field Mappings

| Form Field (various labels) | User Profile Key |
|---|---|
| First Name | user.first_name |
| Last Name | user.last_name |
| Email | user.email |
| Phone | user.phone |
| LinkedIn, LinkedIn URL | user.linkedin |
| Current Company | user.current_company |
| Current Title | user.current_title |
| Resume, CV | user.resume_file |
| Location, City | user.location |
| Portfolio, Website | user.portfolio_url |

### Platform-Specific Notes

**Greenhouse:**
- Forms often inside an iframe — use `browser_evaluate` to access iframe content if needed
- Custom questions appear after standard fields
- File upload uses a dropzone component
- **Tip**: If browser extraction is flaky, try `scripts/ats_form.py <url>` as a cross-check — it returns every field with type, required flag, and dropdown options via API.

**Lever:**
- Clean form layout, usually single-page
- "Additional information" section contains custom questions
- Resume parsing may auto-fill some fields
- **Note**: `scripts/ats_form.py` only returns standard Lever fields (name/email/resume/phone/links). Custom questions must be extracted via browser.

**Workday:**
- Multi-page forms — need to navigate through pages
- Uses `data-automation-id` attributes for field identification
- May require account creation first → trigger login gate
- No public API — browser is the only option
- **Warning**: Workday's Agent Passport detects unauthorized automation. Never automate a Workday submission — always hand over to user.

**Ashby:**
- Modern SPA, fields render dynamically
- Custom questions integrated inline
- File upload via drag-and-drop or click

## Login/Auth Gate Protocol

If the form requires authentication before access:

1. Take screenshot of the login/auth page
2. Inform user: "This application page requires login/registration first. Please complete the login in the browser, then let me know when you're done."
3. Call `request_human_help` to hand over browser
4. After user confirms completion → take new snapshot → verify form is accessible
5. If still blocked → repeat or suggest alternative approach
