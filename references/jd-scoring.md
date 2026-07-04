# JD 6-Dimension Scoring Rubric

## Dimensions

| # | Dimension | What to Evaluate | Requires Resume? |
|---|---|---|---|
| 1 | Role Fit | Overlap between user's skill stack and JD requirements | ✅ |
| 2 | Seniority Fit | Years of experience, job level alignment | ✅ |
| 3 | Salary Competitiveness | JD salary range vs user's target salary | ❌ |
| 4 | Location Feasibility | Remote policy, commute/relocation fit | ❌ |
| 5 | Company Stage Fit | Startup/mid/large company vs user preference | ❌ |
| 6 | Interview Likelihood | Profile strength → predicted chance of getting interview | ✅ |

## Scoring Scale

- **5.0** — Perfect fit, no gaps
- **4.0** — Strong fit, minor gaps
- **3.0** — Moderate fit, some notable gaps
- **2.0** — Weak fit, significant misalignment
- **1.0** — Poor fit, major blockers
- **N/A** — Cannot evaluate (missing user data)

## Scoring Rules

### 1. Role Fit

Compare user's skills, tools, and domain experience against JD requirements:

- 5.0: ≥90% of required skills matched, bonus skills present
- 4.0: 70–89% matched, missing skills are learnable
- 3.0: 50–69% matched, some core requirements missing
- 2.0: 30–49% matched, multiple core gaps
- 1.0: <30% matched, fundamentally different skill set

### 2. Seniority Fit

Compare user's experience level with JD requirements:

- 5.0: Experience years and level match exactly
- 4.0: Within 1 year or 1 level of requirement
- 3.0: 2–3 years or levels off, but compensating factors exist
- 2.0: Significantly over/under-qualified
- 1.0: Extreme mismatch (entry-level vs director)

### 3. Salary Competitiveness

If JD shows salary range and user has a target:

- 5.0: User's target is within or below the offered range
- 4.0: Target slightly above range (≤10% over)
- 3.0: Target moderately above (10–25% over)
- 2.0: Target significantly above (25–50% over)
- 1.0: Target far above range (>50% over)
- N/A: No salary info available in JD or from user

### 4. Location Feasibility

- 5.0: Fully remote or user already in the location
- 4.0: Hybrid with reasonable commute, or willing to relocate
- 3.0: Requires relocation but user is open to it
- 2.0: Requires relocation, user preference unclear
- 1.0: Location is a hard blocker (visa issues, unwilling to move)

### 5. Company Stage Fit

- 5.0: Company stage matches user's stated preference exactly
- 4.0: Close match (e.g. wants mid-stage, company is late-stage startup)
- 3.0: No strong preference stated, neutral
- 2.0: Misaligned (wants startup but company is Fortune 500)
- 1.0: Strong mismatch with stated hard preference

### 6. Interview Likelihood

Holistic assessment combining all factors:

- 5.0: Very likely — strong profile match, in-demand background
- 4.0: Likely — good match, competitive but viable
- 3.0: Possible — decent match but competitive market
- 2.0: Unlikely — significant gaps or very competitive role
- 1.0: Very unlikely — major blockers present

## Output Format

For each JD, output a table row:

```
### [Position Title] @ [Company]
📍 Location | 💰 Salary range (if available) | 🏢 Company stage

| Dimension | Score | Note |
|---|---|---|
| Role Fit | X.X | [brief reason] |
| Seniority Fit | X.X | [brief reason] |
| Salary Competitiveness | X.X | [brief reason] |
| Location Feasibility | X.X | [brief reason] |
| Company Stage Fit | X.X | [brief reason] |
| Interview Likelihood | X.X | [brief reason] |
| **Overall** | **X.X** | [1-sentence summary] |

🔗 [Apply](application_url)
```

**Overall** = weighted average: Role Fit × 0.25 + Seniority Fit × 0.20 + Interview Likelihood × 0.20 + Salary Competitiveness × 0.15 + Location Feasibility × 0.10 + Company Stage Fit × 0.10

When some dimensions are N/A, redistribute weights proportionally among scored dimensions.

Sort results by Overall score descending.
