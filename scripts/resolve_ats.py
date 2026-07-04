#!/usr/bin/env python3
"""Resolve a company to its public ATS board and return its jobs + real apply URLs.

Deterministic probe of known ATS slug patterns (no WebSearch, no guessing). Covers
Greenhouse, Ashby, Lever. Given a company name, returns which board it's on and the
live jobs with their real apply URLs — so the browser can navigate straight to the
real application page instead of fishing for it.

Usage:
  resolve_ats.py "Astronomer"
  resolve_ats.py "The Trade Desk"

Output JSON: {company, hits:[{ats, slug, board_url, jobs:[{title,location,applyUrl}]}]}
Empty hits = not found on these ATSes (try the company careers page in the browser,
or mark needs-human-start). Errors -> stderr {"error","code"}, exit 1.
"""
import json
import re
import sys
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def slugs(company):
    base = re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")
    out = [base, base.replace("-", "")]  # "the-trade-desk" and "thetradedesk"
    seen, uniq = set(), []
    for s in out:
        if s and s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def try_greenhouse(slug):
    code, body = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    if code != 200:
        return None
    try:
        jobs = json.loads(body).get("jobs", [])
    except Exception:
        return None
    if not jobs:
        return None
    return {
        "ats": "greenhouse", "slug": slug,
        "board_url": f"https://boards.greenhouse.io/{slug}",
        "jobs": [{"title": j.get("title"), "location": (j.get("location") or {}).get("name"),
                  "applyUrl": j.get("absolute_url")} for j in jobs],
    }


def try_ashby(slug):
    code, body = get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    if code != 200:
        return None
    try:
        jobs = json.loads(body).get("jobs", [])
    except Exception:
        return None
    if not jobs:
        return None
    return {
        "ats": "ashby", "slug": slug,
        "board_url": f"https://jobs.ashbyhq.com/{slug}",
        "jobs": [{"title": j.get("title"), "location": j.get("location"),
                  "applyUrl": j.get("applyUrl") or j.get("jobUrl"),
                  "jd": j.get("descriptionPlain", "")} for j in jobs],
    }


def try_lever(slug):
    code, body = get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    if code != 200:
        return None
    try:
        jobs = json.loads(body)
    except Exception:
        return None
    if not isinstance(jobs, list) or not jobs:
        return None
    return {
        "ats": "lever", "slug": slug,
        "board_url": f"https://jobs.lever.co/{slug}",
        "jobs": [{"title": j.get("text"), "location": (j.get("categories") or {}).get("location"),
                  "applyUrl": j.get("applyUrl") or (j.get("hostedUrl", "") + "/apply"),
                  "jd": j.get("descriptionPlain", "")} for j in jobs],
    }


def main():
    if len(sys.argv) < 2:
        sys.stderr.write(json.dumps({"error": "usage: resolve_ats.py <company>", "code": "USAGE"}) + "\n")
        sys.exit(1)
    company = sys.argv[1]
    hits = []
    for slug in slugs(company):
        for probe in (try_greenhouse, try_ashby, try_lever):
            if any(h["ats"] == probe.__name__.replace("try_", "") for h in hits):
                continue  # already found this ATS on an earlier slug
            r = probe(slug)
            if r:
                hits.append(r)
    print(json.dumps({"company": company, "hits": hits}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
